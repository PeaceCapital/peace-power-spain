# Roadmap

## Phase 1: Research Repo

Goal: make the current prototype repeatable and understandable.

- Keep the quantile notebook as a research surface.
- Move reusable logic into `src/peace_power/`.
- Standardize templates for BESS and REE node data.
- Add sanity checks and regression tests.

## Phase 2: Live Data

Goal: remove synthetic assumptions.

- Pull OMIE hourly day-ahead prices.
- Pull ESIOS BESS online/absorption/discharge indicators.
- Pull REE node-capacity map snapshots.
- Persist raw and curated datasets separately.

## Phase 3: Bank-Grade Model

Goal: produce something a desk can evaluate.

- Convert notebook logic into train/predict CLIs.
- Promote the pricing engine from notebook logic into a repeatable pricer service.
- Add out-of-sample backtests and drift monitoring.
- Add model cards, feature-importance reports, and risk controls.
- Version the model artifacts and daily signal outputs.

## Phase 4: Commercial Packaging

Goal: make it buyable.

- Streamlit client-demo dashboard scaffold is already in place as an early shell.
- Expand the dashboard into a technical operating screen with pricing, alerts, and market briefing.
- Daily PDF or HTML signal note.
- API or flat-file signal feed.
- Dashboard for pricer outputs, forecast bands, alerts, congestion map, and context/news layer.
- Methodology memo, sample performance pack, and licensing terms.

## Recommended First Buyer

Start with one narrow offer:

`Spain / Iberia day-ahead negative-price and congestion signal pack`

That is easier to explain, easier to validate, and easier to price than a broad “European power intelligence platform.”
