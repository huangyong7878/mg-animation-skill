#!/usr/bin/env python3
"""Check structural coverage of one Visual Contract against its own shot.

This is a metadata gate, NOT visual/physical verification. A passed tag does not
prove that the rendered image or motion is correct; independent video QA is needed.

Usage:
    python scripts/contract_check.py shot_contract.json scene.json [--strict] [--report report.json]

``--strict`` blocks all missing requirements, even for legacy contracts that
explicitly permit downgrades. The default preserves the ``silent_downgrade``
compatibility setting while visibly reporting every omission.
"""
import argparse
import json
from pathlib import Path


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def iter_elements(elements):
    """Yield nested drawable nodes, including nodes in layout containers."""
    for node in elements:
        if not isinstance(node, dict):
            continue
        yield node
        children = node.get("children", [])
        if isinstance(children, list):
            yield from iter_elements(children)


def element_tags(element):
    value = element.get("contract", [])
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [tag for tag in value if isinstance(tag, str) and tag.strip()]
    return []


def audit_contract(contract, scene, strict=False):
    """Return a JSON-serializable shot-scoped audit with errors and warnings."""
    report = {
        "shot_id": contract.get("shot_id") if isinstance(contract, dict) else None,
        "strict": bool(strict),
        "covered": [],
        "missing": [],
        "errors": [],
        "warnings": [],
        "passed": False,
    }
    errors = report["errors"]
    if not isinstance(contract, dict) or not isinstance(scene, dict):
        errors.append("Contract and scene must be JSON objects")
        return report

    shot_id = contract.get("shot_id")
    if not isinstance(shot_id, str) or not shot_id.strip():
        errors.append("Contract requires a nonempty shot_id")
    if not isinstance(contract.get("silent_downgrade"), bool):
        errors.append("Contract requires boolean silent_downgrade")
    required = contract.get("must_show")
    motions = contract.get("continuous_motion", [])
    if not isinstance(required, list) or not required:
        errors.append("Contract requires a nonempty must_show array")
    if not isinstance(motions, list):
        errors.append("continuous_motion must be an array")
    if errors:
        return report

    requested = []
    for field, entries in (("must_show", required), ("continuous_motion", motions)):
        for index, entry in enumerate(entries):
            identifier = entry.get("id") if isinstance(entry, dict) else None
            if not isinstance(identifier, str) or not identifier.strip():
                errors.append(f"{field}[{index}] needs a nonempty id")
            else:
                requested.append((field, identifier))
    ids = [identifier for _, identifier in requested]
    if len(ids) != len(set(ids)):
        errors.append("Contract requirement ids must be unique")
    scenes = scene.get("scenes")
    if not isinstance(scenes, list):
        errors.append("Scene document requires scenes array")
    if errors:
        return report

    matching = [item for item in scenes if isinstance(item, dict) and item.get("id") == shot_id]
    if len(matching) != 1:
        errors.append(f"Expected exactly one scene with id {shot_id!r}; found {len(matching)}")
        return report

    elements = matching[0].get("elements", [])
    if not isinstance(elements, list):
        errors.append("Target scene elements must be an array")
        return report
    covered = set()
    for element in iter_elements(elements):
        covered.update(element_tags(element))
    report["covered"] = sorted(covered.intersection(ids))
    report["missing"] = [identifier for _, identifier in requested if identifier not in covered]
    if report["missing"]:
        message = "Missing contract coverage in target shot: " + ", ".join(report["missing"])
        if strict or not contract["silent_downgrade"]:
            errors.append(message)
        else:
            report["warnings"].append(message + " (downgrade allowed by contract)")
    report["passed"] = not errors
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", help="Shot Visual Contract JSON")
    parser.add_argument("scene", help="Scene document JSON")
    parser.add_argument("--strict", action="store_true", help="Block all missing requirements")
    parser.add_argument("--report", help="Save machine-readable JSON audit")
    args = parser.parse_args(argv)
    try:
        report = audit_contract(load(args.contract), load(args.scene), strict=args.strict)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {"passed": False, "errors": [str(exc)], "warnings": [], "missing": [], "covered": []}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.report:
        output = Path(args.report)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
