# sky_match — spherical catalog cross-matcher

Cross-match two local astronomical catalogs using **true great-circle angular
distance**.  Each left-hand source receives its nearest right-hand source
within a configurable radius, and sources that select each other independently
are flagged as mutual nearest neighbors.  No planar (RA/Dec) approximation is
used, so right-ascension wraparound at 0/360, the celestial poles and
antipodal points are handled correctly.

Coordinates are assumed to share the same epoch and reference frame; no
proper-motion or precession correction is applied.

## Requirements

- Python 3.12+
- Standard library only (`csv`, `json`, `math`, `argparse`, …)

## Usage

```bash
python -m sky_match \
  --left examples/left.csv \
  --right examples/right.csv \
  --config examples/config.json \
  --output-dir build/report
```

The exit code is non-zero on any invalid input and no report files are
produced in that case.

## Input formats

Each catalog is a UTF-8 CSV with a header row.  By default the columns
`id`, `ra`, `dec` are read; column names can be remapped per catalog in the
config (`left_columns` / `right_columns`, keys `id_column`, `ra_column`,
`dec_column`).

Validation rules:

- `id`: non-empty ASCII, unique within its table.
- `ra`: finite degrees in `[0, 360)` (360 is rejected).
- `dec`: finite degrees in `[-90, 90]` (both poles included).
- Empty tables (header only) are allowed.

The config JSON requires `radius_arcsec`, a number in `[0, 648000]` arcseconds
(648000 arcsec = 180°).  A source exactly on the radius boundary counts as a
candidate (inclusive comparison, within floating-point tolerance).

## Matching rules

1. For every left source, count right sources within the radius and pick the
   nearest.  Distances equal within `1e-7` arcsec of the minimum count as a
   tie; the lexicographically smallest target id wins.  Multiple left sources
   may select the same right source — there is no one-by-one greedy
   exclusion.
2. Independently repeat the search from every right source toward the left
   table under the same rules.
3. A pair is marked mutual (`is_mutual = true`) only when the two sides
   choose each other.
4. Left sources with no candidate keep a row with `null` target and distance.

Results are sorted by left id, so input row order never affects the output.

## Outputs

`matches.csv` in the output directory:

| column | meaning |
| --- | --- |
| `left_id` | left catalog id |
| `candidate_count` | right sources within the radius (boundary included) |
| `nearest_right_id` | selected id, or `null` |
| `distance_arcsec` | separation in arcseconds, or `null` |
| `is_mutual` | `true` when both sides select each other, else `false` |

`summary.json`:

```json
{
  "left_count": 4,
  "right_count": 4,
  "matched_count": 3,
  "unmatched_count": 1,
  "mutual_pair_count": 3
}
```

Distance accuracy is better than `1e-6` arcsec absolute error; separations
are computed with the numerically stable `atan2` haversine formula.

## Tests

```bash
python -m pytest
```

The suite covers RA wraparound, the poles, antipodes, precision, radius
boundaries, ties, duplicate coordinates, mutual vs. one-way matches, empty
tables, ordering independence, invalid input and the CLI exit code.
