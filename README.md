# Peace Power Spain

Institutional research stack for Iberian power pricing, storage-adjusted surplus modeling, and congestion analytics.

Core coverage:
- OMIE day-ahead spot pricing and forecast uncertainty
- BESS-aware renewable-surplus and storage sunset modeling
- REE node-capacity mapping and congestion vulnerability scoring
- bank-facing strategy, methodology, and research outputs

## What This Is

This repository is being built as a private market-structure and signal-engine platform for:
- bank commodities and structured products desks
- energy consulting and market-advisory mandates
- institutional research clients needing Iberian power analytics

The objective is to convert the current prototype into a repeatable research product with:
- clean data inputs
- reusable Python modules
- documented methodology
- basic CI and tests
- client-ready outputs

In practical terms, the target product is a focused Iberian power intelligence stack that can explain:
- when renewable surplus is likely to push OMIE below the thermal floor
- when storage deployment starts compressing that edge
- where congestion risk is most likely to remain trapped at the node and zonal level

## Repo Layout

```text
peace-power-spain/
├── apps/dashboard/             client-demo dashboard shell
├── apps/research/              JSX research reports and strategy decks
├── data/templates/             CSV input templates for live data onboarding
├── docs/                       product and commercialization notes
├── notebooks/                  research notebooks
├── scripts/                    sanity checks and helper entry points
├── src/peace_power/            reusable Python package
├── tests/                      lightweight regression tests
├── .env.example                local secrets/config template
├── .gitignore
└── pyproject.toml
```

## Current Assets

- `notebooks/pc_spot_pricer_quantile.ipynb`
  Storage-aware OMIE spot pricer with quantile forecasts, sizing logic, and sunset thresholds.
- `src/peace_power/market_toolkit.py`
  Shared storage, node-mapping, and congestion feature-engineering helpers.
- `apps/dashboard/market_monitor.py`
  Streamlit client-demo dashboard for signals, storage sunset risk, congestion pressure, and build readiness.
- `apps/research/peace_capital_report.jsx`
  Strategy memorandum framed for institutional short-bias and risk review.
- `apps/research/peace_capital_congestion_guide.jsx`
  Congestion workflow with node-to-zone ICS framing for research and client education.

## Current Status

- Research logic: in place
- Dashboard shell: in place
- OMIE ingestion: coded, but your local DNS/network still has to reach OMIE
- ESIOS ingestion: coded, but blocked until you get a valid personal API token
- Base model artifacts: still missing
- Bank-grade daily output: not live yet, but the structure is now there

For the cleanest single-source project summary, use [docs/WORKFLOW.md](/Users/oly/Documents/New%20project/peace-power-spain/docs/WORKFLOW.md).
For the product north star, use [docs/PRODUCT_BRIEF.md](/Users/oly/Documents/New%20project/peace-power-spain/docs/PRODUCT_BRIEF.md).
For outreach targets and public-facing contacts, use [docs/TARGETS.md](/Users/oly/Documents/New%20project/peace-power-spain/docs/TARGETS.md).
For the automation layer, use [docs/N8N_WORKFLOW.md](/Users/oly/Documents/New%20project/peace-power-spain/docs/N8N_WORKFLOW.md).

## Quick Start

1. Create and activate a virtual environment.
2. Install the package in editable mode.
3. Copy `.env.example` to `.env` and fill in tokens or local file paths.
4. Run the sanity script.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python scripts/sanity_check.py
```

## Dashboard Demo

Once dependencies are installed, you can run the dashboard shell locally:

```bash
streamlit run apps/dashboard/market_monitor.py
```

It will:
- use live local OMIE files if they exist
- use the REE node template or raw node file if present
- fall back to a demo market frame when live files are missing
- show a readiness panel so you always know what is real vs synthetic

## Jupyter Data Pulls

You can now pull the core public data sources directly from a notebook instead of downloading files by hand.

```python
from peace_power import (
    fetch_esios_indicator,
    fetch_omie_history,
    fetch_omie_marginal_prices,
    search_esios_indicators,
)

# OMIE Spain day-ahead prices
omie = fetch_omie_marginal_prices(
    "2026-03-01",
    "2026-03-07",
    output_dir="data/raw/omie",
)

# OMIE multi-year backfill
omie_hist = fetch_omie_history(
    "2024-01-01",
    "2025-12-31",
    output_dir="data/raw/omie",
)

# Search ESIOS for the right live indicators
matches = search_esios_indicators("bateria", token="YOUR_ESIOS_TOKEN")
matches[["id", "name", "short_name"]].head(10)

# Pull one chosen indicator once you know the id
bess_online = fetch_esios_indicator(
    indicator_id=int(matches.iloc[0]["id"]),
    token="YOUR_ESIOS_TOKEN",
    start_date="2026-03-01T00:00:00+01:00",
    end_date="2026-03-07T23:00:00+01:00",
    time_trunc="hour",
)
```

Practical search terms for onboarding:
- `bateria`
- `almacenamiento`
- `capacidad comercial`
- `interconexion`
- `francia`
- `portugal`

## Command-Line Helpers

If you want a quick pull outside Jupyter:

```bash
python scripts/download_omie.py 2026-03-01 2026-03-07 --parsed-csv data/raw/omie/omie_mar_2026.csv
python scripts/backfill_omie_history.py 2024-01-01 2025-12-31 --csv data/raw/omie/omie_history.csv
python scripts/esios_indicator_search.py bateria --limit 20
```

## Data You Still Need

- `pc_spot_pricer.pkl`
- `pc_test_predictions.csv`
- ESIOS token and indicator mapping for live BESS/ATC pulls
- REE node map export for the full node universe
- historical OMIE / EPEX market data for out-of-sample backtests

## Near-Term Build Plan

1. Replace synthetic BESS with hourly ESIOS deployment and dispatch data.
2. Convert the notebook path into CLI training and forecasting scripts.
3. Add raw-data ingestion for OMIE, ESIOS, and REE.
4. Produce a daily bank-facing output: forecast table, uncertainty band, storage sunset status, and congestion heatmap.
5. Stand up a private client demo via API, dashboard, or daily report automation.

## Commercial Goal

The first version to sell is not “all European power.”
It is a focused product:

`Spain / Iberia day-ahead negative-price and congestion signal engine`

That is narrow enough to validate, specific enough to explain, and extensible enough to grow into a broader bank research or trading toolkit.
