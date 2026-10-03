import math
import unittest

from sky_match.catalog import Source
from sky_match.match import angular_distance_arcsec, cross_match


def src(sid, ra, dec):
    return Source(sid, ra, dec)


class AngularDistanceTests(unittest.TestCase):
    def test_zero_distance(self):
        self.assertAlmostEqual(
            angular_distance_arcsec(10.0, 20.0, 10.0, 20.0), 0.0, places=9
        )

    def test_ra_wraparound(self):
        dist = angular_distance_arcsec(359.9999, 0.0, 0.0001, 0.0)
        self.assertAlmostEqual(dist, 0.0002 * 3600.0, places=6)

    def test_pole(self):
        dist = angular_distance_arcsec(0.0, 90.0, 180.0, 89.0)
        self.assertAlmostEqual(dist, 3600.0, places=6)

    def test_antipodal(self):
        dist = angular_distance_arcsec(0.0, 0.0, 180.0, 0.0)
        self.assertAlmostEqual(dist, 648000.0, places=6)

    def test_known_value(self):
        ra1, dec1, ra2, dec2 = 83.633, 22.0145, 250.4, -36.4
        p1, p2 = math.radians(dec1), math.radians(dec2)
        dl = math.radians(ra2 - ra1)
        h = (
            math.sin((p2 - p1) / 2) ** 2
            + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        )
        expected = math.degrees(2 * math.asin(math.sqrt(h))) * 3600.0
        self.assertAlmostEqual(
            angular_distance_arcsec(ra1, dec1, ra2, dec2), expected, places=6
        )


class CrossMatchTests(unittest.TestCase):
    def test_basic_match_and_mutual(self):
        left = [src("L1", 10.0, 0.0)]
        right = [src("R1", 10.0, 0.001)]
        result = cross_match(left, right, 10.0)
        row = result["rows"][0]
        self.assertEqual(row.right_id, "R1")
        self.assertTrue(row.mutual)
        self.assertEqual(result["summary"]["mutual_pairs"], 1)

    def test_one_way_nearest_not_mutual(self):
        left = [src("L1", 10.0, 0.0), src("L2", 10.0, 0.00015)]
        right = [src("R1", 10.0, 0.0001)]
        result = cross_match(left, right, 10.0)
        rows = {row.left_id: row for row in result["rows"]}
        self.assertEqual(rows["L1"].right_id, "R1")
        self.assertEqual(rows["L2"].right_id, "R1")
        self.assertFalse(rows["L1"].mutual)
        self.assertTrue(rows["L2"].mutual)
        self.assertEqual(result["summary"]["mutual_pairs"], 1)

    def test_no_candidates_keeps_null_row(self):
        left = [src("L1", 0.0, 0.0)]
        right = [src("R1", 90.0, 0.0)]
        result = cross_match(left, right, 1.0)
        row = result["rows"][0]
        self.assertIsNone(row.right_id)
        self.assertIsNone(row.distance_arcsec)
        self.assertEqual(row.candidate_count, 0)
        self.assertEqual(result["summary"]["unmatched"], 1)

    def test_boundary_inclusive(self):
        left = [src("L1", 0.0, 0.0)]
        right = [src("R1", 0.0, 1.0 / 3600.0)]
        result = cross_match(left, right, 1.0)
        self.assertEqual(result["rows"][0].candidate_count, 1)

    def test_tie_breaks_by_smallest_id(self):
        left = [src("L1", 0.0, 0.0)]
        right = [src("RB", 0.0, 0.001), src("RA", 0.0, -0.001)]
        result = cross_match(left, right, 10.0)
        self.assertEqual(result["rows"][0].right_id, "RA")

    def test_duplicate_coordinates_both_match(self):
        left = [src("L1", 5.0, 5.0)]
        right = [src("R1", 5.0, 5.0), src("R2", 5.0, 5.0)]
        result = cross_match(left, right, 1.0)
        row = result["rows"][0]
        self.assertEqual(row.candidate_count, 2)
        self.assertEqual(row.right_id, "R1")
        self.assertAlmostEqual(row.distance_arcsec, 0.0, places=9)

    def test_empty_tables(self):
        result = cross_match([], [], 5.0)
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["summary"]["matched"], 0)
        result = cross_match([src("L1", 1.0, 1.0)], [], 5.0)
        self.assertIsNone(result["rows"][0].right_id)
        result = cross_match([], [src("R1", 1.0, 1.0)], 5.0)
        self.assertEqual(result["rows"], [])

    def test_input_order_does_not_matter(self):
        left1 = [src("A", 1.0, 1.0), src("B", 2.0, 2.0), src("C", 3.0, 3.0)]
        right1 = [src("X", 1.0, 1.0), src("Y", 2.0, 2.0)]
        r1 = cross_match(left1, right1, 3600.0)
        r2 = cross_match(list(reversed(left1)), list(reversed(right1)), 3600.0)
        self.assertEqual(r1, r2)

    def test_rows_sorted_by_left_id(self):
        left = [src("B", 2.0, 2.0), src("A", 1.0, 1.0)]
        result = cross_match(left, [], 1.0)
        self.assertEqual([row.left_id for row in result["rows"]], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
