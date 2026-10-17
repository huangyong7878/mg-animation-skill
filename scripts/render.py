"""CLI for deterministic MG JSON -> PNG / MP4. FFmpeg required for video."""
import argparse
import subprocess
import sys
import time
from pathlib import Path
from engine import Renderer, load
from validate import validate


def main():
    ap=argparse.ArgumentParser(description='MG Infographic Skill 2.0 renderer')
    ap.add_argument('scene',help='Scene JSON path')
    ap.add_argument('--out',help='MP4 or PNG path; default output/<input>.mp4')
    ap.add_argument('--time',type=float,default=None,help='Time to capture one PNG frame')
    ap.add_argument('--crf',type=int,default=21,help='MP4 quality 16-28; smaller = better')
    args=ap.parse_args()
    data=load(args.scene)
    errors=validate(data)
    if errors:
        print('\n'.join('ERROR: '+x for x in errors),file=sys.stderr);sys.exit(2)
    renderer=Renderer(data,asset_root=Path(args.scene).resolve().parent)
    if args.time is not None:
        output=Path(args.out or 'output/frame.png');output.parent.mkdir(parents=True,exist_ok=True)
        renderer.frame(args.time).save(output)
        print('SAVED',output);return
    output=Path(args.out or 'output/'+Path(args.scene).stem+'.mp4')
    output.parent.mkdir(parents=True,exist_ok=True)
    # raw RGB frames into FFmpeg. Each frame is a pure function of scene and time.
    command=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
       '-s',f'{renderer.width}x{renderer.height}','-r',str(renderer.fps),'-i','-',
       '-an','-c:v','libx264','-crf',str(args.crf),'-preset','veryfast',
       '-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
    frames=round(renderer.duration*renderer.fps)
    start=time.time()
    try:
        with subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE) as proc:
            for f in range(frames):
                proc.stdin.write(renderer.frame(f/renderer.fps).tobytes())
            proc.stdin.close()
            stderr=proc.stderr.read().decode(errors='replace')
            code=proc.wait()
            if code:raise RuntimeError('FFmpeg failed: '+stderr)
    except FileNotFoundError as exc:
        raise SystemExit('FFmpeg not installed (ffmpeg.org/download.html)') from exc
    print(f'SAVED {output} | {frames} frames | {time.time()-start:.1f}s')

if __name__=='__main__':main()
