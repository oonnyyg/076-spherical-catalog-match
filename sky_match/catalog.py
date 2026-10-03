import csv
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    source_id: str
    ra_deg: float
    dec_deg: float


def _validate_id(source_id, path, line_no):
    if not source_id:
        raise ValueError(f"{path}:{line_no}: empty source id")
    if not source_id.isascii():
        raise ValueError(f"{path}:{line_no}: non-ASCII source id {source_id!r}")


def _validate_coord(value, name, lo, hi, include_hi, path, line_no):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{path}:{line_no}: invalid {name} value {value!r}") from None
    if not math.isfinite(number):
        raise ValueError(f"{path}:{line_no}: non-finite {name} value {value!r}")
    upper_ok = number <= hi if include_hi else number < hi
    if not (lo <= number and upper_ok):
        bound = f"[{lo}, {hi}]" if include_hi else f"[{lo}, {hi})"
        raise ValueError(f"{path}:{line_no}: {name} {number} out of range {bound}")
    return number


def load_catalog(path):
    """Load and validate a CSV catalog with columns id, ra_deg, dec_deg."""
    sources = []
    seen = set()
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"id", "ra_deg", "dec_deg"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path}: missing required columns {sorted(required)}")
        for line_no, row in enumerate(reader, start=2):
            source_id = (row.get("id") or "").strip()
            _validate_id(source_id, path, line_no)
            if source_id in seen:
                raise ValueError(f"{path}:{line_no}: duplicate source id {source_id!r}")
            seen.add(source_id)
            ra = _validate_coord(row.get("ra_deg"), "ra_deg", 0.0, 360.0, False, path, line_no)
            dec = _validate_coord(row.get("dec_deg"), "dec_deg", -90.0, 90.0, True, path, line_no)
            sources.append(Source(source_id, ra, dec))
    return sources
