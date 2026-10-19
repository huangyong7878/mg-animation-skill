"""Deterministic 2-D motion graphics renderer; data-driven v2 scene layout.

No fixed table shape or viewport. All layout and timing comes from scene JSON.
Python >= 3.10. Pillow required, FFmpeg for MP4.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont
from primitives import PRIMITIVES
from transitions import build_junctions, compose

DEFAULT_THEME = {
    'paper': '#E7DED4', 'ink': '#353C3E', 'red': '#B75049',
    'blue': '#334B59', 'gold': '#B59150', 'cream': '#F6F1E9',
    'muted': '#746C65', 'white': '#FFFFFF'
}
FONT_CANDIDATES = [
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf',
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    '/System/Library/Fonts/PingFang.ttc',
    '/Library/Fonts/Arial Unicode.ttf',
    'C:/Windows/Fonts/msyh.ttc',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
]


def ease(x: float, name: str = 'out_cubic') -> float:
    x = max(0., min(1., x))
    if name == 'linear': return x
    if name == 'in_out': return 0.5 - 0.5 * math.cos(x * math.pi)
    if name == 'out_back':
        c1 = 1.70158
        return 1 + (c1 + 1) * (x - 1)**3 + c1 * (x - 1)**2
    return 1 - (1 - x)**3


def value_px(value: float | int | str | None, extent: float, default: float = 0) -> float:
    if value is None: return default
    if isinstance(value, str):
        if value.endswith('%'): return float(value[:-1]) * extent / 100
        raise ValueError(f"Dimension should be a number (pixels) or percent: {value!r}")
    return float(value)


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    def inset(self, padding: float) -> 'Box':
        return Box(self.x+padding,self.y+padding,max(0,self.w-2*padding),max(0,self.h-2*padding))

    @property
    def cx(self): return self.x + self.w/2

    @property
    def cy(self): return self.y + self.h/2


def box_from_rect(rect: dict, parent: Box) -> Box:
    return Box(parent.x+value_px(rect.get('x',0), parent.w),
               parent.y+value_px(rect.get('y',0), parent.h),
               value_px(rect.get('w','100%'), parent.w),
               value_px(rect.get('h','100%'), parent.h))


def _split_grid_axis(total: float, n: int, gap: float, weights: list | None) -> list[float]:
    if n < 1: raise ValueError('Grid axis count must be >= 1')
    gap = max(0,gap)
    avail = total - (n-1)*gap
    if avail <= 0: raise ValueError('Grid gaps leave no space for cells')
    weights = weights or [1]*n
    if len(weights) != n or any(float(x) <= 0 for x in weights):
        raise ValueError('Grid weights must contain one positive number per track')
    return [avail*float(v)/sum(map(float,weights)) for v in weights]


def table_dimensions(node: dict) -> tuple[int,int]:
    """Returns columns, rows including one header row; never a fixed shape."""
    return len(node.get('columns',[])), len(node.get('rows',[]))+1


def _layout_node(node: dict, rect: Box, out: list[tuple[dict,Box]], *, inherited: dict | None=None) -> None:
    style = dict(inherited or {})
    style.update(node.get('style',{}))
    n = dict(node)
    n['_effective_style'] = style
    kind = node.get('type')
    if kind in ('row','column','grid','absolute'):
        children = [dict(ch) for ch in node.get('children',[])]
        if node.get('animations'):
            for ch in children:
                ch['animations'] = node['animations'] + ch.get('animations',[])
        pad = value_px(node.get('padding',0), min(rect.w,rect.h))
        area = rect.inset(pad)
        gap = value_px(node.get('gap',0), min(area.w, area.h))
        if kind == 'absolute':
            for child in children:
                _layout_node(child,box_from_rect(child.get('rect',{}),area),out,inherited=style)
            return
        if kind in ('row','column'):
            horizontal = kind == 'row'; extent = area.w if horizontal else area.h
            tracks = _split_grid_axis(extent,len(children),gap,node.get('weights')) if children else []
            loc = area.x if horizontal else area.y
            for child, size in zip(children,tracks):
                child_box = Box(loc,area.y,size,area.h) if horizontal else Box(area.x,loc,area.w,size)
                _layout_node(child, child_box, out, inherited=style)
                loc += size + gap
        else:
            cols = node.get('columns')
            if not isinstance(cols,int) or cols < 1: raise ValueError('grid.columns must be a positive integer')
            rows = math.ceil(len(children)/cols)
            if rows == 0: return
            col_width = _split_grid_axis(area.w,cols,gap,node.get('column_weights'))
            row_heights = _split_grid_axis(area.h,rows,gap,node.get('row_weights'))
            xs = [area.x]
            ys = [area.y]
            for cw in col_width[:-1]: xs.append(xs[-1]+cw+gap)
            for rh in row_heights[:-1]: ys.append(ys[-1]+rh+gap)
            for idx,child in enumerate(children):
                col=idx%cols; row=idx//cols
                _layout_node(child,Box(xs[col],ys[row],col_width[col],row_heights[row]),out,inherited=style)
        return
    out.append((n,rect))


def layout_scene(scene: dict, width: int, height: int) -> list[tuple[dict,Box]]:
    """Resolve all element bounding boxes independently of the render clock."""
    root = Box(0,0,width,height)
    layouts = []
    for node in scene.get('elements',[]):
        rect = box_from_rect(node.get('rect',{}),root)
        _layout_node(node,rect,layouts)
    return layouts


def calculate_grid(box: Box, columns: int, rows: int, column_weights=None) -> list[Box]:
    """Public grid helper used by table renderer and unit tests."""
    ws = _split_grid_axis(box.w, columns, 0, column_weights)
    hs = _split_grid_axis(box.h, rows, 0, None)
    x_positions = [box.x]
    for w in ws[:-1]: x_positions.append(x_positions[-1]+w)
    return [Box(x_positions[c], box.y+r*hs[r], ws[c], hs[r])
            for r in range(rows) for c in range(columns)]


def hex_rgb(s: str, theme: dict | None=None) -> tuple[int,int,int]:
    if not isinstance(s,str): raise ValueError('Color must be a string')
    if theme and s.startswith('$'): s = theme.get(s[1:],s)
    if not s.startswith('#') or len(s) not in (4,7): raise ValueError('Colors use #RGB, #RRGGBB or $themeKey')
    if len(s)==4: s='#'+''.join([v*2 for v in s[1:]])
    return tuple(bytes.fromhex(s[1:]))


def opacity_rgba(s: str, theme: dict, alpha: float=1.0):
    return (*hex_rgb(s, theme), round(255*max(0,min(1,alpha))))


def font_path(preferred: str | None=None):
    for path in [preferred]+FONT_CANDIDATES:
        if path and Path(path).is_file(): return str(path)
    raise RuntimeError('No usable font; install Noto Sans CJK or set canvas.font_path')


class FontCache:
    def __init__(self, path): self.path=font_path(path);self.cache={}
    def get(self, size):
        size=max(7,round(size))
        if size not in self.cache: self.cache[size]=ImageFont.truetype(self.path,size)
        return self.cache[size]


def split_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, limit: int) -> list[str]:
    result=[]
    for paragraph in text.split('\n'):
        if not paragraph: result.append('');continue
        line=''
        for ch in paragraph:
            if line and draw.textbbox((0,0),line+ch,font=font)[2] > limit:
                result.append(line);line=ch
            else:line+=ch
        result.append(line)
    return result


def fit_text(draw, fonts: FontCache, text: str, box: Box, *, requested=26, minimum=10, padding=4, lines=3):
    available_w=max(1,int(box.w-padding*2)); available_h=max(1,int(box.h-padding*2))
    for size in range(int(requested),int(minimum)-1,-1):
        font=fonts.get(size)
        wrapped=split_text(draw,text,font,available_w)
        height=(size*1.42)*len(wrapped)
        if len(wrapped)<=lines and height<=available_h:
            return font,wrapped,size
    font=fonts.get(minimum)
    wrapped=split_text(draw,text,font,available_w)
    if len(wrapped)>lines:
        raise ValueError(f'Text does not fit: {text[:30]!r}, bbox={box}')
    return font,wrapped,minimum


def timeline_state(node: dict, t: float) -> dict:
    """Combine independent animations with deterministic composition; local scene time."""
    state={'alpha':1.0,'dx':0.,'dy':0.,'scale':1.,'draw':1.}
    for a in node.get('animations',[]):
        typ=a['type'];start=float(a.get('start',0));duration=max(1e-6,float(a.get('duration',0.5)))
        hide_before=bool(a.get('hide_before',True))
        if t < start:
            if typ == 'slide':
                state['dx'] += float(a.get('from_x',0))
                state['dy'] += float(a.get('from_y',14))
            elif typ == 'move':
                state['dx'] += float(a.get('from_x',0))
                state['dy'] += float(a.get('from_y',0))
            elif typ in ('fade','pop') and hide_before:
                state['alpha'] = 0.0
            continue
        p=ease((t-start)/duration, a.get('easing','out_cubic'))
        if typ == 'fade':state['alpha']*=p
        elif typ == 'slide':
            state['dx'] += float(a.get('from_x',0))*(1-p)
            state['dy'] += float(a.get('from_y',14))*(1-p)
        elif typ == 'pop':
            start_scale=float(a.get('from_scale',0.65))
            state['scale']*=start_scale+(1-start_scale)*ease((t-start)/duration,'out_back')
            if hide_before:
                state['alpha']*=ease((t-start)/min(duration,0.2),'linear')
        elif typ == 'draw':state['draw']*=p
        elif typ == 'move':
            fx=float(a.get('from_x',0)); fy=float(a.get('from_y',0))
            tx=float(a.get('to_x',0)); ty=float(a.get('to_y',0))
            state['dx']+=fx+(tx-fx)*p
            state['dy']+=fy+(ty-fy)*p
        else: raise ValueError(f'Unsupported animation type: {typ!r}')
    return state


def animated_box(box: Box, state: dict) -> Box:
    factor=max(.001,state['scale'])
    return Box(box.cx-box.w*factor/2+state['dx'],box.cy-box.h*factor/2+state['dy'],box.w*factor,box.h*factor)



def _line_partial(draw, xy1, xy2, ratio, fill, width):
    p=max(0.,min(1.,ratio))
    if p<=0:return
    x1,y1=xy1;x2,y2=xy2
    draw.line([(x1,y1),(x1+(x2-x1)*p,y1+(y2-y1)*p)],fill=fill,width=width,joint='curve')


def _centered_text(draw,fonts,txt,box,*,size,minimum=11,color=(33,33,33,255),padding=5,lines=3,align='center'):
    if not txt: return
    font,strings,size=fit_text(draw,fonts,str(txt),box,requested=size,minimum=minimum,padding=padding,lines=lines)
    lh=size*1.42
    y=box.cy-len(strings)*lh/2
    for line in strings:
        bounds=draw.textbbox((0,0),line,font=font)
        tw=bounds[2]-bounds[0]
        if align=='left': x=box.x+padding
        elif align=='right':x=box.x+box.w-padding-tw
        else:x=box.cx-tw/2
        draw.text((round(x),round(y)),line,font=font,fill=color,stroke_width=0)
        y+=lh


def _draw_icon(draw,box,shape,fill,outline,width,progress=1.):
    c=(box.cx,box.cy);r=min(box.w,box.h)*.33
    if shape=='diamond':
        pts=[(c[0],c[1]-r),(c[0]+r,c[1]),(c[0],c[1]+r),(c[0]-r,c[1])]
        draw.polygon(pts,fill=fill)
    elif shape=='triangle':
        draw.polygon([(c[0],c[1]-r),(c[0]+r,c[1]+r),(c[0]-r,c[1]+r)],fill=fill)
    elif shape=='square':
        draw.rounded_rectangle((c[0]-r,c[1]-r,c[0]+r,c[1]+r),radius=max(1,round(r*.2)),fill=fill)
    elif shape=='bars':
        for i, h in enumerate([.52,1,.76]):
            x=c[0]+(i-1)*r*.72
            draw.rounded_rectangle((x-r*.26,c[1]+r*.7-r*h*1.5,x+r*.26,c[1]+r*.7),radius=2,fill=fill)
    elif shape=='star':
        pts=[]
        for i in range(10):
            a=-math.pi/2+i*math.pi/5;rr=r if i%2==0 else r*.44
            pts.append((c[0]+math.cos(a)*rr,c[1]+math.sin(a)*rr))
        draw.polygon(pts,fill=fill)
    else: draw.ellipse((c[0]-r,c[1]-r,c[0]+r,c[1]+r),fill=fill)


def render_asset(layer, asset, box, alpha, asset_root, cache):
    # Source image is local; SVG rendered via CairoSVG when available.
    path=(asset_root/asset).resolve()
    if not path.is_relative_to(asset_root.resolve()):
        raise ValueError(f'Asset path escapes scene directory: {asset!r}')
    if not path.is_file():raise FileNotFoundError(f'No local asset: {path}')
    if path not in cache:
        if path.suffix.lower()=='.svg':
            try:import cairosvg
            except ImportError as exc:raise RuntimeError('SVG assets require cairosvg package') from exc
            import io
            cache[path]=Image.open(io.BytesIO(cairosvg.svg2png(url=str(path)))).convert('RGBA')
        elif path.suffix.lower() in ('.png','.jpg','.jpeg','.webp'):
            cache[path]=Image.open(path).convert('RGBA')
        else:raise ValueError(f'Unsupported asset format: {path.suffix}')
    img=cache[path]
    if box.w<2 or box.h<2:return
    scale=min(box.w/img.width,box.h/img.height)
    target=img.resize((max(1,round(img.width*scale)),max(1,round(img.height*scale))),Image.Resampling.LANCZOS)
    if alpha<.999:
        chan=target.getchannel('A').point(lambda v:round(v*max(0,min(alpha,1))))
        target.putalpha(chan)
    layer.alpha_composite(target, (round(box.cx-target.width/2),round(box.cy-target.height/2)))


def draw_item(layer: Image.Image, node: dict, box: Box, t: float, theme: dict, fonts: FontCache, asset_root: Path, asset_cache: dict):
    state=timeline_state(node,t)
    if state['alpha']<=0.0001 or state['draw']<=0.0001: return
    box=animated_box(box,state)
    effective=node.get('_effective_style',{})
    draw=ImageDraw.Draw(layer,'RGBA')
    kind=node['type'];alpha=state['alpha']
    def col(name,default):return opacity_rgba(effective.get(name,default),theme,alpha)
    if kind=='image':
        render_asset(layer,node['asset'],box,alpha,asset_root,asset_cache)
    elif kind=='text':
        _centered_text(draw,fonts,str(node.get('text','')),box,
          size=effective.get('size',30)*state['scale'],minimum=effective.get('min_size',11),
          color=col('color','$ink'), padding=effective.get('padding',4),lines=effective.get('max_lines',3),
          align=effective.get('align','center'))
    elif kind=='card':
        fill=col('fill','$cream');outline=col('stroke','$red')
        radius=round(min(box.w,box.h)*effective.get('radius',.12))
        border=int(effective.get('stroke_width',2))
        draw.rounded_rectangle((box.x,box.y,box.x+box.w,box.y+box.h),radius=max(1,radius),fill=fill,outline=outline,width=border)
        txt=node.get('text','')
        if txt:
            _centered_text(draw,fonts,txt,box.inset(8),size=effective.get('size',24)*state['scale'],
              minimum=effective.get('min_size',10),color=col('color','$ink'),lines=effective.get('max_lines',4))
    elif kind=='icon':
        _draw_icon(draw,box,node.get('symbol','circle'),col('fill','$red'),col('stroke','$ink'),int(effective.get('stroke_width',2)))
    elif kind=='line':
        x1=box.x;y1=box.y;x2=box.x+box.w;y2=box.y+box.h
        color=col('stroke','$red');sw=round(effective.get('stroke_width',3))
        _line_partial(draw,(x1,y1),(x2,y2),state['draw'],color,sw)
    elif kind=='arrow':
        color=col('stroke','$red');sw=round(effective.get('stroke_width',3));p=state['draw']
        # x span from box start to end; horizontal arrows in layout rows
        x1=box.x+box.w*.11;x2=box.x+box.w*.89;y=box.cy
        _line_partial(draw,(x1,y),(x2,y),p,color,sw)
        if p>.97:
            r=min(15,max(5,box.w*.13))
            draw.polygon([(x2,y),(x2-r,y-r*.58),(x2-r,y+r*.58)],fill=color)
    elif kind in PRIMITIVES:
        PRIMITIVES[kind](draw, box, t, node, effective, col, fonts)
    elif kind=='table':
        _draw_table(layer,node,box,t,theme,fonts,state,asset_root,asset_cache)
    elif kind=='timeline':
        _draw_timeline(layer,node,box,t,theme,fonts,state)
    else: raise ValueError(f'Unknown drawing type: {kind!r}')


def _cell_content(layer,draw,fonts,cell,box,theme,alpha,asset_root,asset_cache,header=False,base_size=21):
    if isinstance(cell,(int,float,str)):
        cell={'type':'text','text':str(cell)}
    typ=cell.get('type','text')
    style=cell.get('style',{})
    color=opacity_rgba(style.get('color','$ink'),theme,alpha)
    if typ == 'image':
        render_asset(layer,cell['asset'],box.inset(9),alpha,asset_root,asset_cache)
    elif typ == 'icon':
        iw=min(box.w*.7,box.h*.75)
        _draw_icon(draw,Box(box.cx-iw/2,box.cy-iw/2,iw,iw),cell.get('symbol','circle'),
                   opacity_rgba(style.get('fill','$red'),theme,alpha),color,2)
    elif typ == 'badge':
        if not cell.get('text'):return
        badge=box.inset(min(box.h*.17,12))
        draw.rounded_rectangle((badge.x,badge.y,badge.x+badge.w,badge.y+badge.h),radius=round(badge.h*.24),fill=opacity_rgba(style.get('fill','$gold'),theme,alpha))
        _centered_text(draw,fonts,str(cell.get('text','')),badge,size=min(base_size,badge.h*.55),minimum=8,
                       color=opacity_rgba(style.get('color','$white'),theme,alpha),lines=2)
    else:
        text=str(cell.get('text',''))
        _centered_text(draw,fonts,text,box,size=style.get('size',base_size),minimum=style.get('min_size',10),
                       color=color,lines=style.get('max_lines',3))


def _draw_table(layer,node,box,t,theme,fonts,parent_state,asset_root,asset_cache):
    cols=node.get('columns',[]); rows=node.get('rows',[])
    c=len(cols);r=len(rows)+1
    if c<1: raise ValueError('Table must have one or more columns')
    if any(len(row)!=c for row in rows):raise ValueError('All table rows must match column count')
    style=node.get('_effective_style',{})
    gap=0
    ws=_split_grid_axis(box.w,c,gap,node.get('column_weights'))
    header_ratio=float(node.get('header_ratio',.85))
    heights=_split_grid_axis(box.h,r,gap,[header_ratio]+[1]*(r-1))
    xx=[box.x]; yy=[box.y]
    for w in ws:xx.append(xx[-1]+w)
    for h in heights:yy.append(yy[-1]+h)
    d=ImageDraw.Draw(layer,'RGBA')
    stroke=opacity_rgba(style.get('stroke','$red'),theme,parent_state['alpha'])
    ink=opacity_rgba(style.get('color','$ink'),theme,parent_state['alpha'])
    lw=max(1,round(style.get('stroke_width',3)))
    head_fill=opacity_rgba(style.get('header_fill','$red'),theme,parent_state['alpha']*.13)
    d.rectangle((box.x,box.y,box.x+box.w,yy[1]),fill=head_fill)
    # line reveal, always parameterized by table coordinates and local clock
    grid_start=float(node.get('grid_start',0.0));grid_dur=max(.001,float(node.get('grid_duration',.7)))
    for i,x in enumerate(xx):
        p=ease((t-grid_start-i*.045)/grid_dur)
        _line_partial(d,(x,yy[0]),(x,yy[-1]),p,stroke,lw)
    for i,y in enumerate(yy):
        p=ease((t-grid_start-i*.045)/grid_dur)
        _line_partial(d,(xx[0],y),(xx[-1],y),p,stroke,lw)
    enter=float(node.get('cells_start',.3));delay=float(node.get('stagger',.11))
    cell_duration=max(.001,float(node.get('cell_duration',.38)))
    # Header is row index zero; subsequent rows follow. Column-major or row-major reveal.
    order=node.get('order','row')
    for row_idx in range(r):
        for col_idx in range(c):
            index=row_idx*c+col_idx if order=='row' else col_idx*r+row_idx
            a=ease((t-enter-index*delay)/cell_duration)
            if a<=0:continue
            cell=cols[col_idx] if row_idx==0 else rows[row_idx-1][col_idx]
            cellbox=Box(xx[col_idx]+6,yy[row_idx]+3,max(1,ws[col_idx]-12),max(1,heights[row_idx]-6))
            # Small upward slide, fade. Native text sizing follows computed table cell.
            cellbox=Box(cellbox.x,cellbox.y+9*(1-a),cellbox.w,cellbox.h)
            base=min(float(style.get('font_size',24)),heights[row_idx]*.40)
            if row_idx==0: base*=.92
            _cell_content(layer,d,fonts,cell,cellbox,theme,parent_state['alpha']*a,asset_root,asset_cache,row_idx==0,base)


def _draw_timeline(layer,node,box,t,theme,fonts,state):
    pts=node.get('items',[])
    if not pts: return
    d=ImageDraw.Draw(layer,'RGBA')
    style=node.get('_effective_style',{})
    color=opacity_rgba(style.get('stroke','$red'),theme,state['alpha'])
    muted=opacity_rgba(style.get('color','$ink'),theme,state['alpha'])
    cy=box.y+box.h*.54
    x0=box.x+box.w*.08;x1=box.x+box.w*.92
    line_start=float(node.get('line_start',0));line_dur=max(.001,float(node.get('line_duration',.7)))
    p=ease((t-line_start)/line_dur)
    _line_partial(d,(x0,cy),(x1,cy),p,color,3)
    for idx,it in enumerate(pts):
        xx=x0+(x1-x0)*(idx/(len(pts)-1) if len(pts)>1 else .5)
        a=ease((t-float(node.get('items_start',.4))-idx*float(node.get('stagger',.25)))/.35)
        if a<=0: continue
        rad=9*a
        d.ellipse((xx-rad,cy-rad,xx+rad,cy+rad),fill=opacity_rgba(style.get('dot_fill','$red'),theme,a*state['alpha']))
        label=str(it.get('label','')) if isinstance(it,dict) else str(it)
        sub=str(it.get('detail','')) if isinstance(it,dict) else ''
        width=(x1-x0)/max(1,len(pts))*.94
        _centered_text(d,fonts,label,Box(xx-width/2,box.y,width,box.h*.42),size=min(25,box.h*.16),minimum=10,color=muted,lines=2)
        if sub: _centered_text(d,fonts,sub,Box(xx-width/2,cy+16,width,box.h*.32),size=min(19,box.h*.13),minimum=9,color=muted,lines=2)


def make_paper(width:int,height:int,theme:dict,seed:int) -> Image.Image:
    """Deterministic static paper grain; same in every video frame."""
    import numpy as np
    base=hex_rgb(theme['paper'])
    rng=np.random.default_rng(seed)
    noise=rng.normal(0,2.6,(height,width,1))
    rgb=np.clip(np.asarray(base).reshape(1,1,3)+noise,0,255).astype('uint8')
    return Image.fromarray(rgb,mode='RGB').convert('RGBA')


class Renderer:
    def __init__(self, data:dict, asset_root: str | Path='.'): 
        self.asset_root=Path(asset_root).resolve();self.asset_cache={}
        self.data=data; c=data['canvas'];self.width=int(c['width']);self.height=int(c['height'])
        self.fps=int(c.get('fps',24));self.duration=float(c.get('duration',6))
        self.theme={**DEFAULT_THEME,**data.get('theme',{})}
        self.fonts=FontCache(c.get('font_path'))
        self.background=make_paper(self.width,self.height,self.theme,int(c.get('grain_seed',42)))
        self.scenes=[]
        for scene in data['scenes']:
            self.scenes.append((scene,layout_scene(scene,self.width,self.height)))
        self.junctions = build_junctions(data['scenes'], c.get('default_transition')) if data.get('version')=='2.1' else []

    def _scene_frame(self,index:int,t:float)->Image.Image:
        scene, layouts=self.scenes[index]
        local=max(0,min(float(scene['duration'])-1/self.fps,t-float(scene.get('start',0))))
        img=self.background.copy()
        for node,box in layouts:
            layer=Image.new('RGBA',img.size,(0,0,0,0))
            draw_item(layer,node,box,local,self.theme,self.fonts,self.asset_root,self.asset_cache)
            img=Image.alpha_composite(img,layer)
        return img.convert('RGB')

    def frame(self,t:float)->Image.Image:
        if self.data.get('version')=='2.1':
            for junction in self.junctions:
                if junction.start<=t<junction.end:
                    p=ease((t-junction.start)/(junction.end-junction.start),'in_out')
                    old=self._scene_frame(junction.a,t)
                    new=self._scene_frame(junction.b,t)
                    return compose(old,new,p,junction.kind)
            active=[i for i,(scene,_) in enumerate(self.scenes)
                    if float(scene.get('start',0))<=t<float(scene.get('start',0))+float(scene['duration'])]
            if active:return self._scene_frame(active[-1],t)
            return self.background.convert('RGB').copy()
        # Preserve v2.0 legacy behavior for old projects.
        img=self.background.copy()
        for scene,layouts in self.scenes:
            start=float(scene.get('start',0));duration=float(scene['duration'])
            if not(start<=t<start+duration):continue
            local=t-start
            for node,box in layouts:
                layer=Image.new('RGBA',img.size,(0,0,0,0))
                draw_item(layer,node,box,local,self.theme,self.fonts,self.asset_root,self.asset_cache)
                img=Image.alpha_composite(img,layer)
        return img.convert('RGB')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))
