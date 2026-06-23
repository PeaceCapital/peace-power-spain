from __future__ import annotations

from dataclasses import dataclass

from .adapters.base import OrderAdapter, OrderResult
from .guardrails import GuardrailEngine, GuardrailResult
from .signal import TradingSignal


@dataclass
class RouteResult:
    signal: TradingSignal
    guardrail: GuardrailResult
    order: OrderResult | None  # None when guardrail blocks


class ExecutionRouter:
    def __init__(self, adapter: OrderAdapter, guardrails: GuardrailEngine) -> None:
        self._adapter = adapter
        self._guardrails = guardrails

    @property
    def adapter_name(self) -> str:
        return self._adapter.name

    def route(self, signal: TradingSignal) -> RouteResult:
        result = self._guardrails.check(signal)
        if not result.passed:
            return RouteResult(signal=signal, guardrail=result, order=None)
        order = self._adapter.submit(signal)
        return RouteResult(signal=signal, guardrail=result, order=order)
