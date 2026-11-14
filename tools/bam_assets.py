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


# Local-only asset catalog and optional UI binding. No copyrighted PNG is committed.
SPRITE_ROLES = ("golem", "guardian", "hunter", "channeler",
                "soldier", "raider", "brute", "boss")


def resource_id(path: Path) -> tuple[int, str]:
    if not path.stem.isdecimal():
        raise BadResource(f"Not a numeric BAM resource ID: {path.name}")
    return (int(path.stem), path.stem)


def catalog(directory: Path, palette: Path, output: Path, limit: int = 0) -> dict:
    """Decode one preview per supported ANI; record unsupported files, never guess."""
    if not directory.is_dir():
        raise BadResource(f"Not a directory: {directory}")
    if limit < 0:
        raise BadResource("--limit must be >= 0")
    if output.resolve() == directory.resolve() or output.resolve().is_relative_to(directory.resolve()):
        raise BadResource("Catalog output must not be inside original DATA directory")
    rgb = colors(read(palette))
    files = sorted((p for p in directory.iterdir()
                    if p.is_file() and p.suffix.upper() == ".ANI"),
                   key=lambda p: (0, *resource_id(p)) if p.stem.isdecimal()
                   else (1, p.stem.casefold(), p.name))
    if limit:
        files = files[:limit]
    output.mkdir(parents=True, exist_ok=True)
    thumbs = output / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)
    entries = []
    supported = 0
    for src in files:
        item = {"id": src.stem, "name": src.name,
                "bytes": src.stat().st_size, "status": "unsupported"}
        try:
            if not src.stem.isdecimal():
                raise BadResource("Non-numeric resource name")
            data = read(src)
            info = parse(data, src.name)
            if info["type"] != ANI:
                raise BadResource("Not an animation resource")
            f = info["frames"][0]
            pixels = data[RES.size + info["header_size"] + f["offset"]:
                          RES.size + info["header_size"] + f["offset"] + f["length"]]
            name = src.stem + ".png"
            (thumbs / name).write_bytes(png(pixels, f["width"], f["height"], rgb))
            item.update(status="ok", frames=info["frame_count"],
                        width=f["width"], height=f["height"],
                        origin=[f["origin_x"], f["origin_y"]],
                        preview="thumbs/" + name)
            supported += 1
        except (BadResource, OSError, ValueError) as error:
            item["reason"] = str(error)
        entries.append(item)
    report = {
        "palette": palette.name,
        "candidate_palette_only": True,
        "total": len(entries),
        "supported": supported,
        "skipped": len(entries) - supported,
        "resources": entries
    }
    (output / "catalog.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cards = []
    for e in entries:
        ident = html.escape(e["id"], quote=True)
        if e["status"] == "ok":
            dimensions = str(e["width"]) + "×" + str(e["height"])
            img_src = html.escape(e["preview"], quote=True)
            image = '<img loading="lazy" src="' + img_src + '" alt="ANI ' + ident + '">'
            note = str(e["frames"]) + " кадров · " + dimensions
        else:
            image = '<div class="error-mark">Не декодировано</div>'
            note = html.escape(e.get("reason", "Unsupported"), quote=False)
        cards.append(
            '<article class="asset" data-id="' + ident +
            '" data-frames="' + str(e.get("frames", 0)) +
            '" data-ok="' + ("1" if e["status"] == "ok" else "0") +
            '">' + image + '<strong>' + ident + '.ANI</strong><small>' +
            note + '</small></article>'
        )
    page = String_catalog_html_header().replace("__TOTAL__", str(len(entries)))
    page += "\n".join(cards) + String_catalog_html_footer()
    (output / "catalog.html").write_text(page, encoding="utf-8")
    print(f"Catalog: {supported} preview(s), {len(entries)-supported} skipped "
          f"out of {len(entries)} -> {output / 'catalog.html'}")
    return report


def String_catalog_html_header() -> str:
    return """<!doctype html><html lang="ru"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BAM — локальный каталог анимаций</title>
<style>
body{margin:0;padding:22px;background:#101a22;color:#dce6ec;font:14px system-ui}
h1{font-size:26px;margin:0 0 8px}
p{color:#b3bfcb;max-width:780px;line-height:1.5}
.controls{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0 22px}
input[type=search]{min-width:220px;padding:10px;background:#263746;color:white;
 border:1px solid #63808e;border-radius:7px}
label{display:flex;gap:5px;align-items:center}
main{display:grid;grid-template-columns:repeat(auto-fill,minmax(145px,1fr));gap:12px}
.asset{padding:10px;background:#20303c;border:1px solid #364958;border-radius:8px;min-height:170px}
.asset img{max-width:100%;max-height:120px;min-height:80px;object-fit:contain;
 display:block;margin:0 auto 12px;image-rendering:pixelated}
.asset strong,.asset small{display:block;overflow-wrap:anywhere}
.asset small{color:#aebec9;margin-top:5px;font-size:11px}
.error-mark{color:#d89c9c;min-height:75px;padding-top:25px;text-align:center}
[hidden]{display:none!important}
code{color:#f2d39b}
</style>
<h1>Blood & Magic — каталог .ANI</h1>
<p>Все кадры декодированы из локальных ресурсов; цветовая палитра
предположительная. Оригинальные изображения не предназначены для
публикации без разрешения правообладателей.</p>
<div class="controls">
<input id="search" type="search" placeholder="Номер ресурса (напр. 1000)" autocomplete="off">
<label><input id="only-ok" type="checkbox"> Только декодированные</label>
<label><input id="animated" type="checkbox"> Несколько кадров</label>
<b id="count">__TOTAL__ ресурсов</b>
</div><main id="cards">"""


def String_catalog_html_footer() -> str:
    return """</main>
<script>
"use strict";
const cards = Array.from(document.querySelectorAll(".asset"));
const search = document.getElementById("search"),
  onlyOk = document.getElementById("only-ok"),
  animated = document.getElementById("animated"),
  count = document.getElementById("count");
function filter(){
 const q = search.value.trim().toLowerCase();
 let visible = 0;
 for (const card of cards) {
  const show = card.dataset.id.toLowerCase().includes(q) &&
    (!onlyOk.checked || card.dataset.ok === "1") &&
    (!animated.checked || Number(card.dataset.frames) > 1);
  card.hidden = !show;
  if (show) visible++;
 }
 count.textContent = visible + " из " + cards.length;
}
for(const input of [search,onlyOk,animated])
 input.addEventListener("input",filter);
filter();
</script></html>"""


def bind(assets: Path, game_dir: Path, output: Path,
         mappings: list[str], fps: int = 6) -> dict:
    """Build a local script referencing PNGs already exported by the user."""
    if not 1 <= fps <= 24:
        raise BadResource("FPS must be between 1 and 24")
    if not game_dir.is_dir():
        raise BadResource(f"Game directory not found: {game_dir}")
    if not assets.is_dir():
        raise BadResource(f"Extracted assets not found: {assets}")
    if not output.resolve().is_relative_to(assets.resolve()):
        raise BadResource("Asset pack JS must be inside the ignored assets directory")
    if not mappings:
        raise BadResource("Provide --map ROLE=ANI_ID, e.g. --map raider=1000")
    roles = {}
    for mapping in mappings:
        if mapping.count("=") != 1:
            raise BadResource(f"Invalid mapping {mapping!r}; expected ROLE=ANI_ID")
        role, resource = mapping.split("=")
        if role not in SPRITE_ROLES:
            raise BadResource(f"Unknown role {role!r}; expected {', '.join(SPRITE_ROLES)}")
        if role in roles:
            raise BadResource(f"Duplicate role mapping: {role}")
        if not resource.isdecimal():
            raise BadResource(f"Resource ID must be numeric: {resource!r}")
        folder = assets / resource
        metadata = folder / "metadata.json"
        if not metadata.is_file():
            raise BadResource(f"{metadata} missing. Run extract for ANI {resource} first.")
        info = json.loads(metadata.read_text(encoding="utf-8"))
        frames = info.get("frames", [])
        if (not frames or len(frames) > MAX_FRAMES or
                info.get("resource_id") != resource):
            raise BadResource(f"Bad frame metadata: {metadata}")
        entries = []
        for frame in frames:
            index = frame.get("index")
            filename = frame.get("png")
            if (not isinstance(index, int) or not isinstance(filename, str) or
                    filename != f"frame-{index:03d}.png"):
                raise BadResource(f"Invalid frame reference in {metadata}")
            png_file = folder / filename
            if not png_file.is_file():
                raise BadResource(f"Missing PNG: {png_file}")
            if png_file.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
                raise BadResource(f"Invalid PNG signature: {png_file}")
            from_game = Path(__import__("os").path.relpath(png_file, game_dir))
            url = from_game.as_posix()
            entries.append({"src": url, "width": frame["width"],
                            "height": frame["height"],
                            "originX": frame["origin_x"],
                            "originY": frame["origin_y"]})
        roles[role] = {"resourceId": resource, "fps": fps, "frames": entries}
    pack = {"version": 1, "localOnly": True, "roles": roles}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "/* Generated local sprite bindings. Do NOT commit extracted art. */\n"
        "window.BAM_LOCAL_ASSETS = " + json.dumps(pack, ensure_ascii=False, indent=2)
        + ";\n", encoding="utf-8"
    )
    print(f"Bound {len(roles)} role(s) to {output}")
    return pack

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
    cat = sub.add_parser("catalog", help="Catalog all supported ANI previews, skipping unsupported formats")
    cat.add_argument("path", type=Path)
    cat.add_argument("--palette", required=True, type=Path)
    cat.add_argument("--output", required=True, type=Path)
    cat.add_argument("--limit", type=int, default=0)
    bd = sub.add_parser("bind", help="Generate local opt-in sprite mapping for Battle Lab")
    bd.add_argument("--assets", required=True, type=Path)
    bd.add_argument("--game", default=Path("battle-lab"), type=Path)
    bd.add_argument("--output", required=True, type=Path)
    bd.add_argument("--map", action="append", dest="mappings", required=True)
    bd.add_argument("--fps", type=int, default=6)
    opts = parser.parse_args()
    try:
        if opts.cmd == "audit": audit(opts.path, opts.out)
        elif opts.cmd == "inspect": inspect(opts.path)
        elif opts.cmd == "extract": extract(opts.path, opts.palette, opts.output)
        elif opts.cmd == "gallery": gallery(opts.path, opts.output)
        elif opts.cmd == "catalog":
            catalog(opts.path, opts.palette, opts.output, opts.limit)
        elif opts.cmd == "bind":
            bind(opts.assets, opts.game, opts.output, opts.mappings, opts.fps)
        return 0
    except (BadResource, OSError, ValueError) as err:
        print(f"bam-assets: {err}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
