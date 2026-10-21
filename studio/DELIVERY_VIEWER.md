# MG Studio Stage D viewer

From the feature branch, run `python3 studio/server.py` and open
http://127.0.0.1:8765. Use **刷新交付包** to list local
`stage_d_studio_<runid>` and previous `stage_d_delivery[_vN]` directories.
The viewer validates the existing `media_manifest.json` against delivery,
director spec, on-disk file lengths and SHA256, before making an MP4 URL
available. Browser playback uses HTTP byte-range requests.

The list and player are **read-only**. No auto DeepSeek API calls, media
overwrites, Github writes, R5 pass or R7 publication. Delivery status
`ready_for_qa` means only that production assets are ready for independent QA.
A broken or incomplete manifest blocks preview (the original file stays intact).

The existing build button stays Pilot 001-specific. This feature does not
prove that any six previously identified visual defects were fixed. The first
preview source commit may belong to MG Studio implementation work, not the
R4 visual-fix patch. Commit provenance should be reviewed independently.
