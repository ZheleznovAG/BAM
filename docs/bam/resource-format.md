# BAM/TIGRE resources — verified layout (research notes)

Source of truth: original code in CODE/TIGRE. This is **not** a new general-purpose decoder.

## Evidence and structure

- CODE/TIGRE/RES_CFG.HPP: RES_ANIM = 1 (.ANI), RES_PAL = 5 (.PAL), RES_TILELIB = 18 (.TLB), RES_MAP_INFO = 19 (.MIF).
- CODE/TIGRE/WRITERES.HPP: ResHeader, CelHeader, CMP_NONE = 0, CMP_T12 = 2, CMP_TRLE = 4, CMP_SRLE = 8, CMP_2_WIDE = 16.
- CODE/TIGRE/WRITERES.CPP: ResHeader, table of CelHeaders, then indexed image data.
- CODE/TIGRE/PALETTE.CPP: TPalette::Load copies 256 * sizeof(Gun) bytes.
- CODE/TIGRE/PALETTE.HPP: CI_SKIP = 254 (DOS); palette values are 8-bit color channels.
- CODE/TIGRE/COMP.CPP, TRLE.CPP, SRLE.CPP, T12.*: compressed resource variants.

**Real-file header checks using GitHub base64 byte reads:**

| Resource | Total bytes | comp | payload bytes | type | cels | headers |
|---|---:|---:|---:|---:|---:|---:|
| DATA/100.ANI | 128042 | 0 | 128000 | 1 | 1 | 18 |
| DATA/1000.ANI | 1392 | 0 | 1296 | 1 | 4 | 72 |
| DATA/101.ANI | 3264 | 0 | 3186 | 1 | 3 | 54 |
| DATA/100.PAL | 792 | 0 | 768 | 5 | 0 | 0 |

- Resource header: little-endian, 24 bytes, format H I I H H H 3H H; compType, uSize, size, type, numHeaders, sizeOfHeaders, data[3], genID (0xFEFE).
- Cel header: little-endian, 18 bytes, format i i H H H I; originX, originY, width, height, priority, offset.
- CEL coords are 32-bit signed, NOT 16-bit (verified against actual four frames of DATA/1000.ANI).
- ANI pixel payload: one unsigned palette index per pixel, no per-row padding for the inspected CMP_NONE examples. Each frame points to a contiguous segment starting at its CelHeader offset.
- Palette data after ResHeader is exactly 768 bytes (256 * RGB); not a 6-bit VGA byte triplet. Index 254 is the engine's skip/transparent index.
- Frame 1000.ANI offsets = 0, 272, 571, 896 and dimensions 17x16, 13x23, 13x25, 16x25; total 1296 bytes.

**Transparency:** alpha=0 for palette index 254, opaque for other indices. Origin values are retained in metadata.json as coordinates; they do not change the pixel crop itself.

## Explicit boundaries

- Extractor supports only CMP_NONE. Other compression combinations raise descriptive errors and DO NOT generate PNGs.
- No supported TLB/MIF export yet; these formats need separate investigation.
- ANI with compression or non-contiguous data is rejected instead of rendering guesses.
- Shared ANI/PAL numeric ID is only a potential pairing; the palette used by a scene should be verified visually.
- Files remain copyright of their respective rightsholders. Converted assets are **local only**.

## Commands

    python tools/bam_assets.py audit DATA --out docs/bam/assets-audit.md
    python tools/bam_assets.py inspect DATA/1000.ANI
    python tools/bam_assets.py inspect DATA/100.PAL
    python tools/bam_assets.py extract DATA/1000.ANI --palette DATA/100.PAL --output .local/bam-assets/1000
    python tools/bam_assets.py gallery .local/bam-assets --output .local/bam-assets/index.html
    python -m unittest discover -s tools/tests -p test_bam_assets.py

Output stays in the ignored local .local/bam-assets directory.
