"""
bot_trade/exchanges/__init__.py — Exchange registry
"""
from .base import BaseExchange
from .nado import NadoExchange
from .decibel import DecibelExchange
from .rise import RiseExchange
from ..models import ExchangeName


def get_exchange(name: str | ExchangeName) -> BaseExchange:
    """Factory: get exchange adapter by name."""
    if isinstance(name, str):
        name = ExchangeName(name.lower())

    registry = {
        ExchangeName.NADO: NadoExchange,
        ExchangeName.DECIBEL: DecibelExchange,
        ExchangeName.RISE: RiseExchange,
    }

    cls = registry.get(name)
    if cls is None:
        raise ValueError(f"Unknown exchange: {name}. Valid: {list(ExchangeName)}")
    return cls()


def get_all_exchanges() -> dict[ExchangeName, BaseExchange]:
    """Get instances of all exchanges."""
    return {
        ExchangeName.NADO: NadoExchange(),
        ExchangeName.DECIBEL: DecibelExchange(),
        ExchangeName.RISE: RiseExchange(),
    }


__all__ = [
    "BaseExchange", "NadoExchange", "DecibelExchange", "RiseExchange",
    "get_exchange", "get_all_exchanges",
]
