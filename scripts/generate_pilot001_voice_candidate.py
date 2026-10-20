#!/usr/bin/env python3
"""Pilot 001 XiaoxiaoNeural listening candidate; NEVER issues Voice Lock."""
import argparse
import asyncio
import hashlib
import json
import shutil
import subprocess
import wave
from pathlib import Path

SCRIPT = [
    ("intro", "两张订单，同时下单。", 0.0, 3.3),
    ("out_of_stock", "库存不足，订单B等待补货。", 5.90, 9.4),
    ("in_stock", "库存充足，订单A发货。", 9.55, 12.9),
]
SAMPLE_RATE = 22050
TOTAL_SECONDS = 13.0

def command(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

async def generate(out, rate):
    import edge_tts
    out.mkdir(parents=True, exist_ok=False)
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is required")
    chunks = []
    for n, (sid, text, start, deadline) in enumerate(SCRIPT, 1):
        mp3 = out / f"{n:02d}_{sid}.mp3"
        wav = out / f"{n:02d}_{sid}.wav"
        await edge_tts.Communicate(text, voice="zh-CN-XiaoxiaoNeural", rate=rate).save(str(mp3))
        command("ffmpeg", "-v", "error", "-y", "-i", str(mp3),
                "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(wav))
        with wave.open(str(wav), "rb") as f:
            if f.getframerate() != SAMPLE_RATE or f.getnchannels() != 1 or f.getsampwidth() != 2:
                raise RuntimeError("Unexpected WAV format")
            data = f.readframes(f.getnframes())
        duration = len(data) / (2 * SAMPLE_RATE)
        if start + duration > deadline:
            raise RuntimeError(f"{sid}: voice ends at {start+duration:.3f}s; cue deadline {deadline:.3f}s. "
                               "Candidate invalid; do not adjust locked cue without new Script Lock approval.")
        chunks.append((sid, text, start, duration, data, mp3, wav))
    output = bytearray(int(TOTAL_SECONDS * SAMPLE_RATE) * 2)
    segments = []
    for sid, text, start, duration, data, mp3, wav in chunks:
        pos = round(start * SAMPLE_RATE) * 2
        if pos + len(data) > len(output) or any(output[pos:pos+len(data)]):
            raise RuntimeError("Audio overlaps or exceeds video duration")
        output[pos:pos+len(data)] = data
        segments.append({"id": sid, "text": text, "start": start, "end": round(start + duration, 4)})
    final = out / "voice_candidate.wav"
    with wave.open(str(final), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(output)
    (out / "timings_candidate.json").write_text(
        json.dumps({"duration": TOTAL_SECONDS, "segments": segments,
                    "status": "candidate_unapproved"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (out / "candidate_manifest.json").write_text(
        json.dumps({"voice_id": "zh-CN-XiaoxiaoNeural", "rate": rate,
                    "status": "candidate_unapproved", "approved": False, "voice_lock": None,
                    "audio_sha256": sha256(final),
                    "timings_sha256": sha256(out / "timings_candidate.json")},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("CANDIDATE ONLY:", final)
    print("Review each sentence, pacing, silence, and event alignment before approving Voice Lock.")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--rate", default="-5%", help="Edge TTS prosody rate (default -5%%)")
    args = p.parse_args()
    if not args.rate.endswith("%"):
        p.error("--rate must be an Edge TTS percentage")
    asyncio.run(generate(args.out, args.rate))

if __name__ == "__main__":
    main()
