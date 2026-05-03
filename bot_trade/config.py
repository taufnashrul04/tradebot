"""
bot_trade/config.py — Centralized configuration loader
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_env_path)


# ─── Exchange Configs ─────────────────────────────────────────────────────────

@dataclass
class NadoConfig:
    private_key: str = field(default_factory=lambda: os.getenv("NADO_PRIVATE_KEY", ""))
    subaccount_owner: str = field(default_factory=lambda: os.getenv("NADO_SUBACCOUNT_OWNER", ""))
    env: str = field(default_factory=lambda: os.getenv("NADO_ENV", "nadoMainnet"))
    subaccount_name: str = field(default_factory=lambda: os.getenv("NADO_SUBACCOUNT_NAME", "default"))

    @property
    def is_configured(self) -> bool:
        return bool(self.private_key)


@dataclass
class DecibelConfig:
    private_key: str = field(default_factory=lambda: os.getenv("DECIBEL_PRIVATE_KEY", ""))
    subaccount_addr: str = field(default_factory=lambda: os.getenv("DECIBEL_SUBACCOUNT_ADDR", ""))
    geomi_api_key: str = field(default_factory=lambda: os.getenv("DECIBEL_GEOMI_KEY", ""))
    env: str = field(default_factory=lambda: os.getenv("DECIBEL_ENV", "mainnet"))
    api_base: str = "https://api.mainnet.aptoslabs.com/decibel/api/v1"
    testnet_api_base: str = "https://api.testnet.aptoslabs.com/decibel/api/v1"
    aptos_node: str = "https://fullnode.mainnet.aptoslabs.com/v1"

    @property
    def is_configured(self) -> bool:
        return bool(self.private_key and self.subaccount_addr)

    @property
    def effective_api_base(self) -> str:
        if self.env == "testnet":
            return self.testnet_api_base
        return self.api_base


@dataclass
class RiseConfig:
    private_key: str = field(default_factory=lambda: os.getenv("RISE_PRIVATE_KEY", ""))
    api_key: str = field(default_factory=lambda: os.getenv("RISE_API_KEY", ""))
    rpc_url: str = field(default_factory=lambda: os.getenv("RISE_RPC_URL", "https://mainnet.riselabs.xyz"))
    env: str = field(default_factory=lambda: os.getenv("RISE_ENV", "mainnet"))

    @property
    def is_configured(self) -> bool:
        return bool(self.private_key)


# ─── Risk Management ──────────────────────────────────────────────────────────

@dataclass
class RiskConfig:
    max_position_usd: float = field(
        default_factory=lambda: float(os.getenv("MAX_POSITION_USD", "1000"))
    )
    max_drawdown_pct: float = field(
        default_factory=lambda: float(os.getenv("MAX_DRAWDOWN_PCT", "5.0"))
    )
    max_leverage: int = field(
        default_factory=lambda: int(os.getenv("MAX_LEVERAGE", "5"))
    )


# ─── Funding Arb Config ───────────────────────────────────────────────────────

@dataclass
class FundingArbConfig:
    min_funding_diff: float = field(
        default_factory=lambda: float(os.getenv("MIN_FUNDING_DIFF", "0.01"))
    )
    check_interval: int = field(
        default_factory=lambda: int(os.getenv("FUNDING_CHECK_INTERVAL", "60"))
    )


# ─── Master Config ────────────────────────────────────────────────────────────

@dataclass
class BotConfig:
    nado: NadoConfig = field(default_factory=NadoConfig)
    decibel: DecibelConfig = field(default_factory=DecibelConfig)
    rise: RiseConfig = field(default_factory=RiseConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    funding_arb: FundingArbConfig = field(default_factory=FundingArbConfig)
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "./bot_trade.db"))


# Singleton
_config: Optional[BotConfig] = None


def get_config() -> BotConfig:
    global _config
    if _config is None:
        _config = BotConfig()
    return _config
