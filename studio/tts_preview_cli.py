"""Explicit local-only voice preview CLI; never issues Voice Lock."""
import argparse
import asyncio
import json
from pathlib import Path
from studio.tts_providers import VoiceRequest, available_providers, synthesize_preview

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="A NEW preview directory")
    parser.add_argument("--provider", default="edge")
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    parser.add_argument("--rate", default="+0%")
    parser.add_argument("--confirm-network-call", action="store_true")
    args = parser.parse_args()
    if not args.confirm_network_call:
        parser.error("Explicit --confirm-network-call required (TTS uses an online service)")
    text = args.text_file.read_text(encoding="utf-8").strip()
    manifest = asyncio.run(synthesize_preview(
        VoiceRequest(text=text, voice=args.voice, rate=args.rate),
        args.output, provider=args.provider))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
