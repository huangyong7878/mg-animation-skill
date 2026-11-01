# Storyboard — How Wi-Fi Works

## Direction
- Audience: General adult learners
- Language: English
- Canvas: 960 × 540 (16:9), 24 fps
- Total duration: 24.0 s (three 8.0 s shots)
- Narration: On, text timing only; no audio generated or measured
- Tone and palette: Clear and practical; warm paper, ink, and muted red/blue/gold infographic accents

**Creative direction:** Treat the screen like a clean field notebook. Warm paper and dark ink carry the explanation, muted red marks the opening idea, blue tracks the device path, and gold highlights the band-selection trade-off. The pacing is calm and one idea per shot; every frame stays inside an 8% side margin, and no more than three short text blocks compete at once. Radio is shown through abstract signal bars, cards, and arrows rather than device photography.

## Assumptions and open questions
- Defaults used: three equal 8.0 s shots, a 0.6 s crossfade between shots, 960 × 540 at 24 fps, and no music or sound effects.
- The source notes are treated as user-provided, uncited explanation. No independent verification was performed.
- The unsourced claim “Wi-Fi signals can travel up to 100 meters indoors” is omitted from the storyboard, Scene JSON, and narration. It appears only in the claims register and QA notes as an explicit omission.
- Narration timings are estimates at 2.5–3.0 English words per second. Actual TTS durations are unknown.
- No image, font, music, or voice asset was supplied. The plan uses text, cards, one icon, arrows, and a table only.
- Open question: should the 2.4 GHz / 5 GHz guidance be backed by a specific source? If yes, supply it before a verified version is attempted.
- Open question: if the 100 m figure is essential, supply a source with a URL and exact quotation for human review; otherwise it stays out.

## Shot table
| ID | Time (s) | Narrative goal | On-screen content | Animation / transition | Narration | Fact status |
|---|---|---|---|---|---|---|
| shot_01 | 0–8 | Frame Wi-Fi as a radio link, not a data cable | Kicker, title, subtitle, signal-bars icon, two cards, closing line | Fade and slide in; icon pop; crossfade out | “Wi-Fi carries data on radio waves, with no data cable between router and device.” | User-provided background; no verified claims |
| shot_02 | 8–16 | Show the router-to-adapter signal path | Flow row: Router → Radio signal → Adapter, with two arrows; closing note | Staggered fade/pop; arrow draws; crossfade out | “A router broadcasts data by radio. Your Wi-Fi adapter picks it up and exchanges data.” | User-provided source-note explanation; unverified |
| shot_03 | 16–24 | Compare the two common Wi-Fi bands | Three-column table plus a takeaway card | Table grid and cell stagger; takeaway fade; end hold | “2.4 GHz generally goes farther but is more crowded. 5 GHz is generally faster nearby.” | User-provided band comparison; unverified; 100 m claim omitted |

## Shot details

### shot_01 — Radio, not a cable
- **Visual elements:** Red kicker “A PRACTICAL PRIMER”; 56 px title “How Wi-Fi Works”; subtitle “Radio waves carry the data.”; a signal-bars icon; two cream cards, “No cable to the device” and “Two-way exchange”; footer “A router and a Wi-Fi adapter do the talking.”
- **Animation order:** Kicker fades 0.15–0.60 s; title slides in from 28 px left 0.30–0.90 s; subtitle fades 0.55–1.05 s; icon pops 0.80–1.30 s; left card slides 0.95–1.50 s; right card slides 1.10–1.65 s; footer fades 1.50–2.05 s.
- **Transition out:** Crossfade, 0.6 s, into shot_02.
- **Narration:** `n1` at 0.4 s; “Wi-Fi carries data on radio waves, with no data cable between router and device.” Estimated 4.7–5.6 s, ending by 6.0 s at the slowest estimate.
- **Risks:** The title and subtitle rely on the renderer’s default font, which was not supplied or measured. “No cable to the device” is scoped to the router–device Wi-Fi link, not the router’s internet uplink; the narration and QA notes make that scope explicit.
- **Fact status:** User-provided/background explanation. No independently verified claim; the QA notes label all on-screen explanatory content as user-provided/general knowledge.

### shot_02 — The signal path
- **Visual elements:** Kicker “THE SIGNAL PATH”; title “Router to adapter”; a five-child flow row containing three cards and two horizontal arrows. The cards read “Router — Connects to the internet,” “Radio signal — Carries the data,” and “Adapter — Picks it up.” Footer: “The router and device exchange data in both directions.”
- **Animation order:** Kicker fades 0.15–0.55 s; title fades 0.30–0.85 s; Router card fades 0.55–1.10 s; first arrow draws 0.85–1.25 s; Radio signal card pops 1.05–1.55 s; second arrow draws 1.55–1.95 s; Adapter card pops 1.75–2.25 s; footer fades 2.30–2.80 s.
- **Transition out:** Crossfade, 0.6 s, into shot_03.
- **Narration:** `n2` at 0.4 s within the shot (8.4 s absolute); “A router broadcasts data by radio. Your Wi-Fi adapter picks it up and exchanges data.” Estimated 5.0–6.0 s, ending by 14.4 s at the slowest estimate.
- **Risks:** The row’s five children leave roughly 51 px arrows and roughly 213 px outer cards at 960 px; 20 px text with a three-line cap should fit, but font metrics are unverified. Newlines in card text may wrap differently in the legacy renderer.
- **Fact status:** User-provided source-note explanation; no independent verification.

### shot_03 — Pick a band
- **Visual elements:** Kicker “CHOOSING A BAND”; title “2.4 GHz or 5 GHz?”; a three-column table with columns “Band,” “Reach,” and “Trade-off”; two data rows: 2.4 GHz / Generally farther / More crowded, and 5 GHz / Generally shorter / Generally faster; a cream takeaway card reading “Rule of thumb: 2.4 GHz for reach; 5 GHz for speed nearby.”
- **Animation order:** Kicker fades 0.15–0.50 s; title fades 0.30–0.80 s; table grid draws 0.30–0.80 s; six cells stagger from 0.80 s and finish by 2.20 s; takeaway card fades 2.35–2.85 s.
- **Transition out:** No outgoing transition; the final frame holds to 24.0 s.
- **Narration:** `n3` at 0.4 s within the shot (16.4 s absolute); “2.4 GHz generally goes farther but is more crowded. 5 GHz is generally faster nearby.” Estimated 5.0–6.0 s, ending by 22.4 s at the slowest estimate.
- **Risks:** The three-column table at 20 px with short cells must fit 806 px; “Generally shorter” may wrap if the renderer uses a wide font. The takeaway card is capped at two lines. The “generally” qualifiers must remain in any future revision.
- **Fact status:** User-provided band comparison; no independent verification. The 100 m indoor claim is not used.

## Narration and timing plan
| Segment | Scene | Offset (s) | Text | Estimated speech (s) | Risk |
|---|---|---|---|---|---|
| n1 | shot_01 | 0.4 | “Wi-Fi carries data on radio waves, with no data cable between router and device.” | 4.7–5.6 (14 words) | Low: 2.0 s of scene headroom at the slowest estimate |
| n2 | shot_02 | 0.4 | “A router broadcasts data by radio. Your Wi-Fi adapter picks it up and exchanges data.” | 5.0–6.0 (15 words) | Low: 1.6 s of headroom at the slowest estimate; actual TTS is unknown |
| n3 | shot_03 | 0.4 | “2.4 GHz generally goes farther but is more crowded. 5 GHz is generally faster nearby.” | 5.0–6.0 (15 words) | Low: 1.6 s of headroom at the slowest estimate; band names may synthesize unevenly |

Estimated total speech is 44 words, or 14.7–17.6 s at 2.5–3.0 words per second. With the planned offsets, the slowest estimated narration ends at 6.0 s, 14.4 s, and 22.4 s respectively; the segments do not overlap and all finish inside the 24.0 s canvas. These are estimates, not measured audio durations.

## Claims register
| ID | Statement | Status | Evidence | Used on screen? |
|---|---|---|---|---|
| brief-claim-01 (not in JSON) | “Wi-Fi signals can travel up to 100 meters indoors.” | Unverified; omitted | None supplied | No |
| source-note background (no claim IDs) | Radio waves carry data; a router broadcasts a radio signal; an adapter exchanges data; 2.4 GHz generally travels farther and is more crowded; 5 GHz generally offers more speed at shorter range. | User-provided and uncited; no independent verification | Brief source notes only | Yes, paraphrased in narration and visuals |

## Production notes
- Assets still required: none for this text-only plan. No image nodes, remote assets, or third-party files are referenced. Fonts and a TTS voice would be supplied by a local legacy installation if rendering were later approved.
- Decisions for the user: keep the 100 m figure omitted unless a real source is supplied and reviewed; decide whether the band comparison needs a named source; confirm the intended default font at 960 × 540.
- The Scene JSON uses a flow row in shot_02 and a table in shot_03, as briefed. It has not been run through the legacy validator.
