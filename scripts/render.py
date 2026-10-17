"""Render v2.0/v2.1 scene JSON; optionally mux narration and draw timed subtitles."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw
from engine import Renderer, load
from validate import validate


def caption_frame(img,seconds,segments,renderer):
    active=next((s for s in segments if s['start']<=seconds<s['end']),None)
    if not active:return img
    txt=active['text'];out=img.copy().convert('RGBA')
    from engine import Box, _centered_text
    overlay=Image.new('RGBA',out.size,(0,0,0,0))
    d=ImageDraw.Draw(overlay,'RGBA');w,h=out.size
    rect=Box(w*.09,h*.83,w*.82,h*.13)
    d.rounded_rectangle((rect.x,rect.y,rect.x+rect.w,rect.y+rect.h),radius=10,fill=(33,37,40,200))
    _centered_text(d,renderer.fonts,txt,rect.inset(9),size=max(14,round(h*.043)),
                   minimum=max(10,round(h*.023)),color=(255,249,235,255),lines=2)
    return Image.alpha_composite(out,overlay).convert('RGB')


def main():
    ap=argparse.ArgumentParser(description='MG Animation Skill 2.1 renderer')
    ap.add_argument('scene',help='Scene JSON path')
    ap.add_argument('--out',help='MP4 or PNG path; default output/<input>.mp4')
    ap.add_argument('--time',type=float,default=None,help='Time for single PNG frame')
    ap.add_argument('--crf',type=int,default=21)
    ap.add_argument('--audio',help='Optional WAV/MP3 from scripts/narrate.py')
    ap.add_argument('--timings',help='Optional timing JSON for subtitle burn-in')
    args=ap.parse_args()
    data=load(args.scene)
    errors=validate(data)
    if errors:
        print('\n'.join('ERROR: '+x for x in errors),file=sys.stderr);sys.exit(2)
    renderer=Renderer(data,asset_root=Path(args.scene).resolve().parent)
    captions=json.loads(Path(args.timings).read_text(encoding='utf-8'))['segments'] if args.timings else []
    def frame(t):
        img=renderer.frame(t)
        return caption_frame(img,t,captions,renderer) if captions else img
    if args.time is not None:
        output=Path(args.out or 'output/frame.png');output.parent.mkdir(parents=True,exist_ok=True)
        frame(args.time).save(output);print('SAVED',output);return
    output=Path(args.out or 'output/'+Path(args.scene).stem+'.mp4')
    output.parent.mkdir(parents=True,exist_ok=True)
    command=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
       '-s',f'{renderer.width}x{renderer.height}','-r',str(renderer.fps),'-i','-']
    if args.audio:
        if not Path(args.audio).is_file():raise FileNotFoundError(args.audio)
        command+=['-i',str(Path(args.audio).resolve())]
    command+=['-map','0:v:0']
    if args.audio:command+=['-map','1:a:0','-c:a','aac','-b:a','128k','-t',str(renderer.duration)]
    else:command+=['-an']
    command+=['-c:v','libx264','-crf',str(args.crf),'-preset','veryfast','-pix_fmt','yuv420p',
              '-movflags','+faststart',str(output)]
    frames=round(renderer.duration*renderer.fps)
    start=time.time()
    try:
        with subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE) as proc:
            for f in range(frames):proc.stdin.write(frame(f/renderer.fps).tobytes())
            proc.stdin.close()
            stderr=proc.stderr.read().decode(errors='replace')
            code=proc.wait()
            if code:raise RuntimeError('FFmpeg failed: '+stderr)
    except FileNotFoundError as exc:raise SystemExit('FFmpeg not installed') from exc
    print(f'SAVED {output} | {frames} frames | {time.time()-start:.1f}s')

if __name__=='__main__':main()
