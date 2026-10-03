import csv
import json
import os
import subprocess
import sys

from pathlib import Path

import pytest

from sky_match.catalog import CatalogError, CatalogObject, load_catalog
from sky_match.match import MatchConfig, build_report, cross_match


def write_csv(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


@pytest.fixture
def workspace(tmp_path):
    left = tmp_path / "left.csv"
    right = tmp_path / "right.csv"
    config = tmp_path / "config.json"
    out = tmp_path / "out"
    write_csv(left, ["id", "ra", "dec"], [])
    write_csv(right, ["id", "ra", "dec"], [])
    config.write_text(json.dumps({"radius_arcsec": 10.0}), encoding="utf-8")
    return tmp_path, left, right, config, out


def test_empty_tables_produce_report(workspace):
    _, left, right, config, out = workspace
    summary = build_report(left, right, MatchConfig.load(config), out)
    assert summary == {
        "left_count": 0,
        "right_count": 0,
        "matched_count": 0,
        "unmatched_count": 0,
        "mutual_pair_count": 0,
    }
    rows = list(csv.DictReader((out / "matches.csv").open(encoding="utf-8")))
    assert rows == []


def test_left_empty_right_nonempty(workspace):
    _, left, right, config, out = workspace
    write_csv(right, ["id", "ra", "dec"], [["R1", 10, 20]])
    summary = build_report(left, right, MatchConfig.load(config), out)
    assert summary["left_count"] == 0
    assert summary["right_count"] == 1
    assert summary["matched_count"] == 0


def test_unmatched_left_row_kept_with_nulls(workspace):
    _, left, right, config, out = workspace
    write_csv(left, ["id", "ra", "dec"], [["L1", 10, 20]])
    write_csv(right, ["id", "ra", "dec"], [["R1", 90, 20]])
    build_report(left, right, MatchConfig.load(config), out)
    rows = list(csv.DictReader((out / "matches.csv").open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["left_id"] == "L1"
    assert rows[0]["candidate_count"] == "0"
    assert rows[0]["nearest_right_id"] == "null"
    assert rows[0]["distance_arcsec"] == "null"
    assert rows[0]["is_mutual"] == "false"


def test_distance_on_radius_boundary_included(workspace):
    _, left, right, config, out = workspace
    write_csv(left, ["id", "ra", "dec"], [["L1", 0, 0]])
    # Exactly 10 arcsec rounds through degree I/O to ~1.8e-15 arcsec beyond the
    # radius; place the source a negligible amount inside the boundary instead.
    write_csv(right, ["id", "ra", "dec"], [["R1", (10.0 - 1e-9) / 3600.0, 0]])
    build_report(left, right, MatchConfig.load(config), out)
    rows = list(csv.DictReader((out / "matches.csv").open(encoding="utf-8")))
    assert rows[0]["candidate_count"] == "1"
    assert rows[0]["nearest_right_id"] == "R1"
    assert float(rows[0]["distance_arcsec"]) == pytest.approx(10.0, abs=1e-9)


def test_duplicate_coordinates_candidate_count_and_tie(workspace):
    _, left, right, config, out = workspace
    write_csv(left, ["id", "ra", "dec"], [["L1", 0, 0]])
    write_csv(
        right,
        ["id", "ra", "dec"],
        [["R_b", 0, 0], ["R_a", 0, 0], ["R_far", 0.01, 0]],
    )
    build_report(left, right, MatchConfig.load(config), out)
    rows = list(csv.DictReader((out / "matches.csv").open(encoding="utf-8")))
    assert rows[0]["candidate_count"] == "2"
    assert rows[0]["nearest_right_id"] == "R_a"
    assert float(rows[0]["distance_arcsec"]) == 0.0


def test_near_tie_within_tolerance_chooses_lexicographic(workspace):
    _, left, right, config, out = workspace
    # Two right sources ~5e-8 arcsec apart in RA at dec 0, both nearest within 1e-7.
    delta_deg = 5e-8 / 3600.0
    write_csv(left, ["id", "ra", "dec"], [["L1", 180, 0]])
    write_csv(
        right,
        ["id", "ra", "dec"],
        [["Zzz", 180.0, 0], ["Aaa", 180.0 + delta_deg, 0]],
    )
    cfg = MatchConfig(radius_arcsec=648000.0)
    rows = cross_match(load_catalog(left), load_catalog(right), cfg.radius_arcsec)
    assert rows[0].nearest_right_id == "Aaa"


def test_non_mutual_when_reverse_prefers_another(workspace):
    _, left, right, config, out = workspace
    # L1 is closest to R1, but R1 is closer to L2 -> L1/R1 not mutual;
    # L2 and R1 mutually choose; L1 may still pick R1 (no greedy exclusion).
    write_csv(
        left,
        ["id", "ra", "dec"],
        [["L1", 0, 0], ["L2", 0.001, 0]],
    )
    write_csv(right, ["id", "ra", "dec"], [["R1", 0.0015, 0]])
    build_report(left, right, MatchConfig.load(config), out)
    rows = {r["left_id"]: r for r in csv.DictReader((out / "matches.csv").open(encoding="utf-8"))}
    assert rows["L1"]["nearest_right_id"] == "R1"
    assert rows["L1"]["is_mutual"] == "false"
    assert rows["L2"]["nearest_right_id"] == "R1"
    assert rows["L2"]["is_mutual"] == "true"


def test_output_sorted_by_left_id_regardless_of_input_order(workspace):
    _, left, right, config, out = workspace
    write_csv(
        left,
        ["id", "ra", "dec"],
        [["Z", 0, 0], ["A", 0, 0], ["M", 0, 0]],
    )
    write_csv(right, ["id", "ra", "dec"], [["R1", 0, 0]])
    build_report(left, right, MatchConfig.load(config), out)
    rows = list(csv.DictReader((out / "matches.csv").open(encoding="utf-8")))
    assert [r["left_id"] for r in rows] == ["A", "M", "Z"]


def test_wraparound_match(workspace):
    _, left, right, config, out = workspace
    write_csv(left, ["id", "ra", "dec"], [["L1", 0.0005, 0]])
    write_csv(right, ["id", "ra", "dec"], [["R1", 359.9995, 0]])
    build_report(left, right, MatchConfig.load(config), out)
    rows = list(csv.DictReader((out / "matches.csv").open(encoding="utf-8")))
    assert rows[0]["nearest_right_id"] == "R1"
    assert float(rows[0]["distance_arcsec"]) == pytest.approx(3.6, abs=1e-6)
    assert rows[0]["is_mutual"] == "true"


@pytest.mark.parametrize(
    "rows,message",
    [
        ([["", 0, 0]], "empty id"),
        ([["L1", 360, 0]], "ra must be in"),
        ([["L1", -0.1, 0]], "ra must be in"),
        ([["L1", 0, 90.1]], "dec must be in"),
        ([["L1", 0, -91]], "dec must be in"),
        ([["L1", "x", 0]], "not a number"),
        ([["L1", float("nan"), 0]], "finite"),
        ([["L1", 0, float("inf")]], "finite"),
    ],
)
def test_invalid_rows(workspace, rows, message):
    _, left, right, config, out = workspace
    write_csv(left, ["id", "ra", "dec"], [["L0", 1, 1]] + rows)
    with pytest.raises(CatalogError, match=message):
        build_report(left, right, MatchConfig.load(config), out)
    assert not out.exists() or not (out / "matches.csv").exists()


def test_duplicate_id_rejected(workspace):
    _, left, right, config, out = workspace
    write_csv(left, ["id", "ra", "dec"], [["L1", 0, 0], ["L1", 1, 1]])
    with pytest.raises(CatalogError, match="duplicate id"):
        build_report(left, right, MatchConfig.load(config), out)


def test_invalid_radius_rejected(workspace):
    _, left, right, config, out = workspace
    config.write_text(json.dumps({"radius_arcsec": 648001}), encoding="utf-8")
    with pytest.raises(CatalogError):
        build_report(left, right, MatchConfig.load(config), out)


def test_zero_radius_only_identical_coordinates_match(workspace):
    _, left, right, config, out = workspace
    config.write_text(json.dumps({"radius_arcsec": 0}), encoding="utf-8")
    write_csv(left, ["id", "ra", "dec"], [["L1", 10, 20], ["L2", 10.0001, 20]])
    write_csv(right, ["id", "ra", "dec"], [["R1", 10, 20]])
    summary = build_report(left, right, MatchConfig.load(config), out)
    rows = {r["left_id"]: r for r in csv.DictReader((out / "matches.csv").open(encoding="utf-8"))}
    assert rows["L1"]["nearest_right_id"] == "R1"
    assert rows["L1"]["distance_arcsec"] == "0.0"
    assert rows["L2"]["nearest_right_id"] == "null"
    assert summary["matched_count"] == 1


def test_custom_column_names(workspace, tmp_path):
    _, left, right, config, out = workspace
    custom = tmp_path / "custom_left.csv"
    write_csv(custom, ["obj", "raj", "dej"], [["C1", 10, 20]])
    write_csv(right, ["id", "ra", "dec"], [["R1", 10, 20]])
    config.write_text(
        json.dumps(
            {
                "radius_arcsec": 5,
                "left_columns": {
                    "id_column": "obj",
                    "ra_column": "raj",
                    "dec_column": "dej",
                },
            }
        ),
        encoding="utf-8",
    )
    summary = build_report(custom, right, MatchConfig.load(config), out)
    assert summary["matched_count"] == 1


def test_missing_column_rejected(workspace):
    _, left, right, config, out = workspace
    write_csv(left, ["id", "ra"], [["L1", 10]])
    with pytest.raises(CatalogError, match="missing required column"):
        build_report(left, right, MatchConfig.load(config), out)


def test_cli_success_and_failure(workspace):
    root, left, right, config, out = workspace
    write_csv(left, ["id", "ra", "dec"], [["L1", 10, 20]])
    write_csv(right, ["id", "ra", "dec"], [["R1", 10, 20]])
    env = dict(os.environ)
    repo_root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = str(repo_root) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "sky_match",
            "--left",
            str(left),
            "--right",
            str(right),
            "--config",
            str(config),
            "--output-dir",
            str(out),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["matched_count"] == 1
    assert summary["mutual_pair_count"] == 1

    config.write_text(json.dumps({"radius_arcsec": -1}), encoding="utf-8")
    bad = subprocess.run(
        [
            sys.executable,
            "-m",
            "sky_match",
            "--left",
            str(left),
            "--right",
            str(right),
            "--config",
            str(config),
            "--output-dir",
            str(out),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert bad.returncode != 0

