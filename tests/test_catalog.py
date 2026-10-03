import os
import tempfile
import unittest

from sky_match.catalog import load_catalog

HEADER = "id,ra_deg,dec_deg\n"


class LoadCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "cat.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text):
        with open(self.path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)

    def test_valid_catalog(self):
        self._write(HEADER + "a,0.0,-90.0\nb,359.999,90.0\n")
        sources = load_catalog(self.path)
        self.assertEqual([s.source_id for s in sources], ["a", "b"])

    def test_empty_catalog_allowed(self):
        self._write(HEADER)
        self.assertEqual(load_catalog(self.path), [])

    def test_duplicate_id_rejected(self):
        self._write(HEADER + "a,1.0,1.0\na,2.0,2.0\n")
        with self.assertRaises(ValueError):
            load_catalog(self.path)

    def test_empty_id_rejected(self):
        self._write(HEADER + ",1.0,1.0\n")
        with self.assertRaises(ValueError):
            load_catalog(self.path)

    def test_non_ascii_id_rejected(self):
        self._write(HEADER + "café,1.0,1.0\n")
        with self.assertRaises(ValueError):
            load_catalog(self.path)

    def test_ra_360_rejected(self):
        self._write(HEADER + "a,360.0,0.0\n")
        with self.assertRaises(ValueError):
            load_catalog(self.path)

    def test_negative_ra_rejected(self):
        self._write(HEADER + "a,-0.1,0.0\n")
        with self.assertRaises(ValueError):
            load_catalog(self.path)

    def test_dec_out_of_range_rejected(self):
        self._write(HEADER + "a,10.0,90.0001\n")
        with self.assertRaises(ValueError):
            load_catalog(self.path)

    def test_non_finite_rejected(self):
        self._write(HEADER + "a,nan,0.0\n")
        with self.assertRaises(ValueError):
            load_catalog(self.path)
        self._write(HEADER + "a,inf,0.0\n")
        with self.assertRaises(ValueError):
            load_catalog(self.path)

    def test_missing_columns_rejected(self):
        self._write("id,ra\na,1.0\n")
        with self.assertRaises(ValueError):
            load_catalog(self.path)


if __name__ == "__main__":
    unittest.main()
