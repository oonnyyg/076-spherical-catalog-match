"""Loading and validation of CSV star catalogs."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


class CatalogError(ValueError):
    """Raised when a catalog file or its contents are invalid."""


@dataclass(frozen=True)
class CatalogObject:
    """One catalog record: non-empty ASCII id plus ICRS-style degrees."""

    id: str
    ra: float
    dec: float


@dataclass(frozen=True)
class ColumnSpec:
    id_column: str = "id"
    ra_column: str = "ra"
    dec_column: str = "dec"

    @classmethod
    def from_config(cls, raw: object) -> "ColumnSpec":
        if raw is None:
            return cls()
        if not isinstance(raw, dict):
            raise CatalogError("catalog column config must be a JSON object")
        spec = cls(
            id_column=str(raw.get("id_column", "id")),
            ra_column=str(raw.get("ra_column", "ra")),
            dec_column=str(raw.get("dec_column", "dec")),
        )
        return spec


def _parse_coordinate(value: str, name: str, row_number: int, obj_id: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CatalogError(
            f"row {row_number} (id={obj_id!r}): {name} is not a number: {value!r}"
        ) from exc
    if not math.isfinite(number):
        raise CatalogError(f"row {row_number} (id={obj_id!r}): {name} must be finite")
    return number


def load_catalog(path: str | Path, spec: ColumnSpec | None = None) -> list[CatalogObject]:
    """Read a catalog CSV, validating ids, ranges and uniqueness.

    Empty catalogs (a header row only) are permitted.
    """

    spec = spec or ColumnSpec()
    path = Path(path)
    if not path.is_file():
        raise CatalogError(f"catalog file not found: {path}")

    try:
        handle = path.open("r", encoding="utf-8", newline="")
    except OSError as exc:
        raise CatalogError(f"cannot open catalog {path}: {exc}") from exc

    objects: list[CatalogObject] = []
    seen_ids: set[str] = set()
    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise CatalogError(f"{path}: missing header row")
        header = [name.strip() if name is not None else name for name in reader.fieldnames]
        for required in (spec.id_column, spec.ra_column, spec.dec_column):
            if required not in header:
                raise CatalogError(f"{path}: missing required column {required!r}")

        for row_number, row in enumerate(reader, start=2):
            raw_id = row.get(spec.id_column)
            obj_id = (raw_id or "").strip()
            if not obj_id:
                raise CatalogError(f"row {row_number}: empty id")
            if not obj_id.isascii():
                raise CatalogError(f"row {row_number}: id is not ASCII: {obj_id!r}")
            if obj_id in seen_ids:
                raise CatalogError(f"row {row_number}: duplicate id {obj_id!r}")

            ra = _parse_coordinate(
                (row.get(spec.ra_column) or "").strip(), "ra", row_number, obj_id
            )
            dec = _parse_coordinate(
                (row.get(spec.dec_column) or "").strip(), "dec", row_number, obj_id
            )
            if not 0.0 <= ra < 360.0:
                raise CatalogError(
                    f"row {row_number} (id={obj_id!r}): ra must be in [0, 360), got {ra}"
                )
            if not -90.0 <= dec <= 90.0:
                raise CatalogError(
                    f"row {row_number} (id={obj_id!r}): dec must be in [-90, 90], got {dec}"
                )

            seen_ids.add(obj_id)
            objects.append(CatalogObject(id=obj_id, ra=ra, dec=dec))

    return objects
