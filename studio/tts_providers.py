"""Pre-Voice-Lock TTS provider boundary. No approvals, locked media or paid fallbacks."""
from __future__ import annotations
import asyncio
import dataclasses
import hashlib
import json
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Protocol

DEFAULT_PROVIDER = "edge"
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

class TTSError(RuntimeError):
    pass

@dataclasses.dataclass(frozen=True)
class VoiceRequest:
    text: str
    voice: str = DEFAULT_VOICE
    rate: str = "+0%"

class Provider(Protocol):
    name: str
    async def synthesize(self, request: VoiceRequest, output: Path) -> None: ...

class EdgeProvider:
    name = "edge"
    async def synthesize(self, request: VoiceRequest, output: Path) -> None:
        try:
            import edge_tts
        except ImportError as exc:
            raise TTSError("edge-tts not installed") from exc
        await edge_tts.Communicate(request.text, request.voice, rate=request.rate).save(str(output))

_PROVIDERS: dict[str, Provider] = {"edge": EdgeProvider()}

def register_provider(provider: Provider) -> None:
    if not provider.name or not provider.name.isidentifier():
        raise ValueError("Invalid provider name")
    if provider.name in _PROVIDERS:
        raise ValueError("Provider already registered")
    _PROVIDERS[provider.name] = provider

def available_providers() -> tuple[str, ...]:
    return tuple(sorted(_PROVIDERS))

def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()

async def synthesize_preview(request: VoiceRequest, destination: Path, *,
                             provider: str = DEFAULT_PROVIDER,
                             ffmpeg: str = "ffmpeg") -> dict:
    """Create *new* standalone preview in a non-existing directory.

    Destination is explicitly a new preview folder, NEVER the project's locked
    voice/timing directory. Caller must approve and separately promote artifacts.
    """
    if not request.text.strip() or len(request.text) > 5000:
        raise ValueError("Expected 1..5000 characters of narration")
    if not request.voice.strip() or "\\x00" in request.voice:
        raise ValueError("Invalid voice")
    if provider not in _PROVIDERS:
        raise TTSError(f"Unsupported TTS provider: {provider}; no fallback")
    destination = Path(destination)
    if destination.is_symlink() or destination.exists():
        raise FileExistsError("Preview destination must be new")
    # Refuse obvious formal locked-media targets even if called directly.
    if destination.name in {"media", "approvals", "stage_d"}:
        raise ValueError("Refusing reserved production output directory")
    if shutil.which(ffmpeg) is None:
        raise TTSError("ffmpeg is required for PCM WAV normalization")
    # Network/provider operation occurs only after explicit CLI/user invocation.
    with tempfile.TemporaryDirectory(prefix="mg-tts-") as temp:
        raw = Path(temp) / "generated.audio"
        wav = Path(temp) / "voice.wav"
        try:
            await _PROVIDERS[provider].synthesize(request, raw)
        except Exception as exc:
            raise TTSError(f"{provider} synthesis failed ({type(exc).__name__})") from exc
        if not raw.is_file() or raw.stat().st_size == 0:
            raise TTSError("Provider returned empty audio")
        try:
            subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
                            "-y", "-i", str(raw), "-vn", "-ac", "1", "-ar", "22050",
                            "-c:a", "pcm_s16le", str(wav)],
                           check=True, capture_output=True, timeout=90)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise TTSError("Audio normalization failed") from exc
        with wave.open(str(wav), "rb") as w:
            if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, 22050):
                raise TTSError("Normalized audio format is invalid")
            duration = w.getnframes() / w.getframerate()
        if not 0 < duration <= 600:
            raise TTSError("Invalid audio duration")
        manifest = {"status": "preview_only", "provider": provider, "voice": request.voice,
                    "text_sha256": hashlib.sha256(request.text.encode("utf-8")).hexdigest(),
                    "raw_sha256": _digest(raw), "wav_sha256": _digest(wav),
                    "duration_seconds": duration, "timestamps": "not_provided",
                    "voice_lock": False}
        destination.mkdir(parents=True, exist_ok=False)
        try:
            shutil.copy2(raw, destination / "original.audio")
            shutil.copy2(wav, destination / "voice.wav")
            (destination / "manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
        except Exception:
            shutil.rmtree(destination)
            raise
        return manifest
