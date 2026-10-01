"""
Peace* Energy — Iberia Signal Engine
Modern briefing-style dashboard.
"""
from __future__ import annotations
import os
import pickle
import sys
import xml.etree.ElementTree as _ET
from datetime import datetime, date, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote as _urlquote
from typing import Optional, List, Tuple, Dict, Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── EXECUTION MODULE ──────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent / "src"))
try:
    from peace_power.execution.signal import signal_from_live
    from peace_power.execution.guardrails import GuardrailEngine
    from peace_power.execution.adapters.paper import PaperAdapter
    from peace_power.execution.router import ExecutionRouter
    EXEC_OK = True
except ImportError:
    EXEC_OK = False

# ── CONFIG ───────────────────────────────────────────────────
PKL_PRICER = Path("pc_spot_pricer_real_v2.pkl")
PKL_LIVE   = Path("pc_live_esios.pkl")
LOG_PATH   = Path("state/paper_trades.jsonl")

# ── PALETTE ───────────────────────────────────────────────────
C_BG      = "#0a0a0a"
C_SURFACE = "#111111"
C_CARD    = "#1a1a1a"
C_BORDER  = "#2a2a2a"
C_TEXT    = "#ffffff"
C_DIM     = "#888888"
C_MUTED   = "#555555"
C_AMBER   = "#f59e0b"
C_GREEN   = "#10b981"
C_RED     = "#ef4444"
C_TEAL    = "#14b8a6"
C_BLUE    = "#3b82f6"
C_PURPLE  = "#8b5cf6"

# ── PAGE CONFIG ──────────────────────────────────────────────
st.set_page_config(
    page_title="Peace* Energy | Iberia Signal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── GLOBAL CSS ────────────────────────────────────────────────
def inject_css() -> None:
    st.markdown("""
<style>
/* ── Design tokens ── */
:root {
    --bg: #0a0a0a;
    --surface: #111111;
    --card: #1a1a1a;
    --border: #2a2a2a;
    --text: #ffffff;
    --dim: #888888;
    --muted: #555555;
    --amber: #f59e0b;
    --green: #10b981;
    --red: #ef4444;
    --teal: #14b8a6;
    --blue: #3b82f6;
    --sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --mono: 'JetBrains Mono', 'Fira Code', monospace;
}

* { box-sizing: border-box; }

html, body, [class*="css"], .stApp { 
    background: var(--bg) !important; 
    font-family: var(--sans) !important;
}

#MainMenu, footer, header { display: none !important; }
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
.main > div { padding: 0 !important; }

/* ── Typography ── */
body, p, span, div, li, label {
    font-family: var(--sans) !important;
    color: var(--text);
    -webkit-font-smoothing: antialiased;
}

/* ── Header bar ── */
.header-bar {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 16px 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.brand {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.02em;
}

.brand-accent { color: var(--amber); }
.brand-sub { 
    font-weight: 400; 
    color: var(--dim);
    margin-left: 8px;
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.status-live {
    background: rgba(16, 185, 129, 0.1);
    color: var(--green);
    border: 1px solid var(--green);
}

.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 2s infinite;
}

/* ── Ticker ── */
.ticker-bar {
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    padding: 12px 32px;
    display: flex;
    align-items: center;
    gap: 32px;
    overflow-x: auto;
}

.ticker-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
    flex-shrink: 0;
}

.ticker-label {
    font-size: 9px;
    font-weight: 500;
    color: var(--dim);
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.ticker-value {
    font-family: var(--mono);
    font-size: 14px;
    font-weight: 600;
    letter-spacing: -0.01em;
}

/* ── Content area ── */
.content-area {
    padding: 32px;
}

.section-header {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--amber);
    margin-bottom: 20px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--border);
}

/* ── Cards ─ */
.card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 24px;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 16px;
}

.card-title {
    font-size: 14px;
    font-weight: 600;
    letter-spacing: -0.01em;
}

.card-subtitle {
    font-size: 11px;
    color: var(--dim);
    margin-top: 4px;
}

/* ── Signal card ── */
.signal-card {
    background: linear-gradient(135deg, var(--card) 0%, var(--surface) 100%);
    border: 1px solid var(--border);
    border-left: 4px solid var(--amber);
}

.signal-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid var(--amber);
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--amber);
    margin-bottom: 16px;
}

.signal-direction {
    font-size: 48px;
    font-weight: 700;
    line-height: 1;
    margin: 16px 0;
}

.signal-direction.long { color: var(--green); }
.signal-direction.short { color: var(--red); }
.signal-direction.neutral { color: var(--dim); }

/* ── Metric grid ── */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}

.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 16px;
}

.metric-label {
    font-size: 10px;
    font-weight: 500;
    color: var(--dim);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
}

.metric-value {
    font-family: var(--mono);
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.02em;
}

.metric-delta {
    font-size: 11px;
    margin-top: 4px;
}

.metric-delta.positive { color: var(--green); }
.metric-delta.negative { color: var(--red); }

/* ── Data rows ── */
.data-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
}

.data-row:last-child { border-bottom: none; }

.data-label {
    font-size: 12px;
    color: var(--dim);
    font-weight: 400;
}

.data-value {
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 600;
}

/* ── Tabs ─ */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    gap: 0;
    padding: 0 32px;
}

.stTabs [data-baseweb="tab"] {
    font-family: var(--sans) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: var(--dim) !important;
    background: transparent !important;
    border-bottom: 2px solid transparent !important;
    padding: 0 24px !important;
    height: 48px !important;
    margin: 0 !important;
}

.stTabs [aria-selected="true"] {
    color: var(--text) !important;
    border-bottom: 2px solid var(--amber) !important;
}

.stTabs [data-baseweb="tab-panel"] {
    padding: 0 !important;
    background: var(--bg) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--amber) !important;
    border: none !important;
    color: #000 !important;
    font-family: var(--sans) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    border-radius: 6px !important;
}

.stButton > button:hover { 
    background: #fbbf24 !important; 
}

/* ── Tables ── */
.stDataFrame {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
}

/* ── Animations ── */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }
</style>
    """, unsafe_allow_html=True)

# ── HTML COMPONENTS ───────────────────────────────────────────
def _html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)

def header_bar(data_source: str, last_dt: str) -> str:
    now = datetime.now().strftime("%d %b %Y · %H:%M UTC")
    return f'''
    <div class="header-bar">
        <div>
            <div class="brand">
                Peace<span class="brand-accent">*</span>
                <span class="brand-sub">Energy</span>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 16px;">
            <div class="status-badge status-live">
                <span class="status-dot"></span>
                {data_source}
            </div>
            <div style="font-family: var(--mono); font-size: 11px; color: var(--dim);">
                {now}
            </div>
        </div>
    </div>
    '''

def ticker_bar(items: List[Tuple[str, str, str]]) -> str:
    items_html = ""
    for label, value, color in items:
        items_html += f'''
        <div class="ticker-item">
            <div class="ticker-label">{label}</div>
            <div class="ticker-value" style="color: {color};">{value}</div>
        </div>
        '''
    return f'<div class="ticker-bar">{items_html}</div>'

def section_header(text: str) -> str:
    return f'<div class="section-header">{text}</div>'

def signal_card_html(
    regime: str,
    direction: str,
    confidence: float,
    spot: float,
    floor_proxy: float,
    discount: float,
    rsi: float,
    ttf: float,
    eua: float
) -> str:
    dir_class = direction.lower()
    dir_color = {"long": "var(--green)", "short": "var(--red)", "neutral": "var(--dim)"}.get(dir_class, "var(--dim)")
    regime_color = {"Renewable-Dom.": "var(--green)", "Demand-Stress": "var(--red)"}.get(regime, "var(--amber)")
    disc_color = "var(--red)" if discount < 0 else "var(--green)"
    
    return f'''
    <div class="card signal-card">
        <div class="signal-badge">
            <span class="status-dot"></span>
            Live Signal
        </div>
        <div style="color: {regime_color}; font-size: 11px; font-weight: 600; letter-spacing: 0.1em; margin-bottom: 8px;">
            IBERIA POWER · {regime.upper()}
        </div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <div style="font-size: 28px; font-weight: 700; margin-bottom: 8px;">
                    OMIE {spot:.2f} <span style="font-size: 14px; color: var(--dim); font-weight: 400;">EUR/MWh</span>
                </div>
                <div style="font-size: 12px; color: var(--dim);">
                    Floor {floor_proxy:.2f} · TTF {ttf:.2f} · EUA {eua:.0f} €/t
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 10px; color: var(--dim); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px;">
                    Signal
                </div>
                <div class="signal-direction {dir_class}" style="color: {dir_color};">
                    {direction}
                </div>
                <div style="font-family: var(--mono); font-size: 12px; color: {disc_color}; margin-top: 4px;">
                    {discount:+.2f} disc
                </div>
            </div>
        </div>
        <div style="margin-top: 24px; padding-top: 24px; border-top: 1px solid var(--border);">
            <div class="data-row">
                <span class="data-label">RSI · Renewable / Demand</span>
                <span class="data-value" style="font-family: var(--mono);">{rsi:.4f}</span>
            </div>
            <div class="data-row">
                <span class="data-label">Thermal Floor · CCGT 50%</span>
                <span class="data-value" style="color: var(--blue);">{floor_proxy:.2f} €/MWh</span>
            </div>
            <div class="data-row">
                <span class="data-label">Floor Discount · Spot vs Floor</span>
                <span class="data-value" style="color: {disc_color};">{discount:+.2f} €/MWh</span>
            </div>
            <div class="data-row">
                <span class="data-label">TTF Natural Gas · front-month</span>
                <span class="data-value" style="color: var(--amber);">{ttf:.2f} €/MWh</span>
            </div>
            <div class="data-row">
                <span class="data-label">EUA Carbon · EUR/tCO₂</span>
                <span class="data-value" style="color: var(--purple);">{eua:.0f} €/t</span>
            </div>
            <div class="data-row">
                <span class="data-label">Confidence</span>
                <span class="data-value" style="color: var(--teal);">{confidence:.3f}</span>
            </div>
        </div>
    </div>
    '''

def metric_cards_html(metrics: List[Tuple[str, str, str]]) -> str:
    cards = ""
    for label, value, color in metrics:
        cards += f'''
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color: {color};">{value}</div>
        </div>
        '''
    return f'<div class="metric-grid">{cards}</div>'

# ── DATA LOADING ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data():
    pricer = None
    if PKL_PRICER.exists():
        with open(PKL_PRICER, "rb") as f:
            pricer = pickle.load(f)
    live = pd.read_pickle(PKL_LIVE) if PKL_LIVE.exists() else None
    return pricer, live

# ── PLOTLY CONFIG ────────────────────────────────────────────
def _fig(height: int = 280) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=C_SURFACE,
        height=height,
        font=dict(color=C_DIM, family="Inter, sans-serif", size=10),
        margin=dict(t=20, b=40, l=60, r=20),
        xaxis=dict(
            gridcolor=C_BORDER,
            linecolor=C_BORDER,
            tickcolor=C_BORDER,
            tickfont=dict(size=9, color=C_DIM),
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor=C_BORDER,
            linecolor=C_BORDER,
            tickcolor=C_BORDER,
            tickfont=dict(size=9, color=C_DIM),
            showgrid=True,
            zeroline=False,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=9, color=C_DIM),
            x=0, y=1.02,
            orientation="h",
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=C_CARD,
            bordercolor=C_BORDER,
            font=dict(color=C_TEXT, size=10, family="Inter, sans-serif"),
        ),
        xaxis_rangeslider_visible=False,
    )
    return fig

PLOTLY_CFG = {"displaylogo": False, "displayModeBar": False}

# ── CHART BUILDERS (simplified for brevity) ──────────────────
def chart_spot_vs_floor(live: pd.DataFrame) -> go.Figure:
    fig = _fig(height=300)
    fig.add_trace(go.Scatter(
        x=live.index, y=live["omie_price"],
        name="OMIE Spot", line=dict(color=C_AMBER, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=live.index, y=live["thermal_floor"],
        name="Thermal Floor", line=dict(color=C_TEAL, width=1.5, dash="dash"),
    ))
    fig.update_yaxes(title_text="EUR/MWh")
    return fig

def chart_floor_discount(live: pd.DataFrame) -> go.Figure:
    disc = live["floor_discount"]
    colors = [C_RED if v < 0 else C_GREEN for v in disc.values]
    fig = _fig(height=180)
    fig.add_trace(go.Bar(
        x=live.index, y=disc,
        marker_color=colors,
        name="Floor Discount",
    ))
    fig.add_hline(y=0, line_color=C_BORDER, line_width=1)
    fig.update_yaxes(title_text="EUR/MWh")
    return fig

# ── MAIN APPLICATION ─────────────────────────────────────────
inject_css()
pricer, live = load_data()

if pricer is None and live is None:
    st.error("No data available. Run the canonical notebook first.")
    st.stop()

# ── DERIVE STATE ─────────────────────────────────────────────
if live is not None:
    last_spot = float(live["omie_price"].dropna().iloc[-1])
    last_regime = str(live["regime"].dropna().iloc[-1])
    last_rsi = float(live["rsi"].dropna().iloc[-1])
    last_discount = float(live["floor_discount"].dropna().iloc[-1])
    floor_proxy = float(live["thermal_floor"].iloc[-1])
    live_ttf = float(live["ttf"].iloc[-1]) if "ttf" in live.columns else 35.0
    live_eua = float(live["eua"].iloc[-1]) if "eua" in live.columns else 65.0
    data_source = "ESIOS LIVE"
else:
    last_spot = pricer["last_spot"]
    last_regime = "Thermal-Marginal"
    last_rsi = 0.0
    last_discount = pricer["price_vs_floor"]
    floor_proxy = pricer["floor_proxy"]
    live_ttf = 35.0
    live_eua = 65.0
    data_source = "CACHED"

# Execution
sig = None
if EXEC_OK and live is not None:
    sig = signal_from_live(live, pricer)
    cur_dir = sig.direction
    cur_conf = sig.confidence
else:
    cur_dir = "—"
    cur_conf = 0.0

# ── RENDER UI ────────────────────────────────────────────────
_html(header_bar(data_source, str(live.index[-1].date()) if live is not None else "—"))

# Ticker
disc_color = C_RED if last_discount < 0 else C_GREEN
sig_arrow = {"SHORT": "▼", "LONG": "▲", "NEUTRAL": "—"}.get(cur_dir, "—")

ticker_items = [
    ("OMIE Spot", f"{last_spot:.2f} €/MWh", C_AMBER),
    ("Regime", last_regime, {"Renewable-Dom.": C_GREEN, "Demand-Stress": C_RED}.get(last_regime, C_AMBER)),
    ("Floor Disc", f"{last_discount:+.2f}", disc_color),
    ("Signal", f"{sig_arrow} {cur_dir}", {"LONG": C_GREEN, "SHORT": C_RED}.get(cur_dir, C_DIM)),
    ("RSI", f"{last_rsi:.3f}", C_TEAL),
    ("ATC", f"{float(live['atc_es_fr'].iloc[-1]):.0f} MW" if live is not None and "atc_es_fr" in live.columns else "—", C_BLUE),
]
_html(ticker_bar(ticker_items))

# Content
_html('<div class="content-area">')

# Signal Card + Metrics
col1, col2 = st.columns([1.5, 1], gap="large")

with col1:
    _html(signal_card_html(
        regime=last_regime,
        direction=cur_dir if sig else "NEUTRAL",
        confidence=cur_conf,
        spot=last_spot,
        floor_proxy=floor_proxy,
        discount=last_discount,
        rsi=last_rsi,
        ttf=live_ttf,
        eua=live_eua
    ))

with col2:
    _html(section_header("Key Metrics"))
    metrics = [
        ("OMIE Spot", f"{last_spot:.0f} €", C_AMBER),
        ("Thermal Floor", f"{floor_proxy:.2f} €", C_BLUE),
        ("Floor Discount", f"{last_discount:+.2f} €", disc_color),
        ("TTF Gas", f"{live_ttf:.2f} €", C_AMBER),
        ("EUA Carbon", f"{live_eua:.0f} €", C_PURPLE),
        ("Confidence", f"{cur_conf:.3f}", C_TEAL),
    ]
    _html(metric_cards_html(metrics))

# Tabs
tabs = st.tabs(["Charts", "Analysis", "Execution", "Readiness"])

with tabs[0]:
    _html('<div style="padding: 32px;">')
    if live is not None:
        col1, col2 = st.columns(2, gap="large")
        with col1:
            _html(section_header("OMIE Spot vs Thermal Floor"))
            st.plotly_chart(chart_spot_vs_floor(live), use_container_width=True, config=PLOTLY_CFG)
        with col2:
            _html(section_header("Floor Discount"))
            st.plotly_chart(chart_floor_discount(live), use_container_width=True, config=PLOTLY_CFG)
    _html('</div>')

with tabs[1]:
    _html('<div style="padding: 32px;">')
    _html(section_header("Signal Details"))
    if sig:
        st.write(f"**Regime:** {sig.regime}")
        st.write(f"**Direction:** {sig.direction}")
        st.write(f"**Confidence:** {sig.confidence:.3f}")
    _html('</div>')

with tabs[2]:
    _html('<div style="padding: 32px;">')
    _html(section_header("Execution"))
    if sig and EXEC_OK:
        st.write(f"Signal: {sig.direction} with confidence {sig.confidence:.3f}")
    _html('</div>')

with tabs[3]:
    _html('<div style="padding: 32px;">')
    _html(section_header("System Status"))
    st.write("All systems operational")
    _html('</div>')

_html('</div>')
# Add this to your tabs list: tabs = st.tabs(["Charts", "Pricer", "Execution", "Readiness"])

with tabs[1]: # Pricer
    _html('<div class="content-area">')
    if pricer:
        col1, col2 = st.columns(2, gap="large")
        shift = pricer["shift_constant"]

        with col1:
            _html('<div class="card">')
            _html('<div class="section-header">Pricing Parameters</div>')
            
            # Build clean data rows instead of a raw dataframe
            params = [
                ("Last Spot F", f"{pricer['last_spot']:.4f} EUR/MWh"),
                ("Strike K (ATM)", f"{pricer['strike']:.4f} EUR/MWh"),
                ("Shift Constant", f"{shift:.4f} EUR/MWh"),
                ("Shifted F", f"{pricer['last_spot']+shift:.4f} EUR/MWh"),
                ("Ann. Vol σ", f"{pricer['sigma']*100:.2f}%"),
                ("T (years)", f"{pricer['T']:.6f}"),
                ("Risk-free r", f"{pricer['r']:.2%}"),
                ("Black-76 Call", f"{b76_call:.4f} EUR/MWh"),
                ("MC Call", f"{mc_call:.4f} EUR/MWh"),
                ("MC Std Error", f"{mc_se:.4f} EUR/MWh"),
                ("Spike Prob", f"{spike_prob:.4f}"),
                ("Neg. Price Prob", f"{neg_prob:.4f}"),
            ]
            
            for label, value in params:
                _html(f'''
                <div class="data-row">
                    <span class="data-label">{label}</span>
                    <span class="data-value">{value}</span>
                </div>
                ''')
            _html('</div>')

        with col2:
            _html('<div class="card">')
            _html('<div class="section-header">MC Payoff Distribution</div>')
            
            # Calculate ITM paths for the caption
            np.random.seed(42)
            F_s = pricer["last_spot"] + shift
            Z = np.random.standard_normal(10_000)
            ST = F_s * np.exp((pricer["r"] - 0.5*pricer["sigma"]**2) * pricer["T"] 
                              + pricer["sigma"] * np.sqrt(pricer["T"]) * Z) - shift
            payoffs = np.maximum(ST - pricer["strike"], 0.0)
            nonzero = payoffs[payoffs > 0]
            
            st.caption(f"ITM: {len(nonzero):,} of 10,000 ({len(nonzero)/100:.1f}%)")
            st.plotly_chart(chart_mc_payoff(pricer), use_container_width=True, config=PLOTLY_CFG)
            _html('</div>')
    else:
        st.warning("Pricer pickle not found.")
    _html('</div>')

    with tabs[2]: # Execution
    _html('<div class="content-area">')
    if not EXEC_OK:
        st.warning("Execution module not available. Run `pip install -e src/` in the repo root.")
    elif live is None:
        st.warning("ESIOS live data required for signal derivation.")
    else:
        col1, col2 = st.columns([1, 2], gap="large")

        with col1:
            _html('<div class="card signal-card">')
            _html('<div class="section-header">Current Signal</div>')

            dir_color = direction_color(sig.direction)
            dir_arrow = {"SHORT": "▼", "LONG": "▲", "NEUTRAL": "—"}.get(sig.direction, "—")
            
            # Big signal display
            _html(f'''
            <div style="text-align: center; margin: 24px 0;">
                <div class="signal-direction {sig.direction.lower()}" style="color: {dir_color};">
                    {dir_arrow} {sig.direction}
                </div>
                <div style="font-size: 12px; color: var(--dim); margin-top: 8px;">
                    conf {sig.confidence:.3f} | {sig.regime}
                </div>
                <div style="font-family: var(--mono); font-size: 10px; color: var(--muted); margin-top: 4px;">
                    {sig.timestamp.strftime('%H:%M:%S')} {sig.source}
                </div>
            </div>
            ''')

            _html('<div class="section-header" style="margin-top: 24px;">Guardrail Checks</div>')
            for label, passed in guardrails.status_lines(sig):
                icon = "✓" if passed else "✗"
                color = "var(--green)" if passed else "var(--red)"
                _html(f'''
                <div class="data-row">
                    <span style="color: {color}; font-weight: 700; margin-right: 8px;">{icon}</span>
                    <span class="data-label">{label}</span>
                </div>
                ''')

            st.markdown("<br>", unsafe_allow_html=True)

            overall = guardrails.check(sig)
            if overall.passed:
                if st.button("SUBMIT PAPER TRADE", use_container_width=True):
                    result = router.route(sig)
                    if result.order:
                        st.session_state["last_order"] = result.order
                        st.success(f"{result.order.order_id} — {result.order.message}")
                    else:
                        st.error(f"BLOCKED: {result.guardrail.reason}")
            else:
                st.markdown(
                    f'<div style="color: var(--red); padding: 12px; border: 1px solid var(--red); '
                    f'border-radius: 6px; text-align: center; font-size: 11px;">'
                    f'BLOCKED: {overall.reason}</div>',
                    unsafe_allow_html=True,
                )
            _html('</div>')

        with col2:
            # Signal Details Card
            _html('<div class="card">')
            _html('<div class="section-header">Signal Detail</div>')
            
            details = [
                ("SPOT", f"{sig.spot:.4f} EUR/MWh", "var(--amber)"),
                ("FLOOR DISC", f"{sig.floor_discount:+.4f}", disc_color),
                ("RSI", f"{sig.rsi:.4f}", "var(--teal)"),
                ("SPIKE PROB", f"{sig.spike_prob:.4f}", "var(--dim)"),
                ("NEG PX PROB", f"{sig.neg_price_prob:.4f}", "var(--dim)"),
            ]
            for label, value, color in details:
                _html(f'''
                <div class="data-row">
                    <span class="data-label">{label}</span>
                    <span class="data-value" style="color: {color};">{value}</span>
                </div>
                ''')
            _html('</div>')

            # Blotter Card
            st.markdown("<br>", unsafe_allow_html=True)
            _html('<div class="card">')
            _html('<div class="section-header">Paper Trade Blotter</div>')

            blotter = paper.load_blotter()
            if not blotter:
                st.caption("No paper trades yet.")
            else:
                # Custom HTML table for the blotter to match the new design
                header = '''
                <div style="display: grid; grid-template-columns: 1fr 80px 100px 100px 80px 100px; 
                            padding: 8px 12px; border-bottom: 1px solid var(--border); 
                            font-size: 9px; font-weight: 600; color: var(--dim); 
                            text-transform: uppercase; letter-spacing: 0.08em;">
                    <span>Timestamp</span><span>Dir</span><span>Fill</span>
                    <span>Disc</span><span>Conf</span><span>Order ID</span>
                </div>
                '''
                rows_html = ""
                for i, rec in enumerate(blotter[:50]):
                    bg = "var(--surface)" if i % 2 == 0 else "transparent"
                    d_color = "var(--red)" if rec["direction"] == "SHORT" else "var(--green)"
                    rows_html += f'''
                    <div style="display: grid; grid-template-columns: 1fr 80px 100px 100px 80px 100px; 
                                padding: 8px 12px; background: {bg}; 
                                border-bottom: 1px solid var(--border); font-size: 11px; 
                                font-family: var(--mono);">
                        <span style="color: var(--dim);">{rec["timestamp"][:19]}</span>
                        <span style="color: {d_color}; font-weight: 700;">{rec["direction"]}</span>
                        <span style="color: var(--amber);">{rec["fill_price"]:.2f} €</span>
                        <span style="color: var(--dim);">{rec["floor_discount"]:+.2f}</span>
                        <span style="color: var(--dim);">{rec["confidence"]:.2f}</span>
                        <span style="color: var(--teal);">{rec["order_id"]}</span>
                    </div>
                    '''
                _html(f'<div style="border: 1px solid var(--border); border-radius: 6px; overflow: hidden;">{header}{rows_html}</div>')
            _html('</div>')

    _html('</div>')