from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .signal import TradingSignal


@dataclass
class GuardrailResult:
    passed: bool
    reason: str | None  # None when passed


class GuardrailEngine:
    def __init__(
        self,
        min_confidence: float = 0.50,
        max_daily_signals: int = 10,
        cooldown_minutes: int = 60,
        allow_neutral: bool = False,
        log_path: Path | None = None,
    ) -> None:
        self.min_confidence = min_confidence
        self.max_daily_signals = max_daily_signals
        self.cooldown_minutes = cooldown_minutes
        self.allow_neutral = allow_neutral
        self._log_path = log_path

    def check(self, signal: TradingSignal) -> GuardrailResult:
        if signal.direction == "NEUTRAL" and not self.allow_neutral:
            return GuardrailResult(False, "NEUTRAL — no signal")

        if signal.confidence < self.min_confidence:
            return GuardrailResult(
                False,
                f"confidence {signal.confidence:.2f} < threshold {self.min_confidence}",
            )

        if self._log_path and self._log_path.exists():
            records = _load_records(self._log_path)
            today_str = date.today().isoformat()
            today_filled = [r for r in records if r.get("date") == today_str and r.get("status") == "FILLED"]

            if len(today_filled) >= self.max_daily_signals:
                return GuardrailResult(False, f"daily limit reached ({self.max_daily_signals})")

            if today_filled:
                last_ts = datetime.fromisoformat(today_filled[-1]["timestamp"])
                elapsed_min = (signal.timestamp - last_ts).total_seconds() / 60
                if (
                    elapsed_min < self.cooldown_minutes
                    and today_filled[-1].get("direction") == signal.direction
                ):
                    return GuardrailResult(
                        False,
                        f"{signal.direction} cooldown — {elapsed_min:.0f}m of {self.cooldown_minutes}m elapsed",
                    )

        return GuardrailResult(True, None)

    def status_lines(self, signal: TradingSignal) -> list[tuple[str, bool]]:
        """Return each guardrail check as (label, passed) for display."""
        lines = []
        lines.append(("direction != NEUTRAL", signal.direction != "NEUTRAL"))
        lines.append((f"confidence >= {self.min_confidence}", signal.confidence >= self.min_confidence))

        if self._log_path and self._log_path.exists():
            records = _load_records(self._log_path)
            today_str = date.today().isoformat()
            today_filled = [r for r in records if r.get("date") == today_str and r.get("status") == "FILLED"]
            lines.append((f"daily count < {self.max_daily_signals}  ({len(today_filled)} so far)", len(today_filled) < self.max_daily_signals))

            if today_filled:
                last_ts = datetime.fromisoformat(today_filled[-1]["timestamp"])
                elapsed_min = (signal.timestamp - last_ts).total_seconds() / 60
                cooldown_ok = not (elapsed_min < self.cooldown_minutes and today_filled[-1].get("direction") == signal.direction)
                lines.append((f"cooldown clear ({elapsed_min:.0f}m elapsed)", cooldown_ok))
        else:
            lines.append((f"daily count < {self.max_daily_signals}  (0 so far)", True))

        return lines


def _load_records(path: Path) -> list[dict]:
    records = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records
