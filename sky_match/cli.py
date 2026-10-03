import argparse
import json
import sys

from .catalog import load_catalog
from .match import cross_match
from .report import write_outputs


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="python -m sky_match",
        description="Cross-match two CSV catalogs by true spherical angular distance.",
    )
    parser.add_argument("left_csv", help="Path to the left catalog CSV file.")
    parser.add_argument("right_csv", help="Path to the right catalog CSV file.")
    parser.add_argument("config", help="Path to the JSON configuration file.")
    return parser.parse_args(argv)


def _load_config(path):
    with open(path, "r", encoding="utf-8") as fh:
        config = json.load(fh)
    if not isinstance(config, dict):
        raise ValueError("configuration must be a JSON object")
    radius = config.get("radius_arcsec")
    if not isinstance(radius, (int, float)) or isinstance(radius, bool):
        raise ValueError("radius_arcsec must be a number")
    if not (0.0 <= radius <= 648000.0):
        raise ValueError("radius_arcsec must be within [0, 648000]")
    output_dir = config.get("output_dir")
    if not isinstance(output_dir, str) or not output_dir:
        raise ValueError("output_dir must be a non-empty string")
    return radius, output_dir


def main(argv=None):
    args = _parse_args(argv)
    try:
        radius_arcsec, output_dir = _load_config(args.config)
        left = load_catalog(args.left_csv)
        right = load_catalog(args.right_csv)
        result = cross_match(left, right, radius_arcsec)
        write_outputs(result, output_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
