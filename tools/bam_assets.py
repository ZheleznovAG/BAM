#!/usr/bin/env python3
"""Inspect BAM resource headers; export verified CMP_NONE ANI to local RGBA PNG.

Reference: CODE/TIGRE/WRITERES.HPP, WRITERES.CPP, PALETTE.CPP.
Python 3.10+ standard library only. Original resource files are read-only.
"""
from __future__ import annotations
import argparse
import collections
import html
import json
import struct
import sys
import zlib
from pathlib import Path

RES = struct.Struct("<HIIHHH3HH")     # 24 bytes, little-endian Watcom layout
CEL = struct.Struct("<iiHHHI")        # 18 bytes: int32 x/y, uint16 w/h/priority, uint32 offset
SKIP, GEN, ANI, PAL = 254, 0xFEFE, 1, 5
MAX_BYTES, MAX_FRAMES, MAX_SIDE, MAX_PIXELS = 64_000_000, 1024, 4096, 20_000_000

class BadResource(ValueError):
    pass

def read(path: Path) -> bytes:
    if not path.is_file():
        raise BadResource(f"Not a file: {path}")
    if path.stat().st_size > MAX_BYTES:
        raise BadResource("Input too large")
    return path.read_bytes()

def parse(data: bytes, name: str = "<memory>") -> dict:
    if len(data) < RES.size:
        raise BadResource(f"{name}: truncated ResHeader")
    cmp_, usize, csize, kind, count, hs, d0, d1, d2, gen = RES.unpack_from(data)
    if gen != GEN:
        raise BadResource(f"{name}: invalid generation 0x{gen:04x}")
    if count > MAX_FRAMES or hs > MAX_BYTES:
        raise BadResource(f"{name}: impossible header size/count")
    if count and hs != CEL.size * count:
        raise BadResource(f"{name}: {count} cels but {hs} header bytes")
    if RES.size + hs > len(data):
        raise BadResource(f"{name}: truncated CelHeader table")
    if cmp_ != 0:
        raise BadResource(f"{name}: unsupported compression 0x{cmp_:04x} (see COMP/TRLE/SRLE/T12 in CODE/TIGRE)")
    body = data[RES.size + hs:]
    if len(body) != usize or (csize and csize != len(body)):
        raise BadResource(f"{name}: payload {len(body)} != {usize} / {csize}")
    frames = []
    if kind == ANI:
        if not count:
            raise BadResource(f"{name}: animation has no frames")
        for i in range(count):
            x, y, w, h, priority, offset = CEL.unpack_from(data, RES.size + i * CEL.size)
            if not w or not h or w > MAX_SIDE or h > MAX_SIDE or w * h > MAX_PIXELS:
                raise BadResource(f"{name}: invalid frame dimensions {w}x{h}")
            if offset + w * h > len(body):
                raise BadResource(f"{name}: frame {i} exceeds payload")
            frames.append(dict(index=i, origin_x=x, origin_y=y, width=w, height=h,
                               priority=priority, offset=offset, length=w * h))
        spans = sorted((f["offset"], f["offset"] + f["length"]) for f in frames)
        if spans[0][0] or spans[-1][1] != len(body) or any(
            spans[i][1] != spans[i + 1][0] for i in range(len(spans) - 1)
        ):
            raise BadResource(f"{name}: noncontiguous/overlapping frames")
    if kind == PAL and (count or hs or len(body) != 768):
        raise BadResource(f"{name}: expected 256 RGB triplets")
    return dict(type=kind, compression=cmp_, payload_size=usize,
                frames=frames, frame_count=count, header_size=hs)

def colors(data: bytes) -> list[tuple[int, int, int]]:
    if parse(data)["type"] != PAL:
        raise BadResource("Not a RES_PAL resource")
    p = data[RES.size:]
    return [tuple(p[i:i+3]) for i in range(0, 768, 3)]

def chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(
        ">I", zlib.crc32(kind + data) & 0xffffffff)

def png(pixels: bytes, w: int, h: int, pal: list[tuple[int, int, int]]) -> bytes:
    if len(pixels) != w * h or len(pal) != 256:
        raise BadResource("Invalid indexed image or palette")
    raw = bytearray()
    for row in range(h):
        raw.append(0)  # PNG filter NONE
        for idx in pixels[row * w:(row + 1) * w]:
            raw.extend(pal[idx])
            raw.append(0 if idx == SKIP else 255)
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            chunk(b"IEND", b""))

def audit(directory: Path, output: Path) -> None:
    if not directory.is_dir():
        raise BadResource(f"Not a directory: {directory}")
    entries = sorted((p for p in directory.rglob("*") if p.is_file()),
                     key=lambda p: str(p).lower())
    groups = collections.defaultdict(list)
    for p in entries:
        groups[p.suffix.upper() or "<none>"].append(p)
    paired = sorted(set(p.stem for p in groups.get(".ANI", [])) &
                    set(p.stem for p in groups.get(".PAL", [])))
    lines = ["# BAM original resources audit", "",
             f"Read-only path: {directory}. Total: {len(entries)} files.", "",
             "| Extension | Count | Bytes | Examples | Status |",
             "|---|---:|---:|---|---|"]
    known = {".ANI": "animation", ".PAL": "palette", ".WAV": "audio",
             ".SQB": "text resource", ".TLB": "tile library",
             ".MIF": "map info", ".FON": "font"}
    for ext, files in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        lines.append("| {} | {} | {} | {} | {} |".format(
            ext, len(files), sum(p.stat().st_size for p in files),
            ", ".join(p.stem for p in files[:4]), known.get(ext, "unknown")))
    lines += ["", "Matching ANI/PAL IDs (candidate matches only): " +
              (", ".join(paired) or "none"), "",
              "## References in original C++",
              "- CODE/TIGRE/RES_CFG.HPP: extension/type",
              "- CODE/TIGRE/WRITERES.HPP: ResHeader, CelHeader, flags",
              "- CODE/TIGRE/WRITERES.CPP: resource write order",
              "- CODE/TIGRE/PALETTE.CPP: RGB palette",
              "- CODE/TIGRE/PALETTE.HPP: CI_SKIP 254",
              "- CODE/TIGRE/COMP.CPP, TRLE.CPP, SRLE.CPP, T12.*: compression",
              "", "Unsupported formats are recorded as unknown, not guessed."]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Audited {len(entries)} files -> {output}")

def inspect(path: Path) -> None:
    data = read(path)
    info = parse(data, str(path))
    if info["type"] == PAL:
        p = colors(data)
        info["palette"] = dict(entries=len(p), transparent_index=SKIP,
                               first=p[:5], last=p[-3:])
    print(json.dumps(info, ensure_ascii=False, indent=2))

def extract(path: Path, palette: Path, output: Path) -> None:
    if output.resolve() in (path.resolve(), palette.resolve()):
        raise BadResource("Output cannot replace an original resource")
    src, info = read(path), None
    info = parse(src, str(path))
    if info["type"] != ANI:
        raise BadResource("Only RES_ANIM can be extracted")
    pal = colors(read(palette))
    output.mkdir(parents=True, exist_ok=True)
    base = RES.size + info["header_size"]
    manifest = dict(source=str(path), palette=str(palette),
                    resource_id=path.stem, compression="CMP_NONE",
                    transparent_index=SKIP, frames=[])
    for f in info["frames"]:
        pixels = src[base + f["offset"]:base + f["offset"] + f["length"]]
        name = f"frame-{f['index']:03d}.png"
        (output / name).write_bytes(png(pixels, f["width"], f["height"], pal))
        manifest["frames"].append({**f, "png": name})
    (output / "metadata.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Extracted {len(info['frames'])} frames -> {output}")

def gallery(directory: Path, output: Path) -> None:
    if not directory.is_dir():
        raise BadResource(f"Not a directory: {directory}")
    images = sorted(directory.rglob("frame-*.png"))
    if not output.resolve().is_relative_to(directory.resolve()):
        raise BadResource("Gallery output must be inside image directory")
    cards = []
    for p in images[:500]:
        link = html.escape(p.relative_to(output.parent).as_posix(), quote=True)
        caption = html.escape(p.relative_to(directory).as_posix())
        cards.append(f'<figure><img loading="lazy" src="{link}"><figcaption>{caption}</figcaption></figure>')
    page = ('<!doctype html><meta charset="utf-8"><title>BAM local assets</title>'
            '<style>body{background:#141b25;color:#eee;font:15px system-ui}'
            'main{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:1em}'
            'figure{padding:1em;background:#283544;margin:0}'
            'img{max-width:100%;image-rendering:pixelated}</style>'
            '<h1>BAM original resources — local research only</h1>'
            '<p>Do not redistribute these images without permission.</p><main>' +
            "\n".join(cards) + '</main>')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8")
    print(f"Gallery: {len(cards)} images -> {output}")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit"); a.add_argument("path", type=Path)
    a.add_argument("--out", required=True, type=Path)
    i = sub.add_parser("inspect"); i.add_argument("path", type=Path)
    x = sub.add_parser("extract"); x.add_argument("path", type=Path)
    x.add_argument("--palette", required=True, type=Path)
    x.add_argument("--output", required=True, type=Path)
    g = sub.add_parser("gallery"); g.add_argument("path", type=Path)
    g.add_argument("--output", required=True, type=Path)
    opts = parser.parse_args()
    try:
        if opts.cmd == "audit": audit(opts.path, opts.out)
        elif opts.cmd == "inspect": inspect(opts.path)
        elif opts.cmd == "extract": extract(opts.path, opts.palette, opts.output)
        elif opts.cmd == "gallery": gallery(opts.path, opts.output)
        return 0
    except (BadResource, OSError, ValueError) as err:
        print(f"bam-assets: {err}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
