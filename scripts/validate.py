"""Validate AI-authored declarative MG v2 JSON against schema and semantic rules."""
import argparse
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator
from engine import load, layout_scene, table_dimensions, timeline_state, Renderer

SCHEMA=Path(__file__).resolve().parent.parent/'references'/'scene.schema.json'
VALID_ANIMATIONS={'fade','slide','pop','draw','move'}
CONTAINER_TYPES={'absolute','row','column','grid'}
DRAW_TYPES={'text','card','icon','line','arrow','table','timeline','image'}


def validate(data):
    schema=json.loads(SCHEMA.read_text(encoding='utf-8'))
    errors=[e.message+' @ '+ '/'.join(map(str,e.path)) for e in Draft202012Validator(schema).iter_errors(data)]
    if errors:return errors
    used=set()
    def walk(node,location):
        ident=node.get('id')
        if ident:
            if ident in used:errors.append(f'duplicate id {ident!r} @ {location}')
            used.add(ident)
        typ=node['type']
        if typ not in DRAW_TYPES|CONTAINER_TYPES:errors.append(f'Unknown type {typ} @ {location}')
        if typ=='grid' and not isinstance(node.get('columns'),int):errors.append('Layout grid requires integer columns')
        if typ=='table':
            c,r=table_dimensions(node)
            if c==0:errors.append('Table must have at least 1 column')
            for idx,row in enumerate(node.get('rows',[])):
                if len(row)!=c:errors.append(f'Table row {idx} has {len(row)} cells, expected {c}')
            if node.get('column_weights') and len(node['column_weights'])!=c:
                errors.append('Table column_weights mismatch')
        if typ=='image' and not node.get('asset'):errors.append(f'Image node requires asset @ {location}')
        if typ=='timeline' and not node.get('items'):errors.append(f'Empty timeline @ {location}')
        for a in node.get('animations',[]):
            if a['type'] not in VALID_ANIMATIONS:errors.append(f'Unsupported animation {a["type"]} @ {location}')
            if a.get('start',0)<0:errors.append(f'Animation start negative @ {location}')
            if a.get('duration',.5)<=0:errors.append(f'Animation duration must >0 @ {location}')
        for i,child in enumerate(node.get('children',[])):walk(child,f'{location}/children/{i}')
    for ix,scene in enumerate(data['scenes']):
        if scene.get('start',0)+scene['duration']>data['canvas']['duration']+.001:
            errors.append(f'Scene {ix} exceeds canvas.duration')
        for j,node in enumerate(scene['elements']):walk(node,f'scenes/{ix}/elements/{j}')
        if not errors:
            try:layout_scene(scene,data['canvas']['width'],data['canvas']['height'])
            except (ValueError,KeyError,TypeError) as e:errors.append(f'Layout error in scene {ix}: {e}')
    return errors


def main():
    ap=argparse.ArgumentParser();ap.add_argument('scene_json')
    args=ap.parse_args();data=load(args.scene_json)
    errors=validate(data)
    if errors:
        for error in errors:print('ERROR:',error,file=sys.stderr)
        sys.exit(1)
    print(f'OK: {args.scene_json} | {len(data["scenes"])} scene(s) | {data["canvas"]["width"]}x{data["canvas"]["height"]} | duration {data["canvas"]["duration"]}s')

if __name__=='__main__':main()
