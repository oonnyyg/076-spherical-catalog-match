import csv
import json
import os
import tempfile
import unittest

from sky_match.cli import main

HEADER = "id,ra_deg,dec_deg\n"


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.left = os.path.join(root, "left.csv")
        self.right = os.path.join(root, "right.csv")
        self.config = os.path.join(root, "config.json")
        self.outdir = os.path.join(root, "out")

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, path, text):
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)

    def _write_config(self, radius):
        payload = {"radius_arcsec": radius, "output_dir": self.outdir}
        self._write(self.config, json.dumps(payload))

    def test_end_to_end(self):
        self._write(self.left, HEADER + "L1,10.0,0.0\nL2,50.0,50.0\n")
        self._write(self.right, HEADER + "R1,10.0,0.0001\n")
        self._write_config(5.0)
        self.assertEqual(main([self.left, self.right, self.config]), 0)
        matches_path = os.path.join(self.outdir, "matches.csv")
        with open(matches_path, encoding="utf-8", newline="") as  fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual([r["left_id"] for r in rows], ["L1", "L2"])
        self.assertEqual(rows[0]["right_id"], "R1")
        self.assertEqual(rows[0]["mutual"], "true")
        self.assertEqual(rows[1]["right_id"], "")
        self.assertEqual(rows[1]["distance_arcsec"], "")
        with open(os.path.join(self.outdir, "summary.json"), encoding="utf-8") as fh:
            summary = json.load(fh)
        self.assertEqual(summary["matched"], 1)
        self.assertEqual(summary["unmatched"], 1)
        self.assertEqual(summary["mutual_pairs"], 1)

    def test_empty_right_table(self):
        self._write(self.left, HEADER + "L1,10.0,0.0\n")
        self._write(self.right, HEADER)
        self._write_config(5.0)
        self.assertEqual(main([self.left, self.right, self.config]), 0)
        matches_path = os.path.join(self.outdir, "matches.csv")
        with open(matches_path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(rows[0]["right_id"], "")

    def test_invalid_input_no_output(self):
        self._write(self.left, HEADER + "L1,999.0,0.0\n")
        self._write(self.right, HEADER)
        self._write_config(5.0)
        self.assertEqual(main([self.left, self.right, self.config]), 1)
        self.assertFalse(os.path.exists(self.outdir))

    def test_bad_radius_rejected(self):
        self._write(self.left, HEADER)
        self._write(self.right, HEADER)
        self._write_config(648000.1)
        self.assertEqual(main([self.left, self.right, self.config]), 1)
        self.assertFalse(os.path.exists(self.outdir))


if __name__ == "__main__":
    unittest.main()
