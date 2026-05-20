"""Dashboard data helpers for the Peace Power Spain client demo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from peace_power.io import load_node_capacity_csv
from peace_power.market_toolkit import (
    StorageSunsetResult,
    add_bess_features,
    estimate_storage_sunset,
    score_congestion_nodes,
)


@dataclass(frozen=True)
class DashboardBundle:
    market_df: pd.DataFrame
    nodes_df: pd.DataFrame
    zone_summary: pd.DataFrame
    sunset: StorageSunsetResult
    readiness: pd.DataFrame
    market_source: str
    node_source: str


def _sigmoid(values: pd.Series | np.ndarray) -> pd.Series:
    array = np.asarray(values, dtype=float)
    return pd.Series(1.0 / (1.0 + np.exp(-array)), index=getattr(values, "index", None))


def build_demo_market_frame(
    *,
    hours: int = 24 * 45,
    end: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Build a synthetic but structurally realistic market frame for the dashboard."""
    end_ts = pd.Timestamp(end or pd.Timestamp.now(tz="Europe/Madrid")).floor("h")
    idx = pd.date_range(end=end_ts, periods=hours, freq="h")

    hour = pd.Series(idx.hour, index=idx, dtype=float)
    month = pd.Series(idx.month, index=idx, dtype=float)
    day_progress = np.linspace(0, 5 * np.pi, len(idx))

    solar_shape = np.clip(np.sin((hour - 6) / 12 * np.pi), 0.0, None)
    gen_solar = 4 + 14 * solar_shape * (1.0 + 0.18 * np.sin((month - 1) / 12 * 2 * np.pi))
    gen_wind = np.clip(13 + 5 * np.cos(day_progress * 0.8) + 2.5 * np.sin(day_progress * 1.7), 4, None)
    gen_hydro = np.clip(3.8 + 0.7 * np.sin(day_progress * 0.35), 2.5, 5.5)

    morning_peak = np.exp(-0.5 * ((hour - 9) / 2.8) ** 2)
    evening_peak = np.exp(-0.5 * ((hour - 20) / 3.2) ** 2)
    demand = np.clip(
        24
        + 2.2 * np.sin(day_progress)
        + 4.5 * morning_peak
        + 6.2 * evening_peak
        + 0.8 * np.cos((month - 1) / 12 * 2 * np.pi),
        16,
        None,
    )

    ttf = np.clip(34 + 3.5 * np.sin(day_progress * 0.45) + 1.3 * np.cos(day_progress * 0.12), 26, 52)
    renewable_total = gen_solar + gen_wind + gen_hydro
    renewable_surplus = np.clip(renewable_total - demand, 0, None)

    midday_discount = 14 * solar_shape
    wind_discount = 0.8 * (gen_wind - np.median(gen_wind))
    stress_premium = 0.9 * np.clip(demand - renewable_total, 0, None)

    price_omie = np.clip(
        57
        + 0.58 * ttf
        + stress_premium
        - midday_discount
        - wind_discount
        - 1.15 * renewable_surplus,
        -35,
        165,
    )

    frame = pd.DataFrame(
        {
            "gen_solar": gen_solar,
            "gen_wind": gen_wind,
            "gen_hydro": gen_hydro,
            "demand": demand,
            "ttf": ttf,
            "price_omie": price_omie,
            "hour": hour,
            "month": month,
        },
        index=idx,
    )
    frame["rsi"] = renewable_total / frame["demand"].clip(lower=1.0)
    return enrich_market_frame(frame)


def enrich_market_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Ensure a market frame contains the signal fields needed by the dashboard."""
    work = frame.copy()
    if "datetime" in work.columns:
        work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
        work = work.dropna(subset=["datetime"]).set_index("datetime")
    if not isinstance(work.index, pd.DatetimeIndex):
        raise ValueError("market frame must have a DatetimeIndex or datetime column.")
    work = work.sort_index()

    if "hour" not in work.columns:
        work["hour"] = work.index.hour
    if "month" not in work.columns:
        work["month"] = work.index.month

    if "demand" not in work.columns:
        baseline_demand = 25 + 3.8 * np.sin(np.linspace(0, 4 * np.pi, len(work)))
        work["demand"] = np.clip(baseline_demand + 2.5 * ((work.index.hour >= 18) & (work.index.hour <= 22)), 16, None)

    if "gen_solar" not in work.columns:
        solar_shape = np.clip(np.sin((work.index.hour - 6) / 12 * np.pi), 0.0, None)
        work["gen_solar"] = 3 + 13 * solar_shape
    if "gen_wind" not in work.columns:
        work["gen_wind"] = np.clip(11 + 4 * np.cos(np.linspace(0, 3 * np.pi, len(work))), 4, None)
    if "gen_hydro" not in work.columns:
        work["gen_hydro"] = 4.0
    if "ttf" not in work.columns:
        work["ttf"] = 36 + 2.5 * np.sin(np.linspace(0, 2 * np.pi, len(work)))
    if "price_omie" not in work.columns:
        renewable_total = work["gen_solar"] + work["gen_wind"] + work["gen_hydro"]
        work["price_omie"] = np.clip(55 + 0.55 * work["ttf"] - 0.9 * (renewable_total - work["demand"]), -30, 160)

    if "rsi" not in work.columns:
        renewable_total = work["gen_solar"] + work["gen_wind"] + work["gen_hydro"]
        work["rsi"] = renewable_total / work["demand"].clip(lower=1.0)

    work = add_bess_features(work)

    work["thermal_floor_proxy"] = 18.0 + 1.45 * pd.to_numeric(work["ttf"], errors="coerce").fillna(0.0)
    work["price_discount_to_floor"] = work["thermal_floor_proxy"] - pd.to_numeric(work["price_omie"], errors="coerce").fillna(0.0)
    work["rsi_signal_score"] = np.clip((work["rsi_after_bess"] - 0.78) / 0.28, 0.0, 1.0)
    work["tpb_signal_score"] = np.clip(work["price_discount_to_floor"] / 38.0, 0.0, 1.0)

    surplus_scale = max(float(np.nanquantile(np.maximum(work["renewable_surplus_mw"], 0.0), 0.90)), 1.0)
    work["npp_proxy"] = _sigmoid(
        2.8 * (work["rsi_after_bess"] - 0.95)
        + 1.2 * (work["renewable_surplus_mw"] / surplus_scale)
        - 1.8 * work["storage_penetration"]
    ).clip(0.0, 1.0)

    work["ics_proxy"] = _sigmoid(
        2.0 * (work["surplus_after_bess_mw"] / surplus_scale)
        + 0.8 * work["storage_sunset_flag"]
        - 1.1 * (work["peak_gap_after_bess_mw"] / surplus_scale)
    ).clip(0.0, 1.0)

    hydro_anomaly = (pd.to_numeric(work["gen_hydro"], errors="coerce").fillna(0.0) - work["gen_hydro"].median()) / max(
        float(work["gen_hydro"].std(ddof=0)),
        1.0,
    )
    work["hra_proxy"] = np.clip(0.5 + 0.2 * hydro_anomaly, 0.0, 1.0)
    work["composite_signal"] = (
        0.35 * work["rsi_signal_score"]
        + 0.25 * work["tpb_signal_score"]
        + 0.20 * work["npp_proxy"]
        + 0.12 * work["ics_proxy"]
        + 0.08 * work["hra_proxy"]
    ).clip(0.0, 1.0)

    work["signal_regime"] = np.select(
        [
            work["storage_sunset_flag"].eq(1),
            work["composite_signal"] >= 0.90,
            work["composite_signal"] >= 0.80,
            work["composite_signal"] >= 0.70,
            work["composite_signal"] >= 0.60,
        ],
        [
            "Sunset Risk",
            "Maximum",
            "High Conviction",
            "Overweight",
            "Standard",
        ],
        default="No Trade",
    )
    work["negative_price_flag"] = (work["price_omie"] <= 0.0).astype(int)
    work["delivery_date"] = work.index.normalize()
    return work


def load_market_frame(root: str | Path) -> tuple[pd.DataFrame, str]:
    """Load the best available market frame, or fall back to the demo build."""
    root_path = Path(root)
    candidates = [
        root_path / "data" / "curated" / "dashboard_market_frame.csv",
        root_path / "data" / "raw" / "omie" / "omie_history.csv",
        root_path / "data" / "raw" / "omie" / "omie_mar_2026.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            frame = pd.read_csv(candidate)
            return enrich_market_frame(frame), f"Local file: {candidate.relative_to(root_path)}"
    return build_demo_market_frame(), "Synthetic demo frame"


def load_node_frame(root: str | Path) -> tuple[pd.DataFrame, str]:
    """Load node capacity data from a raw file or the starter template."""
    root_path = Path(root)
    candidates = [
        root_path / "data" / "raw" / "ree_node_capacity.csv",
        root_path / "data" / "templates" / "ree_node_capacity_template.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return load_node_capacity_csv(candidate), f"Local file: {candidate.relative_to(root_path)}"
    raise FileNotFoundError("No REE node-capacity file or template found.")


def build_readiness_frame(
    root: str | Path,
    *,
    market_source: str,
    node_source: str,
) -> pd.DataFrame:
    """Summarize what is live, synthetic, blocked, or still missing."""
    root_path = Path(root)
    status_rows = [
        {
            "component": "OMIE day-ahead history",
            "status": "Live" if "Local file" in market_source else "Synthetic fallback",
            "detail": market_source,
        },
        {
            "component": "ESIOS BESS / ATC",
            "status": "Blocked",
            "detail": "API token still returning HTTP 403.",
        },
        {
            "component": "REE node map",
            "status": "Template" if "templates" in node_source else "Live",
            "detail": node_source,
        },
        {
            "component": "Base pricer artifacts",
            "status": "Ready" if (root_path / "pc_spot_pricer.pkl").exists() and (root_path / "pc_test_predictions.csv").exists() else "Missing",
            "detail": "Need pc_spot_pricer.pkl and pc_test_predictions.csv for the original model path.",
        },
        {
            "component": "Dashboard app",
            "status": "Ready",
            "detail": "Client-demo shell is available now and can switch from demo to live files later.",
        },
    ]
    return pd.DataFrame(status_rows)


def summarize_market_state(market_df: pd.DataFrame, zone_summary: pd.DataFrame) -> dict[str, object]:
    """Build a compact KPI dict for the dashboard header cards."""
    latest = market_df.iloc[-1]
    recent = market_df.tail(24 * 7)
    hot_zone = zone_summary.iloc[0] if not zone_summary.empty else None
    return {
        "latest_composite": float(latest["composite_signal"]),
        "latest_regime": str(latest["signal_regime"]),
        "latest_price": float(latest["price_omie"]),
        "negative_hours_7d": int(recent["negative_price_flag"].sum()),
        "sunset_share_7d": float(recent["storage_sunset_flag"].mean()),
        "storage_penetration": float(latest["storage_penetration"]),
        "bess_capture_ratio": float(latest["bess_capture_ratio"]),
        "thermal_discount": float(latest["price_discount_to_floor"]),
        "hot_zone": str(hot_zone["congestion_zone"]) if hot_zone is not None else "N/A",
        "hot_zone_pressure": float(hot_zone["ics_zone_pressure"]) if hot_zone is not None else 0.0,
    }


def build_alert_frame(window: pd.DataFrame, zone_summary: pd.DataFrame) -> pd.DataFrame:
    """Create the operational alert table for the dashboard and automation layer."""
    latest = window.iloc[-1]
    alerts: list[dict[str, str]] = []

    if float(latest["price_omie"]) <= 0:
        alerts.append(
            {
                "severity": "High",
                "alert": "Negative price regime active",
                "detail": f"Latest OMIE print is {latest['price_omie']:.1f} €/MWh.",
            }
        )
    if float(latest["composite_signal"]) >= 0.80:
        alerts.append(
            {
                "severity": "High",
                "alert": "High-conviction signal",
                "detail": f"Composite signal is {latest['composite_signal']:.2f} with regime {latest['signal_regime']}.",
            }
        )
    if int(latest["storage_sunset_flag"]) == 1:
        alerts.append(
            {
                "severity": "Medium",
                "alert": "Storage sunset pressure",
                "detail": (
                    f"Storage penetration is {latest['storage_penetration']:.2f} and "
                    f"capture ratio is {latest['bess_capture_ratio']:.2f}."
                ),
            }
        )
    if not zone_summary.empty and float(zone_summary.iloc[0]["ics_zone_pressure"]) >= 30:
        alerts.append(
            {
                "severity": "Medium",
                "alert": "Congestion hotspot building",
                "detail": (
                    f"Top zone is {zone_summary.iloc[0]['congestion_zone']} with "
                    f"ICS pressure {zone_summary.iloc[0]['ics_zone_pressure']:.1f}."
                ),
            }
        )
    if float(latest["price_discount_to_floor"]) >= 20:
        alerts.append(
            {
                "severity": "Low",
                "alert": "Thermal-floor discount widening",
                "detail": f"OMIE is {latest['price_discount_to_floor']:.1f} €/MWh below the thermal proxy.",
            }
        )

    if not alerts:
        alerts.append(
            {
                "severity": "Info",
                "alert": "No major alert",
                "detail": "Current frame does not show a major threshold breach.",
            }
        )
    return pd.DataFrame(alerts)


def build_market_briefing(snapshot: dict[str, object], bundle: DashboardBundle) -> list[str]:
    """Create compact briefing bullets for the ops panel or automation output."""
    return [
        (
            f"Current regime is **{snapshot['latest_regime']}** with a composite score of "
            f"**{snapshot['latest_composite']:.2f}**."
        ),
        (
            f"OMIE last print is **{snapshot['latest_price']:.1f} €/MWh**, "
            f"with a thermal-floor discount of **{snapshot['thermal_discount']:.1f} €/MWh**."
        ),
        (
            f"Storage penetration is **{snapshot['storage_penetration']:.2f}** and "
            f"the current sunset trigger source is **{bundle.sunset.threshold_source}**."
        ),
        (
            f"Top congestion zone is **{snapshot['hot_zone']}** with ICS pressure "
            f"of **{snapshot['hot_zone_pressure']:.1f}**."
        ),
        (
            "Live external news is not wired yet. Treat this as a model-generated "
            "briefing layer until the outage/news feeds are connected."
        ),
    ]


def build_dashboard_bundle(root: str | Path) -> DashboardBundle:
    """Load all inputs needed by the client-demo dashboard."""
    market_df, market_source = load_market_frame(root)
    nodes_df, node_source = load_node_frame(root)
    scored_nodes, zone_summary = score_congestion_nodes(nodes_df)
    sunset = estimate_storage_sunset(market_df)
    readiness = build_readiness_frame(root, market_source=market_source, node_source=node_source)
    return DashboardBundle(
        market_df=market_df,
        nodes_df=scored_nodes,
        zone_summary=zone_summary,
        sunset=sunset,
        readiness=readiness,
        market_source=market_source,
        node_source=node_source,
    )
