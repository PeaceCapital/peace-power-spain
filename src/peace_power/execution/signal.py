from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class TradingSignal:
    timestamp: datetime
    spot: float           # EUR/MWh
    regime: str           # Thermal-Marginal | Renewable-Dom. | Demand-Stress
    floor_discount: float # negative = below thermal floor = short candidate
    rsi: float            # renewable surplus index
    spike_prob: float
    neg_price_prob: float
    direction: str        # SHORT | LONG | NEUTRAL
    confidence: float     # 0–1
    source: str           # ESIOS_LIVE | PRICER_CACHE


def signal_from_live(
    live: "pd.DataFrame",
    pricer: dict | None = None,
    source: str = "ESIOS_LIVE",
) -> TradingSignal:
    row = live.dropna(subset=["omie_price"]).iloc[-1]
    spot = float(row["omie_price"])
    regime = str(row["regime"])
    rsi = float(row["rsi"])
    floor_discount = float(row["floor_discount"])

    spike_prob = float(pricer["spike_prob"]) if pricer else 0.0
    neg_price_prob = float(pricer["neg_price_prob"]) if pricer else 0.0

    direction, confidence = _classify(floor_discount, regime, rsi, spike_prob)

    return TradingSignal(
        timestamp=datetime.now(),
        spot=spot,
        regime=regime,
        floor_discount=floor_discount,
        rsi=rsi,
        spike_prob=spike_prob,
        neg_price_prob=neg_price_prob,
        direction=direction,
        confidence=confidence,
        source=source,
    )


def _classify(
    floor_discount: float,
    regime: str,
    rsi: float,
    spike_prob: float,
) -> tuple[str, float]:
    # Strong short: deep below floor + renewable-dominated
    if floor_discount < -10 and regime == "Renewable-Dom.":
        return "SHORT", round(min(0.95, 0.75 + abs(floor_discount) / 60), 3)
    # Moderate short: any floor discount > 2 EUR/MWh
    if floor_discount < -2:
        return "SHORT", round(min(0.80, 0.55 + abs(floor_discount) / 50), 3)
    # Long: demand stress or significant floor premium
    if regime == "Demand-Stress" or floor_discount > 15:
        return "LONG", round(min(0.80, 0.60 + spike_prob), 3)
    return "NEUTRAL", 0.25
