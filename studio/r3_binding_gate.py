"""Conservative Pilot 001 R3 event binding check for R4 source changes.

This is a STATIC contract gate, not proof of frame-level timing or AV sync.
Unknown implementations fail closed pending an independent rendered-frame gate.
"""
import ast
import subprocess
from pathlib import Path

SOURCE="scripts/primitives/orderflow.py"
EVENTS=("order_a_appears","order_b_appears")

def _parse(source):
    tree=ast.parse(source)
    events=None
    draw=None
    for n in tree.body:
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="PILOT_EVENT_SECONDS" for t in n.targets):
            events=ast.literal_eval(n.value)
        if isinstance(n,ast.FunctionDef) and n.name=="draw":
            draw=n
    if events is None or draw is None:
        raise ValueError("R3 Pilot event dictionary/draw function missing")
    return events,draw

def check(repo,tree,base_commit):
    if not isinstance(base_commit,str) or len(base_commit)!=40:
        raise ValueError("Invalid baseline commit")
    old=subprocess.run(["git","-C",str(repo),"show",base_commit+":"+SOURCE],
        check=True,capture_output=True,text=True,timeout=20).stdout
    new=(Path(tree)/SOURCE).read_text(encoding="utf-8")
    baseline,_=_parse(old)
    actual,draw=_parse(new)
    issues=[]
    if any(actual.get(k)!=baseline.get(k) for k in EVENTS):
        issues.append("R3 order appearance event constants modified")
    card_defs=[n for n in ast.walk(draw) if isinstance(n,ast.FunctionDef) and n.name=="card"]
    if len(card_defs)!=1 or "appear_t" not in card_defs[0].args.args[-5:].__str__():
        # Name lookup below is explicit so AST object representations cannot pass the gate.
        pass
    if len(card_defs)!=1 or "appear_t" not in [a.arg for a in card_defs[0].args.args]:
        issues.append("Card fade no longer accepts approved R3 appearance time")
    else:
        fade_calls=[n for n in ast.walk(card_defs[0]) if isinstance(n,ast.Call)
                    and isinstance(n.func,ast.Name) and n.func.id=="_fade"]
        if not any(len(n.args)>=2 and isinstance(n.args[1],ast.Name) and n.args[1].id=="appear_t"
                   for n in fade_calls):
            issues.append("Card fade is no longer driven by approved appearance time")
    card_calls=[n for n in ast.walk(draw) if isinstance(n,ast.Call)
                and isinstance(n.func,ast.Name) and n.func.id=="card"]
    for letter,event in (("A","order_a_appears"),("B","order_b_appears")):
        matches=[n for n in card_calls if any(isinstance(arg,ast.Constant) and arg.value==letter for arg in n.args)]
        if len(matches)!=1 or not any(
            isinstance(arg,ast.Subscript) and isinstance(arg.value,ast.Name)
            and arg.value.id=="PILOT_EVENT_SECONDS"
            and isinstance(arg.slice,ast.Constant) and arg.slice.value==event
            for arg in matches[0].args):
            issues.append(letter+" card not directly bound to R3 "+event)
    return {"passed":not issues,"issues":issues,"scope":"static_r3_binding_only",
            "visual_frame_validation":"not_performed"}
