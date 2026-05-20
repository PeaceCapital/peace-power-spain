#!/usr/bin/env python3
"""n8n-friendly operational checks and briefing output for Peace Power Spain."""

from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import socket
import sys
from typing import Any
import urllib.error
import urllib.request
import warnings

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL 1.1.1+")


REPO_ROOT = Path(__file__).resolve().parents[1]


def json_print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def probe_omie_dns() -> dict[str, str]:
    try:
        resolved = socket.gethostbyname("www.omie.es")
        return {"status": "live", "detail": f"Resolved www.omie.es to {resolved}."}
    except Exception as exc:  # pragma: no cover - platform/network dependent
        return {"status": "blocked", "detail": f"DNS resolution failed: {exc}"}


def probe_esios_auth() -> dict[str, str]:
    token = os.getenv("ESIOS_TOKEN", "").strip()
    if not token:
        return {"status": "blocked", "detail": "ESIOS_TOKEN is missing from the environment."}

    request = urllib.request.Request(
        "https://api.esios.ree.es/indicators?text=bateria",
        headers={
            "Accept": "application/json; application/vnd.esios-api-v1+json",
            "Content-Type": "application/json",
            "x-api-key": token,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 - official API endpoint
            return {"status": "live", "detail": f"ESIOS API responded with HTTP {response.status}."}
    except urllib.error.HTTPError as exc:  # pragma: no cover - depends on token state
        return {"status": "blocked", "detail": f"ESIOS API returned HTTP {exc.code}."}
    except Exception as exc:  # pragma: no cover - platform/network dependent
        return {"status": "blocked", "detail": f"ESIOS probe failed: {exc}"}


def file_component(name: str, path: Path, *, critical: bool = False, missing_detail: str | None = None) -> dict[str, Any]:
    exists = path.exists()
    return {
        "component": name,
        "status": "ready" if exists else "missing",
        "critical": critical,
        "detail": f"Present at {path.relative_to(REPO_ROOT)}." if exists else (missing_detail or f"Missing: {path.name}"),
    }


def build_probe_payload() -> dict[str, Any]:
    omie = probe_omie_dns()
    esios = probe_esios_auth()

    components: list[dict[str, Any]] = [
        {
            "component": "OMIE network access",
            "status": omie["status"],
            "critical": True,
            "detail": omie["detail"],
        },
        {
            "component": "ESIOS authentication",
            "status": esios["status"],
            "critical": True,
            "detail": esios["detail"],
        },
        file_component(
            "OMIE history backfill",
            REPO_ROOT / "data" / "raw" / "omie" / "omie_history.csv",
            missing_detail="Backfill data/raw/omie/omie_history.csv so the live history path exists.",
        ),
        file_component(
            "REE node universe",
            REPO_ROOT / "data" / "raw" / "ree_node_capacity.csv",
            missing_detail="Replace the template node CSV with the full REE node universe.",
        ),
        file_component(
            "Base pricer artifacts",
            REPO_ROOT / "pc_spot_pricer.pkl",
            critical=True,
            missing_detail="Recover pc_spot_pricer.pkl from the base notebook run.",
        ),
        file_component(
            "Prediction artifact",
            REPO_ROOT / "pc_test_predictions.csv",
            critical=True,
            missing_detail="Recover pc_test_predictions.csv from the base notebook run.",
        ),
        file_component(
            "Quantile pricer artifact",
            REPO_ROOT / "pc_spot_pricer_v2.pkl",
            missing_detail="Optional but valuable: save the quantile pricer artifact from pc_spot_pricer_quantile.ipynb.",
        ),
    ]

    blockers = [
        item
        for item in components
        if item["critical"] and item["status"] != "ready" and item["status"] != "live"
    ]
    has_critical_blocker = len(blockers) > 0

    next_action = (
        "Stay in demo mode. Focus on ESIOS auth, OMIE network access, and recovering the base pricer artifacts."
        if has_critical_blocker
        else "Safe to trigger the daily refresh and briefing flow."
    )

    return {
        "run_date": date.today().isoformat(),
        "repo_root": str(REPO_ROOT),
        "has_critical_blocker": has_critical_blocker,
        "critical_blocker_count": len(blockers),
        "critical_blockers": blockers,
        "components": components,
        "next_action": next_action,
    }


def build_briefing_payload() -> dict[str, Any]:
    from peace_power.dashboard import (  # local import so `probe` stays lighter
        build_alert_frame,
        build_dashboard_bundle,
        build_market_briefing,
        summarize_market_state,
    )

    bundle = build_dashboard_bundle(REPO_ROOT)
    snapshot = summarize_market_state(bundle.market_df, bundle.zone_summary)
    window = bundle.market_df.tail(24 * 2).copy()
    alerts = build_alert_frame(window, bundle.zone_summary).to_dict(orient="records")
    briefing_lines = build_market_briefing(snapshot, bundle)

    return {
        "repo_root": str(REPO_ROOT),
        "market_source": bundle.market_source,
        "node_source": bundle.node_source,
        "snapshot": snapshot,
        "alerts": alerts,
        "briefing": briefing_lines,
        "readiness": bundle.readiness.to_dict(orient="records"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Operational helper for n8n orchestration.")
    parser.add_argument(
        "command",
        choices=["probe", "briefing", "war-room"],
        help="Output blocker status, a current market briefing, or both combined.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "probe":
        json_print(build_probe_payload())
        return 0
    if args.command == "briefing":
        json_print(build_briefing_payload())
        return 0
    if args.command == "war-room":
        json_print(
            {
                "probe": build_probe_payload(),
                "briefing": build_briefing_payload(),
            }
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
