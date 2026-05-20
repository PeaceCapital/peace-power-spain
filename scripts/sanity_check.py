#!/usr/bin/env python3
"""Quick health check for the repo structure and core helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from peace_power import (
    add_bess_features,
    estimate_storage_sunset,
    load_node_capacity_csv,
    score_congestion_nodes,
)


def run_storage_check() -> None:
    idx = pd.date_range("2024-01-01", periods=72, freq="h")
    df = pd.DataFrame(
        {
            "gen_solar": np.clip(8 + 7 * np.sin(np.linspace(0, 4 * np.pi, len(idx))), 0, None),
            "gen_wind": np.clip(12 + 5 * np.cos(np.linspace(0, 3 * np.pi, len(idx))), 0, None),
            "gen_hydro": 4.0,
            "demand": 23 + 3 * np.sin(np.linspace(0, 5 * np.pi, len(idx))),
            "ttf": 38.0,
            "price_omie": np.clip(48 - 20 * np.sin(np.linspace(0, 4 * np.pi, len(idx))), -10, 150),
            "hour": idx.hour,
            "month": idx.month,
        },
        index=idx,
    )
    df["rsi"] = (df["gen_solar"] + df["gen_wind"]) / df["demand"]
    feat = add_bess_features(df)
    sunset = estimate_storage_sunset(feat)
    print("Storage sanity check")
    print(f"  rows              : {len(feat)}")
    print(f"  mean penetration  : {feat['storage_penetration'].mean():.3f}")
    print(f"  sunset trigger    : {sunset.penetration_threshold:.3f}")
    print(f"  trigger source    : {sunset.threshold_source}")


def run_node_check() -> None:
    root = Path(__file__).resolve().parents[1]
    nodes = load_node_capacity_csv(root / "data" / "templates" / "ree_node_capacity_template.csv")
    _, summary = score_congestion_nodes(nodes)
    print("Node scoring sanity check")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    run_storage_check()
    print()
    run_node_check()
