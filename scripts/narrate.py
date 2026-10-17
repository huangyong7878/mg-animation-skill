"""Narration: offline eSpeak, optional Edge-TTS, or Fish Audio API, sentence-exact audio timings + SRT.

This measures actual generated segment durations; it does not pretend to
perform forced word alignment. See scripts/align.py for optional WhisperX.
"""
import argparse
import asyncio
import json
import shutil
import subprocess
import tempfile
import wave
from array import array
from pathlib import Path

RATE=22050


def synthesize_espeak(text,output,voice='zh',speed=165):
    if not shutil.which('espeak'):raise RuntimeError('Install eSpeak (or choose --engine edge)')
    subprocess.run(['espeak','-v',voice,'-s',str(speed),'-w',str(output),text],check=True,stdout=subprocess.DEVNULL)


def synthesize_edge(text,output,voice='zh-CN-XiaoxiaoNeural',rate='+0%'):
    try:import edge_tts
    except ImportError as e:raise RuntimeError('Install optional dependency: pip install edge-tts') from e
    asyncio.run(edge_tts.Communicate(text,voice,rate=rate).save(str(output)))


def synthesize_fish(text,output,model='s2.1-pro-free',reference_id=None):
    """Fish Audio TTS via REST API. Needs FISH_API_KEY env var."""
    import os
    api_key=os.environ.get('FISH_API_KEY')
    if not api_key:
        # Try Muse connector surrogate (when running inside Muse)
        try:
            import sys
            sys.path.insert(0,"/opt/muse/skills/custom-connector-setup/bin")
            from dynamic_credentials import add_surrogate_to_request
            import urllib.request
            payload=json.dumps({"text":text,"format":"mp3",
                **({"reference_id":reference_id} if reference_id else {})}).encode()
            req=urllib.request.Request("https://api.fish.audio/v1/tts",data=payload,
                headers={"Content-Type":"application/json","model":model},method="POST")
            add_surrogate_to_request(req,"custom.fish-audio",allowed_hosts=["api.fish.audio"])
            with urllib.request.urlopen(req,timeout=120) as resp:
                Path(output).write_bytes(resp.read())
            return
        except Exception as e:
            raise RuntimeError('FISH_API_KEY not set and connector unavailable: '+str(e)[:100])
    import urllib.request
    payload=json.dumps({"text":text,"format":"mp3",
        **({"reference_id":reference_id} if reference_id else {})}).encode()
    req=urllib.request.Request("https://api.fish.audio/v1/tts",data=payload,
        headers={"Content-Type":"application/json","model":model,
                 "Authorization":f"Bearer {api_key}"},method="POST")
    with urllib.request.urlopen(req,timeout=120) as resp:
        Path(output).write_bytes(resp.read())


def load_pcm(path):
    # Format adaptation goes through FFmpeg; both TTS engines work here.
    with tempfile.TemporaryDirectory() as td:
        wav=Path(td)/'audio.wav'
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(path),
           '-ar',str(RATE),'-ac','1','-c:a','pcm_s16le',str(wav)],check=True)
        with wave.open(str(wav),'rb') as r:
            assert r.getnchannels()==1 and r.getsampwidth()==2 and r.getframerate()==RATE
            samples=array('h');samples.frombytes(r.readframes(r.getnframes()))
            return samples


def srt_clock(seconds):
    millis=round(seconds*1000); h,m=divmod(millis,3600000);mi,ms=divmod(m,60000);s,ms=divmod(ms,1000)
    return f'{h:02}:{mi:02}:{s:02},{ms:03}'


def create_narration(data,output_audio,output_timing,engine='espeak',speed=165,voice=None):
    conf=data.get('narration') or {}
    chunks=conf.get('segments') or []
    if not chunks:raise ValueError('scene JSON requires narration.segments')
    pieces=array('h'); timings=[];cursor=0.
    if engine=='espeak':voice=voice or 'zh'
    elif engine=='fish':pass  # voice = reference_id or None (default voice)
    else:voice=voice or 'zh-CN-XiaoxiaoNeural'
    with tempfile.TemporaryDirectory() as td:
        for i,seg in enumerate(chunks):
            text=str(seg['text']).strip()
            if not text:continue
            raw=Path(td)/(str(i)+('.wav' if engine=='espeak' else '.mp3'))
            if engine=='espeak':synthesize_espeak(text,raw,voice,speed)
            elif engine=='edge':synthesize_edge(text,raw,voice)
            elif engine=='fish':synthesize_fish(text,raw,reference_id=voice)
            else:raise ValueError(f'Unknown TTS engine {engine}')
            pcm=load_pcm(raw)
            desired=seg.get('start')
            if desired is None and 'scene_index' in seg:
                ix=int(seg['scene_index'])
                desired=float(data['scenes'][ix].get('start',0))+float(seg.get('offset',0))
            start=max(cursor,float(desired)) if desired is not None else cursor
            if desired is not None and float(desired)<cursor-.005:
                raise ValueError(f'Speech overlap in segment {i}: {desired} < {cursor:.3f}; adjust script/timing')
            padding=max(0,round(start*RATE)-len(pieces))
            pieces.extend(array('h',[0])*padding)
            actual_start=len(pieces)/RATE
            pieces.extend(pcm)
            end=len(pieces)/RATE
            timings.append({'id':seg.get('id',f'segment_{i+1}'),'text':text,
                 'start':round(actual_start,4),'end':round(end,4),'alignment':'synthesized_segment_exact'})
            pause=float(seg.get('pause_after',.25))
            if pause<0:raise ValueError('pause_after cannot be negative')
            cursor=end+pause
            pieces.extend(array('h',[0])*round(pause*RATE))
    canvas_dur=(data.get('canvas') or {}).get('duration')
    if canvas_dur is not None:
        video_duration=float(canvas_dur)
        if len(pieces)/RATE>video_duration+.02:
            raise ValueError(f'Narration ({len(pieces)/RATE:.2f}s) exceeds video ({video_duration:.2f}s); increase canvas.duration or shorten script')
        pieces.extend(array('h',[0])*max(0,round(video_duration*RATE)-len(pieces)))
        video_duration_out=video_duration
    else:
        # No canvas: use actual narration duration (prepare stage)
        video_duration_out=len(pieces)/RATE
    output_audio=Path(output_audio);output_timing=Path(output_timing)
    output_audio.parent.mkdir(parents=True,exist_ok=True);output_timing.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(output_audio),'wb') as r:
        r.setnchannels(1);r.setsampwidth(2);r.setframerate(RATE);r.writeframes(pieces.tobytes())
    result={'audio':str(output_audio),'duration':round(len(pieces)/RATE,4),'segments':timings,
            'alignment_note':'Segment starts/ends measured from synthesized audio. Not word/phoneme forced alignment.'}
    output_timing.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    srt=output_timing.with_suffix('.srt')
    srt.write_text(''.join(f'{i}\n{srt_clock(s["start"])} --> {srt_clock(s["end"])}\n{s["text"]}\n\n'
                           for i,s in enumerate(timings,1)),encoding='utf-8')
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('scene')
    ap.add_argument('--engine',choices=['espeak','edge','fish'],default='espeak')
    ap.add_argument('--voice');ap.add_argument('--speed',type=int,default=165)
    ap.add_argument('--audio',default='output/narration.wav');ap.add_argument('--timings',default='output/timings.json')
    args=ap.parse_args();data=json.loads(Path(args.scene).read_text(encoding='utf-8'))
    result=create_narration(data,args.audio,args.timings,args.engine,args.speed,args.voice)
    print('SAVED',args.audio,'and',args.timings, 'segments',len(result['segments']))

if __name__=='__main__':main()
