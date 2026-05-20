from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from peace_power.market_toolkit import (
    add_bess_features,
    normalize_label,
    score_congestion_nodes,
)


class MarketToolkitTests(unittest.TestCase):
    def test_normalize_label_strips_accents(self) -> None:
        self.assertEqual(normalize_label("Cataluña"), "CATALUNA")
        self.assertEqual(normalize_label("  Aragón  "), "ARAGON")

    def test_add_bess_features_creates_storage_columns(self) -> None:
        idx = pd.date_range("2024-01-01", periods=24, freq="h")
        df = pd.DataFrame(
            {
                "gen_solar": np.linspace(0, 10, len(idx)),
                "gen_wind": np.linspace(8, 14, len(idx)),
                "gen_hydro": 4.0,
                "demand": np.linspace(18, 26, len(idx)),
                "rsi": np.linspace(0.4, 1.1, len(idx)),
                "ttf": 40.0,
                "price_omie": np.linspace(60, 20, len(idx)),
                "hour": idx.hour,
                "month": idx.month,
            },
            index=idx,
        )
        feat = add_bess_features(df)
        for col in [
            "bess_online_mw",
            "bess_absorption_mw",
            "storage_penetration",
            "rsi_after_bess",
            "storage_sunset_flag",
        ]:
            self.assertIn(col, feat.columns)

    def test_score_congestion_nodes_returns_zone_summary(self) -> None:
        nodes = pd.DataFrame(
            {
                "node_id": ["1", "2", "3"],
                "node_name": ["Madrid North", "Zaragoza East", "Sevilla South"],
                "region": ["Madrid", "Aragon", "Andalucia"],
                "available_capacity_mw": [80, 30, 220],
            }
        )
        scored, summary = score_congestion_nodes(nodes)
        self.assertIn("congestion_vulnerability_score", scored.columns)
        self.assertIn("ics_zone_pressure", summary.columns)
        self.assertGreater(len(summary), 0)


if __name__ == "__main__":
    unittest.main()
