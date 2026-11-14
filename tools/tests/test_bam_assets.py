"""Run: python -m unittest discover -s tools/tests -p 'test_bam_assets.py'"""
import importlib.util
import io
import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bam_assets.py"
SPEC = importlib.util.spec_from_file_location("bam_assets", SCRIPT)
assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assets)

def make_ani():
    a = b"\x00\x01\x02\xfe\x03\x04"
    b = b"\x05\x06\x07\x08"
    frames = (assets.CEL.pack(1, 2, 3, 2, 0, 0)
              + assets.CEL.pack(-3, 0, 2, 2, 0, 6))
    data = a + b
    return assets.RES.pack(0, len(data), len(data), 1, 2, len(frames),
                           0, 0, 0, 0xFEFE) + frames + data

def make_pal():
    data = b"".join(bytes((i, 255-i, i//2)) for i in range(256))
    return assets.RES.pack(0, len(data), len(data), 5, 0, 0,
                           0, 0, 0, 0xFEFE) + data

class ResourceTests(unittest.TestCase):
    def test_structure_lengths(self):
        self.assertEqual(assets.RES.size, 24)
        self.assertEqual(assets.CEL.size, 18)

    def test_ani_frames_and_origins(self):
        info = assets.parse(make_ani())
        self.assertEqual(info["frame_count"], 2)
        self.assertEqual(info["frames"][0]["width"], 3)
        self.assertEqual(info["frames"][0]["height"], 2)
        self.assertEqual(info["frames"][1]["origin_x"], -3)
        self.assertEqual(info["frames"][1]["offset"], 6)

    def test_palette_has_exactly_256_rgb_colors(self):
        pal = assets.colors(make_pal())
        self.assertEqual(len(pal), 256)
        self.assertEqual(pal[255], (255, 0, 127))

    def test_valid_rgba_png(self):
        raw = assets.png(b"\xfe\x02", 2, 1, assets.colors(make_pal()))
        self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
        size = struct.unpack(">I", raw[8:12])[0]
        self.assertEqual(size, 13)
        start = 8 + 12 + 13
        self.assertEqual(raw[start+4:start+8], b"IDAT")
        compressed = raw[start+8:start+8+struct.unpack(">I", raw[start:start+4])[0]]
        scanline = zlib.decompress(compressed)
        self.assertEqual(scanline[0], 0)
        self.assertEqual(scanline[4], 0)     # transparent skip index 254
        self.assertEqual(scanline[8], 255)   # regular index 2 opaque

    def test_truncated_and_bad_header_fail(self):
        with self.assertRaises(assets.BadResource):
            assets.parse(b"\x00\x01")
        with self.assertRaises(assets.BadResource):
            assets.parse(make_ani()[:-1])
        with self.assertRaises(assets.BadResource):
            assets.parse(make_ani()[:22] + b"\x00\x00" + make_ani()[24:])

    def test_unknown_compression_rejected(self):
        data = bytearray(make_ani())
        struct.pack_into("<H", data, 0, 2)
        with self.assertRaisesRegex(assets.BadResource, "unsupported compression"):
            assets.parse(data)

    def test_out_of_bounds_frame_rejected(self):
        data = bytearray(make_ani())
        struct.pack_into("<I", data, assets.RES.size + 14, 99999)
        with self.assertRaises(assets.BadResource):
            assets.parse(data)

    def test_local_extract_and_gallery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "DATA").mkdir()
            (root / "DATA" / "42.ANI").write_bytes(make_ani())
            (root / "DATA" / "42.PAL").write_bytes(make_pal())
            output = root / ".local" / "assets"
            assets.extract(root / "DATA" / "42.ANI",
                           root / "DATA" / "42.PAL", output / "42")
            manifest = json.loads((output / "42" / "metadata.json").read_text())
            self.assertEqual(len(manifest["frames"]), 2)
            self.assertEqual((output / "42" / "frame-000.png").read_bytes()[:8],
                             b"\x89PNG\r\n\x1a\n")
            assets.gallery(output, output / "index.html")
            self.assertIn("frame-000.png", (output / "index.html").read_text())
            assets.audit(root / "DATA", root / "docs" / "assets-audit.md")
            self.assertIn("42", (root / "docs" / "assets-audit.md").read_text())

    def test_gallery_path_traversal_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(assets.BadResource):
                assets.gallery(root, root.parent / "outside.html")

    def test_missing_file_fails(self):
        with self.assertRaises(assets.BadResource):
            assets.read(Path("/unavailable-bam-file-7283741.ani"))


    def test_catalog_decodes_previews_and_records_unsupported_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "DATA"
            source.mkdir()
            (source / "42.ANI").write_bytes(make_ani())
            (source / "42.PAL").write_bytes(make_pal())
            corrupt = bytearray(make_ani())
            struct.pack_into("<H", corrupt, 0, 2)
            (source / "43.ANI").write_bytes(corrupt)
            (source / "broken.ANI").write_bytes(b"not valid")
            catalog_dir = root / ".local" / "bam-assets" / "catalog"
            info = assets.catalog(source, source / "42.PAL", catalog_dir)
            self.assertEqual(info["total"], 3)
            self.assertEqual(info["supported"], 1)
            self.assertEqual(info["skipped"], 2)
            png_file = catalog_dir / "thumbs" / "42.png"
            self.assertEqual(png_file.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            html_data = (catalog_dir / "catalog.html").read_text(encoding="utf-8")
            self.assertIn("42.ANI", html_data)
            self.assertIn("43.ANI", html_data)
            self.assertIn('id="search"', html_data)
            self.assertIn('id="animated"', html_data)
            report = json.loads((catalog_dir / "catalog.json").read_text(encoding="utf-8"))
            self.assertEqual(report["resources"][0]["id"], "42")
            self.assertTrue(report["candidate_palette_only"])

    def test_catalog_limit_and_readonly_source_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / "DATA"
            src.mkdir()
            (src / "41.ANI").write_bytes(make_ani())
            (src / "42.ANI").write_bytes(make_ani())
            (src / "41.PAL").write_bytes(make_pal())
            out = root / ".local" / "bam-assets" / "catalog"
            report = assets.catalog(src, src / "41.PAL", out, limit=1)
            self.assertEqual(report["total"], 1)
            with self.assertRaises(assets.BadResource):
                assets.catalog(src, src / "41.PAL", src / "gallery")
            with self.assertRaises(assets.BadResource):
                assets.catalog(src, src / "41.PAL", out, limit=-1)

    def test_bind_generates_only_local_references_and_supports_buildings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / "DATA"
            game = root / "battle-lab"
            assets_dir = root / ".local" / "bam-assets"
            src.mkdir()
            game.mkdir()
            assets_dir.mkdir(parents=True)
            original = src / "42.ANI"
            original.write_bytes(make_ani())
            palette = src / "42.PAL"
            palette.write_bytes(make_pal())
            assets.extract(original, palette, assets_dir / "42")
            out = assets_dir / "asset-pack.js"
            pack = assets.bind(
                assets_dir, game, out, ["raider=42", "forge=42"], fps=7)
            self.assertEqual(pack["version"], 1)
            self.assertTrue(pack["localOnly"])
            self.assertEqual(pack["roles"]["raider"]["resourceId"], "42")
            self.assertEqual(len(pack["roles"]["raider"]["frames"]), 2)
            self.assertEqual(pack["roles"]["raider"]["fps"], 7)
            path = pack["roles"]["raider"]["frames"][0]["src"]
            self.assertEqual(path, "../.local/bam-assets/42/frame-000.png")
            script = out.read_text(encoding="utf-8")
            self.assertIn("window.BAM_LOCAL_ASSETS =", script)
            self.assertNotIn("http://", script)
            self.assertNotIn("https://", script)

    def test_bind_rejects_unknown_or_duplicate_roles_and_missing_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            game = root / "battle-lab"
            local = root / ".local" / "bam-assets"
            local.mkdir(parents=True)
            game.mkdir()
            out = local / "asset-pack.js"
            for mappings in (
                ["invalid=42"], ["raider=../../oops"], ["raider=999"],
                ["raider=42", "raider=42"]):
                with self.assertRaises(assets.BadResource):
                    assets.bind(local, game, out, mappings)

    def test_bind_refuses_output_outside_ignored_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = root / ".local" / "bam-assets"
            game = root / "battle-lab"
            local.mkdir(parents=True)
            game.mkdir()
            with self.assertRaises(assets.BadResource):
                assets.bind(local, game, root / "tracked.js", ["raider=42"])

    def test_bind_rejects_invalid_fps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = root / ".local" / "bam-assets"
            game = root / "battle-lab"
            local.mkdir(parents=True)
            game.mkdir()
            with self.assertRaises(assets.BadResource):
                assets.bind(local, game, local / "pack.js", ["raider=42"], fps=0)

if __name__ == "__main__":
    unittest.main()
