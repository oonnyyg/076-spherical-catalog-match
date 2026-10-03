"""Nearest-neighbor and mutual-nearest-neighbor catalog matching."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .catalog import CatalogError, CatalogObject, ColumnSpec, load_catalog
from .geometry import angular_distance_arcsec

TIE_TOLERANCE_ARCSEC = 1e-7
MAX_RADIUS_ARCSEC = 648_000.0


@dataclass(frozen=True)
class MatchConfig:
    radius_arcsec: float
    left_columns: ColumnSpec = ColumnSpec()
    right_columns: ColumnSpec = ColumnSpec()

    @classmethod
    def load(cls, path: str | Path) -> "MatchConfig":
        path = Path(path)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise CatalogError(f"config file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise CatalogError(f"invalid JSON in config {path}: {exc}") from exc
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: object) -> "MatchConfig":
        if not isinstance(raw, dict):
            raise CatalogError("config must be a JSON object")
        if "radius_arcsec" not in raw:
            raise CatalogError("config missing radius_arcsec")
        radius = raw["radius_arcsec"]
        if not isinstance(radius, (int, float)) or isinstance(radius, bool):
            raise CatalogError("radius_arcsec must be a number")
        radius = float(radius)
        if radius != radius or radius < 0.0 or radius > MAX_RADIUS_ARCSEC:
            raise CatalogError(
                f"radius_arcsec must be in [0, {int(MAX_RADIUS_ARCSEC)}], got {radius}"
            )
        return cls(
            radius_arcsec=radius,
            left_columns=ColumnSpec.from_config(raw.get("left_columns")),
            right_columns=ColumnSpec.from_config(raw.get("right_columns")),
        )


@dataclass(frozen=True)
class NearestChoice:
    target_id: str | None
    distance_arcsec: float | None
    candidate_count: int


@dataclass(frozen=True)
class MatchRow:
    left_id: str
    candidate_count: int
    nearest_right_id: str | None
    distance_arcsec: float | None
    is_mutual: bool


def _nearest(source: CatalogObject, targets: list[CatalogObject], radius: float) -> NearestChoice:
    nearest_distance: float | None = None
    for target in targets:
        distance = angular_distance_arcsec(source.ra, source.dec, target.ra, target.dec)
        if distance <= radius and (nearest_distance is None or distance < nearest_distance):
            nearest_distance = distance
    if nearest_distance is None:
        return NearestChoice(None, None, 0)

    candidate_count = 0
    best_id: str | None = None
    cutoff = nearest_distance + TIE_TOLERANCE_ARCSEC
    for target in targets:
        distance = angular_distance_arcsec(source.ra, source.dec, target.ra, target.dec)
        if distance <= radius:
            candidate_count += 1
            if distance <= cutoff and (best_id is None or target.id < best_id):
                best_id = target.id
    return NearestChoice(best_id, nearest_distance, candidate_count)


def cross_match(
    left: list[CatalogObject],
    right: list[CatalogObject],
    radius: float,
) -> list[MatchRow]:
    """Match every left object to right and then test mutual selection.

    The reverse nearest-neighbor search is run independently for every right
    object; a pair is mutual only when both sides freely select each other.
    """

    left_choices = {obj.id: _nearest(obj, right, radius) for obj in left}
    right_choices = {obj.id: _nearest(obj, left, radius) for obj in right}

    rows: list[MatchRow] = []
    for obj in sorted(left, key=lambda item: item.id):
        choice = left_choices[obj.id]
        is_mutual = (
            choice.target_id is not None
            and right_choices[choice.target_id].target_id == obj.id
        )
        rows.append(
            MatchRow(
                left_id=obj.id,
                candidate_count=choice.candidate_count,
                nearest_right_id=choice.target_id,
                distance_arcsec=choice.distance_arcsec,
                is_mutual=is_mutual,
            )
        )
    return rows


def build_report(
    left_path: str | Path,
    right_path: str | Path,
    config: MatchConfig,
    output_dir: str | Path,
) -> dict[str, int]:
    """Load catalogs, cross-match and write CSV plus summary JSON.

    Returns the summary mapping.  Nothing is written until all inputs have been
    validated, so invalid input never leaves partial reports behind.
    """

    left = load_catalog(left_path, config.left_columns)
    right = load_catalog(right_path, config.right_columns)
    rows = cross_match(left, right, config.radius_arcsec)

    matched = sum(1 for row in rows if row.nearest_right_id is not None)
    mutual = sum(1 for row in rows if row.is_mutual)
    summary = {
        "left_count": len(left),
        "right_count": len(right),
        "matched_count": matched,
        "unmatched_count": len(rows) - matched,
        "mutual_pair_count": mutual,
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "matches.csv", rows)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    return summary


def _write_csv(path: Path, rows: list[MatchRow]) -> None:
    import csv

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            ["left_id", "candidate_count", "nearest_right_id", "distance_arcsec", "is_mutual"]
        )
        for row in rows:
            writer.writerow(
                [
                    row.left_id,
                    row.candidate_count,
                    row.nearest_right_id if row.nearest_right_id is not None else "null",
                    repr(row.distance_arcsec) if row.distance_arcsec is not None else "null",
                    "true" if row.is_mutual else "false",
                ]
            )
