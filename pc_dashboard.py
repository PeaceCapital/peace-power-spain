"""
Peace* Energy — Iberia Signal Engine
Bloomberg terminal-style dashboard.
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

# ── CONFIG ────────────────────────────────────────────────────
PKL_PRICER = Path("pc_spot_pricer_real_v2.pkl")
PKL_LIVE   = Path("pc_live_esios.pkl")
LOG_PATH   = Path("state/paper_trades.jsonl")

# ── PALETTE ───────────────────────────────────────────────────
C_BG      = "#090909"
C_SURFACE = "#0d0d0d"
C_BORDER  = "#1a1a1a"
C_BORDER2 = "#242424"
C_TEXT    = "#d8d8d8"
C_DIM     = "#555555"
C_DIM2    = "#888888"
C_AMBER   = "#f5a623"
C_AMBER2  = "#c47e10"
C_GREEN   = "#26c281"
C_RED     = "#e74c3c"
C_TEAL    = "#00b8a9"
C_BLUE    = "#3a8fd1"

# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(
    page_title="Peace* Energy | Iberia Signal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── GLOBAL CSS ────────────────────────────────────────────────
HV = '"Helvetica Neue", Helvetica, Arial, sans-serif'

def inject_css() -> None:
    st.markdown("""
    <style>
    html, body, [class*="css"] { background: #090909 !important; }
    .stApp { background: #090909 !important; }

    #MainMenu, footer, header { display: none !important; }
    [data-testid="stSidebar"]        { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }

    .block-container { padding: 0 !important; max-width: 100% !important; }
    .main > div { padding: 0 !important; }

    body, p, span, div, li {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-weight: 300;
        color: #d8d8d8;
        -webkit-font-smoothing: antialiased;
    }

    /* Tabs — title case, bold, no numbers */
    .stTabs [data-baseweb="tab-list"] {
        background: #090909; border-bottom: 1px solid #1a1a1a; gap: 0; padding: 0 24px;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-size: 12px; font-weight: 700; letter-spacing: 0.02em; text-transform: none;
        color: #444444; background: transparent; border-bottom: 2px solid transparent;
        padding: 11px 20px; margin: 0;
    }
    .stTabs [aria-selected="true"] {
        color: #f5a623 !important; border-bottom: 2px solid #f5a623 !important; background: transparent !important;
    }
    .stTabs [data-baseweb="tab-panel"] { padding: 0 !important; background: #090909; }

    .stButton > button {
        background: transparent; border: 1px solid #f5a623; color: #f5a623;
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
        padding: 8px 20px; border-radius: 0; transition: background 0.15s;
    }
    .stButton > button:hover { background: rgba(245,166,35,0.08); }

    .stDataFrame { background: #0d0d0d !important; }
    [data-testid="stDataFrame"] { border: 1px solid #1a1a1a !important; border-radius: 0 !important; }

    .stSuccess { background: rgba(38,194,129,0.08); border-left: 3px solid #26c281; border-radius: 0; }
    .stError   { background: rgba(231,76,60,0.08);  border-left: 3px solid #e74c3c; border-radius: 0; }
    .stWarning { background: rgba(245,166,35,0.08); border-left: 3px solid #f5a623; border-radius: 0; }

    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: #090909; }
    ::-webkit-scrollbar-thumb { background: #1f1f1f; }

    .tab-content { padding: 24px 28px; }

    /* Scrolling ticker */
    @keyframes pc-ticker {
        0%   { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    .pc-ticker-track {
        display: inline-flex;
        animation: pc-ticker 38s linear infinite;
        white-space: nowrap;
        align-items: center;
    }
    .pc-ticker-track:hover { animation-play-state: paused; }
    </style>
    """, unsafe_allow_html=True)


# ── TOKEN ─────────────────────────────────────────────────────
def load_token() -> str | None:
    try:
        return st.secrets["ESIOS_TOKEN"]
    except Exception:
        pass
    token = os.environ.get("ESIOS_TOKEN")
    if token:
        return token
    env_path = Path(__file__).parent / ".env"
    try:
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "ESIOS_TOKEN":
                    return v.strip()
    except FileNotFoundError:
        pass
    return None


# ── DATA ──────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data():
    pricer = None
    if PKL_PRICER.exists():
        with open(PKL_PRICER, "rb") as f:
            pricer = pickle.load(f)
    live = pd.read_pickle(PKL_LIVE) if PKL_LIVE.exists() else None
    return pricer, live


# ── PLOTLY BASE ───────────────────────────────────────────────
def _fig(height: int = 260) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=C_BG,
        plot_bgcolor=C_SURFACE,
        height=height,
        font=dict(color=C_DIM2, family="Helvetica Neue, Helvetica, Arial, sans-serif", size=9),
        margin=dict(t=20, b=28, l=52, r=16),
        xaxis=dict(
            gridcolor=C_BORDER,
            linecolor=C_BORDER2,
            tickcolor=C_BORDER2,
            tickfont=dict(size=8, color=C_DIM),
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor=C_BORDER,
            linecolor=C_BORDER2,
            tickcolor=C_BORDER2,
            tickfont=dict(size=8, color=C_DIM),
            showgrid=True,
            zeroline=False,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=8, color=C_DIM2),
            x=0, y=1.02,
            orientation="h",
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#141414",
            bordercolor=C_BORDER2,
            font=dict(color=C_TEXT, size=9, family="Helvetica Neue, Helvetica, Arial, sans-serif"),
        ),
        xaxis_rangeslider_visible=False,
    )
    return fig

PLOTLY_CFG = {"displaylogo": False, "displayModeBar": False}


# ── HTML COMPONENTS ───────────────────────────────────────────
def _html(content: str) -> None:
    st.markdown(content, unsafe_allow_html=True)


def terminal_header(data_source: str, last_dt: str) -> str:
    now = datetime.now().strftime("%d %b %Y  %H:%M")
    live_color = C_GREEN if data_source == "ESIOS LIVE" else C_AMBER
    F = "'Helvetica Neue',Helvetica,Arial,sans-serif"
    return (
        f'<div style="background:{C_BG};border-bottom:1px solid {C_BORDER2};padding:13px 28px 11px;display:flex;justify-content:space-between;align-items:center;">'
        f'<div style="display:flex;align-items:center;gap:18px;">'
        f'<span style="font-family:{F};font-size:21px;font-weight:700;letter-spacing:-0.02em;color:#ffffff;">'
        f'Peace<span style="color:{C_AMBER};font-weight:700;">*</span>'
        f'<span style="font-weight:300;color:#aaaaaa;"> Capital</span>'
        f'</span>'
        f'<span style="color:{C_BORDER2};">|</span>'
        f'<span style="font-family:{F};font-size:12px;font-weight:300;color:{C_DIM2};">Iberia Signal Engine</span>'
        f'<span style="color:{C_BORDER2};">|</span>'
        f'<span style="font-family:{F};font-size:11px;font-weight:600;letter-spacing:0.06em;color:{live_color};">● {data_source}</span>'
        f'</div>'
        f'<div style="font-family:{F};font-size:10px;font-weight:300;color:{C_DIM};text-align:right;line-height:1.7;">'
        f'<div style="font-weight:500;color:{C_DIM2};">{now}</div>'
        f'<div>REF PC-NRG-2026</div>'
        f'</div></div>'
    )


def ticker_bar(items: list[tuple[str, str, str]]) -> str:
    """Scrolling exchange-style ticker. items = [(label, value, color), ...]"""
    F = "'Helvetica Neue',Helvetica,Arial,sans-serif"
    sep = f'<span style="font-family:{F};color:#2a2a2a;font-size:14px;padding:0 18px;">◆</span>'

    def item_html(label: str, value: str, color: str) -> str:
        return (
            f'<span style="display:inline-flex;align-items:baseline;gap:7px;">'
            f'<span style="font-family:{F};font-size:9px;font-weight:400;letter-spacing:0.14em;text-transform:uppercase;color:#555555;">{label}</span>'
            f'<span style="font-family:{F};font-size:13px;font-weight:700;color:{color};">{value}</span>'
            f'</span>'
        )

    # Build one pass of all items
    single = sep.join(item_html(l, v, c) for l, v, c in items)
    # Duplicate for seamless loop
    content = f'{single}{sep}{single}{sep}'

    return (
        f'<div style="background:linear-gradient(90deg,#0c0c0a 0%,#0a0c0c 50%,#0c0a0c 100%);'
        f'border-bottom:1px solid #1e1e1e;border-top:1px solid #1a1a1a;'
        f'overflow:hidden;height:34px;display:flex;align-items:center;'
        f'padding-left:16px;">'
        f'<div class="pc-ticker-track">{content}</div>'
        f'</div>'
    )


def kpi_strip(items: list[tuple[str, str, str]]) -> str:
    F = HV
    cells = ""
    for i, (label, value, color) in enumerate(items):
        bl = f"border-left:1px solid {C_BORDER2};" if i > 0 else ""
        cells += (
            f'<div style="flex:1;padding:14px 20px;{bl}">'
            f'<div style="font-family:{F};font-size:9px;font-weight:300;letter-spacing:0.16em;text-transform:uppercase;color:{C_DIM};margin-bottom:7px;">{label}</div>'
            f'<div style="font-family:{F};font-size:17px;font-weight:700;letter-spacing:-0.02em;color:{color};line-height:1;white-space:nowrap;">{value}</div>'
            f'</div>'
        )
    return f'<div style="display:flex;background:{C_SURFACE};border-bottom:2px solid {C_BORDER2};">{cells}</div>'


def section_header(text: str) -> str:
    F = HV
    return (
        f'<div style="font-family:{F};font-size:9px;font-weight:700;letter-spacing:0.18em;'
        f'text-transform:uppercase;color:{C_AMBER};padding-bottom:8px;'
        f'border-bottom:1px solid {C_BORDER};margin-bottom:16px;">{text}</div>'
    )


def signal_readout_row(label: str, value: str, color: str = C_TEXT, note: str = "") -> str:
    F = HV
    return (
        f'<div style="padding:10px 0;border-bottom:1px solid {C_BORDER};display:flex;justify-content:space-between;align-items:baseline;">'
        f'<div>'
        f'<div style="font-family:{F};font-size:9px;font-weight:300;letter-spacing:0.14em;text-transform:uppercase;color:{C_DIM};margin-bottom:3px;">{label}</div>'
        f'<div style="font-family:{F};font-size:16px;font-weight:700;color:{color};line-height:1;">{value}</div>'
        f'</div>'
        f'<div style="font-family:{F};font-size:10px;font-weight:300;color:{C_DIM};text-align:right;">{note}</div>'
        f'</div>'
    )


def guardrail_row(label: str, passed: bool) -> str:
    icon  = "✓" if passed else "✗"
    color = C_GREEN if passed else C_RED
    F = "font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;"
    return (
        f'<div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid {C_BORDER};">'
        f'<span style="{F}font-size:12px;color:{color};font-weight:700;">{icon}</span>'
        f'<span style="{F}font-size:11px;font-weight:300;color:{C_DIM2};">{label}</span>'
        f'</div>'
    )


def blotter_row(rec: dict, i: int) -> str:
    d_color = C_RED if rec["direction"] == "SHORT" else (C_GREEN if rec["direction"] == "LONG" else C_DIM)
    bg = C_SURFACE if i % 2 == 0 else C_BG
    F = "font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;"
    return (
        f'<div style="display:grid;grid-template-columns:160px 70px 90px 90px 70px 80px;padding:8px 12px;background:{bg};border-bottom:1px solid {C_BORDER};">'
        f'<span style="{F}font-size:9px;font-weight:300;color:{C_DIM2};">{rec["timestamp"][:19]}</span>'
        f'<span style="{F}font-size:10px;font-weight:700;color:{d_color};">{rec["direction"]}</span>'
        f'<span style="{F}font-size:10px;font-weight:700;color:{C_AMBER};">{rec["fill_price"]:.2f} €/MWh</span>'
        f'<span style="{F}font-size:10px;font-weight:300;color:{C_DIM2};">{rec["floor_discount"]:+.2f} disc</span>'
        f'<span style="{F}font-size:10px;font-weight:300;color:{C_DIM2};">{rec["confidence"]:.2f} conf</span>'
        f'<span style="{F}font-size:9px;font-weight:300;color:{C_TEAL};">{rec["order_id"]}</span>'
        f'</div>'
    )


# ── NEWS FEED ─────────────────────────────────────────────────
_NEWS_UA = {"User-Agent": "Mozilla/5.0 (compatible; PeaceCapital/1.0)"}
_GN_BASE = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q="

_NEWS_TOPICS: list[tuple[str, str, str]] = [
    ("Oil & Gas",   "TTF+natural+gas+LNG+oil+energy+europe+spain",         C_AMBER),
    ("Renewables",  "solar+wind+renewable+energy+europe+spain+offshore",    C_GREEN),
    ("BESS",        "battery+energy+storage+BESS+grid+lithium",             C_TEAL),
    ("Nuclear",     "nuclear+energy+power+plant+europe+spain+SMR",          C_BLUE),
]


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news(query: str, max_items: int = 7) -> list[dict]:
    """Pull up to max_items headlines from Google News RSS for the given query."""
    import requests as _req
    try:
        r = _req.get(_GN_BASE + query, headers=_NEWS_UA, timeout=10)
        r.raise_for_status()
        root = _ET.fromstring(r.content)
        channel = root.find("channel")
        items: list[dict] = []
        for el in (channel.findall("item") if channel is not None else [])[:max_items]:
            title = (el.findtext("title") or "").strip()
            link  = (el.findtext("link")  or "#").strip()
            pub   = el.findtext("pubDate") or ""
            src_el = el.find("source")
            source = src_el.text.strip() if src_el is not None and src_el.text else "—"
            try:
                dt    = parsedate_to_datetime(pub)
                delta = datetime.now(timezone.utc) - dt
                hrs   = int(delta.total_seconds() / 3600)
                ago   = f"{int(delta.total_seconds()/60)}m" if hrs < 1 else (f"{hrs}h" if hrs < 24 else f"{hrs//24}d")
            except Exception:
                ago = "—"
            if " - " in title:
                title = title.rsplit(" - ", 1)[0].strip()
            items.append({"title": title, "link": link, "source": source, "ago": ago})
        return items
    except Exception:
        return []


def _news_panel(items: list[dict], color: str) -> str:
    F = HV
    if not items:
        return f'<div style="font-family:{F};font-size:10px;color:{C_DIM};padding:16px 0;">Feed unavailable</div>'
    out = ""
    for i, it in enumerate(items):
        bl = f"border-top:1px solid {C_BORDER};" if i > 0 else ""
        src = it["source"].upper()[:30]
        out += (
            f'<div style="{bl}padding:10px 0;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">'
            f'<span style="font-family:{F};font-size:8px;font-weight:700;letter-spacing:0.11em;color:{color};">{src}</span>'
            f'<span style="font-family:{F};font-size:8px;color:{C_DIM};">{it["ago"]}</span>'
            f'</div>'
            f'<a href="{it["link"]}" target="_blank" rel="noopener noreferrer" '
            f'style="font-family:{F};font-size:11px;font-weight:300;color:{C_TEXT};'
            f'text-decoration:none;line-height:1.45;display:block;">{it["title"]}</a>'
            f'</div>'
        )
    return out


# ── CHART BUILDERS ────────────────────────────────────────────
def chart_spot_vs_floor(live: pd.DataFrame) -> go.Figure:
    fig = _fig(height=300)
    fig.add_trace(go.Scatter(
        x=live.index, y=live["omie_price"],
        name="OMIE Spot", line=dict(color=C_AMBER, width=1.5),
        hovertemplate="%{y:.2f} €",
    ))
    fig.add_trace(go.Scatter(
        x=live.index, y=live["thermal_floor"],
        name="Thermal Floor", line=dict(color=C_TEAL, width=1, dash="dot"),
        hovertemplate="%{y:.2f} €",
    ))
    # fill when spot < floor
    fig.add_trace(go.Scatter(
        x=live.index, y=live["thermal_floor"],
        fill=None, line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=live.index, y=live["omie_price"],
        fill="tonexty",
        fillcolor="rgba(231,76,60,0.06)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip",
    ))
    fig.update_yaxes(title_text="EUR/MWh", title_font=dict(size=8, color=C_DIM))
    return fig


def chart_floor_discount(live: pd.DataFrame) -> go.Figure:
    disc = live["floor_discount"]
    colors = [C_RED if v < 0 else C_GREEN for v in disc.values]
    fig = _fig(height=160)
    fig.add_trace(go.Bar(
        x=live.index, y=disc,
        marker_color=colors,
        name="Floor Discount",
        hovertemplate="%{y:.2f} €",
    ))
    fig.add_hline(y=0, line_color=C_BORDER2, line_width=1)
    fig.update_yaxes(title_text="EUR/MWh", title_font=dict(size=8, color=C_DIM))
    return fig


def chart_generation(live: pd.DataFrame) -> go.Figure:
    fig = _fig(height=300)
    traces = [
        ("gen_wind",          "Wind",           "#3a8fd1", "rgba(58,143,209,0.5)"),
        ("gen_solar_pv",      "Solar PV",       C_AMBER,   "rgba(245,166,35,0.5)"),
        ("gen_solar_thermal", "Solar Thermal",  "#e67e22", "rgba(230,126,34,0.5)"),
        ("gen_hydro",         "Hydro",          C_TEAL,    "rgba(0,184,169,0.5)"),
        ("gen_nuclear",       "Nuclear",        "#9b59b6", "rgba(155,89,182,0.5)"),
    ]
    for col, name, color, fillcolor in traces:
        if col in live.columns:
            fig.add_trace(go.Scatter(
                x=live.index, y=live[col],
                name=name,
                stackgroup="gen",
                fillcolor=fillcolor,
                line=dict(color=color, width=0.5),
                hovertemplate=f"{name}: %{{y:,.0f}} MWh/h",
            ))
    fig.update_yaxes(title_text="MWh/h", title_font=dict(size=8, color=C_DIM))
    return fig


def chart_demand_vs_renew(live: pd.DataFrame) -> go.Figure:
    fig = _fig(height=260)
    if "demand_forecast" in live.columns:
        fig.add_trace(go.Scatter(
            x=live.index, y=live["demand_forecast"],
            name="Demand Forecast", line=dict(color=C_RED, width=1.5),
            hovertemplate="%{y:,.0f} MWh/h",
        ))
    if "gen_renewable" in live.columns:
        fig.add_trace(go.Scatter(
            x=live.index, y=live["gen_renewable"],
            name="Renewable Gen", line=dict(color=C_GREEN, width=1.5),
            hovertemplate="%{y:,.0f} MWh/h",
        ))
    fig.update_yaxes(title_text="MWh/h", title_font=dict(size=8, color=C_DIM))
    return fig


def chart_rsi(live: pd.DataFrame) -> go.Figure:
    fig = _fig(height=160)
    fig.add_trace(go.Scatter(
        x=live.index, y=live["rsi"],
        name="RSI", line=dict(color=C_TEAL, width=1.5),
        fill="tozeroy", fillcolor="rgba(0,184,169,0.06)",
        hovertemplate="RSI: %{y:.4f}",
    ))
    fig.add_hline(y=0.6, line_color=C_RED,   line_width=0.6, line_dash="dot",
                  annotation_text="Renewable threshold", annotation_font_size=8,
                  annotation_font_color=C_DIM)
    fig.update_yaxes(title_text="RSI", title_font=dict(size=8, color=C_DIM))
    return fig


def chart_atc(live: pd.DataFrame) -> go.Figure:
    fig = _fig(height=160)
    if "atc_es_fr" in live.columns:
        vals = live["atc_es_fr"]
        fig.add_trace(go.Scatter(
            x=live.index, y=vals,
            name="ATC ES→FR", line=dict(color=C_BLUE, width=1.5),
            fill="tozeroy", fillcolor="rgba(58,143,209,0.06)",
            hovertemplate="ATC: %{y:.0f} MW",
        ))
        fig.add_hline(y=0, line_color=C_BORDER2, line_width=1)
    fig.update_yaxes(title_text="MW", title_font=dict(size=8, color=C_DIM))
    return fig


def chart_rolling_vol(spot_series: pd.Series, vol_annual: float) -> go.Figure:
    spot_pos = spot_series[spot_series > 0]
    log_ret  = np.log(spot_pos).diff().dropna()
    z        = (log_ret - log_ret.mean()) / log_ret.std()
    ret_clean = log_ret[z.abs() < 4]
    rolling   = ret_clean.rolling(30 * 24).std() * np.sqrt(8760) * 100
    rolling   = rolling.dropna()

    fig = _fig(height=260)
    fig.add_trace(go.Scatter(
        x=rolling.index, y=rolling.values,
        name="30d Rolling Vol (%)",
        line=dict(color=C_AMBER, width=1.5),
        fill="tozeroy", fillcolor="rgba(245,166,35,0.05)",
        hovertemplate="Vol: %{y:.2f}%",
    ))
    fig.add_hline(y=vol_annual * 100, line_color=C_TEAL, line_width=0.8, line_dash="dash",
                  annotation_text="Current", annotation_font_size=8,
                  annotation_font_color=C_DIM)
    fig.update_yaxes(title_text="Ann. Vol %", title_font=dict(size=8, color=C_DIM))
    return fig


def chart_mc_payoff(pricer: dict) -> go.Figure:
    shift = pricer["shift_constant"]
    F_s   = pricer["last_spot"] + shift
    K_s   = pricer["strike"]    + shift
    T, r, sigma = pricer["T"], pricer["r"], pricer["sigma"]

    np.random.seed(42)
    Z       = np.random.standard_normal(10_000)
    ST_real = F_s * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z) - shift
    payoffs = np.maximum(ST_real - pricer["strike"], 0.0)
    nonzero = payoffs[payoffs > 0]

    counts, edges = np.histogram(nonzero, bins=30)
    midpoints = 0.5 * (edges[:-1] + edges[1:])

    fig = _fig(height=280)
    fig.add_trace(go.Bar(
        x=midpoints, y=counts,
        name="Payoff dist.",
        marker_color=C_AMBER,
        marker_opacity=0.7,
        hovertemplate="Payoff ~%{x:.1f}: %{y} paths",
    ))
    fig.update_xaxes(title_text="Payoff (EUR/MWh)", title_font=dict(size=8, color=C_DIM))
    fig.update_yaxes(title_text="Paths", title_font=dict(size=8, color=C_DIM))
    return fig


# ── REGIME ────────────────────────────────────────────────────
def regime_color(r: str) -> str:
    return {
        "Demand-Stress":    C_RED,
        "Renewable-Dom.":   C_GREEN,
        "Thermal-Marginal": C_AMBER,
    }.get(r, C_DIM)


def direction_color(d: str) -> str:
    return {
        "SHORT":   C_RED,
        "LONG":    C_GREEN,
        "NEUTRAL": C_DIM,
    }.get(d, C_DIM)


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
inject_css()

pricer, live = load_data()

if pricer is None and live is None:
    st.error("No data. Run the canonical notebook first.")
    st.stop()

# ── DERIVE STATE ──────────────────────────────────────────────
if live is not None:
    last_spot     = float(live["omie_price"].dropna().iloc[-1])
    last_regime   = str(live["regime"].dropna().iloc[-1])
    last_rsi      = float(live["rsi"].dropna().iloc[-1])
    last_discount = float(live["floor_discount"].dropna().iloc[-1])
    floor_proxy   = float(live["thermal_floor"].iloc[-1])
    live_ttf      = float(live["ttf"].iloc[-1]) if "ttf" in live.columns else 35.0
    live_eua      = float(live["eua"].iloc[-1]) if "eua" in live.columns else 65.0
    data_source   = "ESIOS LIVE"
    last_dt       = str(live.index[-1].date())
else:
    last_spot     = pricer["last_spot"]
    last_regime   = "Thermal-Marginal"
    last_rsi      = 0.0
    last_discount = pricer["price_vs_floor"]
    floor_proxy   = pricer["floor_proxy"]
    live_ttf      = 35.0
    live_eua      = 65.0
    data_source   = "CACHED"
    last_dt       = "—"

if pricer:
    vol_annual = pricer["annualised_vol"]
    b76_call   = pricer["black76_call"]
    mc_call    = pricer["mc_call"]
    mc_se      = pricer["mc_se"]
    spike_prob = pricer["spike_prob"]
    neg_prob   = pricer["neg_price_prob"]
    spot_series = pricer["spot"]
else:
    vol_annual = b76_call = mc_call = mc_se = spike_prob = neg_prob = 0.0
    spot_series = None

# ── EXECUTION SETUP ───────────────────────────────────────────
sig = None
if EXEC_OK and live is not None:
    sig        = signal_from_live(live, pricer)
    paper      = PaperAdapter(log_path=LOG_PATH)
    guardrails = GuardrailEngine(log_path=LOG_PATH)
    router     = ExecutionRouter(adapter=paper, guardrails=guardrails)
    cur_dir    = sig.direction
    cur_conf   = sig.confidence
else:
    cur_dir  = "—"
    cur_conf = 0.0

# ── HEADER ────────────────────────────────────────────────────
_html(terminal_header(data_source, last_dt))

# ── TICKER BAR ────────────────────────────────────────────────
disc_color = C_RED if last_discount < 0 else C_GREEN
sig_arrow  = {"SHORT": "▼", "LONG": "▲", "NEUTRAL": "—"}.get(cur_dir, "—")
atc_val    = float(live["atc_es_fr"].dropna().iloc[-1]) if live is not None and "atc_es_fr" in live.columns else 0.0

ticker_items = [
    ("OMIE Spot",     f"{last_spot:.2f} €/MWh",           C_AMBER),
    ("Regime",        last_regime,                         regime_color(last_regime)),
    ("RSI",           f"{last_rsi:.4f}",                   C_TEAL),
    ("Floor Disc",    f"{last_discount:+.2f} €/MWh",       disc_color),
    ("Signal",        f"{sig_arrow} {cur_dir}  {cur_conf:.2f}", direction_color(cur_dir)),
    ("Ann Vol",       f"{vol_annual*100:.1f}%",            "#a0a0a0"),
    ("B76 Call",      f"{b76_call:.2f} €",                 "#a0a0a0"),
    ("MC Call",       f"{mc_call:.2f} €",                  "#a0a0a0"),
    ("Spike Prob",    f"{spike_prob:.4f}",                  C_AMBER2 if spike_prob > 0.1 else "#a0a0a0"),
    ("Floor",         f"{floor_proxy:.2f} €/MWh",          "#a0a0a0"),
    ("ATC ES→FR",     f"{atc_val:.0f} MW",                 C_BLUE),
]
_html(ticker_bar(ticker_items))

# ── KPI STRIP ─────────────────────────────────────────────────
kpi_items = [
    ("OMIE Spot",    f"{last_spot:.2f} €",               C_AMBER),
    ("Regime",       last_regime,                         regime_color(last_regime)),
    ("RSI",          f"{last_rsi:.4f}",                   C_TEAL),
    ("Floor Disc",   f"{last_discount:+.2f} €/MWh",       disc_color),
    ("Ann Vol",      f"{vol_annual*100:.1f}%",            C_AMBER),
    ("B76 Call",     f"{b76_call:.2f}",                   C_DIM2),
    ("Spike Prob",   f"{spike_prob:.4f}",                 C_DIM2),
    ("Signal",       f"{sig_arrow} {cur_dir}  {cur_conf:.2f}", direction_color(cur_dir)),
]
_html(kpi_strip(kpi_items))

# ── TABS ──────────────────────────────────────────────────────
tabs = st.tabs(["Signal", "Generation", "Pricer", "Volatility", "Execution", "Readiness", "News"])

# ── TAB I: SIGNAL ─────────────────────────────────────────────
with tabs[0]:
    _html('<div class="tab-content">')

    if live is not None:
        left, right = st.columns([2, 1], gap="large")

        with left:
            _html(section_header("OMIE Spot vs Thermal Floor"))
            st.plotly_chart(chart_spot_vs_floor(live), use_container_width=True, config=PLOTLY_CFG)

            _html(section_header("Floor Discount  (EUR/MWh)"))
            st.plotly_chart(chart_floor_discount(live), use_container_width=True, config=PLOTLY_CFG)

        with right:
            _html(section_header("Live Signal Readout"))
            _html(signal_readout_row("REGIME", last_regime, regime_color(last_regime), "RSI + floor ratio"))
            _html(signal_readout_row("OMIE SPOT", f"{last_spot:.2f} EUR/MWh", C_AMBER, "ESIOS ind 600"))
            _html(signal_readout_row("THERMAL FLOOR", f"{floor_proxy:.2f} EUR/MWh", C_DIM2,
                                     f"TTF {live_ttf:.1f} EUR/MWh · EUA {live_eua:.0f} EUR/t"))
            _html(signal_readout_row("FLOOR DISCOUNT", f"{last_discount:+.2f} EUR/MWh", disc_color,
                                     "neg = below floor"))
            _html(signal_readout_row("RSI", f"{last_rsi:.4f}", C_TEAL, "renew / demand"))
            if "atc_es_fr" in live.columns:
                atc_val = float(live["atc_es_fr"].dropna().iloc[-1])
                _html(signal_readout_row("ATC ES→FR", f"{atc_val:.0f} MW", C_BLUE,
                                         "neg = Spain exporting"))

            if sig is not None:
                st.markdown("<br>", unsafe_allow_html=True)
                _html(section_header("Engine Signal"))
                _html(signal_readout_row("DIRECTION", sig.direction, direction_color(sig.direction), ""))
                _html(signal_readout_row("CONFIDENCE", f"{sig.confidence:.3f}", C_TEAL, ""))

        # Regime timeline
        st.markdown("<br>", unsafe_allow_html=True)
        _html(section_header("Regime Timeline"))
        regime_map = {"Thermal-Marginal": 0, "Renewable-Dom.": 1, "Demand-Stress": 2}
        regime_num = live["regime"].map(regime_map)
        fig_r = _fig(height=120)
        colors_r = [
            {0: C_AMBER, 1: C_GREEN, 2: C_RED}.get(int(v), C_DIM)
            for v in regime_num.fillna(0).values
        ]
        fig_r.add_trace(go.Bar(
            x=live.index, y=regime_num.values,
            marker_color=colors_r,
            hovertemplate="Regime: %{y}<br>0=Thermal 1=Renew 2=Stress",
            showlegend=False,
        ))
        fig_r.update_yaxes(tickvals=[0, 1, 2], ticktext=["Thermal", "Renew", "Stress"],
                           tickfont=dict(size=8))
        st.plotly_chart(fig_r, use_container_width=True, config=PLOTLY_CFG)

    else:
        st.warning("ESIOS live data not available.")

    _html("</div>")


# ── TAB II: GENERATION ────────────────────────────────────────
with tabs[1]:
    _html('<div class="tab-content">')

    if live is not None:
        left, right = st.columns(2, gap="large")

        with left:
            _html(section_header("Generation Mix  (MWh/h)"))
            st.plotly_chart(chart_generation(live), use_container_width=True, config=PLOTLY_CFG)

            _html(section_header("Renewable Surplus Index"))
            st.plotly_chart(chart_rsi(live), use_container_width=True, config=PLOTLY_CFG)

        with right:
            _html(section_header("Demand vs Renewable Generation"))
            st.plotly_chart(chart_demand_vs_renew(live), use_container_width=True, config=PLOTLY_CFG)

            _html(section_header("ATC ES→FR Interconnector"))
            st.plotly_chart(chart_atc(live), use_container_width=True, config=PLOTLY_CFG)

        # Latest snapshot table
        st.markdown("<br>", unsafe_allow_html=True)
        _html(section_header("Latest Hour Snapshot"))
        snap = live.dropna(subset=["omie_price"]).iloc[-1]
        snap_cols = {
            "omie_price": ("OMIE Price", "EUR/MWh"),
            "gen_wind": ("Wind", "MWh/h"),
            "gen_solar_pv": ("Solar PV", "MWh/h"),
            "gen_solar_thermal": ("Solar Thermal", "MWh/h"),
            "gen_hydro": ("Hydro", "MWh/h"),
            "gen_nuclear": ("Nuclear", "MWh/h"),
            "gen_renewable": ("Total Renewable", "MWh/h"),
            "demand_forecast": ("Demand Forecast", "MWh/h"),
            "rsi": ("RSI", ""),
            "atc_es_fr": ("ATC ES→FR", "MW"),
            "regime": ("Regime", ""),
        }
        rows = []
        for col, (name, unit) in snap_cols.items():
            if col in snap.index:
                val = snap[col]
                if isinstance(val, float):
                    fmt = f"{val:,.4f}" if col == "rsi" else f"{val:,.2f}"
                    if unit:
                        fmt += f" {unit}"
                else:
                    fmt = str(val)
                rows.append({"Indicator": name, "Value": fmt})
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            height=380,
        )
    else:
        st.warning("ESIOS live data not available.")

    _html("</div>")


# ── TAB III: PRICER ───────────────────────────────────────────
with tabs[2]:
    _html('<div class="tab-content">')

    if pricer:
        left, right = st.columns(2, gap="large")
        shift = pricer["shift_constant"]

        with left:
            _html(section_header("Pricing Parameters"))
            rows = [
                ("Last Spot F",        f"{pricer['last_spot']:.4f} EUR/MWh"),
                ("Strike K (ATM)",     f"{pricer['strike']:.4f} EUR/MWh"),
                ("Shift Constant",     f"{shift:.4f} EUR/MWh"),
                ("Shifted F",          f"{pricer['last_spot']+shift:.4f} EUR/MWh"),
                ("Ann. Vol σ",         f"{pricer['sigma']*100:.2f}%"),
                ("T (years)",          f"{pricer['T']:.6f}"),
                ("Risk-free r",        f"{pricer['r']:.2%}"),
                ("Black-76 Call",      f"{b76_call:.4f} EUR/MWh"),
                ("MC Call",            f"{mc_call:.4f} EUR/MWh"),
                ("MC Std Error",       f"{mc_se:.4f} EUR/MWh"),
                ("B76 vs MC diff",     f"{abs(b76_call-mc_call):.4f} EUR/MWh"),
                ("Spike Prob",         f"{spike_prob:.4f}"),
                ("Neg. Price Prob",    f"{neg_prob:.4f}"),
            ]
            st.dataframe(
                pd.DataFrame(rows, columns=["Parameter", "Value"]),
                use_container_width=True, hide_index=True, height=420,
            )

        with right:
            _html(section_header("MC Payoff Distribution"))
            np.random.seed(42)
            F_s = pricer["last_spot"] + shift
            Z   = np.random.standard_normal(10_000)
            ST  = F_s * np.exp((pricer["r"] - 0.5*pricer["sigma"]**2) * pricer["T"]
                               + pricer["sigma"] * np.sqrt(pricer["T"]) * Z) - shift
            payoffs = np.maximum(ST - pricer["strike"], 0.0)
            nonzero = payoffs[payoffs > 0]
            st.caption(f"ITM: {len(nonzero):,} of 10,000  ({len(nonzero)/100:.1f}%)")
            st.plotly_chart(chart_mc_payoff(pricer), use_container_width=True, config=PLOTLY_CFG)
    else:
        st.warning("Pricer pickle not found.")

    _html("</div>")


# ── TAB IV: VOLATILITY ────────────────────────────────────────
with tabs[3]:
    _html('<div class="tab-content">')

    if spot_series is not None:
        spot_pos  = spot_series[spot_series > 0]
        log_ret   = np.log(spot_pos).diff().dropna()
        z         = (log_ret - log_ret.mean()) / log_ret.std()
        ret_clean = log_ret[z.abs() < 4]

        left, right = st.columns(2, gap="large")

        with left:
            _html(section_header("Rolling 30-Day Annualised Vol  (%)"))
            st.plotly_chart(chart_rolling_vol(spot_series, vol_annual),
                            use_container_width=True, config=PLOTLY_CFG)

            _html(section_header("Log Returns  —  Last 30 Days"))
            fig_lr = _fig(height=160)
            fig_lr.add_trace(go.Scatter(
                x=list(range(len(ret_clean.tail(30*24)))),
                y=ret_clean.tail(30*24).values,
                name="Log Returns",
                line=dict(color=C_TEAL, width=0.8),
                hovertemplate="r: %{y:.5f}",
            ))
            fig_lr.add_hline(y=0, line_color=C_BORDER2, line_width=1)
            st.plotly_chart(fig_lr, use_container_width=True, config=PLOTLY_CFG)

        with right:
            _html(section_header("Vol Statistics"))
            daily_vol = vol_annual / np.sqrt(365)
            st.dataframe(pd.DataFrame([
                ("Hourly vol",        f"{vol_annual/np.sqrt(8760):.6f}"),
                ("Daily vol",         f"{daily_vol*100:.2f}%"),
                ("Annual vol",        f"{vol_annual*100:.2f}%"),
                ("OMIE normal range", "30–80%"),
                ("Status",            "NORMAL" if 0.30 <= vol_annual <= 0.80 else "CHECK"),
            ], columns=["Metric", "Value"]),
            use_container_width=True, hide_index=True)

            st.markdown("<br>", unsafe_allow_html=True)
            _html(section_header("Price Percentiles"))
            pct_vals = np.percentile(spot_series.values, [1,5,10,25,50,75,90,95,99])
            pct_labels = ["P1","P5","P10","P25","P50","P75","P90","P95","P99"]
            st.dataframe(pd.DataFrame({
                "Percentile": pct_labels,
                "EUR/MWh":    [f"{p:.2f}" for p in pct_vals],
            }), use_container_width=True, hide_index=True)
    else:
        st.warning("Spot series not available.")

    _html("</div>")


# ── TAB V: EXECUTION ──────────────────────────────────────────
with tabs[4]:
    _html('<div class="tab-content">')

    if not EXEC_OK:
        st.warning("Execution module not available. Run `pip install -e src/` in the repo root.")
    elif live is None:
        st.warning("ESIOS live data required for signal derivation.")
    else:
        left, right = st.columns([1, 2], gap="large")

        with left:
            _html(section_header("Current Signal"))

            dir_color = direction_color(sig.direction)
            dir_arrow = {"SHORT": "▼", "LONG": "▲", "NEUTRAL": "—"}.get(sig.direction, "—")
            _html(f"""
            <div style="
                padding:20px;
                border:1px solid {dir_color};
                background:rgba(0,0,0,0.3);
                margin-bottom:20px;
                text-align:center;
            ">
                <div style="
                    font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                    font-size:36px;
                    font-weight:700;
                    color:{dir_color};
                    letter-spacing:0.08em;
                ">{dir_arrow}  {sig.direction}</div>
                <div style="
                    font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                    font-size:11px;
                    color:{C_DIM2};
                    margin-top:8px;
                ">conf {sig.confidence:.3f}  |  {sig.regime}</div>
                <div style="
                    font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                    font-size:10px;
                    color:{C_DIM};
                    margin-top:4px;
                ">{sig.timestamp.strftime('%H:%M:%S')}  {sig.source}</div>
            </div>
            """)

            _html(section_header("Guardrail Checks"))
            for label, passed in guardrails.status_lines(sig):
                _html(guardrail_row(label, passed))

            st.markdown("<br>", unsafe_allow_html=True)

            overall = guardrails.check(sig)
            if overall.passed:
                if st.button("SUBMIT PAPER TRADE", use_container_width=True):
                    result = router.route(sig)
                    if result.order:
                        st.session_state["last_order"] = result.order
                        st.success(f"{result.order.order_id}  —  {result.order.message}")
                    else:
                        st.error(f"BLOCKED: {result.guardrail.reason}")
            else:
                st.markdown(
                    f'<div style="font-family:\'Helvetica Neue\',Helvetica,Arial,sans-serif;font-size:10px;font-weight:300;'
                    f'color:{C_RED};padding:12px;border:1px solid {C_RED};text-align:center;">'
                    f'BLOCKED: {overall.reason}</div>',
                    unsafe_allow_html=True,
                )

        with right:
            _html(section_header("Signal Detail"))
            _html(signal_readout_row("SPOT",         f"{sig.spot:.4f} EUR/MWh",       C_AMBER))
            _html(signal_readout_row("FLOOR DISC",   f"{sig.floor_discount:+.4f}",     disc_color))
            _html(signal_readout_row("RSI",          f"{sig.rsi:.4f}",                 C_TEAL))
            _html(signal_readout_row("SPIKE PROB",   f"{sig.spike_prob:.4f}",          C_DIM2))
            _html(signal_readout_row("NEG PX PROB",  f"{sig.neg_price_prob:.4f}",      C_DIM2))

            st.markdown("<br>", unsafe_allow_html=True)
            _html(section_header("Paper Trade Blotter"))

            blotter = paper.load_blotter()
            if not blotter:
                st.caption("No paper trades yet.")
            else:
                header = f"""
                <div style="
                    display:grid;
                    grid-template-columns:160px 70px 90px 90px 70px 80px;
                    padding:6px 12px;
                    border-bottom:1px solid {C_BORDER2};
                    background:{C_BG};
                ">
                    <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:8px;
                                 font-weight:600;letter-spacing:0.14em;color:{C_DIM};">TIMESTAMP</span>
                    <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:8px;
                                 font-weight:600;letter-spacing:0.14em;color:{C_DIM};">DIR</span>
                    <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:8px;
                                 font-weight:600;letter-spacing:0.14em;color:{C_DIM};">FILL</span>
                    <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:8px;
                                 font-weight:600;letter-spacing:0.14em;color:{C_DIM};">DISC</span>
                    <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:8px;
                                 font-weight:600;letter-spacing:0.14em;color:{C_DIM};">CONF</span>
                    <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:8px;
                                 font-weight:600;letter-spacing:0.14em;color:{C_DIM};">ORDER ID</span>
                </div>
                """
                rows_html = "".join(blotter_row(r, i) for i, r in enumerate(blotter[:50]))
                _html(f'<div style="border:1px solid {C_BORDER2};">{header}{rows_html}</div>')

    _html("</div>")


# ── TAB VI: READINESS ─────────────────────────────────────────
with tabs[5]:
    _html('<div class="tab-content">')

    pricer_ok = pricer is not None
    live_ok   = live is not None
    exec_ok   = EXEC_OK and live is not None

    STATUS_COLOR = {
        "LIVE":    C_GREEN,
        "PROXY":   C_AMBER,
        "PENDING": C_DIM2,
        "MISSING": C_RED,
    }

    capabilities = [
        ("OMIE DA prices",        "LIVE"    if pricer_ok else "MISSING",  "28k+ hourly rows in pricer pickle"),
        ("ESIOS generation mix",  "LIVE"    if live_ok else "MISSING",    "Wind, solar, hydro, nuclear"),
        ("ESIOS demand forecast", "LIVE"    if live_ok else "MISSING",    "Indicator 544 — peninsular prevista"),
        ("ESIOS ATC ES→FR",       "LIVE"    if live_ok else "MISSING",    "Indicator 10209 — interconnector"),
        ("Spot pricer B76+MC",    "LIVE"    if pricer_ok else "MISSING",  "Shifted log-normal, correct vol"),
        ("Regime classifier",     "LIVE"    if live_ok else "PROXY",      "RSI + floor ratio, rule-based"),
        ("Thermal floor",         "LIVE"    if live_ok else "PROXY",      f"TTF {live_ttf:.1f} EUR/MWh · EUA {live_eua:.0f} EUR/t · CCGT 50%"),
        ("Execution router",      "LIVE"    if exec_ok else "PENDING",    "PaperAdapter — Bloomberg EMSX next"),
        ("BESS sunset model",     "PENDING",                              "Search ESIOS bateria indicators"),
        ("REE node map",          "PENDING",                              "230-node demand map — ingest REE"),
        ("Daily PDF briefing",    "PENDING",                              "Wire Mailjet + scheduler"),
        ("Bloomberg EMSX",        "PENDING",                              "After paper router is validated"),
    ]

    _html(section_header("System Capabilities"))

    for cap, status, note in capabilities:
        c = STATUS_COLOR.get(status, C_DIM)
        _html(f"""
        <div style="
            display:flex;
            align-items:center;
            gap:16px;
            padding:9px 0;
            border-bottom:1px solid {C_BORDER};
        ">
            <span style="
                font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                font-size:8px;
                font-weight:700;
                letter-spacing:0.14em;
                color:{c};
                border:1px solid {c};
                padding:2px 8px;
                min-width:58px;
                text-align:center;
            ">{status}</span>
            <span style="
                font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                font-size:11px;
                color:{C_TEXT};
                min-width:200px;
            ">{cap}</span>
            <span style="
                font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                font-size:9px;
                color:{C_DIM};
            ">{note}</span>
        </div>
        """)

    st.markdown("<br>", unsafe_allow_html=True)
    _html(section_header("Next Build"))

    next_steps = [
        ("NEXT",     C_AMBER, "Upgrade EUA feed from hardcode to licensed ICE/EEX tick"),
        ("NEXT",     C_AMBER, "Schedule daily data refresh (cron → Railway) to keep pkl fresh"),
        ("SOON",     C_TEAL,  "Search ESIOS 'bateria' indicators for BESS data"),
        ("SOON",     C_TEAL,  "Wire daily PDF briefing via Mailjet"),
        ("LATER",    C_DIM2,  "Bloomberg EMSX adapter — swap in after paper validates"),
    ]
    for priority, c, text in next_steps:
        _html(f"""
        <div style="
            display:flex;gap:14px;padding:9px 0;
            border-bottom:1px solid {C_BORDER};align-items:center;
        ">
            <span style="
                font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;
                font-size:8px;font-weight:700;letter-spacing:0.14em;
                color:{c};border:1px solid {c};
                padding:2px 10px;min-width:48px;text-align:center;
            ">{priority}</span>
            <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;font-size:10px;color:{C_DIM2};">{text}</span>
        </div>
        """)

    _html("</div>")

# ── TAB VII: NEWS ─────────────────────────────────────────────
with tabs[6]:
    _html('<div class="tab-content">')
    _html(section_header("Energy & Commodity Feed"))

    col_left, col_right = st.columns(2, gap="large")

    for topic, query, color in _NEWS_TOPICS:
        target_col = col_left if topic in ("Oil & Gas", "Renewables") else col_right
        with target_col:
            _html(
                f'<div style="font-family:{HV};font-size:9px;font-weight:700;'
                f'letter-spacing:0.18em;text-transform:uppercase;color:{color};'
                f'padding:10px 0 8px 0;border-bottom:2px solid {color};'
                f'margin-bottom:0;margin-top:16px;">{topic}</div>'
            )
            items = fetch_news(query)
            _html(_news_panel(items, color))

    _html("</div>")
