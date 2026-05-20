#!/usr/bin/env python3
"""Search ESIOS indicators by text."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from peace_power.io import search_esios_indicators


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search ESIOS indicators using your API token.",
    )
    parser.add_argument("query", help="Text to search for, for example bateria or interconexion.")
    parser.add_argument(
        "--token",
        default=None,
        help="Optional ESIOS token. Defaults to the ESIOS_TOKEN environment variable.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of rows to show.",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Optional path where the search results should be saved as CSV.",
    )
    parser.add_argument(
        "--include-contents",
        action="store_true",
        help="Include content results as well as indicator results.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    frame = search_esios_indicators(
        args.query,
        token=args.token,
        include_contents=args.include_contents,
        limit=args.limit,
    )

    csv_path = Path(args.csv) if args.csv else None
    if csv_path is not None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(csv_path, index=False)

    if frame.empty:
        print("No ESIOS results returned.")
        return

    display_cols = [
        col
        for col in [
            "id",
            "name",
            "short_name",
            "description",
            "result_type",
            "result_bucket",
            "match_score",
        ]
        if col in frame.columns
    ]
    with pd.option_context("display.max_colwidth", 72, "display.width", 180):
        print(frame[display_cols].to_string(index=False))
    if csv_path is not None:
        print(f"\nSaved search results to: {csv_path.resolve()}")


if __name__ == "__main__":
    main()
