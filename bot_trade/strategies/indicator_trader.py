"""
bot_trade/strategies/indicator_trader.py

Technical Indicator-Based Trading Strategy

Supported strategies:
  - RSI Mean Reversion: Long < 30, Short > 70
  - EMA Crossover: Long when fast EMA crosses above slow EMA
  - MACD Momentum: Trade MACD histogram direction
  - Bollinger Band: Trade bounces or breakouts
  - VWAP: Trade relative to intraday VWAP

Uses pandas-ta for indicator computation.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

import pandas as pd
import numpy as np

from loguru import logger

from ..models import (
    ExchangeName, OrderSide, Order, SessionStats, TradingMode
)
from ..exchanges.base import BaseExchange
from ..config import get_config

try:
    import pandas_ta as ta
    HAS_PANDAS_TA = True
except ImportError:
    HAS_PANDAS_TA = False
    logger.warning("pandas-ta not installed. Using basic indicator calculations.")


class IndicatorStrategy(str, Enum):
    RSI = "rsi"
    EMA_CROSS = "ema"
    MACD = "macd"
    BOLLINGER = "bb"
    VWAP = "vwap"


class IndicatorTrader:
    """
    Signal-based directional trading using technical indicators.
    """

    def __init__(
        self,
        exchange: BaseExchange,
        symbol: str = "BTC",
        strategy: IndicatorStrategy = IndicatorStrategy.RSI,
        timeframe: str = "15m",
        size_usd: float = 100.0,
        leverage: int = 1,
        # RSI params
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        # EMA params
        ema_fast: int = 9,
        ema_slow: int = 21,
        # MACD params
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        # BB params
        bb_period: int = 20,
        bb_std: float = 2.0,
        # Candle lookback
        candle_limit: int = 100,
    ):
        self.exchange = exchange
        self.symbol = symbol
        self.strategy = strategy
        self.timeframe = timeframe
        self.size_usd = min(size_usd, get_config().risk.max_position_usd)
        self.leverage = min(leverage, get_config().risk.max_leverage)

        # Strategy params
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.candle_limit = candle_limit

        self.session = SessionStats(
            session_id=str(uuid.uuid4())[:8],
            mode=TradingMode.INDICATOR,
            exchange=exchange.name.value,
            symbol=symbol,
        )
        self._running = False
        self._current_position: Optional[OrderSide] = None
        self._last_signal: Optional[str] = None

    # ─── Main Loop ────────────────────────────────────────────────────────────

    async def run(self, check_interval_seconds: int = 60):
        """Run strategy loop, checking for signals at each interval."""
        self._running = True
        logger.info(
            f"📊 Indicator Trader | "
            f"Exchange: {self.exchange.name.value} | "
            f"Strategy: {self.strategy.value.upper()} | "
            f"Timeframe: {self.timeframe} | "
            f"Size: ${self.size_usd}"
        )

        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Indicator tick error: {e}")
            await asyncio.sleep(check_interval_seconds)

    async def _tick(self):
        """One iteration: fetch candles → compute signal → act."""
        # Fetch candles
        candles = await self.exchange.fetch_candles(
            self.symbol, self.timeframe, self.candle_limit
        )
        if len(candles) < 30:
            logger.warning(f"Not enough candles: {len(candles)}")
            return

        # Build DataFrame
        df = pd.DataFrame(candles)
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Compute signal
        signal, reason = self._compute_signal(df)

        if signal == self._last_signal:
            logger.debug(f"Signal unchanged: {signal} ({reason})")
            return

        logger.info(f"🔔 Signal: {signal} | Reason: {reason}")
        self._last_signal = signal

        # Act on signal
        if signal == "long":
            await self._enter_long()
        elif signal == "short":
            await self._enter_short()
        elif signal == "close":
            await self._close_current()

    def _compute_signal(self, df: pd.DataFrame) -> tuple[Optional[str], str]:
        """Returns (signal, reason) where signal is 'long', 'short', 'close', or None."""
        if self.strategy == IndicatorStrategy.RSI:
            return self._signal_rsi(df)
        elif self.strategy == IndicatorStrategy.EMA_CROSS:
            return self._signal_ema_cross(df)
        elif self.strategy == IndicatorStrategy.MACD:
            return self._signal_macd(df)
        elif self.strategy == IndicatorStrategy.BOLLINGER:
            return self._signal_bollinger(df)
        elif self.strategy == IndicatorStrategy.VWAP:
            return self._signal_vwap(df)
        return None, "unknown strategy"

    # ─── Signal Logic ─────────────────────────────────────────────────────────

    def _signal_rsi(self, df: pd.DataFrame) -> tuple[Optional[str], str]:
        """RSI Mean Reversion."""
        if HAS_PANDAS_TA:
            df.ta.rsi(length=self.rsi_period, append=True)
            col = f"RSI_{self.rsi_period}"
        else:
            # Manual RSI
            delta = df["close"].diff()
            gain = delta.clip(lower=0).rolling(self.rsi_period).mean()
            loss = (-delta.clip(upper=0)).rolling(self.rsi_period).mean()
            rs = gain / (loss + 1e-10)
            df[f"RSI_{self.rsi_period}"] = 100 - (100 / (1 + rs))
            col = f"RSI_{self.rsi_period}"

        rsi = df[col].iloc[-1]
        prev_rsi = df[col].iloc[-2]

        if rsi < self.rsi_oversold:
            return "long", f"RSI={rsi:.1f} (oversold < {self.rsi_oversold})"
        elif rsi > self.rsi_overbought:
            return "short", f"RSI={rsi:.1f} (overbought > {self.rsi_overbought})"
        elif self._current_position == OrderSide.LONG and rsi > 50:
            return "close", f"RSI={rsi:.1f} (exit long)"
        elif self._current_position == OrderSide.SHORT and rsi < 50:
            return "close", f"RSI={rsi:.1f} (exit short)"
        return None, f"RSI={rsi:.1f} (neutral)"

    def _signal_ema_cross(self, df: pd.DataFrame) -> tuple[Optional[str], str]:
        """EMA Crossover strategy."""
        df["ema_fast"] = df["close"].ewm(span=self.ema_fast).mean()
        df["ema_slow"] = df["close"].ewm(span=self.ema_slow).mean()

        curr_fast = df["ema_fast"].iloc[-1]
        curr_slow = df["ema_slow"].iloc[-1]
        prev_fast = df["ema_fast"].iloc[-2]
        prev_slow = df["ema_slow"].iloc[-2]

        bullish_cross = (curr_fast > curr_slow) and (prev_fast <= prev_slow)
        bearish_cross = (curr_fast < curr_slow) and (prev_fast >= prev_slow)

        if bullish_cross:
            return "long", f"EMA{self.ema_fast} crossed above EMA{self.ema_slow}"
        elif bearish_cross:
            return "short", f"EMA{self.ema_fast} crossed below EMA{self.ema_slow}"
        elif self._current_position == OrderSide.LONG and curr_fast < curr_slow:
            return "close", "EMA bearish — exit long"
        elif self._current_position == OrderSide.SHORT and curr_fast > curr_slow:
            return "close", "EMA bullish — exit short"
        return None, f"EMA{self.ema_fast}={curr_fast:.2f} EMA{self.ema_slow}={curr_slow:.2f}"

    def _signal_macd(self, df: pd.DataFrame) -> tuple[Optional[str], str]:
        """MACD Histogram momentum."""
        ema_fast = df["close"].ewm(span=self.macd_fast).mean()
        ema_slow = df["close"].ewm(span=self.macd_slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal).mean()
        histogram = macd_line - signal_line

        curr_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]

        if curr_hist > 0 and prev_hist <= 0:
            return "long", f"MACD histogram turned positive ({curr_hist:.2f})"
        elif curr_hist < 0 and prev_hist >= 0:
            return "short", f"MACD histogram turned negative ({curr_hist:.2f})"
        elif self._current_position == OrderSide.LONG and curr_hist < 0:
            return "close", "MACD negative — exit long"
        elif self._current_position == OrderSide.SHORT and curr_hist > 0:
            return "close", "MACD positive — exit short"
        return None, f"MACD hist={curr_hist:.4f}"

    def _signal_bollinger(self, df: pd.DataFrame) -> tuple[Optional[str], str]:
        """Bollinger Band bounce strategy."""
        sma = df["close"].rolling(self.bb_period).mean()
        std = df["close"].rolling(self.bb_period).std()
        upper = sma + (std * self.bb_std)
        lower = sma - (std * self.bb_std)

        price = df["close"].iloc[-1]
        upper_val = upper.iloc[-1]
        lower_val = lower.iloc[-1]
        mid_val = sma.iloc[-1]

        if price <= lower_val:
            return "long", f"Price at lower BB ({price:.2f} ≤ {lower_val:.2f})"
        elif price >= upper_val:
            return "short", f"Price at upper BB ({price:.2f} ≥ {upper_val:.2f})"
        elif self._current_position == OrderSide.LONG and price >= mid_val:
            return "close", "Price at midline — exit long"
        elif self._current_position == OrderSide.SHORT and price <= mid_val:
            return "close", "Price at midline — exit short"
        return None, f"Price={price:.2f} BB=[{lower_val:.2f}, {upper_val:.2f}]"

    def _signal_vwap(self, df: pd.DataFrame) -> tuple[Optional[str], str]:
        """VWAP-based signal."""
        df["typical"] = (df["high"] + df["low"] + df["close"]) / 3
        df["vwap"] = (
            (df["typical"] * df["volume"]).cumsum() /
            df["volume"].cumsum()
        )
        price = df["close"].iloc[-1]
        vwap = df["vwap"].iloc[-1]
        prev_price = df["close"].iloc[-2]
        prev_vwap = df["vwap"].iloc[-2]

        above_vwap = price > vwap
        was_below_vwap = prev_price < prev_vwap

        if above_vwap and was_below_vwap:
            return "long", f"Price crossed above VWAP ({vwap:.2f})"
        elif not above_vwap and not was_below_vwap:
            return "short", f"Price crossed below VWAP ({vwap:.2f})"
        return None, f"Price={price:.2f} VWAP={vwap:.2f}"

    # ─── Order Execution ──────────────────────────────────────────────────────

    async def _enter_long(self):
        """Close any short, then go long."""
        if self._current_position == OrderSide.SHORT:
            await self._close_current()

        try:
            ticker = await self.exchange.fetch_ticker(self.symbol)
            size = self.size_usd / ticker.mid

            order = await self.exchange.place_market_order(
                symbol=self.symbol,
                side=OrderSide.LONG,
                size=size,
                leverage=self.leverage,
            )
            self._current_position = OrderSide.LONG
            self.session.total_trades += 1
            self.session.total_volume_usd += self.size_usd
            logger.success(f"📗 Entered LONG {size:.4f} {self.symbol}")
        except Exception as e:
            logger.error(f"Long entry failed: {e}")

    async def _enter_short(self):
        """Close any long, then go short."""
        if self._current_position == OrderSide.LONG:
            await self._close_current()

        try:
            ticker = await self.exchange.fetch_ticker(self.symbol)
            size = self.size_usd / ticker.mid

            order = await self.exchange.place_market_order(
                symbol=self.symbol,
                side=OrderSide.SHORT,
                size=size,
                leverage=self.leverage,
            )
            self._current_position = OrderSide.SHORT
            self.session.total_trades += 1
            self.session.total_volume_usd += self.size_usd
            logger.success(f"📕 Entered SHORT {size:.4f} {self.symbol}")
        except Exception as e:
            logger.error(f"Short entry failed: {e}")

    async def _close_current(self):
        if self._current_position is None:
            return
        try:
            await self.exchange.close_position(self.symbol)
            self._current_position = None
            self.session.total_trades += 1
            logger.success(f"🔒 Closed position")
        except Exception as e:
            logger.error(f"Close failed: {e}")

    def stop(self):
        self._running = False
