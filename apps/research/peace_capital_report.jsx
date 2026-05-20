import { useState } from "react";

const SECTIONS = [
  { id: "thesis", label: "I. Investment Thesis" },
  { id: "signals", label: "II. Signal Architecture" },
  { id: "execution", label: "III. Execution Framework" },
  { id: "risk", label: "IV. Risk Management" },
  { id: "infra", label: "V. Infrastructure" },
];

/* ─── THESIS ─────────────────────────────────────────────────── */
function ThesisSection() {
  return (
    <div className="section-body">
      <div className="abstract">
        <span className="abstract-label">Abstract</span>
        <p>
          Structural oversupply of zero-marginal-cost renewable generation is
          exerting systematic downward pressure on European electricity spot prices.
          The accelerating displacement of thermal dispatch, combined with inadequate
          grid flexibility, produces recurring negative price episodes that create
          exploitable short opportunities across Day-Ahead and Intraday markets.
          This strategy seeks to capture the structural premium embedded in that
          dislocation through a disciplined, signal-driven short bias, while
          explicitly monitoring the level of deployed storage at which the edge
          begins to decay.
        </p>
      </div>

      <div className="two-col">
        <div>
          <h3 className="subhead">Core Mechanism</h3>
          <p className="body-text">
            The merit order effect places renewable generation — operating at
            effectively zero marginal cost — at the front of the dispatch stack,
            pushing gas, coal, and nuclear units off the margin or offline entirely.
            During high-generation windows, spot prices converge to the marginal cost
            of the last thermal unit or collapse below zero when curtailment capacity
            is exhausted. This is not a cyclical phenomenon; it is a structural
            feature of grids transitioning faster than their balancing infrastructure.
          </p>
          <p className="body-text" style={{ marginTop: "12px" }}>
            Negative price hours in Germany rose from 134 in 2022 to 457 in 2023, a
            rate of increase consistent with the buildout trajectory of onshore wind
            and utility-scale solar across Central Europe.
          </p>
        </div>
        <div>
          <h3 className="subhead">Strategic Edge</h3>
          <p className="body-text">
            Market participants systematically underestimate renewable generation
            during auction windows, creating a persistent short-side mispricing in
            Day-Ahead settlements. The edge is not in forecasting demand — it is in
            forecasting supply displacement more accurately than the auction clears.
          </p>
          <p className="body-text" style={{ marginTop: "12px" }}>
            Installed renewable capacity is still outpacing storage deployment,
            demand response, and cross-border interconnector expansion. The
            short remains valid today, but it is no longer open-ended: a 97 GW
            BESS pipeline, with 25 GW already granted and 12 GW under review,
            is the structural release valve that can compress the same spread
            this strategy monetises.
          </p>

          <div className="callout">
            <span className="callout-label">Key Observation</span>
            The short case does not require negative prices — it requires prices
            below the thermal floor. That condition is becoming the base case, not
            the tail.
          </div>

          <div className="callout" style={{ marginTop: "16px" }}>
            <span className="callout-label">Time Horizon</span>
            Base case: the thesis remains structurally attractive for roughly the
            next 18-24 months. Sunset condition: once deployed BESS can absorb
            about 35% of surplus in high-RSI hours, or storage penetration reaches
            roughly 0.30 versus the model's P95 surplus window, fresh short risk
            must be cut materially.
          </div>
        </div>
      </div>

      <h3 className="subhead" style={{ marginTop: "32px" }}>Target Markets</h3>
      <table className="report-table">
        <thead>
          <tr>
            <th>Market</th>
            <th>Exchange</th>
            <th>Settlement</th>
            <th>Neg. Price Frequency</th>
            <th>Classification</th>
          </tr>
        </thead>
        <tbody>
          {[
            ["Germany / Austria", "EPEX SPOT", "DA Auction + ID Continuous", "Very High", "Primary"],
            ["Spain / Portugal",  "OMIE",      "DA Auction + MIBEL ID",       "High",      "Primary"],
            ["France",           "EPEX SPOT", "DA + ID Continuous",           "Moderate",  "Secondary"],
            ["Nordic (NO/SE/FI)", "Nord Pool", "Elspot DA + Elbas ID",        "Moderate",  "Secondary"],
            ["ERCOT (Texas)",    "ERCOT RT",  "Real-Time 5-min",              "High",      "Monitor"],
          ].map(([mkt, ex, sett, freq, cls]) => (
            <tr key={mkt}>
              <td className="td-strong">{mkt}</td>
              <td>{ex}</td>
              <td>{sett}</td>
              <td>{freq}</td>
              <td>
                <span className={`pill pill-${cls.toLowerCase()}`}>{cls}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ─── SIGNALS ────────────────────────────────────────────────── */
function SignalsSection() {
  const signals = [
    {
      tier: "Tier I",
      name: "Renewable Surplus Index",
      abbr: "RSI",
      weight: "35%",
      desc: "Forecast wind and solar generation expressed as a percentage of forecast demand for the target delivery window. The raw RSI is haircut by live BESS absorption and discharge capacity so that surplus is measured net of storage, not gross. The signal fires when storage-adjusted RSI exceeds 85% across three or more consecutive hours. This is a prerequisite signal — no short position is initiated without RSI confirmation.",
      source: "ENTSO-E Transparency Platform / ECMWF CDS API / Solcast / ESIOS BESS online-capacity and dispatch feeds",
      timing: "D−1, available by 08:30 CET",
    },
    {
      tier: "Tier I",
      name: "DA Price Basis vs. Thermal Floor",
      abbr: "TPB",
      weight: "25%",
      desc: "Day-Ahead auction clearing price relative to the implied marginal cost of gas-fired generation, computed as TTF spot price multiplied by heat rate plus EUA CO₂ price. When DA trades at a discount greater than 20% to the thermal floor, thermal displacement is confirmed and short entry is warranted. A negative spread constitutes a high-conviction condition.",
      source: "EPEX SPOT / OMIE DA results; ICE TTF front-month; EEX EUA front-month",
      timing: "D−1, post-auction results (13:30 CET)",
    },
    {
      tier: "Tier II",
      name: "Negative Price Probability Score",
      abbr: "NPP",
      weight: "20%",
      desc: "Machine learning estimate of the probability that at least one delivery hour in the target window will clear at a negative price. Trained on three years of hourly data using gradient-boosted trees. Features include raw RSI, storage-adjusted RSI, BESS penetration, hydro reservoir level, interconnector headroom, lagged price, weekday, and seasonal dummies. Threshold: NPP ≥ 40% reinforces the short signal; NPP ≥ 60% elevates position sizing only when the storage sunset trigger has not been breached.",
      source: "Internal model — XGBoost, retrained monthly on ENTSO-E + ECMWF historical",
      timing: "D−1, available by 08:00 CET",
    },
    {
      tier: "Tier II",
      name: "Interconnector Capacity Slack",
      abbr: "ICS",
      weight: "12%",
      desc: "Available cross-border transmission headroom on key export corridors, adjusted by a node-level congestion vulnerability score built from the REE demand-availability map. When utilisation exceeds 90% and the node map shows low local absorption capacity, surplus generation is trapped domestically, amplifying price suppression. Low slack is a signal augmenter, not a standalone trigger.",
      source: "ENTSO-E Transparency — ATC/NTC, updated every 30 minutes; REE node-capacity map cross-referenced to internal OMIE/EPEX congestion zones",
      timing: "Continuous; reviewed at D−1 12:00 CET for DA sizing",
    },
    {
      tier: "Tier III",
      name: "Nordic Hydro Reservoir Anomaly",
      abbr: "HRA",
      weight: "8%",
      desc: "Nordic reservoir fill level relative to the ten-year seasonal normal. Above-normal hydro competes with wind and solar across the Nordic zone and spills surplus into German and French interconnectors via the NorNed and SwePol links. Signal: reservoir fill above 105% of normal augments the short in connected Central European markets.",
      source: "NVE (Norway) / Svenska Kraftnät weekly hydro bulletins",
      timing: "Weekly, published Tuesday",
    },
  ];

  return (
    <div className="section-body">
      <div className="abstract">
        <span className="abstract-label">Composite Rule</span>
        <p>
          Signals are scored and aggregated daily at D−1. The composite score is
          bounded [0, 1]. A short signal is activated when the composite reaches
          or exceeds <strong>0.60</strong>, subject to at least one Tier I signal
          having fired independently. Tier II and III signals function as
          amplifiers, not independent triggers.
        </p>
      </div>

      {signals.map((s) => (
        <div key={s.abbr} className="signal-block">
          <div className="signal-header">
            <div className="signal-left">
              <span className={`tier-tag tier-${s.tier.replace(" ", "").toLowerCase()}`}>{s.tier}</span>
              <span className="signal-name">{s.name}</span>
              <span className="signal-abbr">({s.abbr})</span>
            </div>
            <div className="signal-weight">{s.weight} composite weight</div>
          </div>
          <p className="body-text">{s.desc}</p>
          <div className="signal-meta-row">
            <span><em>Source:</em> {s.source}</span>
            <span><em>Timing:</em> {s.timing}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ─── EXECUTION ──────────────────────────────────────────────── */
function ExecutionSection() {
  return (
    <div className="section-body">
      <div className="abstract">
        <span className="abstract-label">Execution Overview</span>
        <p>
          Entry is structured in two layers. The primary position is established
          via the Day-Ahead auction. The secondary layer uses Intraday continuous
          markets for refinement and risk reduction based on real-time tracking
          of generation actuals versus forecast.
        </p>
      </div>

      <div className="two-col">
        <div>
          <h3 className="subhead">Layer I — Day-Ahead Entry</h3>
          <p className="body-text">
            Sell orders are submitted to the EPEX SPOT or OMIE DA auction when the
            D−1 composite signal reaches the activation threshold. Targeted delivery
            hours are the solar window (09:00–17:00 local) and high-wind periods
            identified by the RSI model. Gate close is 12:00 CET for EPEX; 12:00 CET
            for OMIE. Results are received by 13:00–13:30 CET and feed directly into
            the Tier I TPB signal update.
          </p>
        </div>
        <div>
          <h3 className="subhead">Layer II — Intraday Refinement</h3>
          <p className="body-text">
            The XBID cross-border intraday market and domestic ID continuous sessions
            (OMIE ID, EPEX ID) are used to scale into the position when RSI tracking
            confirms the D−1 forecast, or to partially cover when a demand spike or
            weather revision triggers the risk protocols. All intraday trades are
            executed at least 60 minutes prior to delivery. Market orders are not
            used; limit orders only.
          </p>
        </div>
      </div>

      <h3 className="subhead" style={{ marginTop: "28px" }}>Position Sizing Schedule</h3>
      <table className="report-table">
        <thead>
          <tr>
            <th>Composite Score</th>
            <th>Size Multiplier</th>
            <th>Tier I Requirement</th>
            <th>Classification</th>
          </tr>
        </thead>
        <tbody>
          {[
            ["0.60 – 0.69", "1.0×", "One Tier I signal required", "Standard"],
            ["0.70 – 0.79", "1.5×", "One Tier I signal required", "Overweight"],
            ["0.80 – 0.89", "2.0×", "Both Tier I signals preferred", "High Conviction"],
            ["≥ 0.90",      "2.5×", "Both Tier I signals required", "Maximum"],
            ["< 0.60",      "—",    "—", "No Trade"],
          ].map(([score, mult, req, cls]) => (
            <tr key={score}>
              <td className="td-mono">{score}</td>
              <td className="td-mono td-strong">{mult}</td>
              <td>{req}</td>
              <td>
                <span className={`pill pill-${cls.toLowerCase().replace(" ", "")}`}>{cls}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="callout" style={{ marginTop: "28px" }}>
        <span className="callout-label">Execution Note</span>
        Intraday liquidity thins materially beyond two hours before delivery on most
        European exchanges. All ID order entry is therefore constrained to a minimum
        of three hours prior to the delivery period. Positions held to within 60
        minutes of delivery are carried to settlement absent an overriding risk event.
      </div>
    </div>
  );
}

/* ─── RISK ───────────────────────────────────────────────────── */
function RiskSection() {
  const risks = [
    {
      name: "Storage Deployment / Flexibility Catch-Up",
      severity: "High",
      text: "Battery deployment is the cleanest structural threat to the strategy. When modeled storage penetration rises above roughly 0.30 of the P95 surplus window, or observed BESS capture exceeds 35% of surplus in high-RSI hours, new short risk is cut by at least 50%. Above that level, the thesis shifts from structural to tactical and requires explicit CIO review.",
    },
    {
      name: "Demand Spike / Cold Snap",
      severity: "High",
      text: "A temperature forecast revision of 3°C or more colder than the D−1 model run triggers cancellation of pending DA orders or intraday partial cover of existing positions. The ECMWF ensemble P10 temperature percentile is monitored at signal generation. Positions are reduced by 50% within 30 minutes of a confirmed cold revision exceeding the threshold.",
    },
    {
      name: "Unplanned Generation Outage",
      severity: "High",
      text: "ENTSO-E Outage Publication is monitored continuously. An unplanned offline event exceeding 2 GW in the target zone suspends new entry. Existing positions are reduced by 50% within 30 minutes of confirmation. The position is not reinstated until the outage is resolved or replaced by equivalent renewable generation.",
    },
    {
      name: "Interconnector Congestion Reversal",
      severity: "Medium",
      text: "A reversal of interconnector slack greater than 500 MW versus the signal assumption — for instance, the sudden absorption of domestic surplus by a neighbouring zone — reduces exposure by 30%. ATC updates are reviewed every 30 minutes during the trading day.",
    },
    {
      name: "Regulatory Price Floor",
      severity: "Medium",
      text: "EPEX SPOT and OMIE enforce negative price floors (−500 €/MWh). These caps constrain the full P&L realisation of extreme negative price events. This is not a strategy risk per se — the thesis does not require negative prices — but expected value calculations must account for the floor when sizing during high-NPP conditions.",
    },
    {
      name: "Weather Model Error",
      severity: "Medium",
      text: "ECMWF ensemble spread is used as a proxy for forecast uncertainty. When the P10–P90 wind speed spread exceeds 15% of the median at hub height, position size is reduced by 30%. GFS is maintained as a cross-check model. Signal generation proceeds only when the two models agree within a 10% generation tolerance.",
    },
    {
      name: "Intraday Liquidity",
      severity: "Low",
      text: "XBID and domestic ID markets become thin beyond the two-hour mark. All adjustment trades are constrained to ≥3 hours before delivery. Limit orders only; no market orders in intraday sessions. For structurally illiquid hours (overnight, weekends), DA is the sole execution layer.",
    },
  ];

  return (
    <div className="section-body">
      <div className="abstract">
        <span className="abstract-label">Risk Philosophy</span>
        <p>
          Risk management is embedded into signal generation, not applied as a
          downstream override. Each signal incorporates its own uncertainty proxy.
          The hard limits below represent the outer bounds; the expectation is that
          normal operation remains well within them.
        </p>
      </div>

      {risks.map((r) => (
        <div key={r.name} className="risk-block">
          <div className="risk-header">
            <span className="risk-name">{r.name}</span>
            <span className={`severity sev-${r.severity.toLowerCase()}`}>{r.severity} Severity</span>
          </div>
          <p className="body-text">{r.text}</p>
        </div>
      ))}

      <h3 className="subhead" style={{ marginTop: "28px" }}>Hard Risk Limits</h3>
      <table className="report-table">
        <thead>
          <tr><th>Parameter</th><th>Limit</th><th>Response</th></tr>
        </thead>
        <tbody>
          {[
            ["Daily loss limit", "1.5× average daily P&L", "Close all positions, no new entries same day"],
            ["Maximum open exposure", "2.5× base lot per zone", "Hard cap; no override without CIO approval"],
            ["Storage sunset trigger", ">= 0.30 storage penetration or >= 35% surplus capture", "Reduce new shorts by 50%; CIO sign-off required above trigger"],
            ["Signal data staleness", "> 6 hours", "No new entries until data refreshed"],
            ["Concurrent market exposure", "> 3 zones simultaneously", "Require explicit approval"],
          ].map(([p, l, r]) => (
            <tr key={p}>
              <td className="td-strong">{p}</td>
              <td className="td-mono">{l}</td>
              <td>{r}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ─── INFRA ──────────────────────────────────────────────────── */
function InfraSection() {
  return (
    <div className="section-body">
      <div className="two-col">
        <div>
          <h3 className="subhead">Data Architecture</h3>
          <p className="body-text">
            All market and meteorological data is ingested through a unified pipeline
            into a time-series database. The signal engine queries this store at
            scheduled intervals and on-demand for intraday updates.
          </p>
          <div className="infra-list">
            {[
              ["ENTSO-E Transparency", "Generation forecast, actual load, outage publication, ATC/NTC flows — REST API, polled every 15 minutes"],
              ["ECMWF CDS API", "HRES and ENS runs — hub-height wind speed, GHI, surface temperature; ingested at 00z and 12z"],
              ["Solcast API", "High-resolution solar irradiance and PV generation forecast"],
              ["EPEX SPOT Market Data", "DA auction results, ID order book snapshots"],
              ["OMIE", "DA clearing results and MIBEL ID continuous feed"],
              ["ICE / EEX", "TTF front-month gas price, EUA CO₂ front-month — for thermal floor computation"],
            ].map(([name, desc]) => (
              <div key={name} className="infra-item">
                <span className="infra-name">{name}</span>
                <span className="infra-desc">{desc}</span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <h3 className="subhead">Signal Pipeline</h3>
          <p className="body-text">
            The D−1 signal run executes as a scheduled Python job at 07:30 CET,
            prior to ECMWF HRES delivery. A secondary run at 09:00 CET incorporates
            the updated HRES and refreshed ENTSO-E generation forecasts.
          </p>
          <div className="infra-list">
            {[
              ["Scheduler", "Airflow DAG — D−1 07:30 and 09:00 CET; intraday watcher every 15 minutes"],
              ["Feature Store", "PostgreSQL time-series schema; dbt for feature transformations and lineage"],
              ["ML Model", "XGBoost NPP model, retrained monthly on rolling 36-month window"],
              ["Output", "Signal JSON to OMS and desk alert system; composite score logged to database"],
              ["Monitoring", "Datadog alert on data feed latency >10 minutes; model drift tracked via PSI"],
            ].map(([name, desc]) => (
              <div key={name} className="infra-item">
                <span className="infra-name">{name}</span>
                <span className="infra-desc">{desc}</span>
              </div>
            ))}
          </div>

          <h3 className="subhead" style={{ marginTop: "24px" }}>Exchange Connectivity</h3>
          <table className="report-table">
            <thead><tr><th>Venue</th><th>Protocol</th></tr></thead>
            <tbody>
              {[
                ["EPEX SPOT", "FIX 4.4 / EFET API"],
                ["OMIE", "OMIE Web API / MIBEL gateway"],
                ["XBID", "XBID NEMO API"],
                ["Nord Pool", "Volue Insight API"],
                ["Broker fallback", "Statkraft / Axpo desk (illiquid hours)"],
              ].map(([v, p]) => (
                <tr key={v}><td className="td-strong">{v}</td><td className="td-mono">{p}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="callout" style={{ marginTop: "28px" }}>
        <span className="callout-label">Backtesting Specification</span>
        Backtest period: January 2021 – December 2024. Replay of DA auction outcomes
        versus composite signal score across all target delivery windows. Primary
        evaluation metrics: directional hit rate by signal tier, average P&L per
        MWh per signal event, daily Sharpe ratio, and maximum drawdown. The edge is
        expected to be most pronounced in German summer midday hours and Spanish
        spring shoulder periods — these regimes are to be validated independently
        before live deployment.
      </div>
    </div>
  );
}

const componentMap = {
  thesis: ThesisSection,
  signals: SignalsSection,
  execution: ExecutionSection,
  risk: RiskSection,
  infra: InfraSection,
};

/* ─── ROOT ───────────────────────────────────────────────────── */
export default function PeaceCapitalReport() {
  const [active, setActive] = useState("thesis");
  const ActiveComponent = componentMap[active];
  const today = new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });

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
          font-size: 14px;
          line-height: 1.75;
          min-height: 100vh;
        }

        .page {
          max-width: 900px;
          margin: 0 auto;
          padding: 0 32px 80px;
        }

        /* ── MASTHEAD ── */
        .masthead {
          border-bottom: 2px solid var(--teal);
          padding: 36px 0 20px;
          margin-bottom: 0;
        }

        .masthead-top {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 16px;
        }

        .firm-name {
          font-family: 'Cormorant Garamond', Georgia, serif;
          font-size: 28px;
          font-weight: 600;
          letter-spacing: 0.06em;
          color: #f0f4f8;
          text-transform: uppercase;
        }

        .firm-sub {
          font-family: 'Cormorant Garamond', Georgia, serif;
          font-size: 13px;
          font-weight: 400;
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
          font-family: 'Cormorant Garamond', Georgia, serif;
          font-size: 20px;
          font-weight: 500;
          font-style: italic;
          color: var(--text);
          letter-spacing: 0.01em;
        }

        .report-tag {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          letter-spacing: 0.12em;
          color: var(--crimson);
          border: 1px solid var(--crimson);
          padding: 3px 10px;
          text-transform: uppercase;
        }

        /* ── NAV ── */
        .nav {
          display: flex;
          border-bottom: 1px solid var(--rule);
          margin-bottom: 32px;
          gap: 0;
          overflow-x: auto;
        }

        .nav-btn {
          font-family: 'Source Serif 4', serif;
          font-size: 12px;
          font-style: italic;
          color: var(--text3);
          background: none;
          border: none;
          padding: 14px 20px 12px;
          cursor: pointer;
          border-bottom: 2px solid transparent;
          margin-bottom: -1px;
          white-space: nowrap;
          transition: color 0.15s, border-color 0.15s;
        }

        .nav-btn:hover { color: var(--text2); }

        .nav-btn.active {
          color: var(--teal-ll);
          border-bottom-color: var(--teal-ll);
        }

        /* ── SECTION ── */
        .section-body > * + * { margin-top: 20px; }

        .abstract {
          border-left: 3px solid var(--teal);
          padding: 16px 20px;
          background: var(--navy2);
        }

        .abstract-label {
          display: block;
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          letter-spacing: 0.2em;
          text-transform: uppercase;
          color: var(--teal-ll);
          margin-bottom: 8px;
        }

        .abstract p {
          font-size: 13.5px;
          color: var(--text2);
          line-height: 1.85;
        }

        .two-col {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 32px;
        }

        .subhead {
          font-family: 'Cormorant Garamond', Georgia, serif;
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

        .callout {
          background: rgba(160, 28, 46, 0.07);
          border-left: 3px solid var(--crimson);
          padding: 14px 18px;
          font-size: 13px;
          color: var(--text2);
          line-height: 1.8;
          margin-top: 20px;
        }

        .callout-label {
          display: block;
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          letter-spacing: 0.2em;
          text-transform: uppercase;
          color: var(--crim-l);
          margin-bottom: 6px;
        }

        /* ── TABLES ── */
        .report-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12.5px;
          margin-top: 4px;
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
        .td-mono   { font-family: 'JetBrains Mono', monospace; font-size: 12px; }

        /* ── PILLS ── */
        .pill {
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          padding: 2px 8px;
          border-radius: 1px;
        }

        .pill-primary     { background: rgba(26,92,92,0.25);  color: var(--teal-ll); border: 1px solid var(--teal); }
        .pill-secondary   { background: rgba(26,92,92,0.1);   color: var(--text3);   border: 1px solid var(--rule2); }
        .pill-monitor     { background: transparent;           color: var(--text3);   border: 1px solid var(--rule); }
        .pill-standard    { background: rgba(26,92,92,0.15);  color: var(--teal-ll); border: 1px solid var(--teal); }
        .pill-overweight  { background: rgba(201,168,76,0.1); color: var(--gold);    border: 1px solid rgba(201,168,76,0.4); }
        .pill-highconviction { background: rgba(201,168,76,0.18); color: var(--gold); border: 1px solid rgba(201,168,76,0.5); }
        .pill-maximum     { background: rgba(160,28,46,0.15); color: var(--crim-l);  border: 1px solid rgba(160,28,46,0.4); }
        .pill-notrade     { background: transparent;           color: var(--text3);   border: 1px solid var(--rule); }

        /* ── SIGNALS ── */
        .signal-block {
          padding: 18px 0;
          border-bottom: 1px solid var(--rule);
        }

        .signal-header {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          margin-bottom: 10px;
          gap: 12px;
          flex-wrap: wrap;
        }

        .signal-left {
          display: flex;
          align-items: baseline;
          gap: 10px;
          flex-wrap: wrap;
        }

        .tier-tag {
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          padding: 2px 8px;
        }

        .tier-tieri  { background: rgba(26,92,92,0.2);  color: var(--teal-ll); border: 1px solid var(--teal); }
        .tier-tierii { background: rgba(201,168,76,0.1); color: var(--gold);    border: 1px solid rgba(201,168,76,0.4); }
        .tier-tieriii{ background: rgba(103,122,144,0.1); color: var(--text3);  border: 1px solid var(--rule2); }

        .signal-name {
          font-family: 'Cormorant Garamond', serif;
          font-size: 16px;
          font-weight: 600;
          color: var(--text);
        }

        .signal-abbr {
          font-family: 'JetBrains Mono', monospace;
          font-size: 11px;
          color: var(--text3);
        }

        .signal-weight {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          color: var(--text3);
          white-space: nowrap;
        }

        .signal-meta-row {
          margin-top: 10px;
          display: flex;
          gap: 24px;
          flex-wrap: wrap;
          font-size: 11.5px;
          color: var(--text3);
          font-style: italic;
        }

        /* ── RISK ── */
        .risk-block {
          padding: 16px 0;
          border-bottom: 1px solid var(--rule);
        }

        .risk-header {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          margin-bottom: 8px;
        }

        .risk-name {
          font-family: 'Cormorant Garamond', serif;
          font-size: 16px;
          font-weight: 600;
          color: var(--text);
        }

        .severity {
          font-family: 'JetBrains Mono', monospace;
          font-size: 10px;
          letter-spacing: 0.1em;
          text-transform: uppercase;
        }

        .sev-high   { color: var(--crim-l); }
        .sev-medium { color: var(--gold); }
        .sev-low    { color: var(--text3); }

        /* ── INFRA ── */
        .infra-list {
          margin-top: 14px;
          display: flex;
          flex-direction: column;
          gap: 0;
        }

        .infra-item {
          padding: 10px 0;
          border-bottom: 1px solid var(--rule);
          display: flex;
          flex-direction: column;
          gap: 3px;
        }

        .infra-name {
          font-size: 12.5px;
          font-weight: 600;
          color: var(--text);
        }

        .infra-desc {
          font-size: 12px;
          color: var(--text3);
          line-height: 1.6;
        }

        /* ── FOOTER ── */
        .report-footer {
          margin-top: 48px;
          padding-top: 16px;
          border-top: 1px solid var(--rule);
          font-size: 11px;
          color: var(--text3);
          font-style: italic;
          line-height: 1.7;
        }

        @media (max-width: 640px) {
          .two-col { grid-template-columns: 1fr; gap: 20px; }
          .masthead-top { flex-direction: column; gap: 12px; }
          .report-title-row { flex-direction: column; gap: 8px; }
        }
      `}</style>

      <div className="page">
        {/* MASTHEAD */}
        <div className="masthead">
          <div className="masthead-top">
            <div>
              <div className="firm-name">Peace Capital</div>
              <div className="firm-sub">Investment Management</div>
            </div>
            <div className="masthead-meta">
              <div>CONFIDENTIAL — INTERNAL USE ONLY</div>
              <div>Strategy Memorandum</div>
              <div>{today}</div>
              <div>Ref: PC-PWR-2026-001</div>
            </div>
          </div>
          <div className="report-title-row">
            <div className="report-title">
              European Electricity Spot Markets — Structural Short on Renewable Overcapacity
            </div>
            <span className="report-tag">Short Bias</span>
          </div>
        </div>

        {/* NAV */}
        <div className="nav">
          {SECTIONS.map((s) => (
            <button
              key={s.id}
              className={`nav-btn${active === s.id ? " active" : ""}`}
              onClick={() => setActive(s.id)}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* CONTENT */}
        <ActiveComponent />

        {/* FOOTER */}
        <div className="report-footer">
          This memorandum is prepared solely for the internal use of Peace Capital Investment Management
          and its authorised personnel. It does not constitute investment advice and must not be
          distributed to third parties without prior written consent. Past performance is not indicative
          of future results. All strategies involve risk of loss.
        </div>
      </div>
    </>
  );
}
