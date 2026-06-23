#!/usr/bin/env python3
"""Refresh pc_live_esios.pkl — 90 days of ESIOS data with live thermal floor.

Thermal floor = TTF gas price / CCGT efficiency + EUA carbon price × CO2 factor
  - TTF:  fetched from Yahoo Finance (EUR/MWh)
  - EUA:  hardcoded at 65 EUR/tCO2; upgrade to a licensed feed (EEX/ICE) when available
  - CCGT efficiency: 50%
  - CO2 factor (CCGT): 0.34 tCO2/MWh_el
  - Variable O&M: +3 EUR/MWh

Run locally, then `git add pc_live_esios.pkl && git commit && git push` to deploy to Railway.
"""

from __future__ import annotations

import os
import pathlib
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# ── Config ─────────────────────────────────────────────────────────────────
ESIOS_BASE = "https://api.esios.ree.es"
N_DAYS = 90

# CCGT thermal floor parameters (Spain's marginal gas fleet)
CCGT_EFFICIENCY = 0.50       # 50% net efficiency
CCGT_CO2_FACTOR = 0.34       # tCO2/MWh_el
CCGT_VOM = 3.0               # EUR/MWh variable O&M

EUA_HARDCODE = 65.0          # EUR/tCO2 — replace with live feed when licensed

LIVE_INDICATORS: dict[int, tuple[str, dict]] = {
    600:   ("omie_price",        {"geo_ids[]": 3}),
    541:   ("gen_wind",          {}),
    542:   ("gen_solar_pv",      {}),
    10034: ("gen_solar_thermal", {}),
    138:   ("gen_hydro",         {}),
    474:   ("gen_nuclear",       {}),
    544:   ("demand_forecast",   {}),
    10209: ("atc_es_fr",         {}),
}

OUT_PATH = REPO_ROOT / "pc_live_esios.pkl"


def load_token() -> str:
    env_path = REPO_ROOT / ".env"
    token = os.getenv("ESIOS_TOKEN", "").strip()
    if not token and env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "ESIOS_TOKEN":
                    token = v.strip()
    if not token:
        raise RuntimeError("ESIOS_TOKEN not found in env or .env file")
    return token


def fetch_ttf_eur_per_mwh() -> float:
    """Fetch TTF front-month gas price from Yahoo Finance (EUR/MWh)."""
    try:
        import yfinance as yf
        import warnings
        warnings.filterwarnings("ignore")
        h = yf.Ticker("TTF=F").history(period="5d")
        if not h.empty:
            price = float(h["Close"].dropna().iloc[-1])
            print(f"  TTF live:  {price:.2f} EUR/MWh")
            return price
    except Exception as exc:
        print(f"  TTF fetch failed ({exc}) — using fallback 40.0")
    return 40.0


def compute_thermal_floor(ttf: float, eua: float) -> float:
    return round(ttf / CCGT_EFFICIENCY + eua * CCGT_CO2_FACTOR + CCGT_VOM, 2)


def pull_esios(token: str, start: datetime, end: datetime) -> pd.DataFrame:
    headers = {
        "x-api-key": token,
        "Accept": "application/json",
    }
    start_str = start.strftime("%Y-%m-%dT00:00:00+02:00")
    end_str = end.strftime("%Y-%m-%dT23:00:00+02:00")

    frames: dict[str, pd.DataFrame] = {}
    for ind_id, (name, extra) in LIVE_INDICATORS.items():
        params = {"start_date": start_str, "end_date": end_str, "time_trunc": "hour", **extra}
        r = requests.get(
            f"{ESIOS_BASE}/indicators/{ind_id}",
            headers=headers,
            params=params,
            timeout=30,
        )
        if r.status_code != 200:
            print(f"  FAIL {ind_id:>5} — {name} — HTTP {r.status_code}")
            continue
        values = r.json()["indicator"]["values"]
        df = pd.DataFrame(values)[["datetime", "value"]].rename(columns={"value": name})
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
        df = df.set_index("datetime")
        df = df[~df.index.duplicated(keep="last")]
        frames[name] = df
        last_val = float(df[name].dropna().iloc[-1]) if not df.empty else float("nan")
        print(f"  OK  {ind_id:>5} — {name:<22} — {len(df):>5} rows — last: {last_val:.2f}")

    if not frames:
        raise RuntimeError("No ESIOS indicators fetched — check token and connectivity")

    live = pd.concat(frames.values(), axis=1, join="outer")
    live = live.resample("h").mean()
    live = live.ffill(limit=3)
    return live


def add_derived(live: pd.DataFrame, ttf: float, eua: float, thermal_floor: float) -> pd.DataFrame:
    live = live.copy()
    live["ttf"] = ttf
    live["eua"] = eua

    live["gen_renewable"] = (
        live.get("gen_solar_pv", 0)
        + live.get("gen_solar_thermal", 0)
        + live.get("gen_wind", 0)
    )
    demand = live.get("demand_forecast", pd.Series(dtype=float))
    live["rsi"] = live["gen_renewable"] / demand.clip(lower=1.0)
    live["thermal_floor"] = thermal_floor
    live["floor_discount"] = live["omie_price"] - thermal_floor

    rsi_thresh = float(live["rsi"].dropna().quantile(0.75))
    price_stress_thresh = float(live["omie_price"].dropna().quantile(0.75))

    def _regime(row: pd.Series) -> str:
        if row["rsi"] >= rsi_thresh:
            return "Renewable-Dom."
        if row["omie_price"] >= price_stress_thresh:
            return "Demand-Stress"
        return "Thermal-Marginal"

    live["regime"] = live.apply(_regime, axis=1)

    # Negative and spike price probabilities (rolling 168-hour window)
    price = live["omie_price"].dropna()
    live["neg_price_prob"] = (
        (price < 0).rolling(168, min_periods=24).mean().reindex(live.index).ffill().fillna(0.0)
    )
    live["spike_prob"] = (
        (price > price_stress_thresh).rolling(168, min_periods=24).mean()
        .reindex(live.index).ffill().fillna(0.0)
    )
    return live


def main() -> None:
    print("=" * 60)
    print("Peace Power Spain — live data refresh")
    print("=" * 60)

    token = load_token()
    print(f"ESIOS token: {token[:6]}...{token[-4:]}")

    print("\n[TTF]")
    ttf = fetch_ttf_eur_per_mwh()
    eua = EUA_HARDCODE
    floor = compute_thermal_floor(ttf, eua)
    print(f"  EUA:       {eua:.2f} EUR/tCO2  (hardcoded — upgrade to ICE/EEX feed)")
    print(f"  Floor:     {floor:.2f} EUR/MWh  (= TTF/{CCGT_EFFICIENCY} + EUA×{CCGT_CO2_FACTOR} + {CCGT_VOM})")

    end = datetime.now()
    start = end - timedelta(days=N_DAYS)
    print(f"\n[ESIOS] {N_DAYS}-day pull: {start:%Y-%m-%d} → {end:%Y-%m-%d}")
    live = pull_esios(token, start, end)

    print("\n[Derived features]")
    live = add_derived(live, ttf, eua, floor)

    # Quick regime summary
    if "regime" in live.columns:
        for regime, cnt in live["regime"].value_counts().items():
            pct = cnt / len(live) * 100
            print(f"  {regime:<22}: {cnt:>5} hrs  ({pct:.1f}%)")

    last = live.dropna(subset=["omie_price"]).iloc[-1]
    print(f"\n[Last reading]")
    print(f"  Spot:         {last['omie_price']:.2f} EUR/MWh")
    print(f"  Thermal floor:{floor:.2f} EUR/MWh")
    print(f"  Floor disc:   {last['floor_discount']:+.2f} EUR/MWh")
    print(f"  RSI:          {last['rsi']:.4f}")
    print(f"  Regime:       {last['regime']}")

    live.to_pickle(OUT_PATH)
    rows = len(live)
    span_days = (live.index[-1] - live.index[0]).days
    print(f"\n  Saved → {OUT_PATH.name}  ({rows:,} rows, {span_days} days)")
    print("=" * 60)


if __name__ == "__main__":
    main()
