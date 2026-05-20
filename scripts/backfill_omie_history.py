#!/usr/bin/env python3
"""Backfill OMIE historical prices using yearly archives when available."""

from __future__ import annotations

import argparse
from pathlib import Path

from peace_power.io import fetch_omie_history


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill OMIE day-ahead prices over a long history range.",
    )
    parser.add_argument("start_date", help="Inclusive start date, for example 2024-01-01.")
    parser.add_argument("end_date", help="Inclusive end date, for example 2025-12-31.")
    parser.add_argument(
        "--output-dir",
        default="data/raw/omie",
        help="Directory where OMIE raw archives and daily files should be stored.",
    )
    parser.add_argument(
        "--csv",
        default="data/raw/omie/omie_history.csv",
        help="Path for the combined parsed CSV output.",
    )
    parser.add_argument(
        "--no-year-archives",
        action="store_true",
        help="Disable yearly archive downloads and use only daily files.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    frame = fetch_omie_history(
        args.start_date,
        args.end_date,
        prefer_year_archives=not args.no_year_archives,
        output_dir=args.output_dir,
    )

    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)

    print(f"Downloaded {len(frame)} rows from OMIE for {args.start_date} to {args.end_date}.")
    print(f"Combined CSV saved to: {csv_path.resolve()}")
    print(f"Raw files directory: {Path(args.output_dir).resolve()}")
    if not frame.empty:
        print(frame.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
