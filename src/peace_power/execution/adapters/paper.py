from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from pathlib import Path

from .base import OrderAdapter, OrderResult
from ..signal import TradingSignal

_DEFAULT_LOG = Path(__file__).resolve().parents[4] / "state" / "paper_trades.jsonl"


class PaperAdapter(OrderAdapter):
    """Logs signals as paper trades — no real orders, full audit trail."""

    name = "paper"

    def __init__(self, log_path: Path | None = None) -> None:
        self._log = log_path or _DEFAULT_LOG
        self._log.parent.mkdir(parents=True, exist_ok=True)

    def submit(self, signal: TradingSignal) -> OrderResult:
        order_id = "PPR-" + uuid.uuid4().hex[:8].upper()
        record = {
            "order_id": order_id,
            "timestamp": signal.timestamp.isoformat(),
            "date": date.today().isoformat(),
            "direction": signal.direction,
            "spot": round(signal.spot, 4),
            "floor_discount": round(signal.floor_discount, 4),
            "regime": signal.regime,
            "confidence": round(signal.confidence, 4),
            "rsi": round(signal.rsi, 4),
            "fill_price": round(signal.spot, 4),
            "status": "FILLED",
            "adapter": "paper",
        }
        with open(self._log, "a") as fh:
            fh.write(json.dumps(record) + "\n")

        return OrderResult(
            order_id=order_id,
            status="FILLED",
            fill_price=signal.spot,
            message=f"Paper fill @ {signal.spot:.2f} EUR/MWh",
        )

    def load_blotter(self) -> list[dict]:
        if not self._log.exists():
            return []
        records: list[dict] = []
        for line in self._log.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return list(reversed(records))  # newest first
