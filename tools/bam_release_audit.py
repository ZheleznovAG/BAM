#!/usr/bin/env python3
"""Read-only inventory and comparison of Blood & Magic DOS release builds.

Inputs: unpacked release directories or .zip archives. No executables are run,
no binaries extracted, and no source material is modified. Python 3.10+ stdlib.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import struct
import sys
import zipfile
from contextlib import closing
from pathlib import Path, PurePosixPath

ASSETS = frozenset("ANI PAL SQB WAV HMP FON TLB MIF DAT BNK SMK FLC".split())
TEXT = frozenset("TXT INI CFG BAT DOC LNG STR NFO".split())
EXEC = frozenset("EXE COM DLL OVL DRV".split())
INTERESTING = ASSETS | TEXT | EXEC
RES_HEADER = struct.Struct("<HIIHHH3HH")  # TIGRE 24-byte resource header
EXPECTED_TYPES = {"ANI": 1, "PAL": 5, "FON": 7, "SQB": 8,
                  "TLB": 18, "MIF": 19}
MAX_ENTRY = 512 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


class AuditError(ValueError):
    pass


def logical_key(filename: str) -> str:
    """Match file names case-insensitively, independent of installer folder."""
    return PurePosixPath(filename.replace("\\", "/")).name.casefold()


def category(filename: str) -> str:
    ext = PurePosixPath(filename).suffix[1:].upper()
    if ext in ASSETS:
        return "resource"
    if ext in EXEC:
        return "executable"
    if ext in TEXT:
        return "documentation/localization"
    return "other"


def inspect_header(filename: str, head: bytes, size: int) -> dict:
    ext = PurePosixPath(filename).suffix[1:].upper()
    if ext == "EXE":
        return {"kind": "DOS-MZ/Windows-PE-candidate" if head[:2] == b"MZ"
                else "unknown-executable",
                "valid_mz": head[:2] == b"MZ"}
    if ext == "WAV":
        return {"kind": "RIFF-WAVE" if head[:4] == b"RIFF" and head[8:12] == b"WAVE"
                else "unknown-WAV"}
    if ext not in EXPECTED_TYPES:
        return {}
    if size < RES_HEADER.size:
        return {"kind": "TIGRE", "status": "short-header"}
    (comp, usize, compressed, typ, n, headers, d0, d1, d2,
     generation) = RES_HEADER.unpack_from(head)
    expected = EXPECTED_TYPES[ext]
    status = "header-recognized" if generation == 0xFEFE and typ == expected else "unrecognized-header"
    info = {"kind": "TIGRE", "status": status, "compression": comp,
            "uncompressed_bytes": usize, "stored_bytes": compressed,
            "resource_type": typ, "subheaders": n,
            "subheader_bytes": headers, "generation": generation}
    if status == "header-recognized" and ext == "ANI":
        info["headers_consistent"] = n > 0 and headers == n * 18
        if comp == 0:
            info["payload_consistent"] = size == 24 + headers + usize
    if status == "header-recognized" and ext == "PAL" and comp == 0:
        info["palette_consistent"] = (size == 24 + 768 and usize == 768)
    return info


def hash_fileobj(fileobj, expected_size: int):
    digest = hashlib.sha256()
    head = bytearray()
    total = 0
    while True:
        block = fileobj.read(CHUNK_SIZE)
        if not block:
            break
        total += len(block)
        if total > MAX_ENTRY or total > expected_size:
            raise AuditError("Entry exceeded reported size or size limit")
        digest.update(block)
        if len(head) < 24:
            head.extend(block[:24 - len(head)])
    if total != expected_size:
        raise AuditError("Entry size changed during scan")
    return digest.hexdigest(), bytes(head)


def entry(name: str, size: int, digest: str, head: bytes, container: str) -> dict:
    suffix = PurePosixPath(name).suffix[1:].upper()
    return {"name": name, "key": logical_key(name), "extension": suffix,
            "category": category(name), "bytes": size, "sha256": digest,
            "container": container, "header": inspect_header(name, head, size)}


def safe_archive_name(name: str) -> bool:
    if "\\" in name or name.startswith("/"):
        return False
    parts = PurePosixPath(name).parts
    return bool(parts) and all(p not in (".", "..") for p in parts)


def scan_directory(root: Path) -> tuple[list[dict], list[str]]:
    found, warnings = [], []
    for p in sorted(root.rglob("*"), key=lambda x: str(x).casefold()):
        if p.is_symlink():  # Do not follow links to other drives / unrelated folders.
            warnings.append(f"Skipped symlink: {p.relative_to(root)}")
            continue
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        try:
            size = p.stat().st_size
            if size > MAX_ENTRY:
                raise AuditError("File exceeds 512 MiB safety limit")
            with p.open("rb") as stream:
                digest, head = hash_fileobj(stream, size)
            found.append(entry(rel, size, digest, head, "directory"))
        except (AuditError, OSError) as exc:
            warnings.append(f"Skipped {rel}: {exc}")
    return found, warnings


def scan_zip(src: Path) -> tuple[list[dict], list[str]]:
    found, warnings = [], []
    with zipfile.ZipFile(src) as archive:
        for info in sorted(archive.infolist(), key=lambda x: x.filename.casefold()):
            if info.is_dir():
                continue
            name = info.filename
            if not safe_archive_name(name):
                warnings.append(f"Skipped unsafe ZIP entry: {name!r}")
                continue
            if info.file_size > MAX_ENTRY:
                warnings.append(f"Skipped oversized ZIP entry: {name}")
                continue
            # ZIP encryption, corruption and malformed entries are reported.
            try:
                with archive.open(info, "r") as stream:
                    digest, head = hash_fileobj(stream, info.file_size)
                found.append(entry(name, info.file_size, digest, head, "zip"))
            except (AuditError, OSError, RuntimeError, ValueError,
                    zipfile.BadZipFile) as exc:
                warnings.append(f"Skipped ZIP entry {name}: {exc}")
    return found, warnings


def scan_build(name: str, root: Path) -> dict:
    if not root.exists():
        raise AuditError(f"Build {name!r} does not exist: {root}")
    if root.is_dir():
        files, warnings = scan_directory(root)
        source_type = "directory"
    elif root.is_file() and root.suffix.casefold() == ".zip":
        files, warnings = scan_zip(root)
        source_type = "zip"
    else:
        raise AuditError(f"Build {name!r} must be a folder or ZIP: {root}")
    by_key = collections.defaultdict(list)
    by_ext = collections.Counter()
    for f in files:
        by_key[f["key"]].append(f)
        by_ext[f["extension"] or "<none>"] += 1
    conflicts = {key: [f["name"] for f in values]
                 for key, values in by_key.items()
                 if len({f["sha256"] for f in values}) > 1}
    return {"name": name, "root": str(root), "source_type": source_type,
            "files": files, "warnings": warnings, "extensions": dict(sorted(by_ext.items())),
            "conflicts": conflicts}


def signature_group(build: dict) -> dict[str, set[str]]:
    groups = collections.defaultdict(set)
    for f in build["files"]:
        groups[f["key"]].add(f["sha256"])
    return dict(groups)


def resource_set(build: dict, ext: str) -> set[str]:
    return {f["key"] for f in build["files"] if f["extension"] == ext}


def matrix(builds: list[dict]) -> tuple[list[dict], list[dict]]:
    by_build = {b["name"]: signature_group(b) for b in builds}
    keys = sorted(set().union(*(m.keys() for m in by_build.values())))
    rows = []
    for key in keys:
        present = [name for name, mapping in by_build.items() if key in mapping]
        hashes = [tuple(sorted(by_build[name][key])) for name in present]
        state = "missing-in-some" if len(present) < len(builds) else (
            "identical" if len(set(hashes)) == 1 else "different-bytes")
        ext = PurePosixPath(key).suffix[1:].upper()
        rows.append({"key": key, "extension": ext, "category": category(key),
                     "status": state,
                     "builds": {name: {
                         "present": key in by_build[name],
                         "sha256": sorted(by_build[name].get(key, []))
                     } for name in by_build}})
    pairs = []
    for i, left in enumerate(builds):
        for right in builds[i+1:]:
            L, R = by_build[left["name"]], by_build[right["name"]]
            common = set(L) & set(R)
            pairs.append({
                "left": left["name"], "right": right["name"],
                "only_left": sorted(set(L) - set(R)),
                "only_right": sorted(set(R) - set(L)),
                "same_bytes": sorted(k for k in common if L[k] == R[k]),
                "different_bytes": sorted(k for k in common if L[k] != R[k])
            })
    return rows, pairs


def md_safe(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def write_report(builds: list[dict], out: Path) -> dict:
    rows, pairs = matrix(builds)
    out.mkdir(parents=True, exist_ok=True)
    headers = "ANI PAL SQB WAV HMP FON TLB MIF EXE COM".split()
    union = {ext: set().union(*(resource_set(b, ext) for b in builds))
             for ext in headers}
    report = {"schema_version": 1, "builds": builds, "matrix": rows,
              "pairs": pairs, "extension_union": {k: len(v) for k,v in union.items()},
              "disclaimer": "Counts indicate observed file coverage, not functional completeness"}
    (out / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (out / "files.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        w = csv.writer(stream)
        w.writerow(["build","path","logical_key","type","bytes","sha256","format_status","compression","subheaders"])
        for b in builds:
            for f in b["files"]:
                h = f["header"]
                w.writerow([b["name"], f["name"], f["key"], f["extension"],
                            f["bytes"], f["sha256"], h.get("status", h.get("kind", "")),
                            h.get("compression", ""), h.get("subheaders", "")])
    with (out / "differences.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        w = csv.writer(stream)
        w.writerow(["logical_key", "extension", "status", *[b["name"] for b in builds]])
        for row in rows:
            w.writerow([row["key"], row["extension"], row["status"]] + [
                ",".join(h[:16] for h in row["builds"][b["name"]]["sha256"]) or "MISSING"
                for b in builds])
    lines = ["# Blood & Magic — release and localization inventory", "",
             "**Read-only static audit.** The script never executes EXE/COM files.",
             "Counts only establish which files and bytes are available, **not whether a game feature works**.",
             "",
             "## Build overview", "",
             "| Build | Files | Logical names | Asset files | Total MiB | Warnings |",
             "|---|---:|---:|---:|---:|---:|"]
    for b in builds:
        lines.append("| {} | {} | {} | {} | {:.1f} | {} |".format(
            md_safe(b["name"]), len(b["files"]), len(signature_group(b)),
            sum(1 for f in b["files"] if f["extension"] in ASSETS),
            sum(f["bytes"] for f in b["files"]) / (1024*1024),
            len(b["warnings"])))
    lines += ["", "## Resource coverage relative to ALL supplied builds",
              "", "Values are unique case-insensitive file names / union of names, not quality scores.",
              "", "| Build | " + " | ".join(headers) + " |",
              "|---|" + "|".join(["---:"] * len(headers)) + "|"]
    for b in builds:
        columns = [f"{len(resource_set(b, ext))}/{len(union[ext])}"
                   for ext in headers]
        lines.append("| " + md_safe(b["name"]) + " | " + " | ".join(columns) + " |")
    lines += ["", "## Pairwise differences", ""]
    for pair in pairs:
        lines += [
            f"### {md_safe(pair['left'])} vs {md_safe(pair['right'])}",
            f"Same bytes: {len(pair['same_bytes'])}; different bytes: {len(pair['different_bytes'])}; "
            f"only {md_safe(pair['left'])}: {len(pair['only_left'])}; only {md_safe(pair['right'])}: {len(pair['only_right'])}.",
            ""
        ]
        for label, values in [
            ("Only left", pair["only_left"]), ("Only right", pair["only_right"]),
            ("Changed content", pair["different_bytes"])]:
            if values:
                lines.append(f"**{label}** ({len(values)}): " +
                             ", ".join(md_safe(x) for x in values[:45]) +
                             (" ... (see differences.csv)" if len(values) > 45 else ""))
                lines.append("")
        localization = [x for x in pair["different_bytes"]
                        if PurePosixPath(x).suffix[1:].upper() in
                        {"SQB", "TXT", "LNG", "FON", "PAL", "INI"}]
        if localization:
            lines.append("Localization/visual candidates (requires semantic inspection): " +
                         ", ".join(md_safe(x) for x in localization[:30]))
            lines.append("")
    lines += ["## Integrity and filename collisions", ""]
    for b in builds:
        interesting = [(f["name"],f["header"]) for f in b["files"] if
                       f["header"].get("status") not in (None,"header-recognized") or
                       f["header"].get("headers_consistent") is False or
                       f["header"].get("payload_consistent") is False or
                       f["header"].get("palette_consistent") is False]
        lines.append(f"### {md_safe(b['name'])}")
        lines.append(f"- Duplicate logical names with DIFFERENT bytes: {len(b['conflicts'])}.")
        lines.append(f"- Suspicious headers: {len(interesting)}.")
        lines.append(f"- Skipped/unreadable: {len(b['warnings'])}.")
        for key, names in list(b["conflicts"].items())[:10]:
            lines.append(f"  - Conflict {md_safe(key)}: " +
                         ", ".join(md_safe(n) for n in names))
        for key, h in interesting[:10]:
            lines.append(f"  - Header {md_safe(key)}: {h.get('status','invalid span')}")
        for w in b["warnings"][:10]:
            lines.append(f"  - Warning: {md_safe(w)}")
        lines.append("")
    lines += ["## What this does NOT prove", "",
              "- EXE/DOS version differences mean differing binaries, not confirmed extra features.",
              "- Different SQB, fonts, palettes and text may be intentional localization.",
              "- A larger file count can mean duplicate/corrupt/beta files, not a more complete game.",
              "- No conclusion is possible about menus, missions, multiplayer, cutscenes, music or crashes",
              "  until a controlled DOSBox runtime test is performed for each candidate build.",
              "- ZIP contents are hashed without extraction; nested archives and ISO/7z/RAR are not expanded.",
              "",
              "## Suggested next stage", "",
              "1. Review report.json and differences.csv; group builds with identical EXE fingerprints.",
              "2. Verify suspect/changed animations, palettes, maps, scripts and missing audio.",
              "3. Select the most complete asset set, but keep language-specific resources together.",
              "4. Run the same mission/menu/save/restore/audio/input smoke checklist in isolated DOSBox",
              "   using separate copies of each build. Log evidence and screenshots.",
              "5. Choose a base release only after static and runtime evidence agree.",
              ""]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def parse_build(spec: str) -> tuple[str, Path]:
    if "=" not in spec:
        raise AuditError("Each --build must be NAME=PATH")
    name, value = spec.split("=", 1)
    if not name.strip() or not value.strip():
        raise AuditError("Build name/path cannot be empty")
    if any(c in name for c in "\\/\r\n|"):
        raise AuditError("Use a short build name without paths, pipes or line breaks")
    return name.strip(), Path(value.strip()).expanduser().resolve()


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="append", required=True,
                        help='Build folder or ZIP: --build "RU=C:\\Games\\BAM-RU"')
    parser.add_argument("--out", type=Path, default=Path(".local/bam-release-audit"))
    opts = parser.parse_args(argv)
    try:
        specs = [parse_build(s) for s in opts.build]
        if len(specs) < 2:
            raise AuditError("At least two --build entries are required")
        if len({name.casefold() for name, _ in specs}) != len(specs):
            raise AuditError("Build names must be unique")
        out = opts.out.resolve()
        for name, source in specs:
            if source.is_dir() and out.is_relative_to(source):
                raise AuditError(f"Output must be outside compared build folder: {name}")
            if out == source:
                raise AuditError("Output may not replace an original file")
        builds = [scan_build(name, root) for name, root in specs]
        result = write_report(builds, out)
        print(f"Compared {len(builds)} builds, {len(result['matrix'])} logical names.")
        print(f"Results: {out / 'summary.md'}")
        print(f"Data: {out / 'report.json'}, files.csv, differences.csv")
        if any(b["warnings"] for b in builds):
            print("Some files were skipped; inspect summary.md warnings.")
        return 0
    except (AuditError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"bam-release-audit: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(run())
