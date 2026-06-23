from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..signal import TradingSignal


@dataclass
class OrderResult:
    order_id: str
    status: str           # FILLED | REJECTED | ERROR
    fill_price: float | None
    message: str


class OrderAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def submit(self, signal: TradingSignal) -> OrderResult: ...
