"""Optional forced alignment via WhisperX. Requires models and extra packages.

Input: narration.wav and timings.json produced by narrate.py.
Output: aligned.json with model-returned words/characters when supported.
This command is NOT needed for accurate *segment* timing.
"""
import argparse
import json
from pathlib import Path

def force_align(audio_path,timings_path,out_path,device='cpu',language='zh'):
    try:import whisperx
    except ImportError as exc:raise RuntimeError(
      'WhisperX not installed. Install from https://github.com/m-bain/whisperX; model download may be required.') from exc
    source=json.loads(Path(timings_path).read_text(encoding='utf-8'))
    wave=whisperx.load_audio(str(audio_path))
    model,meta=whisperx.load_align_model(language_code=language,device=device)
    inputs=[{'start':s['start'],'end':s['end'],'text':s['text']} for s in source['segments']]
    aligned=whisperx.align(inputs,model,meta,wave,device,return_char_alignments=True)
    output={'language':language,'backend':'WhisperX','segments':aligned['segments'],
            'note':'Check missing alignments and timing manually; alignment model accuracy varies.'}
    Path(out_path).write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audio',required=True);p.add_argument('--timings',required=True)
    p.add_argument('--out',default='output/aligned.json');p.add_argument('--device',default='cpu')
    p.add_argument('--language',default='zh');a=p.parse_args()
    result=force_align(a.audio,a.timings,a.out,a.device,a.language)
    print('SAVED',a.out,'segments',len(result['segments']))
