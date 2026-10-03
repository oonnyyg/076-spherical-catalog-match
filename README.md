# spherical-catalog-match

Cross-match two astronomical catalogs by true spherical angular distance
(great-circle separation), using only the Python standard library.

## Usage

```
python -m sky_match LEFT.csv RIGHT.csv config.json
```

### Input catalogs

CSV files with a header row and columns `id,ra_deg,dec_deg`:

- `id`: non-empty ASCII identifier, unique within each catalog.
- `ra_deg`: right ascension in degrees, finite, in `[0, 360)`.
- `dec_deg`: declination in degrees, finite, in `[-90, 90]`.

Coordinates are assumed to share the same epoch and reference frame; no
proper-motion or precession correction is applied. Empty catalogs (header
only) are allowed.

### Configuration

```json
{
  "radius_arcsec": 5.0,
  "output_dir": "out"
}
```

`radius_arcsec` is the match radius in arcseconds, within `[0, 648000]`.

### Output

Written into `output_dir`:

- `matches.csv`: one row per left-catalog object, sorted by `left_id`, with
  columns `left_id,candidate_count,right_id,distance_arcsec,mutual`.
  `candidate_count` lists all right objects within the radius (boundary
  inclusive). `right_id` is the nearest candidate; candidates within
  `1e-7` arcsec of the minimum distance are ties, broken by the
  lexicographically smallest id. Objects without candidates keep a row with
  empty `right_id`/`distance_arcsec`. `mutual` is `true` only when the two
  objects are each other's nearest neighbor.
- `summary.json`: counts for `matched`, `unmatched`, and `mutual_pairs`,
  plus the input catalog sizes and match radius.

Invalid input exits with a non-zero status and produces no reports.

## Method

Angular separation uses the numerically stable atan2 (Vincenty) form of the
great-circle distance, correct across RA=0, at the poles, and for antipodal
points; distances are reported in arcseconds. Matching is computed
independently in both directions, so several left objects may select the
same right object and mutual pairs are detected without greedy assignment.

## Tests

```
python -m unittest discover -s tests
```
