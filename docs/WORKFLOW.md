# Workflow

This is the one file to come back to when the project starts feeling scattered.

## Where We Are

The repo is now in a usable demo state.

What already exists:
- storage-aware spot-pricer research notebook
- reusable Python toolkit for BESS and congestion logic
- OMIE and ESIOS ingestion helpers
- REE node-capacity scoring
- client-demo dashboard shell with technical-monitor foundations
- strategy memo and congestion guide

What is still blocked:
- OMIE live pull on your machine because of a local DNS/network issue
- ESIOS live pull because the current token returns `403`
- original base model artifacts:
  - `pc_spot_pricer.pkl`
  - `pc_test_predictions.csv`

## If You Need One Thing To Open

Open the dashboard:

```bash
cd "/Users/oly/Documents/New project/peace-power-spain"
source .venv/bin/activate
streamlit run apps/dashboard/market_monitor.py
```

That gives you the cleanest “control room” view of the project, even while some live data is still blocked.

## What To Use For What

If you want something to show:
- run the dashboard in `apps/dashboard/market_monitor.py`

If you want to work in notebooks:
- use `notebooks/pc_spot_pricer_quantile.ipynb`
- use `notebooks/omie_backfill_quickstart.ipynb`
- use `notebooks/data_pull_quickstart.ipynb`

If you want the reusable Python logic:
- use `src/peace_power/market_toolkit.py`
- use `src/peace_power/io.py`
- use `src/peace_power/dashboard.py`

If you want the commercial narrative:
- use `apps/research/peace_capital_report.jsx`
- use `apps/research/peace_capital_congestion_guide.jsx`

If you want the actual product definition:
- use `docs/PRODUCT_BRIEF.md`

## Working Order

Do the project in this order:

1. Keep the dashboard as the main surface.
2. Get OMIE history pulling on your machine.
3. Get a valid ESIOS token.
4. Replace synthetic BESS and ATC with live inputs.
5. Recover the original base pricer artifacts.
6. Turn the research notebook into train/predict scripts.
7. Turn the dashboard into the technical operating screen: pricing, signals, alerts, briefing.
8. Use the dashboard as the client-facing output shell.

## Today’s Practical Move

If you want momentum today, do this:

1. Run the dashboard.
2. Use it as the master view.
3. Ignore ESIOS for the moment.
4. Fix OMIE network access next.

## Exact Commands

Install or refresh the local environment:

```bash
cd "/Users/oly/Documents/New project/peace-power-spain"
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install -e .
python3 -m pip install streamlit jupyterlab ipykernel
```

Run the dashboard:

```bash
streamlit run apps/dashboard/market_monitor.py
```

Open Jupyter:

```bash
jupyter lab
```

Backfill OMIE from the terminal:

```bash
python scripts/backfill_omie_history.py 2024-01-01 2025-12-31 --csv data/raw/omie/omie_history.csv
```

## Decision Rule

When you are not sure what to do next:

- if you need clarity, open the dashboard
- if you need data, work on OMIE first
- if you need the sellable story, work in the memo and dashboard together
- if you need the actual model, focus on recovering the base artifacts and replacing synthetic inputs

## Current North Star

The product is:

`Spain / Iberia day-ahead pricer, signal engine, and market monitor`

Not a giant “European power platform.”
Not a generic dashboard.
Not just a notebook.

That focus is what keeps the project coherent.
