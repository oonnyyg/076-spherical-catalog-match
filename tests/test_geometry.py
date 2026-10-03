import math

from sky_match.geometry import angular_distance_arcsec


def test_zero_distance():
    assert angular_distance_arcsec(42.0, 10.0, 42.0, 10.0) == 0.0


def test_equator_one_degree_is_3600_arcsec():
    d = angular_distance_arcsec(10.0, 0.0, 11.0, 0.0)
    assert abs(d - 3600.0) < 1e-9


def test_ra_wraparound():
    direct = angular_distance_arcsec(0.1, 0.0, 359.9, 0.0)
    wrapped = angular_distance_arcsec(359.9, 0.0, 360.1 % 360.0, 0.0)
    assert abs(direct - 720.0) < 1e-7
    assert abs(direct - wrapped) < 1e-7


def test_antipodes_on_equator():
    d = angular_distance_arcsec(10.0, 0.0, 190.0, 0.0)
    assert abs(d - 648000.0) < 1e-7


def test_north_pole_to_equator():
    d = angular_distance_arcsec(45.0, 90.0, 200.0, 0.0)
    assert abs(d - 324000.0) < 1e-7


def test_pole_ra_independent():
    d1 = angular_distance_arcsec(0.0, 90.0, 123.0, 90.0)
    assert d1 < 1e-6
    d2 = angular_distance_arcsec(0.0, -90.0, 77.0, -90.0)
    assert d2 < 1e-6


def test_antipodal_poles():
    d = angular_distance_arcsec(0.0, 90.0, 0.0, -90.0)
    assert abs(d - 648000.0) < 1e-7


def test_tiny_separation_precision():
    d = angular_distance_arcsec(10.0, 45.0, 10.0 + 1e-7, 45.0)
    expected = 1e-7 * 3600.0 * math.cos(math.radians(45.0))
    assert abs(d - expected) < 1e-9


def test_known_spherical_triangle():
    # Two points both at dec 60, separated by 2 deg in RA.
    d = angular_distance_arcsec(0.0, 60.0, 2.0, 60.0)
    expected = math.degrees(math.acos(math.sin(math.radians(60.0)) ** 2 +
                                      math.cos(math.radians(60.0)) ** 2 *
                                      math.cos(math.radians(2.0)))) * 3600.0
    assert abs(d - expected) < 1e-9
