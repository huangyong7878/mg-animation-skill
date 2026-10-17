"""Deterministic timeline transitions for MG Animation Skill 2.1.

Scenes are full images, never alpha-overlaid. For contiguous scenes, transition
straddles the edit point; for overlapping scenes, overlap is the transition.
"""
from __future__ import annotations
from PIL import Image
from dataclasses import dataclass
from typing import Callable

TYPES={'crossfade','wipe_left','slide_left','cut'}

@dataclass(frozen=True)
class Junction:
    a: int
    b: int
    start: float
    end: float
    kind: str


def build_junctions(scenes: list, default: dict|None=None) -> list[Junction]:
    default=default or {'type':'crossfade','duration':0.5}
    out=[]
    for i in range(1,len(scenes)):
        prev,nxt=scenes[i-1],scenes[i]
        ae=float(prev.get('start',0))+float(prev['duration'])
        bs=float(nxt.get('start',0))
        if bs>ae+1e-6:continue  # gap: no transition; show paper
        conf=nxt.get('transition_in',default)
        kind=conf.get('type','crossfade')
        if kind not in TYPES:raise ValueError('Unknown transition type: '+kind)
        if kind=='cut':continue
        if bs<ae-1e-6:
            lo,hi=bs,ae
        else:
            duration=float(conf.get('duration',0.5))
            # Never consume entire scene (or intersect previous junction for simple sequences).
            duration=min(duration,max(0.,min(float(prev['duration']),float(nxt['duration']))*.8))
            lo,hi=bs-duration/2,bs+duration/2
        if hi>lo+1e-6:out.append(Junction(i-1,i,lo,hi,kind))
    return out


def compose(old:Image.Image,new:Image.Image,p:float,kind:str)->Image.Image:
    p=max(0.,min(1.,p))
    if kind=='crossfade':return Image.blend(old,new,p)
    w,h=old.size
    k=max(0,min(w,round(p*w)))
    if kind=='wipe_left':
        img=old.copy()
        if k:img.paste(new.crop((0,0,k,h)),(0,0))
        return img
    if kind=='slide_left':
        img=Image.new('RGB',(w,h))
        if k<w:img.paste(old.crop((k,0,w,h)),(0,0))
        if k:img.paste(new.crop((0,0,k,h)),(w-k,0))
        return img
    raise ValueError(kind)
