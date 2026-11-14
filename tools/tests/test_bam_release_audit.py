"""Unit tests for local BAM release comparison (no real game binaries required)."""
import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bam_release_audit as audit


def ani(pixels=b"\x01\x02\x03\x04"):
    cel = struct.pack("<iiHHHI", 0, 0, 2, 2, 0, 0)
    head = audit.RES_HEADER.pack(
        0, len(pixels), len(pixels), 1, 1, len(cel), 0, 0, 0, 0xFEFE)
    return head + cel + pixels


def put(root, name, payload):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(payload)
    return p


class BAMReleaseAuditTests(unittest.TestCase):
    def test_case_insensitive_logical_ids(self):
        self.assertEqual(audit.logical_key("DATA/1000.ANI"), "1000.ani")
        self.assertEqual(audit.logical_key("ani\\1000.ani"), "1000.ani")
        self.assertEqual(audit.category("sound/100.WAV"), "resource")
        self.assertEqual(audit.category("BAM.EXE"), "executable")

    def test_original_header_recognition(self):
        data = ani()
        h = audit.inspect_header("100.ANI", data[:24], len(data))
        self.assertEqual(h["status"], "header-recognized")
        self.assertEqual(h["subheaders"], 1)
        self.assertTrue(h["headers_consistent"])
        self.assertTrue(h["payload_consistent"])
        bad = audit.inspect_header("100.ANI", b"nope", 4)
        self.assertEqual(bad["status"], "short-header")

    def test_dos_executable_is_not_treated_as_proven_functionality(self):
        h = audit.inspect_header("BAM.EXE", b"MZ" + b"\x00" * 22, 24)
        self.assertTrue(h["valid_mz"])
        self.assertIn("candidate", h["kind"])
        self.assertFalse(audit.inspect_header("BAM.EXE", b"invalid", 7)["valid_mz"])

    def test_folder_hash_inventory_preserves_binary_differences(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "RU"
            put(root, "DATA/101.ANI", ani())
            put(root, "DATA/102.ANI", ani(b"\x01\x02\x04\x04"))
            put(root, "README.TXT", "Тест".encode("cp1251"))
            result = audit.scan_build("RU", root)
            self.assertEqual(len(result["files"]), 3)
            self.assertEqual(result["extensions"]["ANI"], 2)
            self.assertNotEqual(
                result["files"][0]["sha256"], result["files"][1]["sha256"])
            self.assertEqual(result["warnings"], [])

    def test_zip_scanned_without_extracting(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            zpath = root / "English.zip"
            with zipfile.ZipFile(zpath, "w") as z:
                z.writestr("GAME/100.ANI", ani())
                z.writestr("GAME/BAM.EXE", b"MZ" + b"\0" * 30)
                z.writestr("../unsafe.txt", "do not traverse")
            result = audit.scan_build("EN", zpath)
            self.assertEqual(result["source_type"], "zip")
            self.assertEqual(len(result["files"]), 2)
            self.assertEqual(len(result["warnings"]), 1)
            self.assertFalse((root / "GAME").exists())

    def test_same_named_different_payloads_report_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            put(root, "DATA/100.ANI", ani())
            put(root, "ALT/100.ani", ani(b"\x09\x08\x07\x06"))
            b = audit.scan_build("mixed", root)
            self.assertEqual(len(b["conflicts"]), 1)
            self.assertIn("100.ani", b["conflicts"])

    def test_diff_distinguishes_identical_changed_and_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            left, right = root / "left", root / "right"
            put(left, "DATA/100.ANI", ani())
            put(right, "ALT/100.ani", ani())
            put(left, "DATA/101.ANI", ani())
            put(right, "DATA/101.ANI", ani(b"\x09\x08\x07\x06"))
            put(left, "text/RU.SQB", b"RU")
            put(right, "text/EN.SQB", b"EN")
            builds = [audit.scan_build("left", left), audit.scan_build("right", right)]
            rows, pairs = audit.matrix(builds)
            by_key = {row["key"]: row for row in rows}
            self.assertEqual(by_key["100.ani"]["status"], "identical")
            self.assertEqual(by_key["101.ani"]["status"], "different-bytes")
            self.assertEqual(by_key["ru.sqb"]["status"], "missing-in-some")
            self.assertIn("en.sqb", pairs[0]["only_right"])

    def test_reports_are_written_outside_sources(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            left, right = root / "English", root / "Russian"
            put(left, "BAM.EXE", b"MZ" + b"\0" * 30)
            put(right, "BAM.EXE", b"MZ" + b"\1" * 30)
            put(left, "100.ANI", ani())
            put(right, "100.ANI", ani())
            report = audit.write_report(
                [audit.scan_build("EN", left), audit.scan_build("RU", right)],
                root / "outputs")
            self.assertEqual(len(report["pairs"]), 1)
            for filename in ["files.csv", "differences.csv", "summary.md", "report.json", "functional-checklist.csv"]:
                self.assertTrue((root / "outputs" / filename).is_file())
            self.assertIn("1/1", (root / "outputs" / "summary.md").read_text())
            self.assertIn("bam.exe", (root / "outputs" / "differences.csv").read_text(
                encoding="utf-8-sig"))
            functional = (root / "outputs" / "functional-checklist.csv").read_text(
                encoding="utf-8-sig")
            self.assertEqual(functional.count("not_tested"), 2 * len(audit.FUNCTIONAL_CHECKS))
            self.assertIn("save-load", functional)

    def test_from_dir_discovers_direct_children_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            releases = root / "releases"
            put(releases, "RU/DATA/1.ANI", ani())
            put(releases, "EN/DATA/1.ANI", ani())
            zpath = releases / "DE.zip"
            with zipfile.ZipFile(zpath, "w") as z:
                z.writestr("DATA/1.ANI", ani())
            out = root / "report"
            with contextlib.redirect_stdout(io.StringIO()):
                code = audit.run(["--from-dir", str(releases), "--out", str(out)])
            self.assertEqual(code, 0)
            doc = json.loads((out / "report.json").read_text(encoding="utf-8"))
            self.assertEqual({b["name"] for b in doc["builds"]}, {"RU", "EN", "DE"})

    def test_refuses_output_inside_a_compared_build(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            put(root, "RU/BAM.EXE", b"MZ" + b"\0"*10)
            put(root, "EN/BAM.EXE", b"MZ" + b"\0"*10)
            with contextlib.redirect_stderr(io.StringIO()):
                code = audit.run([
                    "--build", f"RU={root/'RU'}",
                    "--build", f"EN={root/'EN'}",
                    "--out", str(root / "RU" / "result")])
            self.assertEqual(code, 2)
            self.assertFalse((root / "RU" / "result").exists())

    def test_requires_two_different_builds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            root.mkdir(exist_ok=True)
            with contextlib.redirect_stderr(io.StringIO()):
                status = audit.run(["--build", f"same={root}"])
            self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
