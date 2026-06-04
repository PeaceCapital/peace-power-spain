"""
Peace* Energy — Iberia Signal Engine
Live dashboard. Reads from:
  - pc_spot_pricer_real_v2.pkl  (pricer outputs)
  - pc_live_esios.pkl           (live ESIOS generation, demand, ATC)

No peace_power package dependency.

Run with:
    streamlit run pc_dashboard.py
"""

from __future__ import annotations

import pickle
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# ── CONFIG ────────────────────────────────────────────────────
PKL_PRICER = Path('pc_spot_pricer_real_v2.pkl')
PKL_LIVE   = Path('pc_live_esios.pkl')

st.set_page_config(
    page_title="Peace* Energy — Iberia Pricer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

import streamlit as st

# Token loading — Streamlit secrets in production, .env locally

def load_token():

    try:

        return st.secrets["f6835be28cb33be5b677a4f8866bec14955f81f7ff39cac08880a8c2fc474792"]

    except Exception:

        env_path = '/Users/oly/Documents/New project/peace-power-spain/.env'

        with open(env_path) as f:

            for line in f:

                line = line.strip()

                if line and not line.startswith('#') and '=' in line:

                    key, val = line.split('=', 1)

                    if key.strip() == 'f6835be28cb33be5b677a4f8866bec14955f81f7ff39cac08880a8c2fc474792':

                        return val.strip()

        return None

TOKEN = load_token()

# ── STYLES ────────────────────────────────────────────────────
# Helvetica Neue is a system font on macOS/iOS; Arial is the Windows fallback.
# No remote font load needed — faster and no FOUT.
def inject_styles():
    st.markdown("""
    <style>
    html, body, [class*="css"], * {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        font-weight: 300;
        -webkit-font-smoothing: antialiased;
    }
    .stApp {
        background: #090a0d;
        color: #f0f4f3;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    h1, h2, h3, h4 {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: #f0f4f3 !important;
    }
    p, li, span, div, caption { font-weight: 300 !important; }
    .stTabs [data-baseweb="tab-list"] {
        background: #090a0d;
        border-bottom: 1px solid rgba(13,148,136,0.18);
        gap: 0;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #5f8a85;
        background: transparent;
        border-bottom: 2px solid transparent;
        padding: 0.75rem 1.2rem;
    }
    .stTabs [aria-selected="true"] {
        color: #0D9488 !important;
        border-bottom: 2px solid #0D9488 !important;
        background: transparent !important;
    }
    [data-testid="stSidebar"] {
        background: #090a0d;
        border-right: 1px solid rgba(13,148,136,0.14);
    }
    [data-testid="stSidebar"] * {
        color: #8ab5b0 !important;
        font-weight: 300 !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] strong {
        font-weight: 700 !important;
        color: #f0f4f3 !important;
    }
    hr { border-color: rgba(13,148,136,0.18); }
    .stDataFrame { border: 1px solid rgba(13,148,136,0.15) !important; border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)


# ── HTML COMPONENTS ───────────────────────────────────────────
def masthead(live_status: str, data_end: str) -> str:
    return """
    <div style="border-bottom:1px solid rgba(13,148,136,0.28); padding:32px 0 20px; margin-bottom:4px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:18px;">
            <div>
                <div style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                            font-size:28px; font-weight:700; letter-spacing:-0.02em; color:#f0f4f3;
                            line-height:1;">
                    Iberia Signal Engine
                </div>
            </div>
            <div style="text-align:right; font-size:10.5px; font-weight:300;
                        color:#5f8a85; line-height:1.9; letter-spacing:0.04em;">
                <div>CONFIDENTIAL — INTERNAL USE ONLY</div>
                <div>{date}</div>
                <div>Ref: PC-NRG-2026-DASH</div>
            </div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:baseline;
                    padding-top:14px; border-top:1px solid rgba(13,148,136,0.14);">
            <div style="font-size:15px; font-weight:300; letter-spacing:0.01em; color:#8ab5b0;">
                Spain / OMIE Day-Ahead Price Monitor &amp; Signal Engine
            </div>
            <div style="font-size:9px; font-weight:700; letter-spacing:0.16em;
                        color:#0D9488; border:1px solid rgba(13,148,136,0.35);
                        padding:3px 11px; text-transform:uppercase; white-space:nowrap;">
                {status}
            </div>
        </div>
    </div>
    """.format(date=datetime.now().strftime('%d %B %Y'), status=live_status)


def metric_card(label, value, note, accent="#0D9488"):
    return """
    <div style="background:linear-gradient(160deg,rgba(17,20,26,0.92) 0%,rgba(24,18,21,0.86) 100%);
                border:1px solid rgba(13,148,136,0.18); border-radius:16px;
                padding:18px 20px; border-top:2px solid {accent};">
        <div style="font-size:9px; font-weight:700; letter-spacing:0.2em;
                    text-transform:uppercase; color:#5f8a85; margin-bottom:10px;">{label}</div>
        <div style="font-size:26px; font-weight:700; letter-spacing:-0.03em;
                    color:#f0f4f3; line-height:1;">{value}</div>
        <div style="font-size:12px; font-weight:300; color:#5f8a85; margin-top:8px;">{note}</div>
    </div>
    """.format(accent=accent, label=label, value=value, note=note)


def panel_note(text, color="#2d7d74"):
    return """
    <div style="border-left:3px solid {color}; padding:12px 16px;
                background:rgba(45,125,116,0.07); margin-bottom:16px;
                font-size:13px; font-weight:300; color:#8ab5b0; line-height:1.75;">
        {text}
    </div>
    """.format(color=color, text=text)


def section_label(text):
    return """
    <div style="font-size:10px; font-weight:700; letter-spacing:0.2em;
                text-transform:uppercase; color:#0D9488;
                padding-bottom:7px; border-bottom:1px solid rgba(13,148,136,0.18);
                margin-bottom:14px;">
        {text}
    </div>
    """.format(text=text)


def signal_row(label, value, note="", color="#0D9488"):
    return """
    <div style="padding:10px 0; border-bottom:1px solid rgba(13,148,136,0.12);">
        <div style="font-size:9px; font-weight:700; letter-spacing:0.2em;
                    text-transform:uppercase; color:#5f8a85;">
            {label}
        </div>
        <div style="font-size:20px; font-weight:700; letter-spacing:-0.02em;
                    color:{color}; margin-top:3px; line-height:1.1;">
            {value}
        </div>
        <div style="font-size:11px; font-weight:300; color:#5f8a85; margin-top:1px;">{note}</div>
    </div>
    """.format(label=label, value=value, color=color, note=note)


# ── DATA LOADING ──────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data():
    pricer, live = None, None

    if PKL_PRICER.exists():
        with open(PKL_PRICER, 'rb') as f:
            pricer = pickle.load(f)

    if PKL_LIVE.exists():
        live = pd.read_pickle(PKL_LIVE)

    return pricer, live


# ── SIDEBAR ───────────────────────────────────────────────────
def render_sidebar(pricer, live):
    with st.sidebar:
        st.markdown("### Peace\* Energy")
        st.markdown("---")

        if pricer:
            st.markdown("**Pricer Data**")
            st.caption("{} → {}".format(pricer['data_start'], pricer['data_end']))
            st.caption("{:,} hourly rows".format(pricer['n_hours']))
            st.caption("Neg. hours: {:,}  ({:.1f}%)".format(
                pricer['n_negative_hours'],
                pricer['n_negative_hours'] / pricer['n_hours'] * 100
            ))

        if live is not None:
            st.markdown("**ESIOS Live Data**")
            st.caption("{} rows".format(len(live)))
            st.caption("{} → {}".format(
                str(live.index[0].date()),
                str(live.index[-1].date())
            ))

        st.markdown("---")
        st.markdown("**Feed Status**")

        feeds = [
            ("OMIE Pricer",   "LIVE"    if pricer else "MISSING"),
            ("ESIOS Live",    "LIVE"    if live is not None else "MISSING"),
            ("Thermal Floor", "PROXY"   ),
            ("BESS Data",     "PENDING" ),
            ("REE Node Map",  "PENDING" ),
        ]

        colors = {
            "LIVE":    "#2d7d74",
            "PROXY":   "#0D9488",
            "PENDING": "#5f8a85",
            "MISSING": "#8c3050",
        }

        for name, status in feeds:
            c = colors.get(status, "#5f8a85")
            st.markdown(
                '<span style="color:{c}; font-family:monospace; font-size:11px;">'
                '● {s}</span> <span style="font-size:11px; color:#5f8a85;">{n}</span>'.format(
                    c=c, s=status, n=name
                ),
                unsafe_allow_html=True,
            )

        st.markdown("---")
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()


# ── MAIN ──────────────────────────────────────────────────────
inject_styles()
pricer, live = load_data()

if pricer is None and live is None:
    st.error("No data files found. Run the canonical notebook first.")
    st.stop()

render_sidebar(pricer, live)

# ── DERIVE CURRENT STATE ──────────────────────────────────────
# Prefer live ESIOS data, fall back to pricer pickle
if live is not None:
    last_spot     = float(live['omie_price'].dropna().iloc[-1])
    last_regime   = str(live['regime'].dropna().iloc[-1])
    last_rsi      = float(live['rsi'].dropna().iloc[-1])
    last_discount = float(live['floor_discount'].dropna().iloc[-1])
    floor_proxy   = float(live['thermal_floor'].iloc[-1])
    data_source   = "ESIOS LIVE"
else:
    last_spot     = pricer['last_spot']
    last_regime   = "Thermal-Marginal"
    last_rsi      = 0.0
    last_discount = pricer['price_vs_floor']
    floor_proxy   = pricer['floor_proxy']
    data_source   = "CACHED"

# Pricer outputs
if pricer:
    vol_annual  = pricer['annualised_vol']
    b76_call    = pricer['black76_call']
    mc_call     = pricer['mc_call']
    mc_se       = pricer['mc_se']
    spike_prob  = pricer['spike_prob']
    neg_prob    = pricer['neg_price_prob']
    spot_series = pricer['spot']
else:
    vol_annual  = 0.0
    b76_call    = 0.0
    mc_call     = 0.0
    mc_se       = 0.0
    spike_prob  = 0.0
    neg_prob    = 0.0
    spot_series = None

regime_color = {
    "Demand-Stress":     "#8c3050",
    "Renewable-Dom.":    "#2d7d74",
    "Thermal-Marginal":  "#0D9488",
}.get(last_regime, "#5f8a85")

# Masthead
st.markdown(masthead(data_source, str(live.index[-1].date()) if live is not None else "—"),
            unsafe_allow_html=True)

# ── METRIC ROW ────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    st.markdown(metric_card(
        "OMIE Last Spot",
        "{:.2f} EUR/MWh".format(last_spot),
        "Floor disc: {:+.1f}".format(last_discount),
        "#2d7d74"
    ), unsafe_allow_html=True)

with c2:
    st.markdown(metric_card(
        "Market Regime",
        last_regime,
        "RSI: {:.3f}".format(last_rsi),
        regime_color
    ), unsafe_allow_html=True)

with c3:
    st.markdown(metric_card(
        "Annualised Vol",
        "{:.1f}%".format(vol_annual * 100),
        "Hourly, 4σ clipped",
        "#0D9488"
    ), unsafe_allow_html=True)

with c4:
    st.markdown(metric_card(
        "Black-76 Call",
        "{:.2f}".format(b76_call),
        "ATM 1M shifted lognormal",
        "#2d7d74"
    ), unsafe_allow_html=True)

with c5:
    st.markdown(metric_card(
        "MC Call",
        "{:.2f}".format(mc_call),
        "+/- {:.3f} SE".format(mc_se),
        "#0D9488"
    ), unsafe_allow_html=True)

with c6:
    st.markdown(metric_card(
        "Thermal Floor",
        "{:.2f} EUR/MWh".format(floor_proxy),
        "TTF 35x0.45 + EUA 65x0.35",
        "#5f8a85"
    ), unsafe_allow_html=True)

st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────
tab_signal, tab_generation, tab_pricer, tab_vol, tab_readiness = st.tabs([
    "I. Signal Deck",
    "II. Live Generation",
    "III. Pricer Output",
    "IV. Volatility",
    "V. Readiness",
])


# ── TAB I: SIGNAL DECK ────────────────────────────────────────
with tab_signal:
    st.markdown(panel_note(
        "OMIE spot vs thermal floor proxy. When spot trades below the floor, "
        "thermal generation is displaced and the short thesis is active. "
        "Regime is classified hourly from RSI and spot/floor ratio."
    ), unsafe_allow_html=True)

    if live is not None:
        left, right = st.columns([2, 1])

        with left:
            st.markdown(section_label("OMIE Spot vs Thermal Floor — Live"), unsafe_allow_html=True)
            chart = live[['omie_price', 'thermal_floor']].rename(columns={
                'omie_price':    'OMIE Price (EUR/MWh)',
                'thermal_floor': 'Thermal Floor Proxy',
            })
            st.line_chart(chart, height=260)

            st.markdown(section_label("Floor Discount (EUR/MWh)"), unsafe_allow_html=True)
            discount = live[['floor_discount']].rename(columns={
                'floor_discount': 'Floor Discount'
            })
            st.line_chart(discount, height=160)

        with right:
            st.markdown(section_label("Live Signal Readout"), unsafe_allow_html=True)
            latest = live.dropna(subset=['omie_price']).iloc[-1]

            st.markdown(signal_row(
                "Regime", last_regime, "from RSI + floor ratio", regime_color
            ), unsafe_allow_html=True)
            st.markdown(signal_row(
                "OMIE Last Spot",
                "{:.2f} EUR/MWh".format(last_spot),
                "ESIOS indicator 600"
            ), unsafe_allow_html=True)
            st.markdown(signal_row(
                "Thermal Floor",
                "{:.2f} EUR/MWh".format(floor_proxy),
                "TTF proxy + EUA proxy"
            ), unsafe_allow_html=True)
            st.markdown(signal_row(
                "Floor Discount",
                "{:+.2f} EUR/MWh".format(last_discount),
                "negative = below floor — short signal",
                "#8c3050" if last_discount < 0 else "#2d7d74"
            ), unsafe_allow_html=True)
            st.markdown(signal_row(
                "RSI",
                "{:.4f}".format(last_rsi),
                "renewable gen / demand"
            ), unsafe_allow_html=True)
            st.markdown(signal_row(
                "ATC ES→FR",
                "{:.1f} MW".format(float(live['atc_es_fr'].dropna().iloc[-1])),
                "negative = Spain exporting"
            ), unsafe_allow_html=True)

        # Regime timeline
        st.markdown(section_label("Regime Timeline"), unsafe_allow_html=True)
        regime_map = {
            'Thermal-Marginal': 0,
            'Renewable-Dom.':   1,
            'Demand-Stress':    2,
        }
        regime_num = live['regime'].map(regime_map).rename('Regime (0=Thermal 1=Renew 2=Stress)')
        st.line_chart(regime_num, height=140)

    else:
        st.warning("ESIOS live data not found. Run the ESIOS pull cell in Jupyter first.")


# ── TAB II: LIVE GENERATION ───────────────────────────────────
with tab_generation:
    st.markdown(panel_note(
        "Live peninsular Spain generation mix from ESIOS. "
        "All values in MWh/h (= MW effective). "
        "Renewable penetration drives the RSI signal."
    ), unsafe_allow_html=True)

    if live is not None:
        left, right = st.columns(2)

        with left:
            st.markdown(section_label("Generation Mix"), unsafe_allow_html=True)
            gen_cols = ['gen_wind', 'gen_solar_pv', 'gen_solar_thermal',
                        'gen_hydro', 'gen_nuclear']
            gen_chart = live[gen_cols].rename(columns={
                'gen_wind':          'Wind',
                'gen_solar_pv':      'Solar PV',
                'gen_solar_thermal': 'Solar Thermal',
                'gen_hydro':         'Hydro',
                'gen_nuclear':       'Nuclear',
            })
            st.area_chart(gen_chart, height=280)

            st.markdown(section_label("Renewable Surplus Index (RSI)"), unsafe_allow_html=True)
            st.line_chart(live[['rsi']].rename(columns={'rsi': 'RSI'}), height=160)

        with right:
            st.markdown(section_label("Demand vs Renewable Generation"), unsafe_allow_html=True)
            dr = live[['demand_forecast', 'gen_renewable']].rename(columns={
                'demand_forecast': 'Demand Forecast (MWh/h)',
                'gen_renewable':   'Renewable Generation (MWh/h)',
            })
            st.line_chart(dr, height=280)

            st.markdown(section_label("ATC ES→FR Interconnector"), unsafe_allow_html=True)
            st.line_chart(
                live[['atc_es_fr']].rename(columns={'atc_es_fr': 'ATC MW (neg=export)'}),
                height=160
            )

        # Latest generation snapshot
        st.markdown(section_label("Latest Hour Snapshot"), unsafe_allow_html=True)
        snap = live.dropna(subset=['omie_price']).iloc[-1]
        snap_df = pd.DataFrame([
            ("OMIE Price",        "{:.2f} EUR/MWh".format(snap['omie_price'])),
            ("Wind",              "{:,.0f} MWh/h".format(snap['gen_wind'])),
            ("Solar PV",          "{:,.0f} MWh/h".format(snap['gen_solar_pv'])),
            ("Solar Thermal",     "{:,.0f} MWh/h".format(snap['gen_solar_thermal'])),
            ("Hydro",             "{:,.0f} MWh/h".format(snap['gen_hydro'])),
            ("Nuclear",           "{:,.0f} MWh/h".format(snap['gen_nuclear'])),
            ("Total Renewable",   "{:,.0f} MWh/h".format(snap['gen_renewable'])),
            ("Demand Forecast",   "{:,.0f} MWh/h".format(snap['demand_forecast'])),
            ("RSI",               "{:.4f}".format(snap['rsi'])),
            ("ATC ES→FR",         "{:.1f} MW".format(snap['atc_es_fr'])),
            ("Regime",            snap['regime']),
        ], columns=["Indicator", "Value"])
        st.dataframe(snap_df, use_container_width=True, hide_index=True)

    else:
        st.warning("ESIOS live data not found.")


# ── TAB III: PRICER OUTPUT ────────────────────────────────────
with tab_pricer:
    st.markdown(panel_note(
        "Black-76 and Monte Carlo call prices on the OMIE spot forward. "
        "Negative prices handled via shifted log-normal. "
        "Shift = |min| + 1 = {:.2f} EUR/MWh.".format(
            pricer['shift_constant'] if pricer else 0
        )
    ), unsafe_allow_html=True)

    if pricer:
        left, right = st.columns(2)

        with left:
            st.markdown(section_label("Pricing Parameters"), unsafe_allow_html=True)
            shift = pricer['shift_constant']
            rows = [
                ("Last Spot (F)",       "{:.4f} EUR/MWh".format(pricer['last_spot'])),
                ("Strike (K, ATM)",     "{:.4f} EUR/MWh".format(pricer['strike'])),
                ("Shift Constant",      "{:.4f} EUR/MWh".format(shift)),
                ("Shifted F",           "{:.4f} EUR/MWh".format(pricer['last_spot'] + shift)),
                ("Annualised Vol (σ)",  "{:.4f}  ({:.2f}%)".format(
                    pricer['sigma'], pricer['sigma'] * 100)),
                ("T (years)",           "{:.6f}".format(pricer['T'])),
                ("Risk-free Rate",      "{:.2%}".format(pricer['r'])),
                ("Black-76 Call",       "{:.4f} EUR/MWh".format(b76_call)),
                ("MC Call",             "{:.4f} EUR/MWh".format(mc_call)),
                ("MC Std Error",        "{:.4f} EUR/MWh".format(mc_se)),
                ("B76 vs MC Diff",      "{:.4f} EUR/MWh".format(abs(b76_call - mc_call))),
                ("Spike Prob",          "{:.4f}".format(spike_prob)),
                ("Neg. Price Prob",     "{:.4f}".format(neg_prob)),
            ]
            st.dataframe(
                pd.DataFrame(rows, columns=["Parameter", "Value"]),
                use_container_width=True, hide_index=True, height=420
            )

        with right:
            st.markdown(section_label("MC Payoff Distribution"), unsafe_allow_html=True)
            np.random.seed(42)
            F_s = pricer['last_spot'] + shift
            K_s = pricer['strike']    + shift
            T, r, sigma = pricer['T'], pricer['r'], pricer['sigma']
            Z        = np.random.standard_normal(10000)
            ST_shift = F_s * np.exp((r - 0.5*sigma**2)*T + sigma*np.sqrt(T)*Z)
            ST_real  = ST_shift - shift
            payoffs  = np.maximum(ST_real - pricer['strike'], 0.0)
            nonzero  = payoffs[payoffs > 0]

            st.caption("In-the-money: {:,} of 10,000  ({:.1f}%)".format(
                len(nonzero), len(nonzero) / 100
            ))
            hist_df = pd.DataFrame({'payoff': nonzero})
            hist_df['bucket'] = pd.cut(hist_df['payoff'], bins=25)
            counts = hist_df.groupby('bucket', observed=True).size().reset_index()
            counts.columns = ['bucket', 'count']
            counts['label'] = counts['bucket'].apply(lambda x: "{:.1f}".format(x.mid))
            st.bar_chart(counts.set_index('label')['count'], height=340)
    else:
        st.warning("Pricer pickle not found. Run Pricer_OMIE_Canonical.ipynb first.")


# ── TAB IV: VOLATILITY ────────────────────────────────────────
with tab_vol:
    st.markdown(panel_note(
        "Rolling 30-day annualised volatility on positive-price hourly log returns. "
        "Outliers beyond 4σ excluded. "
        "Current annualised vol: {:.2f}%.".format(vol_annual * 100)
    ), unsafe_allow_html=True)

    if spot_series is not None:
        spot_pos    = spot_series[spot_series > 0]
        log_ret     = np.log(spot_pos).diff().dropna()
        z           = (log_ret - log_ret.mean()) / log_ret.std()
        ret_clean   = log_ret[z.abs() < 4]
        rolling_vol = ret_clean.rolling(30 * 24).std() * np.sqrt(8760) * 100
        rolling_vol = rolling_vol.dropna().to_frame('Rolling 30d Vol (%)')

        left, right = st.columns(2)

        with left:
            st.markdown(section_label("Rolling 30-Day Annualised Vol (%)"), unsafe_allow_html=True)
            st.line_chart(rolling_vol, height=260)

            st.markdown(section_label("Log Returns — Last 30 Days"), unsafe_allow_html=True)
            st.line_chart(
                ret_clean.tail(30*24).to_frame('Log Returns'),
                height=180
            )

        with right:
            st.markdown(section_label("Vol Statistics"), unsafe_allow_html=True)
            context = pd.DataFrame([
                ("Hourly vol",        "{:.6f}".format(vol_annual / np.sqrt(8760))),
                ("Daily vol",         "{:.4f}  ({:.2f}%)".format(
                    vol_annual / np.sqrt(365), vol_annual / np.sqrt(365) * 100)),
                ("Annual vol",        "{:.4f}  ({:.2f}%)".format(vol_annual, vol_annual * 100)),
                ("Typical OMIE range","30–80% annualised"),
                ("Status",            "NORMAL" if 0.3 <= vol_annual <= 0.8 else "CHECK"),
            ], columns=["Metric", "Value"])
            st.dataframe(context, use_container_width=True, hide_index=True)

            st.markdown(section_label("Price Percentiles"), unsafe_allow_html=True)
            pct = np.percentile(spot_series.values, [1,5,10,25,50,75,90,95,99])
            dist_df = pd.DataFrame({
                'Percentile': ['P1','P5','P10','P25','P50','P75','P90','P95','P99'],
                'EUR/MWh':    ["{:.2f}".format(p) for p in pct],
            })
            st.dataframe(dist_df, use_container_width=True, hide_index=True)
    else:
        st.warning("Spot series not available.")


# ── TAB V: READINESS ─────────────────────────────────────────
with tab_readiness:
    st.markdown(panel_note(
        "Honest status of every capability. Visible to clients — "
        "it signals methodology rigour, not incompleteness.",
        color="#5f1327"
    ), unsafe_allow_html=True)

    pricer_ok = pricer is not None
    live_ok   = live is not None

    readiness = pd.DataFrame([
        ("OMIE DA prices",       "LIVE"    if pricer_ok else "MISSING",
         "28,674 rows in pricer pickle."),
        ("ESIOS generation mix", "LIVE"    if live_ok else "MISSING",
         "Wind, solar PV, solar thermal, hydro, nuclear — 168 hours."),
        ("ESIOS demand forecast","LIVE"    if live_ok else "MISSING",
         "Indicator 544 — peninsular demand prevista."),
        ("ESIOS ATC ES→FR",      "LIVE"    if live_ok else "MISSING",
         "Indicator 10209 — interconnector flow."),
        ("Spot pricer (B76+MC)", "LIVE"    if pricer_ok else "MISSING",
         "Shifted log-normal, correct vol estimation."),
        ("Regime classifier",    "LIVE"    if live_ok else "PROXY",
         "RSI + floor ratio rule-based. ML model next."),
        ("Thermal floor",        "PROXY",
         "TTF=35, EUA=65 hardcoded. Wire live feeds next."),
        ("BESS sunset model",    "PENDING",
         "Search ESIOS for bateria/almacenamiento indicators."),
        ("REE node map",         "PENDING",
         "230-node demand availability map — ingest from REE."),
        ("Daily PDF briefing",   "PENDING",
         "Structure ready. Wire once thermal floor is live."),
        ("Git version control",  "PENDING",
         "Commit current state before next iteration."),
        ("Streamlit deployment", "PENDING",
         "Deploy to Streamlit Cloud for shareable URL."),
    ], columns=["Capability", "Status", "Notes"])

    status_color = {
        "LIVE":    "#2d7d74",
        "PROXY":   "#0D9488",
        "PENDING": "#5f8a85",
        "MISSING": "#8c3050",
    }

    def style_status(val):
        c = status_color.get(val, "#5f8a85")
        return "color:{}; font-weight:700; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;".format(c)

    st.dataframe(
        readiness.style.applymap(style_status, subset=["Status"]),
        use_container_width=True, hide_index=True, height=400
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(section_label("Next Steps"), unsafe_allow_html=True)

    steps = [
        ("CRITICAL", "Search ESIOS for BESS indicators: search 'bateria' and 'almacenamiento' to find live storage data."),
        ("CRITICAL", "Git init + commit — repo is still untracked."),
        ("HIGH",     "Wire live TTF and EUA prices to replace the hardcoded thermal floor proxy."),
        ("HIGH",     "Ingest REE 230-node demand availability map for congestion scoring."),
        ("HIGH",     "Deploy dashboard to Streamlit Community Cloud for a shareable URL."),
        ("MED",      "Extend ESIOS history pull from 7 days to 90 days for richer signal analysis."),
    ]

    colors = {"CRITICAL": "#8c3050", "HIGH": "#0D9488", "MED": "#2d7d74"}

    for priority, text in steps:
        c = colors.get(priority, "#5f8a85")
        st.markdown("""
        <div style="display:flex; gap:12px; padding:10px 0;
                    border-bottom:1px solid rgba(13,148,136,0.12); align-items:flex-start;">
            <span style="font-size:9px; font-weight:700; letter-spacing:0.14em;
                         color:{c}; border:1px solid {c}; padding:2px 8px; min-width:62px;
                         text-align:center; margin-top:1px;">{p}</span>
            <span style="font-size:13px; font-weight:300; color:#8ab5b0; line-height:1.6;">{t}</span>
        </div>
        """.format(c=c, p=priority, t=text), unsafe_allow_html=True)
