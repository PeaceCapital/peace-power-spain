#!/usr/bin/env python3
"""Export pc_live_esios.pkl + pc_spot_pricer_real_v2.pkl → energy-dashboard/public/live_data.json

Run after refresh_live_data.py to update the React dashboard's data source.
"""

from __future__ import annotations

import json
import math
import pathlib
import pickle
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

REPO_ROOT   = pathlib.Path(__file__).resolve().parent.parent
PKL_LIVE    = REPO_ROOT / "pc_live_esios.pkl"
PKL_PRICER  = REPO_ROOT / "pc_spot_pricer_real_v2.pkl"
OUT_PATH    = REPO_ROOT / "energy-dashboard" / "public" / "live_data.json"
DAYS_EXPORT = 30    # days of hourly data included in JSON


def _safe(v: object) -> object:
    """Coerce to JSON-safe scalar."""
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 6)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 6)
    return v


def export_pricer(pricer: dict) -> dict:
    """Serialise all pricer fields + derived stats + MC payoff histogram."""
    spot_series: pd.Series = pricer["spot"]
    shift = pricer["shift_constant"]
    F_s   = pricer["last_spot"] + shift
    sigma = pricer["sigma"]
    T     = pricer["T"]
    r     = pricer["r"]
    K     = pricer["strike"]

    # ── MC payoff distribution (10 000 paths, reproducible) ────
    np.random.seed(42)
    Z       = np.random.standard_normal(10_000)
    ST_real = F_s * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z) - shift
    payoffs = np.maximum(ST_real - K, 0.0)
    nonzero = payoffs[payoffs > 0]
    itm_count = int(len(nonzero))

    counts, edges = np.histogram(nonzero, bins=30)
    midpoints     = 0.5 * (edges[:-1] + edges[1:])

    # ── Vol stats ───────────────────────────────────────────────
    vol_annual = pricer["annualised_vol"]
    vol_daily  = vol_annual / math.sqrt(365)
    vol_hourly = vol_annual / math.sqrt(8_760)

    # ── Spot series percentiles ─────────────────────────────────
    pct_labels = ["P1", "P5", "P10", "P25", "P50", "P75", "P90", "P95", "P99"]
    pct_vals   = np.percentile(spot_series.values, [1, 5, 10, 25, 50, 75, 90, 95, 99])

    # ── Rolling 30-day vol series (for chart) ───────────────────
    spot_pos  = spot_series[spot_series > 0]
    log_ret   = np.log(spot_pos).diff().dropna()
    z         = (log_ret - log_ret.mean()) / log_ret.std()
    ret_clean = log_ret[z.abs() < 4]
    rolling   = (
        ret_clean.rolling(30 * 24)
        .std()
        .mul(math.sqrt(8_760) * 100)
        .dropna()
    )
    # downsample to ~500 points for the chart
    stride = max(1, len(rolling) // 500)
    rolling_chart = [
        {"ts": ts.isoformat(), "vol": round(float(v), 3)}
        for ts, v in rolling.iloc[::stride].items()
        if not math.isnan(v)
    ]

    print(f"  Pricer: B76={pricer['black76_call']:.4f}  MC={pricer['mc_call']:.4f}  σ={vol_annual*100:.2f}%  ITM={itm_count}/10000")

    return {
        # Core parameters
        "last_spot":       _safe(pricer["last_spot"]),
        "strike":          _safe(K),
        "shift_constant":  _safe(shift),
        "shifted_f":       _safe(float(F_s)),
        "sigma":           _safe(sigma),
        "T":               _safe(T),
        "r":               _safe(r),
        # Prices
        "b76_call":        _safe(pricer["black76_call"]),
        "mc_call":         _safe(pricer["mc_call"]),
        "mc_se":           _safe(pricer["mc_se"]),
        "b76_vs_mc":       _safe(abs(pricer["black76_call"] - pricer["mc_call"])),
        # Probabilities
        "spike_prob":      _safe(pricer["spike_prob"]),
        "neg_price_prob":  _safe(pricer["neg_price_prob"]),
        # Vol
        "vol_annual":      _safe(vol_annual),
        "vol_daily":       _safe(vol_daily),
        "vol_hourly":      _safe(vol_hourly),
        "vol_normal_min":  0.30,
        "vol_normal_max":  0.80,
        # Additional
        "price_vs_floor":  _safe(pricer.get("price_vs_floor", 0.0)),
        "floor_proxy":     _safe(pricer.get("floor_proxy", 0.0)),
        # MC payoff distribution
        "mc_payoff": {
            "midpoints":  [round(float(x), 4) for x in midpoints],
            "counts":     [int(x) for x in counts],
            "itm_count":  itm_count,
            "itm_pct":    round(itm_count / 100, 1),
        },
        # Price percentiles
        "percentiles": {label: _safe(float(v)) for label, v in zip(pct_labels, pct_vals)},
        # Rolling vol series
        "rolling_vol": rolling_chart,
    }


def main() -> None:
    print("=" * 60)
    print("Peace Energy — JSON export for React dashboard")
    print("=" * 60)

    # ── Load live ──────────────────────────────────────────────
    if not PKL_LIVE.exists():
        print(f"ERROR: {PKL_LIVE} not found — run refresh_live_data.py first")
        sys.exit(1)

    live: pd.DataFrame = pd.read_pickle(PKL_LIVE)
    print(f"Loaded live data: {len(live):,} rows ({live.index[0].date()} → {live.index[-1].date()})")

    cutoff = live.index[-1] - pd.Timedelta(days=DAYS_EXPORT)
    live   = live[live.index >= cutoff]
    print(f"Exporting last {DAYS_EXPORT} days: {len(live):,} rows")

    # ── Load pricer ────────────────────────────────────────────
    pricer: dict | None = None
    if PKL_PRICER.exists():
        with open(PKL_PRICER, "rb") as f:
            pricer = pickle.load(f)
        print(f"Loaded pricer: spot {pricer['last_spot']:.2f} EUR/MWh")
    else:
        print("WARNING: pricer pickle not found — pricer section will be null")

    # ── Derive live scalars ────────────────────────────────────
    last        = live.dropna(subset=["omie_price"]).iloc[-1]
    last_spot   = float(last["omie_price"])
    last_regime = str(last["regime"])          if "regime"        in last.index else "Thermal-Marginal"
    last_rsi    = float(last["rsi"])           if "rsi"           in last.index else 0.0
    last_disc   = float(last["floor_discount"])if "floor_discount" in last.index else 0.0
    floor_proxy = float(last["thermal_floor"]) if "thermal_floor"  in last.index else 0.0
    live_ttf    = float(live["ttf"].iloc[-1])  if "ttf"           in live.columns else 35.0
    live_eua    = float(live["eua"].iloc[-1])  if "eua"           in live.columns else 65.0
    atc_last     = float(live["atc_es_fr"].dropna().iloc[-1])   if "atc_es_fr"    in live.columns else None
    omip_m1      = float(live["omip_m1"].dropna().iloc[-1])     if "omip_m1"      in live.columns else None
    omip_q1      = float(live["omip_q1"].dropna().iloc[-1])     if "omip_q1"      in live.columns else None
    forward_basis= float(live["forward_basis"].dropna().iloc[-1])if "forward_basis"in live.columns else None
    es_pt_spread = float(live["es_pt_spread"].dropna().iloc[-1])if "es_pt_spread" in live.columns else None

    # Signal direction (naive, without execution module)
    if last_disc < -5 and last_rsi > 0.4:
        cur_dir = "SHORT"
    elif last_disc > 10:
        cur_dir = "LONG"
    else:
        cur_dir = "NEUTRAL"
    cur_conf = min(0.99, abs(last_disc) / 50.0 + last_rsi * 0.3)

    vol_annual = pricer["annualised_vol"] if pricer else 0.0

    scalars = {
        "last_spot":     _safe(last_spot),
        "last_regime":   last_regime,
        "last_rsi":      _safe(last_rsi),
        "last_discount": _safe(last_disc),
        "floor_proxy":   _safe(floor_proxy),
        "live_ttf":      _safe(live_ttf),
        "live_eua":      _safe(live_eua),
        "vol_annual":    _safe(vol_annual),
        "b76_call":      _safe(pricer["black76_call"] if pricer else 0.0),
        "mc_call":       _safe(pricer["mc_call"]       if pricer else 0.0),
        "spike_prob":    _safe(float(live["spike_prob"].dropna().iloc[-1])        if "spike_prob"       in live.columns else 0.0),
        "neg_prob":      _safe(float(live["neg_price_prob"].dropna().iloc[-1])    if "neg_price_prob"   in live.columns else 0.0),
        "cur_dir":        cur_dir,
        "cur_conf":       _safe(cur_conf),
        "atc_last":       _safe(atc_last)      if atc_last      is not None else None,
        "omip_m1":        _safe(omip_m1)       if omip_m1       is not None else None,
        "omip_q1":        _safe(omip_q1)       if omip_q1       is not None else None,
        "forward_basis":  _safe(forward_basis) if forward_basis is not None else None,
        "es_pt_spread":   _safe(es_pt_spread)  if es_pt_spread  is not None else None,
    }

    # ── Serialise live rows ────────────────────────────────────
    cols = [
        "omie_price", "omie_price_pt", "gen_wind", "gen_solar_pv", "gen_solar_thermal",
        "gen_hydro", "gen_nuclear", "demand_forecast", "atc_es_fr",
        "ttf", "eua", "gen_renewable", "rsi", "thermal_floor",
        "floor_discount", "regime", "neg_price_prob", "spike_prob",
        "es_pt_spread", "forward_basis",
    ]
    available = [c for c in cols if c in live.columns]
    rows = []
    for ts, row in live[available].iterrows():
        r: dict[str, object] = {"ts": ts.isoformat()}
        for c in available:
            v = row[c]
            r[c] = _safe(v) if not isinstance(v, str) else str(v)
        rows.append(r)

    # ── Build pricer section ───────────────────────────────────
    print("\n[Pricer]")
    pricer_section = export_pricer(pricer) if pricer else None

    # ── Write JSON ─────────────────────────────────────────────
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "live":       rows,
        "scalars":    scalars,
        "pricer":     pricer_section,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, separators=(",", ":"))

    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"\nSaved → {OUT_PATH}")
    print(f"  {len(rows):,} live rows · {size_kb:.0f} KB")
    print("=" * 60)


if __name__ == "__main__":
    main()
