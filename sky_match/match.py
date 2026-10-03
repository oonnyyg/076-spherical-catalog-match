import math
from dataclasses import dataclass
from typing import Optional

TIE_TOLERANCE_ARCSEC = 1e-7


@dataclass(frozen=True)
class MatchRow:
    left_id: str
    candidate_count: int
    right_id: Optional[str]
    distance_arcsec: Optional[float]
    mutual: bool


def angular_distance_arcsec(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
    """Shortest great-circle angular distance between two points, in arcseconds."""
    ra1 = math.radians(ra1_deg)
    dec1 = math.radians(dec1_deg)
    ra2 = math.radians(ra2_deg)
    dec2 = math.radians(dec2_deg)
    d_ra = ra2 - ra1
    sin_d1, cos_d1 = math.sin(dec1), math.cos(dec1)
    sin_d2, cos_d2 = math.sin(dec2), math.cos(dec2)
    cos_d_ra = math.cos(d_ra)
    numerator = math.hypot(
        cos_d2 * math.sin(d_ra),
        cos_d1 * sin_d2 - sin_d1 * cos_d2 * cos_d_ra,
    )
    denominator = sin_d1 * sin_d2 + cos_d1 * cos_d2 * cos_d_ra
    return math.degrees(math.atan2(numerator, denominator)) * 3600.0


def _nearest(source, others, radius_arcsec):
    """Return (candidate_count, nearest_id, nearest_distance) for one source."""
    best_id = None
    best_dist = None
    count = 0
    for other in others:
        dist = angular_distance_arcsec(
            source.ra_deg, source.dec_deg, other.ra_deg, other.dec_deg
        )
        if dist > radius_arcsec:
            continue
        count += 1
        if best_dist is None or dist < best_dist - TIE_TOLERANCE_ARCSEC:
            best_dist = dist
            best_id = other.source_id
        elif dist <= best_dist + TIE_TOLERANCE_ARCSEC and other.source_id < best_id:
            best_id = other.source_id
    return count, best_id, best_dist


def cross_match(left, right, radius_arcsec):
    """Match catalogs both ways; returns rows sorted by left id plus summary."""
    left_best = {}
    rows = []
    for source in left:
        count, best_id, best_dist = _nearest(source, right, radius_arcsec)
        left_best[source.source_id] = best_id
        rows.append(
            MatchRow(
                left_id=source.source_id,
                candidate_count=count,
                right_id=best_id,
                distance_arcsec=best_dist,
                mutual=False,
            )
        )
    right_best = {}
    for source in right:
        _, best_id, _ = _nearest(source, left, radius_arcsec)
        right_best[source.source_id] = best_id
    rows = [
        MatchRow(
            left_id=row.left_id,
            candidate_count=row.candidate_count,
            right_id=row.right_id,
            distance_arcsec=row.distance_arcsec,
            mutual=row.right_id is not None
            and right_best.get(row.right_id) == row.left_id,
        )
        for row in rows
    ]
    rows.sort(key=lambda row: row.left_id)
    matched = sum(1 for row in rows if row.right_id is not None)
    summary = {
        "radius_arcsec": radius_arcsec,
        "left_count": len(left),
        "right_count": len(right),
        "matched": matched,
        "unmatched": len(rows) - matched,
        "mutual_pairs": sum(1 for row in rows if row.mutual),
    }
    return {"rows": rows, "summary": summary}
