from __future__ import annotations

from pathlib import Path
import unittest

from peace_power.dashboard import (
    build_alert_frame,
    build_dashboard_bundle,
    build_demo_market_frame,
    build_market_briefing,
    summarize_market_state,
)


class DashboardTests(unittest.TestCase):
    def test_build_demo_market_frame_has_dashboard_fields(self) -> None:
        frame = build_demo_market_frame(hours=24 * 10, end="2026-03-26 12:00:00")
        for column in [
            "composite_signal",
            "signal_regime",
            "storage_penetration",
            "thermal_floor_proxy",
        ]:
            self.assertIn(column, frame.columns)
        self.assertEqual(len(frame), 24 * 10)

    def test_build_dashboard_bundle_uses_repo_templates(self) -> None:
        root = Path(__file__).resolve().parents[1]
        bundle = build_dashboard_bundle(root)
        self.assertGreater(len(bundle.market_df), 0)
        self.assertGreater(len(bundle.zone_summary), 0)
        self.assertIn("Dashboard app", bundle.readiness["component"].tolist())

    def test_summarize_market_state_returns_hot_zone(self) -> None:
        root = Path(__file__).resolve().parents[1]
        bundle = build_dashboard_bundle(root)
        snapshot = summarize_market_state(bundle.market_df, bundle.zone_summary)
        self.assertIn("latest_composite", snapshot)
        self.assertIn("hot_zone", snapshot)

    def test_alert_frame_and_briefing_are_non_empty(self) -> None:
        root = Path(__file__).resolve().parents[1]
        bundle = build_dashboard_bundle(root)
        window = bundle.market_df.tail(48)
        snapshot = summarize_market_state(bundle.market_df, bundle.zone_summary)
        alerts = build_alert_frame(window, bundle.zone_summary)
        briefing = build_market_briefing(snapshot, bundle)
        self.assertGreater(len(alerts), 0)
        self.assertGreater(len(briefing), 0)


if __name__ == "__main__":
    unittest.main()
