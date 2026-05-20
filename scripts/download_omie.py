#!/usr/bin/env python3
"""Download and parse OMIE Spain day-ahead prices."""

from __future__ import annotations

import argparse
from pathlib import Path

from peace_power.io import fetch_omie_marginal_prices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download OMIE marginal prices for Spain over a date range.",
    )
    parser.add_argument("start_date", help="Inclusive start date, for example 2026-03-01.")
    parser.add_argument(
        "end_date",
        nargs="?",
        help="Inclusive end date. Defaults to start_date for a single day pull.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/raw/omie",
        help="Directory where raw OMIE files should be stored.",
    )
    parser.add_argument(
        "--parsed-csv",
        default=None,
        help="Optional path for the parsed combined CSV output.",
    )
    parser.add_argument(
        "--revision",
        type=int,
        default=None,
        help="Specific OMIE revision to request. Default tries the highest available revision from 9 down to 1.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    end_date = args.end_date or args.start_date
    prices = fetch_omie_marginal_prices(
        args.start_date,
        end_date,
        revision=args.revision,
        output_dir=args.output_dir,
    )

    csv_path = Path(args.parsed_csv) if args.parsed_csv else None
    if csv_path is not None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        prices.to_csv(csv_path, index=False)

    print(f"Downloaded {len(prices)} rows from OMIE for {args.start_date} to {end_date}.")
    print(f"Raw files directory: {Path(args.output_dir).resolve()}")
    if csv_path is not None:
        print(f"Parsed CSV saved to: {csv_path.resolve()}")
    if not prices.empty:
        print(prices.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
