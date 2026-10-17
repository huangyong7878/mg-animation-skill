"""One command pipeline for narrated MG animations (Skill 2.1)."""
import argparse
import subprocess
import sys
from pathlib import Path
from engine import load
from validate import validate
from factcheck import check
from narrate import create_narration


def pipeline(scene_path,output_dir,engine='espeak',voice=None,speed=165,fetch_sources=False):
    scene_path=Path(scene_path).resolve();output_dir=Path(output_dir).resolve()
    output_dir.mkdir(parents=True,exist_ok=True)
    data=load(scene_path)
    issues=validate(data)
    if issues:raise ValueError('Scene validation blocked:\n'+'\n'.join(issues))
    fact_issues=check(data,fetch=fetch_sources)
    if fact_issues:raise ValueError('Fact/provenance gate blocked:\n'+'\n'.join(fact_issues))
    print('PASS: scene validation and claim evidence gate',flush=True)
    basename=scene_path.stem
    audio=output_dir/(basename+'.wav')
    timing=output_dir/(basename+'.timings.json')
    video=output_dir/(basename+'.mp4')
    create_narration(data,audio,timing,engine,speed,voice)
    print('SAVED audio, sentence timestamps and SRT',flush=True)
    subprocess.run([sys.executable,str(Path(__file__).with_name('render.py')),str(scene_path),
                   '--audio',str(audio),'--timings',str(timing),'--out',str(video)],check=True)
    return video

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scene');p.add_argument('--output-dir',default='output')
    p.add_argument('--engine',choices=['espeak','edge'],default='espeak')
    p.add_argument('--voice');p.add_argument('--speed',type=int,default=165)
    p.add_argument('--fetch-sources',action='store_true');args=p.parse_args()
    result=pipeline(args.scene,args.output_dir,args.engine,args.voice,args.speed,args.fetch_sources)
    print('PIPELINE COMPLETE:',result)
