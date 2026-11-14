# BAM resources — inspected repository snapshot

Data source: original master tree in ZheleznovAG/BAM, read-only.

The DATA directory contains 842 entries on the inspected Git tree. The main file categories are:

| Extension | Count | Bytes | Interpretation |
|---|---:|---:|---|
| ANI | 475 | 3,326,450 | animation resources |
| WAV | 211 | 11,654,764 | audio |
| SQB | 97 | 98,534 | text/squib resources |
| PAL | 18 | 14,256 | RGB palettes |
| FON | 12 | 267,434 | fonts |
| HMP | 7 | 327,274 | music files |
| TLB | 3 | 1,199,093 | tile libraries |
| MIF | 3 | 174,964 | map information |

Other files and binary formats are not yet classified here; run the CLI for a complete, fresh inventory.

## First confirmed decodable samples

- DATA/100.ANI: CMP_NONE, one 320×400 frame
- DATA/1000.ANI: CMP_NONE, four indexed frames
- DATA/101.ANI: CMP_NONE, three indexed frames
- DATA/100.PAL: CMP_NONE, 256 RGB values

Their headers and byte spans were validated against binary content obtained from the repository. The CLI supports exporting these local CMP_NONE images, but **manual visual inspection of their pixel output has not yet been completed**.

## How to refresh

    python tools/bam_assets.py audit DATA --out docs/bam/assets-audit.md

The full dynamic audit includes IDs paired between .ANI and .PAL, aggregate sizes and links to original code. No original binaries, decoded PNGs or sounds should be committed.
