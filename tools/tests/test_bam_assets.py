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

if __name__ == "__main__":
    unittest.main()
