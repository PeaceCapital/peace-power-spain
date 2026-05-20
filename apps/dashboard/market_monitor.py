from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from peace_power import (
    build_alert_frame,
    build_dashboard_bundle,
    build_market_briefing,
    summarize_market_state,
)


ROOT = Path(__file__).resolve().parents[2]


st.set_page_config(
    page_title="Iberia Power Signal Engine",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(225, 116, 78, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(45, 91, 128, 0.18), transparent 24%),
                linear-gradient(180deg, #f7f1e7 0%, #efe5d4 100%);
            color: #182028;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3 {
            font-family: "Georgia", "Times New Roman", serif;
            letter-spacing: -0.02em;
            color: #132030;
        }
        p, li, label, div, span {
            font-family: "Avenir Next", "Segoe UI", sans-serif;
        }
        .hero-shell {
            border: 1px solid rgba(24, 32, 40, 0.08);
            border-radius: 28px;
            padding: 1.4rem 1.6rem;
            background: rgba(255, 252, 246, 0.86);
            box-shadow: 0 20px 60px rgba(42, 37, 31, 0.08);
            margin-bottom: 1.2rem;
        }
        .eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-size: 0.76rem;
            color: #8d5c42;
            margin-bottom: 0.35rem;
            font-weight: 700;
        }
        .hero-title {
            font-size: 2.5rem;
            line-height: 1.0;
            margin: 0;
        }
        .hero-copy {
            font-size: 1rem;
            color: #475569;
            margin-top: 0.7rem;
            max-width: 880px;
        }
        .status-strip {
            display: flex;
            gap: 0.65rem;
            flex-wrap: wrap;
            margin-top: 1rem;
        }
        .status-pill {
            display: inline-block;
            border-radius: 999px;
            padding: 0.38rem 0.8rem;
            font-size: 0.82rem;
            background: #f3e5cc;
            color: #6a452d;
            border: 1px solid rgba(106, 69, 45, 0.12);
        }
        .metric-card {
            border-radius: 24px;
            padding: 1rem 1.05rem;
            background: rgba(255, 251, 246, 0.92);
            border: 1px solid rgba(19, 32, 48, 0.08);
            min-height: 148px;
            box-shadow: 0 14px 30px rgba(42, 37, 31, 0.06);
        }
        .metric-label {
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.72rem;
            color: #7a685d;
            margin-bottom: 0.65rem;
            font-weight: 700;
        }
        .metric-value {
            font-family: "Georgia", "Times New Roman", serif;
            font-size: 2rem;
            line-height: 1.05;
            color: #162130;
        }
        .metric-note {
            margin-top: 0.65rem;
            color: #54606f;
            font-size: 0.92rem;
        }
        .panel-note {
            border-left: 4px solid #b45d3c;
            padding: 0.9rem 1rem;
            border-radius: 0 18px 18px 0;
            background: rgba(255, 247, 235, 0.9);
            margin-bottom: 1rem;
            color: #4b5563;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, note: str) -> str:
    return f"""
    <div class="metric-card">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{value}</div>
      <div class="metric-note">{note}</div>
    </div>
    """


@st.cache_data(show_spinner=False)
def load_bundle() -> object:
    return build_dashboard_bundle(ROOT)


inject_styles()
bundle = load_bundle()
market_df = bundle.market_df
zone_summary = bundle.zone_summary
snapshot = summarize_market_state(market_df, zone_summary)

with st.sidebar:
    st.markdown("## Control Room")
    lookback_days = st.slider("Lookback window", min_value=7, max_value=45, value=21, step=7)
    show_nodes = st.slider("Node rows", min_value=5, max_value=40, value=15, step=5)
    st.markdown("### Data Sources")
    st.caption(bundle.market_source)
    st.caption(bundle.node_source)
    st.markdown("### Strategic Lens")
    st.caption("Current build is a client-demo shell. Live BESS and ATC remain blocked until ESIOS token access works.")

window = market_df.tail(lookback_days * 24).copy()
daily = (
    window.groupby("delivery_date", as_index=False)
    .agg(
        price_omie=("price_omie", "mean"),
        composite_signal=("composite_signal", "max"),
        storage_penetration=("storage_penetration", "mean"),
        bess_capture_ratio=("bess_capture_ratio", "mean"),
        negative_price_hours=("negative_price_flag", "sum"),
    )
)
alerts = build_alert_frame(window, zone_summary)
briefing = build_market_briefing(snapshot, bundle)

st.markdown(
    f"""
    <div class="hero-shell">
      <div class="eyebrow">Peace Capital / Iberia Power Analytics</div>
      <h1 class="hero-title">Spain / Iberia Signal Engine</h1>
      <div class="hero-copy">
        Technical market monitor for the Iberian pricer: OMIE price monitoring, storage-aware signals,
        congestion pressure, and the operating layer that should eventually carry alerts, briefing, and market context.
      </div>
      <div class="status-strip">
        <span class="status-pill">Market frame: {bundle.market_source}</span>
        <span class="status-pill">Node map: {bundle.node_source}</span>
        <span class="status-pill">Sunset source: {bundle.sunset.threshold_source}</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(
        metric_card(
            "Composite Signal",
            f"{snapshot['latest_composite']:.2f}",
            f"Current regime: {snapshot['latest_regime']}",
        ),
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        metric_card(
            "OMIE Last Print",
            f"{snapshot['latest_price']:.1f} €/MWh",
            f"Discount to thermal floor: {snapshot['thermal_discount']:.1f} €/MWh",
        ),
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        metric_card(
            "Storage Sunset",
            f"{snapshot['storage_penetration']:.2f}",
            f"7d sunset-flag share: {snapshot['sunset_share_7d']:.0%}",
        ),
        unsafe_allow_html=True,
    )
with col4:
    st.markdown(
        metric_card(
            "Congestion Hot Zone",
            snapshot["hot_zone"],
            f"ICS pressure: {snapshot['hot_zone_pressure']:.1f}",
        ),
        unsafe_allow_html=True,
    )

tab_signal, tab_ops, tab_storage, tab_congestion, tab_readiness = st.tabs(
    ["Signal Deck", "Technical Ops", "Storage Risk", "Congestion", "Readiness"]
)

with tab_signal:
    st.markdown(
        """
        <div class="panel-note">
          This view tracks the strategic core of the memo: when storage-adjusted renewable surplus pushes prices below the thermal floor
          and whether that pressure is strong enough to justify a short bias.
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.8, 1.2])
    with left:
        st.subheader("OMIE vs Thermal Floor")
        st.line_chart(
            window[["price_omie", "thermal_floor_proxy"]].rename(
                columns={
                    "price_omie": "OMIE",
                    "thermal_floor_proxy": "Thermal floor proxy",
                }
            )
        )
        st.subheader("Composite Signal vs Negative Price Hours")
        chart_df = daily.set_index("delivery_date")[["composite_signal", "negative_price_hours"]]
        st.line_chart(chart_df.rename(columns={"composite_signal": "Composite", "negative_price_hours": "Negative hours"}))
    with right:
        st.subheader("Latest Signal Readout")
        latest_cols = [
            "price_omie",
            "rsi_after_bess",
            "npp_proxy",
            "ics_proxy",
            "composite_signal",
            "signal_regime",
        ]
        st.dataframe(window[latest_cols].tail(12), use_container_width=True, height=420)

with tab_ops:
    st.markdown(
        """
        <div class="panel-note">
          This is the technical operating layer for the product. It is where alerts, market briefing, live news, and daily monitoring should converge as the stack matures.
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.15, 1.35])
    with left:
        st.subheader("Market Alerts")
        st.dataframe(alerts, use_container_width=True, hide_index=True)
    with right:
        st.subheader("Market Briefing")
        for line in briefing:
            st.markdown(f"- {line}")
    st.subheader("Pricer Monitor")
    ops_cols = [
        "price_omie",
        "thermal_floor_proxy",
        "price_discount_to_floor",
        "composite_signal",
        "npp_proxy",
        "ics_proxy",
        "signal_regime",
    ]
    st.dataframe(window[ops_cols].tail(24), use_container_width=True, height=360)

with tab_storage:
    st.markdown(
        """
        <div class="panel-note">
          This is the strategic sunset monitor: the short thesis is valid now, but the dashboard has to show when BESS starts absorbing too much surplus.
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns(2)
    with left:
        st.subheader("Storage Penetration and Capture")
        storage_chart = daily.set_index("delivery_date")[["storage_penetration", "bess_capture_ratio"]]
        st.line_chart(storage_chart.rename(columns={"storage_penetration": "Penetration", "bess_capture_ratio": "Capture ratio"}))
    with right:
        st.subheader("Sunset Thresholds")
        threshold_df = pd.DataFrame(
            [
                {"Metric": "Penetration threshold", "Value": f"{bundle.sunset.penetration_threshold:.2f}"},
                {"Metric": "Capture ratio threshold", "Value": f"{bundle.sunset.capture_ratio_threshold:.2f}"},
                {"Metric": "Online MW threshold", "Value": f"{bundle.sunset.online_capacity_threshold:.1f}"},
                {"Metric": "Edge retention ratio", "Value": f"{bundle.sunset.edge_ratio:.2f}"},
                {"Metric": "Trigger source", "Value": bundle.sunset.threshold_source},
            ]
        )
        st.table(threshold_df)
    st.subheader("Hourly Storage View")
    st.area_chart(
        window[["bess_online_mw", "bess_absorption_mw", "bess_discharge_mw"]].rename(
            columns={
                "bess_online_mw": "Online MW",
                "bess_absorption_mw": "Absorption MW",
                "bess_discharge_mw": "Discharge MW",
            }
        )
    )

with tab_congestion:
    st.markdown(
        """
        <div class="panel-note">
          The node map is the locational layer behind ICS. This section shows where surplus is most likely to stay trapped and which internal zones deserve spread attention.
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.2, 1.4])
    with left:
        st.subheader("Zone Pressure")
        zone_chart = zone_summary.set_index("congestion_zone")[["ics_zone_pressure", "mean_vulnerability_score"]]
        st.bar_chart(zone_chart.rename(columns={"ics_zone_pressure": "ICS pressure", "mean_vulnerability_score": "Vulnerability"}))
    with right:
        st.subheader("Most Vulnerable Nodes")
        node_cols = [
            "node_name",
            "region",
            "congestion_zone",
            "available_capacity_mw",
            "congestion_vulnerability_score",
        ]
        vulnerable_nodes = bundle.nodes_df.sort_values("congestion_vulnerability_score", ascending=False).head(show_nodes)
        st.dataframe(vulnerable_nodes[node_cols], use_container_width=True, height=420)

with tab_readiness:
    st.markdown(
        """
        <div class="panel-note">
          This keeps the project honest. It shows what is genuinely live, what is still demo logic, and what still needs to be unlocked before the product is bank-grade.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(bundle.readiness, use_container_width=True, hide_index=True)
    st.subheader("Immediate Next Moves")
    st.markdown(
        """
        1. Resolve OMIE DNS/local network access and backfill hourly history into `data/raw/omie/`.
        2. Obtain a valid ESIOS personal API token so live BESS and ATC can replace the synthetic fallback.
        3. Recover `pc_spot_pricer.pkl` and `pc_test_predictions.csv` so the dashboard can surface real model outputs instead of proxies.
        4. Replace the template node map with the full REE node universe for real zone-pressure monitoring.
        """
    )
