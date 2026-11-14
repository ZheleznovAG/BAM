# BAM Battle Lab v0.4 — test and playtest record

## Verified through connected GitHub and in-process JavaScript V8

- Read original resource bytes via GitHub base64: 100.ANI, 1000.ANI, 101.ANI and 100.PAL.
- Validated original header field values, 24-byte ResHeader, 18-byte CelHeader,
  four-frame offsets/dimensions in 1000.ANI, and 256 RGB entries in 100.PAL.
- Independent in-memory JavaScript pixel decoding of **four frames from
  DATA/1000.ANI + candidate palette DATA/100.PAL** produced a visually
  recognizable small hooded figure. A second decode of DATA/100.ANI + 100.PAL
  showed an original UI frame with a large index-254 green-key area. These
  previews validate the uncompressed indexed-pixel mapping, but not the exact
  Python CLI output or all palette pairings.
- The Python exporter and ten unittest cases are committed. **Python unit tests
  have NOT been run in an interpreter in this execution environment**; they must
  be run locally, and the CLI-exported PNGs must be visually inspected.
- 30/30 JavaScript logic scenarios executed successfully in isolated V8 using
  an adapter for node:test and node:assert/strict. Actual Node CLI test run
  is still necessary on the local machine.
- UI smoke in a mocked DOM/Canvas: initialization, Hunter command, Barrier
  activation, animation callbacks, upgrade overlay, upgrade choice and
  overlay closing all completed without exception. JS syntax parsed;
  HTML element IDs referenced by the script exist with no duplicate IDs.
- Actual Chromium/browser visual test NOT executed; no claim of production-ready UI.

## Automatic deterministic battle results (not human playtesting)

For fixed seeds 42, 2026, 345, 999, 0.5 second simulation steps:

| Bot policy | 42 | 2026 | 345 | 999 | Observation |
|---|---|---|---|---|---|
| Only initial army / no commands | lost wave 1 | stopped for upgrade after wave 1 | stopped for upgrade after wave 1 | stopped for upgrade after wave 1 | Very weak economy decisions |
| Mass Guardian + Summon + improvements | won 5 | won 5 | won 5 | won 5 | May be overpowered |
| Maintain 5 golems + Hunters/Channelers | won 5 | won 5 | won 5 | won 5 | Alternative winning path |
| Immediate altar + mostly Channelers | lost wave 3 | lost wave 3 | lost wave 3 | lost wave 3 | Building too early is risky |
| Reserve 7 golems + Hunters + altar + Channelers | won 5 | won 5 | won 5 | won 5 | More deliberate altar strategy works |

- Winning machine strategies took roughly **115–140 simulation seconds**, so the
  goal of a real 10–15 minute session is **not achieved**.
- Bots issue a command every 0.5 simulated second and have perfect state
  information: they are **not a substitute** for a human player.
- Real balance, readability, visual originality and desire to replay remain unknown.

## Local completion checklist

1. From the branch feature/bam-v04-assets-gameplay, run:
   - python -m unittest discover -s tools/tests -p test_bam_assets.py
   - python tools/bam_assets.py inspect DATA/100.ANI
   - python tools/bam_assets.py inspect DATA/100.PAL
   - python tools/bam_assets.py extract DATA/100.ANI --palette DATA/100.PAL --output .local/bam-assets/100
   - python tools/bam_assets.py gallery .local/bam-assets --output .local/bam-assets/index.html
2. Open .local/bam-assets/index.html: visually verify that extracted pixels,
   origin offsets and palette produce recognizable, non-corrupted frames.
3. Run: cd battle-lab && node --test sim.test.cjs
4. Open battle-lab/index.html in a real desktop Chromium/Edge browser.
5. Play twice, intentionally choosing different roles and timing of the altar,
   monitoring browser console errors, accessibility, clarity of effects and FPS.
6. Record: first confusing decision, moment of tactical satisfaction,
   frustration, outcome, match duration and desire to replay.

## Known limitations and next decision

- Python exporter supports only uncompressed CMP_NONE and no TLB/MIF.
  For CMP_T12/TRLE/SRLE, use the engine C++ source instead of heuristic
  guessing. The tool refuses unknown compression rather than writing damaged PNG.
- Art is not integrated into the public browser game and no converted original
  image is committed. Licensing permission has not been established.
- Avoid adding content until actual human playtest identifies the strongest
  moment and the weakest element. Highest-value follow-up is balancing
  class counters after real play, not introducing new frameworks.
