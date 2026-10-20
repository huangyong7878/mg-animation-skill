#!/usr/bin/env python3
"""Mechanical AV cue contract verifier, never a substitute for watching/listening.

R3 specifies which spoken segment belongs to which R4 renderer event. R4 checks
both planned and *measured* TTS against those constraints, before/after render.
Independent R5 audiovisual inspection remains a separately required stage.
"""
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts/av_sync_cues.schema.json"


def validate_av_cues(spec, plan, events, contract, timings=None):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(contract))
    if errors:
        raise ValueError("AV cue schema invalid: " + "; ".join(e.message for e in errors))
    for field, expected in (("project_id", spec["project_id"]),
                            ("spec_id", spec["spec_id"]),
                            ("spec_revision", spec["revision"])):
        if contract[field] != expected:
            raise ValueError(f"AV cue contract {field} differs from director spec")
    if contract["status"] != "draft":
        raise ValueError("Pilot Stage C cue contract must be draft, not release approved")
    if contract["event_source"] != "scripts/primitives/orderflow.py:PILOT_EVENT_SECONDS":
        raise ValueError("Unexpected visual event source")
    if not isinstance(events, dict) or not all(
            isinstance(k, str) and type(v) in (int, float)
            and math.isfinite(v) and v >= 0 for k, v in events.items()):
        raise ValueError("Renderer must expose valid nonnegative event seconds")

    segments = plan.get("narration", {}).get("segments", [])
    cues = contract["cues"]
    actual_ids = [s.get("id") for s in segments]
    cue_ids = [c["segment_id"] for c in cues]
    if len(set(cue_ids)) != len(cue_ids) or actual_ids != cue_ids:
        raise ValueError("Narration/cue IDs must match exactly in event order")
    measured = None if timings is None else timings.get("segments")
    if measured is not None and len(measured) != len(cues):
        raise ValueError("Measured timing/cue counts mismatch")
    if timings is not None and not isinstance(measured, list):
        raise ValueError("Measured timing segments missing")

    results = []
    prior_end = 0.0
    for i, (cue, segment) in enumerate(zip(cues, segments)):
        try:
            anchor_start = float(events[cue["start_event"]])
            anchor_end = float(events[cue["end_event"]])
        except KeyError as exc:
            raise ValueError(f"Visual event missing from renderer: {exc}") from None
        off_min, off_max = cue["start_offsets_s"]
        if not all(math.isfinite(x) for x in (off_min, off_max, cue["max_end_offset_s"])):
            raise ValueError("AV cue offsets must be finite")
        earliest, latest = anchor_start + off_min, anchor_start + off_max
        deadline = anchor_end + cue["max_end_offset_s"]
        if earliest < 0 or earliest > latest or latest >= deadline:
            raise ValueError(f"Invalid cue window for {cue['segment_id']}")
        text = segment.get("text", "")
        if not isinstance(text, str) or not all(
                token in text for token in cue["required_words"]):
            raise ValueError(f"Wrong spoken subject/text for {cue['segment_id']}")
        planned = segment.get("start")
        if type(planned) not in (float, int) or not math.isfinite(planned):
            raise ValueError(f"Missing finite explicit cue start for {cue['segment_id']}")
        if not earliest <= planned <= latest:
            raise ValueError(f"Wrong visual event time for {cue['segment_id']}")
        result = {
            "segment_id": cue["segment_id"],
            "visual_event": cue["start_event"],
            "visual_event_at_s": round(anchor_start, 4),
            "expected_visual": cue["expected_visual"],
            "allowed_start_s": [round(earliest, 4), round(latest, 4)],
            "must_end_by_s": round(deadline, 4),
            "planned_start_s": planned,
        }
        if measured is not None:
            item = measured[i]
            if item.get("id") != cue["segment_id"] or item.get("text") != text.strip():
                raise ValueError(f"Measured audio does not match cue text/id: {cue['segment_id']}")
            try:
                start, end = float(item["start"]), float(item["end"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("Measured audio timing fields invalid") from exc
            if not (math.isfinite(start) and math.isfinite(end)):
                raise ValueError("Measured audio timing values non-finite")
            if start < prior_end - 0.005 or end <= start:
                raise ValueError(f"Overlapping or negative cue timing: {cue['segment_id']}")
            # Allow only <=60ms WAV synthesis / rounding error in event windows.
            if not earliest - .06 <= start <= latest + .06:
                raise ValueError(f"Actual narration begins outside visual event: {cue['segment_id']}")
            if abs(start - planned) > .07:
                raise ValueError(f"Actual narration differs from scheduled start: {cue['segment_id']}")
            if end > deadline + .05:
                raise ValueError(f"Actual narration ends outside visual event: {cue['segment_id']}")
            prior_end = end
            result["actual_start_s"] = start
            result["actual_end_s"] = end
            result["timing_check"] = "pass"
        results.append(result)

    return {
        "schema_version": "1.0",
        "result": "mechanical_pass",
        "scope": "Stage C draft: declared renderer events vs planned/measured TTS only",
        "director_approval": "draft",
        "independent_audiovisual_review": False,
        "verified_video_pixels": False,
        "verified_spoken_audio_semantics": False,
        "cues": results,
        "warning": "A passing cue contract does not prove rendered pictures or spoken audio are semantically correct; independent AV QA and human release approval still required.",
    }
