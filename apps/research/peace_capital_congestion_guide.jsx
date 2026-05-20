import { useState } from "react";

const STEPS = [
  { id: "concept",   label: "I. The Concept" },
  { id: "data",      label: "II. Data Setup" },
  { id: "model",     label: "III. Spread Model" },
  { id: "signal",    label: "IV. Signal Engine" },
  { id: "backtest",  label: "V. Backtest" },
  { id: "pnl",       label: "VI. P&L & Output" },
];

/* ── CODE BLOCK ─────────────────────────────────────────────── */
function Code({ children, lang = "python" }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(children.trim());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="code-wrap">
      <div className="code-bar">
        <span className="code-lang">{lang}</span>
        <button className="copy-btn" onClick={copy}>{copied ? "Copied" : "Copy"}</button>
      </div>
      <pre className="code-block"><code>{children.trim()}</code></pre>
    </div>
  );
}

/* ── NOTE / CALLOUT ─────────────────────────────────────────── */
function Note({ label = "Note", color = "teal", children }) {
  return (
    <div className={`callout callout-${color}`}>
      <span className="callout-label">{label}</span>
      {children}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════ */
/*  STEP CONTENT                                                */
/* ════════════════════════════════════════════════════════════ */

function ConceptStep() {
  return (
    <div className="step-body">
      <Note label="What You Are Building">
        A congestion spread trading simulator that detects when transmission
        constraints between two price zones create a persistent, exploitable
        price differential — and generates entry/exit signals around it.
      </Note>

      <h3 className="subhead">The Core Idea</h3>
      <p className="body-text">
        Electricity grids are divided into zones. When a transmission line
        between two zones becomes congested — i.e., more power wants to flow
        through it than its physical capacity allows — the two zones decouple
        and trade at different prices. The zone with surplus generation trades
        cheap; the zone with deficit trades expensive.
      </p>
      <p className="body-text" style={{marginTop:"12px"}}>
        In California, this happened between NP15 (north, hydro-heavy) and
        SP15 (south, gas-heavy, high demand). In Europe, the same dynamic
        plays between Spain and France across the Pyrenees, or between
        northern and southern Germany on the North-South corridor.
      </p>
      <p className="body-text" style={{marginTop:"12px"}}>
        The trade is simple in structure: <strong>buy the cheap zone, sell
        the expensive zone</strong> when the spread exceeds your threshold,
        and close when it reverts. The complexity is in knowing when the
        spread is genuinely bound by congestion versus noise.
      </p>

      <h3 className="subhead" style={{marginTop:"28px"}}>The Five Variables You Need</h3>
      <table className="report-table">
        <thead>
          <tr><th>Variable</th><th>What It Is</th><th>Why It Matters</th></tr>
        </thead>
        <tbody>
          {[
            ["Zone A Price", "DA clearing price in the surplus zone (€/MWh)", "Your buy leg — you want this cheap"],
            ["Zone B Price", "DA clearing price in the deficit zone (€/MWh)", "Your sell leg — you want this expensive"],
            ["Spread", "Zone B − Zone A", "Your P&L driver. Positive = congestion. Negative = uncongested or reversed."],
            ["ATC (Available Transfer Capacity)", "Remaining headroom on the interconnector (MW)", "Congestion confirmation. Low ATC = spread is real, not noise."],
            ["REE Node Capacity Map", "Available demand / absorption capacity by node", "Tells you where surplus can escape and where it stays trapped. This is the locational layer behind the ICS signal."],
          ].map(([v,w,m]) => (
            <tr key={v}>
              <td className="td-strong">{v}</td>
              <td>{w}</td>
              <td>{m}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3 className="subhead" style={{marginTop:"28px"}}>The Signal Logic — Plain English</h3>
      <p className="body-text">
        You go long the spread when: the price gap is wide, ATC is low
        (confirming the line is actually congested), and the spread has been
        persistent for at least a few hours — not a single-hour spike.
        You close the position when the spread narrows below your exit
        threshold or ATC opens up, suggesting the constraint is lifting.
      </p>

      <Note label="Mapping to Europe" color="gold">
        The California NP15/SP15 framework maps directly onto OMIE.
        Zone A = peninsular Spain (surplus, cheap solar/wind).
        Zone B = France or a constrained Spanish subzone.
        ATC = the Pyrenean interconnector capacity from ESIOS / ENTSO-E.
        The strategy you build here runs on real European data with minor
        variable substitutions.
      </Note>
    </div>
  );
}

function DataStep() {
  return (
    <div className="step-body">
      <Note label="What You Are Building Here">
        A data ingestion module that pulls zonal prices, ATC, and the
        REE demand-node availability map, cleans them, and outputs a
        single analysis-ready workflow. We use synthetic data first so
        you can build without API keys, then swap in real feeds.
      </Note>

      <h3 className="subhead">Step 1 — Install Dependencies</h3>
      <Code>{`
pip install pandas numpy matplotlib seaborn requests python-dotenv
      `}</Code>

      <h3 className="subhead" style={{marginTop:"24px"}}>Step 2 — Generate Synthetic Market Data</h3>
      <p className="body-text">
        This generates two years of hourly zonal prices with realistic
        congestion dynamics — spread spikes during peak hours, dampens
        overnight, with random congestion events injected.
      </p>
      <Code>{`
import pandas as pd
import numpy as np

np.random.seed(42)

# ── Parameters ──────────────────────────────────────────────
N_HOURS = 24 * 365 * 2          # two years of hourly data
START   = "2023-01-01"
ZONES   = ["NP15", "SP15"]      # or "ES", "FR" for European version

idx = pd.date_range(START, periods=N_HOURS, freq="h")

# ── Base price (mean-reverting around 50 €/MWh) ─────────────
base = 50 + np.cumsum(np.random.normal(0, 0.5, N_HOURS))
base = np.clip(base, 10, 200)

# ── Intraday seasonality (peak premium during 08-20) ─────────
hour_factor = np.where(
    (idx.hour >= 8) & (idx.hour < 20), 1.15, 0.85
)

# ── NP15: surplus zone — cheaper on average ──────────────────
price_np15 = base * hour_factor * np.random.lognormal(0, 0.05, N_HOURS)
price_np15 = np.clip(price_np15, -50, 300)

# ── Congestion events: inject spread spikes ───────────────────
# Congestion occurs ~15% of peak hours
is_peak       = (idx.hour >= 8) & (idx.hour < 20)
is_congested  = is_peak & (np.random.rand(N_HOURS) < 0.15)

congestion_premium = np.where(is_congested,
    np.random.uniform(20, 80, N_HOURS), 0)

# ── SP15: deficit zone — more expensive when congested ────────
price_sp15 = price_np15 + congestion_premium
price_sp15 += np.random.normal(0, 2, N_HOURS)   # noise
price_sp15  = np.clip(price_sp15, -50, 300)

# ── ATC: inversely related to congestion premium ─────────────
max_atc = 3000  # MW
atc = max_atc - (congestion_premium / 80) * max_atc
atc += np.random.normal(0, 100, N_HOURS)
atc  = np.clip(atc, 0, max_atc)

# ── Assemble DataFrame ────────────────────────────────────────
df = pd.DataFrame({
    "datetime":    idx,
    "price_np15":  price_np15,
    "price_sp15":  price_sp15,
    "atc_mw":      atc,
    "is_congested": is_congested,
}, index=idx)

df["spread"] = df["price_sp15"] - df["price_np15"]

print(df.head(10))
print(f"\\nSpread stats:\\n{df['spread'].describe().round(2)}")
print(f"Congested hours: {df['is_congested'].sum()} / {N_HOURS}")
      `}</Code>

      <h3 className="subhead" style={{marginTop:"24px"}}>Step 3 — Swap in Real Data (Optional)</h3>
      <p className="body-text">
        When you're ready to use real prices, replace the synthetic
        generation with these two API calls. The structure of <code>df</code> stays
        identical — the rest of the pipeline does not change.
      </p>
      <Code>{`
# ── Real OMIE prices (Spain DA) ───────────────────────────────
# OMIE publishes daily CSVs at:
# https://www.omie.es/es/file-access-list (free, no key needed)

import requests, io

def fetch_omie_prices(date_str: str) -> pd.DataFrame:
    """date_str format: YYYYMMDD"""
    url = (
        f"https://www.omie.es/es/file-access-list?parents%5B%5D="
        f"/{date_str[:4]}/{date_str[4:6]}/{date_str[6:8]}/"
        f"&filename=marginalpdbc_{date_str}.1"
    )
    # Parse the semicolon-delimited file OMIE publishes
    r = requests.get(url, timeout=10)
    lines = [l for l in r.text.splitlines() if l.strip()]
    rows  = [l.split(";") for l in lines[1:]]
    df    = pd.DataFrame(rows, columns=["date","hour","es","pt","extra"])
    df["price_es"] = pd.to_numeric(df["es"], errors="coerce")
    df["hour"]     = pd.to_numeric(df["hour"], errors="coerce") - 1
    return df[["date","hour","price_es"]].dropna()

# ── Real ATC from ESIOS (REE) ─────────────────────────────────
# Requires free ESIOS API token: https://api.esios.ree.es

def fetch_esios_atc(token: str, start: str, end: str) -> pd.DataFrame:
    headers = {"Authorization": f"Token token={token}",
               "Accept": "application/json"}
    # Indicator 10209 = ATC ES->FR interconnector
    url = (
        f"https://api.esios.ree.es/indicators/10209"
        f"?start_date={start}&end_date={end}"
    )
    r    = requests.get(url, headers=headers, timeout=15).json()
    rows = r["indicator"]["values"]
    df   = pd.DataFrame(rows)[["datetime","value"]]
    df.columns = ["datetime","atc_mw"]
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df.set_index("datetime")
      `}</Code>

      <Note label="Build Tip" color="teal">
        Keep both paths — synthetic and real — in your codebase. Use a
        config flag <code>USE_SYNTHETIC = True</code> while developing the
        signal engine, then flip it to False when you connect live feeds.
        The DataFrame schema never changes, so nothing downstream breaks.
      </Note>

      <h3 className="subhead" style={{marginTop:"24px"}}>Step 4 — Score the REE Node Map</h3>
      <p className="body-text">
        REE's locational availability map is the missing bridge between a
        generic ATC signal and a true congestion view. Nodes with spare
        demand capacity can absorb surplus; nodes without it trap surplus
        locally. That means the node map belongs inside ICS, not outside it.
      </p>
      <Code>{`
from peace_power_market_toolkit import score_congestion_nodes

nodes = pd.read_csv("data/ree_node_capacity_template.csv")
nodes_scored, zone_summary = score_congestion_nodes(nodes)

print(
    nodes_scored[
        ["node_name", "region", "congestion_zone", "available_capacity_mw",
         "congestion_vulnerability_score"]
    ]
    .sort_values("congestion_vulnerability_score", ascending=False)
    .head(10)
)

print("\\nICS-style zone pressure")
print(zone_summary[["congestion_zone", "constrained_share",
                    "mean_vulnerability_score", "ics_zone_pressure"]])
      `}</Code>

      <Note label="Locational Read" color="gold">
        Madrid, Aragon, and Cataluna should sit near the top of the
        vulnerability table when local capacity is scarce. That is where
        zonal spread trades should cluster first.
      </Note>
    </div>
  );
}

function ModelStep() {
  return (
    <div className="step-body">
      <Note label="What You Are Building Here">
        The spread model: statistical characterisation of the NP15/SP15
        spread, rolling z-score normalisation, node-aware ICS pressure,
        and congestion state classification. This is the analytical
        foundation the signal engine sits on top of.
      </Note>

      <h3 className="subhead">Step 1 — Compute the Spread & Rolling Statistics</h3>
      <Code>{`
# Assumes df from Step II is in scope

WINDOW = 168   # 7-day rolling window (168 hours)

# ── Rolling spread statistics ─────────────────────────────────
df["spread_mean"] = df["spread"].rolling(WINDOW, min_periods=24).mean()
df["spread_std"]  = df["spread"].rolling(WINDOW, min_periods=24).std()

# ── Z-score: how many std devs is today's spread from the norm?
df["spread_z"] = (
    (df["spread"] - df["spread_mean"]) / df["spread_std"]
)

# ── ATC utilisation ratio (0=empty corridor, 1=fully congested)
MAX_ATC = 3000
df["atc_util"] = 1 - (df["atc_mw"] / MAX_ATC)
df["atc_util"] = df["atc_util"].clip(0, 1)

print(df[["spread","spread_mean","spread_std",
          "spread_z","atc_util"]].tail(20).round(2))
      `}</Code>

      <h3 className="subhead" style={{marginTop:"24px"}}>Step 2 — Congestion State Classifier</h3>
      <p className="body-text">
        We classify each hour into one of four states. This replaces a
        simple threshold rule with a structured regime framework — cleaner
        for signal generation and easier to analyse in backtesting.
      </p>
      <Code>{`
def classify_congestion(row):
    """
    States:
      0 - Uncongested   : spread low, ATC available
      1 - Mild           : spread moderate OR ATC tightening
      2 - Congested      : spread elevated AND ATC constrained
      3 - Severe         : spread very high AND ATC near-zero
    """
    z   = row["spread_z"]
    atc = row["atc_util"]

    if z > 2.0 and atc > 0.85:
        return 3   # Severe
    elif z > 1.0 and atc > 0.60:
        return 2   # Congested
    elif z > 0.5 or atc > 0.40:
        return 1   # Mild
    else:
        return 0   # Uncongested

df["congestion_state"] = df.apply(classify_congestion, axis=1)

# ── Summary ───────────────────────────────────────────────────
state_labels = {0:"Uncongested", 1:"Mild", 2:"Congested", 3:"Severe"}
counts = df["congestion_state"].value_counts().sort_index()
for state, count in counts.items():
    pct = count / len(df) * 100
    print(f"  {state_labels[state]:<14}: {count:>5} hours ({pct:.1f}%)")
      `}</Code>

      <h3 className="subhead" style={{marginTop:"24px"}}>Step 3 — Persistence Filter</h3>
      <p className="body-text">
        Single-hour spikes are noise. Real congestion persists. This filter
        requires the state to hold for a minimum number of consecutive hours
        before a signal is eligible to fire. This is one of the most
        important practical improvements over a naive threshold model.
      </p>
      <Code>{`
MIN_PERSISTENCE = 3   # hours the state must hold before signal fires

def rolling_persistence(series: pd.Series, min_run: int) -> pd.Series:
    """Returns True only after min_run consecutive identical values."""
    result = pd.Series(False, index=series.index)
    run_len = 0
    prev    = None

    for i, val in enumerate(series):
        if val == prev:
            run_len += 1
        else:
            run_len = 1
            prev    = val
        result.iloc[i] = (run_len >= min_run)

    return result

df["state_persistent"] = rolling_persistence(
    df["congestion_state"], MIN_PERSISTENCE
)

print(f"Hours where state is persistent: "
      f"{df['state_persistent'].sum()} / {len(df)}")
      `}</Code>

      <Note label="Why This Matters" color="gold">
        Without the persistence filter, your backtest will be full of
        phantom trades on single-hour price spikes that are gone before
        you can execute. In real DA/ID markets, you need the congestion
        to last long enough for the auction to price it in and for you
        to get filled. Three hours is a conservative minimum — you can
        tune this in the backtest.
      </Note>
    </div>
  );
}

function SignalStep() {
  return (
    <div className="step-body">
      <Note label="What You Are Building Here">
        The signal engine: entry and exit logic that reads the congestion
        state model and outputs a position recommendation for each hour.
        Clean, explicit, no magic — every trade decision is traceable to a rule.
      </Note>

      <h3 className="subhead">Step 1 — Define Signal Parameters</h3>
      <Code>{`
# ── Signal parameters (tune these in backtest) ────────────────
PARAMS = {
    "entry_state":       2,      # min congestion state to enter (2=Congested)
    "exit_state":        1,      # exit when state falls below this
    "entry_z_min":       1.0,    # min z-score to enter
    "exit_z_max":        0.3,    # exit when z-score falls below this
    "atc_entry_min":     0.60,   # min ATC utilisation to enter
    "peak_only":         True,   # only trade peak hours (08-20)
    "min_spread_entry":  15.0,   # min absolute spread (€/MWh) to enter
}
      `}</Code>

      <h3 className="subhead" style={{marginTop:"24px"}}>Step 2 — Entry & Exit Logic</h3>
      <Code>{`
def generate_signals(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    df = df.copy()
    df["signal"]   = 0     # 0=flat, 1=long spread, -1=short spread
    df["position"] = 0

    in_position = False

    for i in range(len(df)):
        row  = df.iloc[i]
        hour = row.name.hour

        # ── Peak filter ───────────────────────────────────────
        if params["peak_only"] and not (8 <= hour < 20):
            df.iloc[i, df.columns.get_loc("signal")] = 0
            df.iloc[i, df.columns.get_loc("position")] = (
                1 if in_position else 0
            )
            continue

        # ── Entry conditions ──────────────────────────────────
        entry_ok = (
            not in_position
            and row["congestion_state"] >= params["entry_state"]
            and row["state_persistent"]
            and row["spread_z"]   >= params["entry_z_min"]
            and row["atc_util"]   >= params["atc_entry_min"]
            and row["spread"]     >= params["min_spread_entry"]
        )

        # ── Exit conditions ───────────────────────────────────
        exit_ok = (
            in_position
            and (
                row["congestion_state"] < params["exit_state"]
                or row["spread_z"] < params["exit_z_max"]
            )
        )

        if entry_ok:
            in_position = True
            df.iloc[i, df.columns.get_loc("signal")] = 1   # entry signal

        elif exit_ok:
            in_position = False
            df.iloc[i, df.columns.get_loc("signal")] = -1  # exit signal

        df.iloc[i, df.columns.get_loc("position")] = (
            1 if in_position else 0
        )

    return df

df = generate_signals(df, PARAMS)

# ── Quick summary ─────────────────────────────────────────────
entries = (df["signal"] ==  1).sum()
exits   = (df["signal"] == -1).sum()
hours_long = df["position"].sum()

print(f"Entries     : {entries}")
print(f"Exits       : {exits}")
print(f"Hours long  : {hours_long} ({hours_long/len(df)*100:.1f}%)")
      `}</Code>

      <h3 className="subhead" style={{marginTop:"24px"}}>Step 3 — Trade Log</h3>
      <Code>{`
def build_trade_log(df: pd.DataFrame) -> pd.DataFrame:
    """Pairs each entry signal with its corresponding exit."""
    trades = []
    entry_row = None

    for dt, row in df.iterrows():
        if row["signal"] == 1:
            entry_row = row
            entry_dt  = dt

        elif row["signal"] == -1 and entry_row is not None:
            trades.append({
                "entry_dt":     entry_dt,
                "exit_dt":      dt,
                "entry_spread": entry_row["spread"],
                "exit_spread":  row["spread"],
                "entry_z":      entry_row["spread_z"],
                "duration_h":   (dt - entry_dt).total_seconds() / 3600,
            })
            entry_row = None

    trades_df = pd.DataFrame(trades)
    trades_df["spread_change"] = (
        trades_df["exit_spread"] - trades_df["entry_spread"]
    )
    return trades_df

trades = build_trade_log(df)
print(trades.head(10).round(2))
print(f"\\nTotal trades: {len(trades)}")
print(f"Avg duration: {trades['duration_h'].mean():.1f} hours")
      `}</Code>

      <Note label="Build Tip" color="teal">
        Keep <code>PARAMS</code> as a dictionary from day one. When you
        get to the backtest step, you'll run a parameter sweep over
        different combinations — having everything in one dict makes that
        trivial. Never hardcode thresholds inline.
      </Note>
    </div>
  );
}

function BacktestStep() {
  return (
    <div className="step-body">
      <Note label="What You Are Building Here">
        A vectorised backtesting engine that computes P&L for each trade,
        runs a parameter sweep to find optimal thresholds, and produces
        the performance metrics you would present to a PM or CIO.
      </Note>

      <h3 className="subhead">Step 1 — P&L Calculation Per Trade</h3>
      <Code>{`
# ── Assumptions ───────────────────────────────────────────────
# You buy Zone A (cheap) and sell Zone B (expensive) at the spread.
# P&L per MWh = spread_entry - spread_exit (you profit if spread widens
#               further while you're in, or you entered early enough
#               that mean-reversion is your exit)
#
# More precisely for a congestion long:
#   Entry: buy NP15, sell SP15 → you receive the spread at entry
#   Exit : sell NP15, buy SP15 → you pay the spread at exit
#   P&L  = entry_spread - exit_spread  (positive if spread compressed)
#
# Wait — we want spread to WIDEN to profit, then compress to exit.
# So: P&L = exit_spread - entry_spread (positive if it widened)

MW_SIZE = 10   # MW position size per trade

def compute_pnl(trades_df: pd.DataFrame, mw: int = MW_SIZE) -> pd.DataFrame:
    t = trades_df.copy()
    # P&L per MWh = how much the spread moved in our favour
    t["pnl_per_mwh"] = t["exit_spread"] - t["entry_spread"]
    # Total P&L = €/MWh × MW × hours (approximation for hourly blocks)
    t["pnl_eur"]     = t["pnl_per_mwh"] * mw * t["duration_h"]
    t["pnl_cumsum"]  = t["pnl_eur"].cumsum()
    return t

trades = compute_pnl(trades)

print(trades[["entry_dt","exit_dt","entry_spread","exit_spread",
              "pnl_per_mwh","pnl_eur","duration_h"]].round(2).head(15))
      `}</Code>

      <h3 className="subhead" style={{marginTop:"24px"}}>Step 2 — Performance Metrics</h3>
      <Code>{`
def performance_metrics(trades_df: pd.DataFrame,
                         df_hourly: pd.DataFrame) -> dict:
    pnl = trades_df["pnl_eur"]

    # ── Daily P&L series (for Sharpe) ────────────────────────
    daily = trades_df.set_index("exit_dt")["pnl_eur"].resample("D").sum()

    sharpe = (daily.mean() / daily.std()) * (252 ** 0.5) if daily.std() > 0 else 0

    # ── Drawdown ──────────────────────────────────────────────
    cumsum   = trades_df["pnl_cumsum"]
    peak     = cumsum.cummax()
    drawdown = cumsum - peak
    max_dd   = drawdown.min()

    # ── Hit rate ──────────────────────────────────────────────
    hit_rate = (pnl > 0).mean()

    metrics = {
        "Total P&L (€)":        round(pnl.sum(), 2),
        "Num Trades":            len(trades_df),
        "Hit Rate":              f"{hit_rate:.1%}",
        "Avg P&L per Trade (€)": round(pnl.mean(), 2),
        "Avg Duration (h)":      round(trades_df["duration_h"].mean(), 1),
        "Ann. Sharpe":           round(sharpe, 2),
        "Max Drawdown (€)":      round(max_dd, 2),
        "Best Trade (€)":        round(pnl.max(), 2),
        "Worst Trade (€)":       round(pnl.min(), 2),
    }

    for k, v in metrics.items():
        print(f"  {k:<26}: {v}")

    return metrics

metrics = performance_metrics(trades, df)
      `}</Code>

      <h3 className="subhead" style={{marginTop:"24px"}}>Step 3 — Parameter Sweep</h3>
      <p className="body-text">
        Grid search over the key thresholds to find the combination that
        maximises risk-adjusted returns. Do not optimise on total P&L alone
        — that leads to overfitting. Use Sharpe as the primary objective.
      </p>
      <Code>{`
import itertools

def run_sweep(df_base: pd.DataFrame) -> pd.DataFrame:
    param_grid = {
        "entry_z_min":      [0.75, 1.0, 1.25, 1.5],
        "exit_z_max":       [0.1, 0.3, 0.5],
        "atc_entry_min":    [0.50, 0.65, 0.80],
        "min_spread_entry": [10, 15, 20, 25],
    }

    # Fixed params that don't change in sweep
    base_params = {
        "entry_state": 2,
        "exit_state":  1,
        "peak_only":   True,
    }

    keys   = list(param_grid.keys())
    combos = list(itertools.product(*param_grid.values()))
    results = []

    for combo in combos:
        params = {**base_params, **dict(zip(keys, combo))}
        try:
            _df     = generate_signals(df_base, params)
            _trades = build_trade_log(_df)
            _trades = compute_pnl(_trades)

            if len(_trades) < 10:   # skip sparse results
                continue

            daily  = _trades.set_index("exit_dt")["pnl_eur"].resample("D").sum()
            sharpe = (daily.mean() / daily.std()) * (252**0.5) if daily.std() > 0 else 0

            results.append({
                **dict(zip(keys, combo)),
                "n_trades": len(_trades),
                "total_pnl": _trades["pnl_eur"].sum(),
                "sharpe":    round(sharpe, 3),
                "hit_rate":  (_trades["pnl_eur"] > 0).mean(),
            })
        except Exception:
            continue

    return pd.DataFrame(results).sort_values("sharpe", ascending=False)

sweep = run_sweep(df)
print("\\nTop 10 parameter combinations by Sharpe:")
print(sweep.head(10).to_string(index=False))
      `}</Code>

      <Note label="Overfitting Warning" color="crimson">
        Run the sweep on your first year of data only. Validate the top
        parameters on the second year without touching them. If the Sharpe
        collapses out-of-sample, the strategy is curve-fit, not robust.
        A genuine edge holds across regimes.
      </Note>
    </div>
  );
}

function PnlStep() {
  return (
    <div className="step-body">
      <Note label="What You Are Building Here">
        Visualisation and reporting — the cumulative P&L curve, spread
        regime chart, and a clean summary output you can present or
        drop into the Peace Capital report template.
      </Note>

      <h3 className="subhead">Step 1 — Cumulative P&L Chart</h3>
      <Code>{`
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=False)
fig.patch.set_facecolor("#0e1829")

for ax in axes:
    ax.set_facecolor("#121f33")
    ax.tick_params(colors="#677a90")
    ax.spines[:].set_color("#1e3050")

# ── Panel 1: Cumulative P&L ───────────────────────────────────
ax1 = axes[0]
ax1.plot(trades["exit_dt"], trades["pnl_cumsum"],
         color="#3d9e9e", linewidth=1.5, label="Cumulative P&L")
ax1.axhline(0, color="#1e3050", linewidth=0.8)
ax1.fill_between(trades["exit_dt"], trades["pnl_cumsum"], 0,
                 where=trades["pnl_cumsum"] >= 0,
                 alpha=0.15, color="#3d9e9e")
ax1.fill_between(trades["exit_dt"], trades["pnl_cumsum"], 0,
                 where=trades["pnl_cumsum"] < 0,
                 alpha=0.15, color="#c0283e")
ax1.set_title("Cumulative P&L (€)", color="#dde4ed",
              fontsize=11, loc="left", pad=8)
ax1.yaxis.label.set_color("#677a90")

# ── Panel 2: Hourly spread with position overlay ──────────────
ax2 = axes[1]
sample = df["2024-01-01":"2024-03-31"]   # 3-month window for clarity

ax2.plot(sample.index, sample["spread"],
         color="#677a90", linewidth=0.6, alpha=0.7)
ax2.fill_between(sample.index, sample["spread"],
                 where=sample["position"] == 1,
                 alpha=0.35, color="#3d9e9e", label="Long position")
ax2.axhline(PARAMS["min_spread_entry"], color="#c9a84c",
            linewidth=0.8, linestyle="--", label="Entry threshold")
ax2.axhline(0, color="#1e3050", linewidth=0.6)
ax2.set_title("Spread (€/MWh) with Position Overlay — Q1 2024",
              color="#dde4ed", fontsize=11, loc="left", pad=8)
ax2.legend(facecolor="#121f33", edgecolor="#1e3050",
           labelcolor="#a8b8cc", fontsize=9)

# ── Panel 3: Trade P&L distribution ──────────────────────────
ax3 = axes[2]
colors = ["#3d9e9e" if p > 0 else "#c0283e"
          for p in trades["pnl_eur"]]
ax3.bar(range(len(trades)), trades["pnl_eur"],
        color=colors, width=0.8, alpha=0.85)
ax3.axhline(0, color="#677a90", linewidth=0.8)
ax3.set_title("P&L per Trade (€)", color="#dde4ed",
              fontsize=11, loc="left", pad=8)
ax3.set_xlabel("Trade Number", color="#677a90", fontsize=9)

plt.tight_layout(pad=2.5)
plt.savefig("peace_capital_congestion_backtest.png",
            dpi=150, bbox_inches="tight",
            facecolor="#0e1829")
plt.show()
print("Chart saved.")
      `}</Code>

      <h3 className="subhead" style={{marginTop:"24px"}}>Step 2 — Clean Summary Export</h3>
      <Code>{`
def export_summary(trades_df: pd.DataFrame,
                   metrics: dict,
                   params: dict,
                   path: str = "pc_congestion_summary.csv"):

    # ── Trade log ─────────────────────────────────────────────
    trades_df.to_csv(path, index=False)
    print(f"Trade log saved to {path}")

    # ── Print report-style summary ────────────────────────────
    print("\\n" + "─" * 50)
    print("  PEACE CAPITAL — Congestion Spread Strategy")
    print("  Backtest Summary")
    print("─" * 50)
    print(f"  Strategy    : NP15 / SP15 Zonal Congestion Long")
    print(f"  Period      : {trades_df['entry_dt'].min().date()} → "
          f"{trades_df['exit_dt'].max().date()}")
    print(f"  Position Sz : {MW_SIZE} MW per trade")
    print("─" * 50)
    for k, v in metrics.items():
        print(f"  {k:<26}: {v}")
    print("─" * 50)
    print("  Active Parameters:")
    for k, v in params.items():
        print(f"    {k:<22}: {v}")
    print("─" * 50)

export_summary(trades, metrics, PARAMS)
      `}</Code>

      <Note label="Next Steps from Here" color="gold">
        You now have a complete working simulation. The natural extensions
        are: (1) swap synthetic data for real OMIE + ESIOS feeds, (2) map
        the full REE node set into your internal congestion zones and push
        the vulnerability score into ICS, (3) layer the RSI signal from
        the main report as an entry filter, adjusted for BESS absorption.
        These steps take the simulation to a deployable research prototype.
      </Note>
    </div>
  );
}

const stepComponents = {
  concept:  ConceptStep,
  data:     DataStep,
  model:    ModelStep,
  signal:   SignalStep,
  backtest: BacktestStep,
  pnl:      PnlStep,
};

/* ── ROOT ───────────────────────────────────────────────────── */
export default function CongestionGuide() {
  const [active, setActive] = useState("concept");
  const ActiveStep = stepComponents[active];
  const today = new Date().toLocaleDateString("en-GB", {
    day: "numeric", month: "long", year: "numeric"
  });

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Source+Serif+4:ital,wght@0,300;0,400;0,600;1,300;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
          --navy:   #0e1829;
          --navy2:  #121f33;
          --navy3:  #192740;
          --teal:   #1a5c5c;
          --teal-l: #2a7d7d;
          --teal-ll:#3d9e9e;
          --crimson:#a01c2e;
          --crim-l: #c0283e;
          --gold:   #c9a84c;
          --text:   #dde4ed;
          --text2:  #a8b8cc;
          --text3:  #677a90;
          --rule:   #1e3050;
          --rule2:  #243855;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body, #root {
          background: var(--navy);
          color: var(--text);
          font-family: 'Source Serif 4', Georgia, serif;
          min-height: 100vh;
        }

        .page { max-width: 900px; margin: 0 auto; padding: 0 32px 80px; }

        .masthead {
          border-bottom: 2px solid var(--teal);
          padding: 36px 0 20px;
        }

        .masthead-top {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 16px;
        }

        .firm-name {
          font-family: 'Cormorant Garamond', serif;
          font-size: 28px;
          font-weight: 600;
          letter-spacing: 0.06em;
          color: #f0f4f8;
          text-transform: uppercase;
        }

        .firm-sub {
          font-family: 'Cormorant Garamond', serif;
          font-size: 13px;
          letter-spacing: 0.2em;
          color: var(--teal-ll);
          text-transform: uppercase;
          margin-top: 2px;
        }

        .masthead-meta {
          text-align: right;
          font-size: 11px;
          color: var(--text3);
          line-height: 1.9;
          font-family: 'JetBrains Mono', monospace;
        }

        .report-title-row {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          padding-top: 14px;
          border-top: 1px solid var(--rule);
        }

        .report-title {
          font-family: 'Cormorant Garamond', serif;
          font-size: 20px;
          font-weight: 500;
          font-style: italic;
          color: var(--text);
        }

        .report-tag {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          letter-spacing: 0.12em;
          color: var(--teal-ll);
          border: 1px solid var(--teal);
          padding: 3px 10px;
          text-transform: uppercase;
          white-space: nowrap;
        }

        .nav {
          display: flex;
          border-bottom: 1px solid var(--rule);
          margin-bottom: 32px;
          overflow-x: auto;
        }

        .nav-btn {
          font-family: 'Source Serif 4', serif;
          font-size: 12px;
          font-style: italic;
          color: var(--text3);
          background: none;
          border: none;
          padding: 14px 18px 12px;
          cursor: pointer;
          border-bottom: 2px solid transparent;
          margin-bottom: -1px;
          white-space: nowrap;
          transition: color 0.15s, border-color 0.15s;
          flex-shrink: 0;
        }

        .nav-btn:hover { color: var(--text2); }
        .nav-btn.active { color: var(--teal-ll); border-bottom-color: var(--teal-ll); }

        /* STEP BODY */
        .step-body > * + * { margin-top: 20px; }

        .subhead {
          font-family: 'Cormorant Garamond', serif;
          font-size: 15px;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--text2);
          margin-bottom: 12px;
          padding-bottom: 6px;
          border-bottom: 1px solid var(--rule);
        }

        .body-text {
          font-size: 13.5px;
          color: var(--text2);
          line-height: 1.85;
        }

        /* CALLOUTS */
        .callout {
          padding: 14px 18px;
          font-size: 13px;
          color: var(--text2);
          line-height: 1.8;
        }

        .callout-teal {
          background: rgba(26,92,92,0.1);
          border-left: 3px solid var(--teal-ll);
        }

        .callout-gold {
          background: rgba(201,168,76,0.07);
          border-left: 3px solid var(--gold);
        }

        .callout-crimson {
          background: rgba(160,28,46,0.08);
          border-left: 3px solid var(--crimson);
        }

        .callout-label {
          display: block;
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          letter-spacing: 0.2em;
          text-transform: uppercase;
          margin-bottom: 7px;
        }

        .callout-teal   .callout-label { color: var(--teal-ll); }
        .callout-gold   .callout-label { color: var(--gold); }
        .callout-crimson .callout-label { color: var(--crim-l); }

        /* CODE */
        .code-wrap {
          border: 1px solid var(--rule2);
          border-radius: 3px;
          overflow: hidden;
          margin-top: 10px;
        }

        .code-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: var(--navy3);
          padding: 6px 14px;
          border-bottom: 1px solid var(--rule);
        }

        .code-lang {
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          letter-spacing: 0.15em;
          text-transform: uppercase;
          color: var(--teal-ll);
        }

        .copy-btn {
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--text3);
          background: none;
          border: 1px solid var(--rule2);
          padding: 2px 8px;
          cursor: pointer;
          border-radius: 2px;
          transition: color 0.15s, border-color 0.15s;
        }

        .copy-btn:hover { color: var(--teal-ll); border-color: var(--teal); }

        .code-block {
          background: #090e18;
          padding: 18px;
          overflow-x: auto;
          font-family: 'JetBrains Mono', monospace;
          font-size: 12px;
          line-height: 1.7;
          color: #a8c8d8;
          white-space: pre;
        }

        /* TABLE */
        .report-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12.5px;
        }

        .report-table th {
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          letter-spacing: 0.14em;
          text-transform: uppercase;
          color: var(--text3);
          text-align: left;
          padding: 8px 12px;
          border-bottom: 1px solid var(--rule2);
          border-top: 1px solid var(--rule2);
          background: var(--navy2);
        }

        .report-table td {
          padding: 9px 12px;
          border-bottom: 1px solid var(--rule);
          color: var(--text2);
          vertical-align: top;
        }

        .report-table tr:last-child td { border-bottom: none; }
        .td-strong { color: var(--text); font-weight: 600; }

        code {
          font-family: 'JetBrains Mono', monospace;
          font-size: 11.5px;
          color: var(--teal-ll);
          background: rgba(26,92,92,0.1);
          padding: 1px 5px;
          border-radius: 2px;
        }

        .footer {
          margin-top: 48px;
          padding-top: 16px;
          border-top: 1px solid var(--rule);
          font-size: 11px;
          color: var(--text3);
          font-style: italic;
          line-height: 1.7;
        }

        @media (max-width: 640px) {
          .page { padding: 0 16px 60px; }
          .masthead-top { flex-direction: column; gap: 12px; }
          .report-title-row { flex-direction: column; gap: 8px; }
        }
      `}</style>

      <div className="page">
        <div className="masthead">
          <div className="masthead-top">
            <div>
              <div className="firm-name">Peace Capital</div>
              <div className="firm-sub">Investment Management</div>
            </div>
            <div className="masthead-meta">
              <div>CONFIDENTIAL — INTERNAL USE ONLY</div>
              <div>Strategy Build Guide</div>
              <div>{today}</div>
              <div>Ref: PC-PWR-2026-SIM01</div>
            </div>
          </div>
          <div className="report-title-row">
            <div className="report-title">
              Congestion Spread Trading — Python Build Guide
            </div>
            <span className="report-tag">Quantitative Research</span>
          </div>
        </div>

        <div className="nav">
          {STEPS.map(s => (
            <button
              key={s.id}
              className={`nav-btn${active === s.id ? " active" : ""}`}
              onClick={() => setActive(s.id)}
            >
              {s.label}
            </button>
          ))}
        </div>

        <ActiveStep />

        <div className="footer">
          This build guide is prepared for internal quantitative research purposes only.
          All code is provided as a working prototype and must be subject to independent
          validation before any live deployment. Peace Capital Investment Management
          accepts no liability for outcomes arising from use of this material.
        </div>
      </div>
    </>
  );
}
