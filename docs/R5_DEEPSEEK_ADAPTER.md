# R0 R5 DeepSeek adapter (Stage D)

Use the existing R0 orchestration path; no standalone downloaded script:

```bash
export DEEPSEEK_API_KEY="..."  # Prefer read -s in terminal, never commit keys
python workflow/orchestrator.py review \
  --workdir work/orders_pilot/formal_r4 \
  --provider deepseek \
  --artifact-root work/orders_pilot/stage_d_delivery
```

The `workdir` must already have completed `prepare --formal`, `receive`, and `review-package` for the **same** Stage D delivery. This command makes one paid DeepSeek API request, extracts two frames per second from the real MP4, and creates:

- `WORKDIR/r5_deepseek/observations.md`: actual provider response
- `WORKDIR/r5_deepseek/evidence.json`: source SHA, input MP4 SHA, model and token usage
- `WORKDIR/r5_deepseek/qa_report_PENDING.json`: QA draft, **pending only**

This is **sampled-frame visual feedback**, not a full AV review. DeepSeek is not sent the WAV and cannot claim to have listened to it; sampled frames cannot prove all-frame continuous motion. Formal `record-qa` deliberately rejects `pending`. An independent reviewer must inspect full motion and listen to the sound, document the checks in a separate QA report, and only then submit `record-qa`. R7 still needs separate human authorization.

Security: API key is taken only from environment, HTTPS endpoint is pinned to `https://api.deepseek.com/chat/completions`. No automatic workflow dispatch or GitHub posting. A pre-existing output folder blocks duplicate requests; failures never mint a PASS.

Supports `deepseek-flash` images documented at https://api-docs.deepseek.com/guides/vision/. Requires `ffmpeg` installed.
