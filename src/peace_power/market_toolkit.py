#!/usr/bin/env python3
"""Shared helpers for the Peace Capital Spain power stack.

This module adds two things the original prototype was missing:
- storage-aware features for the OMIE spot pricer
- node-to-zone congestion scoring for REE capacity maps
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional
import unicodedata

import numpy as np
import pandas as pd


DEFAULT_ZONE_MAP = {
    "GALICIA": "ES-NW",
    "ASTURIAS": "ES-NW",
    "CASTILLA Y LEON": "ES-NW",
    "CASTILLA-LEON": "ES-NW",
    "PAIS VASCO": "ES-NE",
    "NAVARRA": "ES-NE",
    "ARAGON": "ES-NE",
    "CATALUNA": "ES-NE",
    "LA RIOJA": "ES-NE",
    "MADRID": "ES-CENTER",
    "CASTILLA-LA MANCHA": "ES-CENTER",
    "CASTILLA LA MANCHA": "ES-CENTER",
    "EXTREMADURA": "ES-SW",
    "ANDALUCIA": "ES-SW",
    "MURCIA": "ES-SE",
    "COMUNITAT VALENCIANA": "ES-SE",
    "VALENCIA": "ES-SE",
    "BALEARES": "ES-ISLANDS",
    "CANARIAS": "ES-ISLANDS",
}

DEFAULT_REGION_RISK = {
    "MADRID": 0.92,
    "ARAGON": 1.00,
    "CATALUNA": 1.00,
    "PAIS VASCO": 0.82,
    "NAVARRA": 0.80,
    "CASTILLA Y LEON": 0.70,
    "CASTILLA-LA MANCHA": 0.72,
    "ANDALUCIA": 0.62,
    "VALENCIA": 0.78,
}


@dataclass(frozen=True)
class StorageSunsetResult:
    penetration_threshold: float
    capture_ratio_threshold: float
    online_capacity_threshold: float
    baseline_edge: float
    edge_at_threshold: float
    edge_ratio: float
    threshold_source: str


def normalize_label(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.upper().strip().split())


def _resolve_column(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    lower = {col.lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    return None


def _renewable_total(df: pd.DataFrame) -> pd.Series:
    if "ren_total" in df.columns:
        return pd.to_numeric(df["ren_total"], errors="coerce").fillna(0.0)
    cols = [col for col in ["gen_solar", "gen_wind", "gen_hydro"] if col in df.columns]
    if not cols:
        raise ValueError("Need renewable generation columns or 'ren_total'.")
    return df[cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).sum(axis=1)


def simulate_bess_fleet(
    df: pd.DataFrame,
    *,
    demand_col: str = "demand",
    deployed_share_start: float = 0.06,
    deployed_share_end: float = 0.30,
    charge_midpoint_hour: int = 14,
    discharge_midpoint_hour: int = 20,
) -> pd.DataFrame:
    """Create a synthetic storage fleet when live ESIOS data is unavailable."""
    out = df.copy()
    demand = pd.to_numeric(out[demand_col], errors="coerce").ffill()
    ren_total = _renewable_total(out)
    surplus = (ren_total - demand).clip(lower=0.0)
    peak_gap = (demand - ren_total).clip(lower=0.0)

    if "hour" in out.columns:
        hour = pd.to_numeric(out["hour"], errors="coerce").fillna(0.0)
    else:
        hour = pd.Series(out.index.hour, index=out.index, dtype=float)
    if "month" in out.columns:
        month = pd.to_numeric(out["month"], errors="coerce").fillna(1.0)
    else:
        month = pd.Series(out.index.month, index=out.index, dtype=float)

    deployment_curve = np.linspace(deployed_share_start, deployed_share_end, len(out))
    seasonal = 1.0 + 0.12 * np.sin(2 * np.pi * ((month - 1) / 12.0))
    base_scale = max(float(np.nanquantile(np.maximum(ren_total, demand), 0.90)), 1.0)
    bess_online = np.clip(base_scale * deployment_curve * seasonal, 0.35, None)

    charge_shape = np.exp(-0.5 * ((hour - charge_midpoint_hour) / 3.5) ** 2)
    discharge_shape = np.exp(-0.5 * ((hour - discharge_midpoint_hour) / 2.8) ** 2)

    charge_cap = bess_online * (0.18 + 0.82 * charge_shape)
    discharge_cap = bess_online * (0.15 + 0.85 * discharge_shape)

    out["bess_online_mw"] = bess_online
    out["bess_absorption_mw"] = np.minimum(surplus, charge_cap)
    out["bess_discharge_mw"] = np.minimum(peak_gap, discharge_cap)
    return out


def add_bess_features(
    df: pd.DataFrame,
    *,
    demand_col: str = "demand",
    rsi_col: str = "rsi",
    price_col: str = "price_omie",
    sunset_penetration: float = 0.30,
    sunset_capture: float = 0.35,
) -> pd.DataFrame:
    """Adds storage-aware features for the spot pricer feature matrix."""
    out = df.copy()
    if not {"bess_online_mw", "bess_absorption_mw", "bess_discharge_mw"}.issubset(out.columns):
        out = simulate_bess_fleet(out, demand_col=demand_col)

    demand = pd.to_numeric(out[demand_col], errors="coerce").ffill()
    ren_total = _renewable_total(out)
    online = pd.to_numeric(out["bess_online_mw"], errors="coerce").fillna(0.0)
    absorption = pd.to_numeric(out["bess_absorption_mw"], errors="coerce").fillna(0.0)
    discharge = pd.to_numeric(out["bess_discharge_mw"], errors="coerce").fillna(0.0)

    renewable_surplus = (ren_total - demand).clip(lower=0.0)
    peak_gap = (demand - ren_total).clip(lower=0.0)
    storage_scale = max(float(np.nanquantile(np.maximum(renewable_surplus, online), 0.95)), 1.0)

    out["renewable_surplus_mw"] = renewable_surplus
    out["surplus_after_bess_mw"] = (renewable_surplus - absorption).clip(lower=0.0)
    out["peak_gap_mw"] = peak_gap
    out["peak_gap_after_bess_mw"] = (peak_gap - discharge).clip(lower=0.0)
    out["bess_capture_ratio"] = absorption / renewable_surplus.clip(lower=1.0)
    out["bess_peak_relief_ratio"] = discharge / peak_gap.clip(lower=1.0)
    out["storage_penetration"] = online / storage_scale
    out["rsi_after_bess"] = (ren_total - absorption) / demand.clip(lower=1.0)
    out["rsi_delta_bess"] = out[rsi_col] - out["rsi_after_bess"]
    out["rsi_storage_decay"] = np.clip(
        1.0 - (out["storage_penetration"] / max(sunset_penetration, 1e-6)),
        0.15,
        1.0,
    )
    out["short_edge_score"] = np.clip(out[rsi_col] - 0.65, 0.0, None) * out["rsi_storage_decay"]
    out["storage_sunset_flag"] = (
        (out["storage_penetration"] >= sunset_penetration)
        | (out["bess_capture_ratio"] >= sunset_capture)
    ).astype(int)
    out["ttf_x_rsi_after_bess"] = (
        pd.to_numeric(out["ttf"], errors="coerce").fillna(0.0) * out["rsi_after_bess"]
        if "ttf" in out.columns
        else out["rsi_after_bess"]
    )
    out["storage_x_surplus"] = out["storage_penetration"] * out["renewable_surplus_mw"]
    out["storage_x_peak_gap"] = out["storage_penetration"] * out["peak_gap_mw"]
    if price_col in out.columns:
        out["price_vs_bess_net_surplus"] = (
            pd.to_numeric(out[price_col], errors="coerce").fillna(0.0)
            - out["surplus_after_bess_mw"]
        )
    return out


def estimate_storage_sunset(
    df: pd.DataFrame,
    *,
    rsi_col: str = "rsi",
    price_col: str = "price_omie",
    storage_penetration_col: str = "storage_penetration",
    capture_ratio_col: str = "bess_capture_ratio",
    online_capacity_col: str = "bess_online_mw",
    negative_price_cutoff: float = 0.0,
    high_rsi_quantile: float = 0.80,
    edge_retention_floor: float = 0.50,
    capture_ratio_trigger: float = 0.35,
    min_points: int = 72,
) -> StorageSunsetResult:
    """Estimate when the RSI-to-negative-price edge materially decays."""
    work = df[
        [
            rsi_col,
            price_col,
            storage_penetration_col,
            capture_ratio_col,
            online_capacity_col,
        ]
    ].dropna()
    if work.empty:
        raise ValueError("Need storage-enriched price history to estimate a sunset threshold.")

    work = work.copy()
    work["neg_price"] = (work[price_col] <= negative_price_cutoff).astype(int)
    high_rsi_cut = float(work[rsi_col].quantile(high_rsi_quantile))

    baseline = work[work[storage_penetration_col] <= work[storage_penetration_col].quantile(0.25)]
    if len(baseline) < min_points:
        baseline = work

    baseline_edge = float(
        baseline.loc[baseline[rsi_col] >= high_rsi_cut, "neg_price"].mean()
        - baseline["neg_price"].mean()
    )
    if not np.isfinite(baseline_edge) or baseline_edge <= 0:
        baseline_edge = float(
            baseline[[rsi_col, "neg_price"]].corr().iloc[0, 1]
            if len(baseline) > 1
            else 0.0
        )
    if not np.isfinite(baseline_edge) or baseline_edge <= 0:
        baseline_edge = 1e-6

    thresholds = np.unique(
        np.round(work[storage_penetration_col].quantile(np.linspace(0.10, 0.90, 9)).to_numpy(), 4)
    )
    selected = None
    for threshold in thresholds:
        sub = work[work[storage_penetration_col] >= threshold]
        if len(sub) < min_points:
            continue
        edge = float(
            sub.loc[sub[rsi_col] >= high_rsi_cut, "neg_price"].mean() - sub["neg_price"].mean()
        )
        if not np.isfinite(edge):
            edge = 0.0
        edge_ratio = edge / baseline_edge
        capture_ratio = float(sub[capture_ratio_col].mean())
        trigger_hit = (
            edge_ratio <= edge_retention_floor
            or capture_ratio >= capture_ratio_trigger
        )
        if trigger_hit:
            selected = (threshold, capture_ratio, float(sub[online_capacity_col].median()), edge, edge_ratio)
            source = "edge_decay" if edge_ratio <= edge_retention_floor else "capture_ratio"
            break

    if selected is None:
        sub = work[work[storage_penetration_col] >= thresholds[-1]]
        edge = float(
            sub.loc[sub[rsi_col] >= high_rsi_cut, "neg_price"].mean() - sub["neg_price"].mean()
        )
        edge_ratio = edge / baseline_edge if baseline_edge else 0.0
        selected = (
            float(thresholds[-1]),
            float(sub[capture_ratio_col].mean()),
            float(sub[online_capacity_col].median()),
            edge,
            edge_ratio,
        )
        source = "max_observed"

    return StorageSunsetResult(
        penetration_threshold=float(selected[0]),
        capture_ratio_threshold=float(selected[1]),
        online_capacity_threshold=float(selected[2]),
        baseline_edge=float(baseline_edge),
        edge_at_threshold=float(selected[3]),
        edge_ratio=float(selected[4]),
        threshold_source=source,
    )


def map_ree_nodes_to_congestion_zones(
    nodes: pd.DataFrame,
    *,
    region_col: Optional[str] = None,
    zone_map: Optional[Mapping[str, str]] = None,
) -> pd.DataFrame:
    """Maps REE node rows into internal congestion zones for spread analysis."""
    work = nodes.copy()
    zone_map = {
        normalize_label(key): value
        for key, value in (zone_map or DEFAULT_ZONE_MAP).items()
    }
    region_col = region_col or _resolve_column(work, "region", "autonomous_community", "province", "location")
    if region_col is None:
        raise ValueError("Need a region-style column to map nodes into congestion zones.")

    work["region_norm"] = work[region_col].map(normalize_label)

    def map_zone(region: str) -> str:
        for key, zone in zone_map.items():
            if key in region:
                return zone
        return "ES-OTHER"

    work["congestion_zone"] = work["region_norm"].map(map_zone)
    return work


def score_congestion_nodes(
    nodes: pd.DataFrame,
    *,
    availability_col: Optional[str] = None,
    region_col: Optional[str] = None,
    constrained_regions: tuple[str, ...] = ("MADRID", "ARAGON", "CATALUNA"),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Scores node vulnerability and aggregates it into an ICS-style zone signal."""
    work = map_ree_nodes_to_congestion_zones(nodes, region_col=region_col)
    availability_col = availability_col or _resolve_column(
        work,
        "available_capacity_mw",
        "available_capacity",
        "capacity_available_mw",
        "available_mw",
    )
    if availability_col is None:
        raise ValueError("Need an available-capacity column to score congestion nodes.")

    available = pd.to_numeric(work[availability_col], errors="coerce").fillna(0.0)
    p95 = max(float(np.nanquantile(np.maximum(available, 0.0), 0.95)), 1.0)
    constrained_cutoff = max(float(np.nanquantile(np.maximum(available, 0.0), 0.20)), 0.0)

    work["available_capacity_mw"] = available
    work["availability_ratio"] = (available / p95).clip(lower=0.0, upper=1.0)
    work["regional_risk_weight"] = work["region_norm"].map(DEFAULT_REGION_RISK).fillna(0.60)
    work["is_constrained_region"] = work["region_norm"].isin({normalize_label(v) for v in constrained_regions})
    work["is_low_capacity_node"] = (available <= constrained_cutoff).astype(int)
    work["zone_constraint_share"] = work.groupby("congestion_zone")["is_low_capacity_node"].transform("mean")

    work["congestion_vulnerability_score"] = (
        100.0
        * (
            0.55 * (1.0 - work["availability_ratio"])
            + 0.25 * work["regional_risk_weight"]
            + 0.10 * work["zone_constraint_share"]
            + 0.10 * work["is_constrained_region"].astype(float)
        )
    ).round(1)

    zone_summary = (
        work.groupby("congestion_zone", as_index=False)
        .agg(
            nodes=("congestion_zone", "size"),
            constrained_nodes=("is_low_capacity_node", "sum"),
            constrained_share=("is_low_capacity_node", "mean"),
            available_capacity_mw=("available_capacity_mw", "sum"),
            mean_vulnerability_score=("congestion_vulnerability_score", "mean"),
        )
        .sort_values(["mean_vulnerability_score", "constrained_share"], ascending=False)
    )
    zone_summary["ics_zone_pressure"] = (
        zone_summary["mean_vulnerability_score"] * zone_summary["constrained_share"]
    ).round(2)
    return work, zone_summary
