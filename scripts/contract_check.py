#!/usr/bin/env python3
"""contract_check.py — validate a scene JSON against its Visual Contract.

Usage:
    python3 scripts/contract_check.py <contract.json> <scene.json>

Checks:
  1. Every must_show.id has at least one element with matching `contract` field.
  2. Every continuous_motion.id has at least one element tagged with it
     (waterpath / custom elements carry the motion id in `contract`).
  3. If silent_downgrade is false and anything is missing -> exit 1 (blocked).

Element tagging convention: scene elements carry e.g.
    "contract": "soil_layers"
or for motion:
    "contract": "drainage_path"
A single element may serve both (list or single string accepted).
"""
import json
import sys


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def all_elements(scene):
    els = []
    for sc in scene.get("scenes", []):
        els.extend(sc.get("elements", []))
    return els


def tags(el):
    c = el.get("contract")
    if not c:
        return []
    return c if isinstance(c, list) else [c]


def main():
    if len(sys.argv) != 3:
        print("usage: contract_check.py <contract.json> <scene.json>", file=sys.stderr)
        return 2
    contract = load(sys.argv[1])
    scene = load(sys.argv[2])
    els = all_elements(scene)
    covered = set()
    for el in els:
        covered.update(tags(el))

    ok = True
    print(f"Contract: {contract.get('shot_id')} | silent_downgrade={contract.get('silent_downgrade')}")
    print(f"Scene elements: {len(els)} tagged, {len(covered)} distinct ids\n")

    print("== must_show ==")
    for item in contract.get("must_show", []):
        iid = item["id"]
        hit = iid in covered
        ok = ok and hit
        print(f"  [{'OK' if hit else 'MISSING'}] {iid}: {item.get('desc', '')}")

    print("\n== continuous_motion ==")
    for m in contract.get("continuous_motion", []):
        mid = m["id"]
        hit = mid in covered
        # motion coverage is advisory unless silent_downgrade is false
        mark = "OK" if hit else ("MISSING" if not contract.get("silent_downgrade", True) else "warn")
        if not hit and not contract.get("silent_downgrade", True):
            ok = False
        print(f"  [{mark}] {mid}: {m.get('from')} -> {m.get('through')} -> {m.get('to')}")

    print()
    if ok:
        print("PASS: all must_show items covered.")
        return 0
    if not contract.get("silent_downgrade", True):
        print("BLOCKED: silent_downgrade=false and items missing. Fix or report, do not ship.")
        return 1
    print("WARN: items missing but silent_downgrade allowed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
