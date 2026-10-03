"""Command-line entry point: ``python -m sky_match``."""

from __future__ import annotations

import argparse
import json
import sys

from .catalog import CatalogError
from .match import MatchConfig, build_report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m sky_match",
        description="Cross-match two CSV star catalogs by spherical angular distance.",
    )
    parser.add_argument("--left", required=True, help="left catalog CSV path")
    parser.add_argument("--right", required=True, help="right catalog CSV path")
    parser.add_argument("--config", required=True, help="JSON config path")
    parser.add_argument("--output-dir", required=True, help="directory for report files")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = MatchConfig.load(args.config)
        summary = build_report(args.left, args.right, config, args.output_dir)
    except CatalogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
