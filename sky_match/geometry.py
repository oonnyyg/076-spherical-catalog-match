"""Spherical geometry helpers.

All coordinates are expressed in degrees: right ascension in ``[0, 360)`` and
declination in ``[-90, 90]``.  Angular separations are computed as great-circle
central angles, so right-ascension wraparound at 0/360, the celestial poles and
antipodal points are handled without any planar approximation.
"""

from __future__ import annotations

import math

ARCSECONDS_PER_RADIAN = 180.0 * 3600.0 / math.pi


def angular_distance_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Return the shortest great-circle separation in arcseconds.

    Uses the numerically stable ``atan2`` form of the haversine formula, which
    clamps the intermediate quantities to their valid domains so that identical
    points yield exactly zero and antipodal points exactly 180 degrees.
    """

    ra1_r = math.radians(ra1)
    ra2_r = math.radians(ra2)
    dec1_r = math.radians(dec1)
    dec2_r = math.radians(dec2)

    dra = ra2_r - ra1_r
    sin_d_half_sq = (
        math.sin((dec2_r - dec1_r) / 2.0) ** 2
        + math.cos(dec1_r) * math.cos(dec2_r) * math.sin(dra / 2.0) ** 2
    )
    if sin_d_half_sq <= 0.0:
        return 0.0
    if sin_d_half_sq >= 1.0:
        return 180.0 * 3600.0

    a = sin_d_half_sq
    angle = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return angle * ARCSECONDS_PER_RADIAN
