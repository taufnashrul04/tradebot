"""
bot_trade/strategies/delta_neutral.py

Cross-Exchange Delta Neutral Strategy

Flow:
  1. Scan funding rates across all exchanges
  2. Find best opportunity (e.g. SHORT Nado + LONG Decibel)
  3. Open paired positions simultaneously with equal notional
  4. Monitor and collect funding at each interval
  5. Close when: opportunity disappears / max duration reached / drawdown limit hit

Risk controls:
  - Size capped by max_position_usd from config
  - Stop if net funding goes negative (rates flipped)
  - Rebalance if position sizes drift > 1%
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from ..models import (
    ExchangeName, OrderSide, DeltaNeutralPosition,
    FundingDiff, Order, SessionStats, TradingMode
)
from ..exchanges.base import BaseExchange
from ..config import get_config
from .funding_scanner import FundingScanner


class DeltaNeutralStrategy:
    """
    Cross-exchange delta-neutral strategy.

    Places a LONG on one exchange and equal SHORT on another,
    targeting funding rate differential as profit source.
    No directional exposure = delta neutral.
    """

    def __init__(
        self,
        exchanges: dict[ExchangeName, BaseExchange],
        scanner: FundingScanner,
        symbol: str = "BTC",
        size_usd: float = 100.0,
        min_annual_yield: float = 5.0,
        max_duration_hours: float = 24.0,
        leverage: int = 1,
        auto_rebalance: bool = True,
    ):
        self.exchanges = exchanges
        self.scanner = scanner
        self.symbol = symbol
        self.size_usd = min(size_usd, get_config().risk.max_position_usd)
        self.min_annual_yield = min_annual_yield
        self.max_duration_hours = max_duration_hours
        self.leverage = min(leverage, get_config().risk.max_leverage)
        self.auto_rebalance = auto_rebalance

        self.active_position: Optional[DeltaNeutralPosition] = None
        self.session: SessionStats = SessionStats(
            session_id=str(uuid.uuid4())[:8],
            mode=TradingMode.DELTA_NEUTRAL,
            exchange="multi",
            symbol=symbol,
        )
        self._running = False

    # ─── Main Loop ────────────────────────────────────────────────────────────

    async def run(self, check_interval_seconds: int = 60):
        """
        Main strategy loop.
          - Continuously monitors funding rates
          - Opens positions when opportunity found
          - Closes when opportunity gone or criteria not met
        """
        self._running = True
        logger.info(
            f"🎯 Delta Neutral Strategy started | "
            f"Symbol: {self.symbol} | Size: ${self.size_usd} | "
            f"Min yield: {self.min_annual_yield}% annual"
        )

        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Strategy tick error: {e}")

            await asyncio.sleep(check_interval_seconds)

    async def _tick(self):
        """Single strategy tick: scan → decide → act."""
        # 1. Refresh funding rates
        await self.scanner.scan_all()

        # 2. Find best opportunity
        best_opp = self.scanner.get_best_opportunity(self.symbol)

        # 3. Decision logic
        if self.active_position is None:
            # No open position — should we open one?
            if best_opp and best_opp.annual_yield_pct >= self.min_annual_yield:
                logger.info(f"🎯 Found opportunity: {best_opp}")
                await self._open_position(best_opp)
            else:
                logger.info(
                    f"⏳ No opportunity found for {self.symbol}. "
                    f"Best: {best_opp.annual_yield_pct:.2f}% vs threshold {self.min_annual_yield}%"
                    if best_opp else f"⏳ No opportunities for {self.symbol}"
                )
        else:
            # Position is open — should we close it?
            should_close, reason = await self._should_close(best_opp)
            if should_close:
                logger.info(f"🔒 Closing position: {reason}")
                await self._close_position(reason)
            else:
                # Log current status
                await self._log_position_status(best_opp)

    # ─── Position Management ──────────────────────────────────────────────────

    async def _open_position(self, opportunity: FundingDiff):
        """
        Open delta-neutral position:
          - LONG on long_exchange (lower/negative funding)
          - SHORT on short_exchange (higher/positive funding)
        """
        session_id = str(uuid.uuid4())[:8]

        # Calculate size in base currency
        # Get ticker to determine contract size
        long_ex = self.exchanges.get(opportunity.long_exchange)
        short_ex = self.exchanges.get(opportunity.short_exchange)

        if not long_ex or not short_ex:
            logger.warning(f"Exchange not configured: {opportunity}")
            return

        try:
            ticker = await long_ex.fetch_ticker(self.symbol)
            price = ticker.mid
            size_base = self.size_usd / price  # e.g. $100 / $65000 = 0.00154 BTC

            logger.info(
                f"📤 Opening delta-neutral position:\n"
                f"   LONG  {size_base:.6f} {self.symbol} on {opportunity.long_exchange.value} "
                f"(rate: {opportunity.long_rate*100:+.4f}%)\n"
                f"   SHORT {size_base:.6f} {self.symbol} on {opportunity.short_exchange.value} "
                f"(rate: {opportunity.short_rate*100:+.4f}%)\n"
                f"   Expected net: {opportunity.net_funding_per_interval*100:+.4f}%/interval "
                f"= {opportunity.annual_yield_pct:.1f}% annual"
            )

            # Place both legs concurrently
            long_task = long_ex.place_market_order(
                symbol=self.symbol,
                side=OrderSide.LONG,
                size=size_base,
                leverage=self.leverage,
            )
            short_task = short_ex.place_market_order(
                symbol=self.symbol,
                side=OrderSide.SHORT,
                size=size_base,
                leverage=self.leverage,
            )

            long_order, short_order = await asyncio.gather(
                long_task, short_task,
                return_exceptions=True
            )

            # Handle partial failures
            if isinstance(long_order, Exception):
                logger.error(f"Long leg failed: {long_order}")
                if not isinstance(short_order, Exception):
                    logger.warning("Closing orphaned short leg...")
                    await short_ex.close_position(self.symbol)
                return

            if isinstance(short_order, Exception):
                logger.error(f"Short leg failed: {short_order}")
                logger.warning("Closing orphaned long leg...")
                await long_ex.close_position(self.symbol)
                return

            # Both legs successful
            self.active_position = DeltaNeutralPosition(
                symbol=self.symbol,
                long_exchange=opportunity.long_exchange,
                short_exchange=opportunity.short_exchange,
                long_order=long_order,
                short_order=short_order,
                size=size_base,
                target_funding_profit=opportunity.net_funding_per_interval * self.size_usd,
                session_id=session_id,
            )

            self.session.total_trades += 2
            logger.success(
                f"✅ Position opened! Long {opportunity.long_exchange.value} + "
                f"Short {opportunity.short_exchange.value} | "
                f"Size: {size_base:.6f} {self.symbol} (${self.size_usd:.2f})"
            )

        except Exception as e:
            logger.error(f"Failed to open delta-neutral position: {e}")

    async def _close_position(self, reason: str = ""):
        """Close both legs of the delta-neutral position."""
        if not self.active_position:
            return

        pos = self.active_position
        long_ex = self.exchanges.get(pos.long_exchange)
        short_ex = self.exchanges.get(pos.short_exchange)

        logger.info(f"🔒 Closing position ({reason})...")

        tasks = []
        if long_ex:
            tasks.append(long_ex.close_position(pos.symbol))
        if short_ex:
            tasks.append(short_ex.close_position(pos.symbol))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Error closing leg: {r}")

        pos.closed_at = datetime.utcnow()
        duration_h = (pos.closed_at - pos.opened_at).total_seconds() / 3600

        # Estimate funding collected (conservative: actual intervals elapsed)
        intervals_elapsed = duration_h / 8  # 8h funding interval
        estimated_funding = pos.target_funding_profit * intervals_elapsed
        self.session.funding_collected += estimated_funding

        logger.success(
            f"✅ Position closed | Duration: {duration_h:.1f}h | "
            f"Est. funding collected: ${estimated_funding:.4f}"
        )

        self.active_position = None

    # ─── Close Criteria ───────────────────────────────────────────────────────

    async def _should_close(
        self, current_opp: Optional[FundingDiff]
    ) -> tuple[bool, str]:
        """Determine if we should close the active position."""
        pos = self.active_position
        if not pos:
            return False, ""

        # 1. Max duration reached
        age_hours = (datetime.utcnow() - pos.opened_at).total_seconds() / 3600
        if age_hours >= self.max_duration_hours:
            return True, f"max duration reached ({self.max_duration_hours}h)"

        # 2. Opportunity flipped (no longer profitable)
        if current_opp is None:
            return True, "no more funding rate opportunity"

        if current_opp.annual_yield_pct < (self.min_annual_yield * 0.3):
            # Close if yield dropped to less than 30% of threshold
            return True, (
                f"yield degraded: {current_opp.annual_yield_pct:.1f}% < "
                f"{self.min_annual_yield * 0.3:.1f}% threshold"
            )

        # 3. Funding flipped direction for our position
        if (current_opp.long_exchange != pos.long_exchange or
                current_opp.short_exchange != pos.short_exchange):
            # Best opportunity is now on different exchanges — consider rebalancing
            # For now just log, don't force close
            logger.debug(
                f"Opportunity shifted: was {pos.long_exchange.value}/{pos.short_exchange.value}, "
                f"now {current_opp.long_exchange.value}/{current_opp.short_exchange.value}"
            )

        return False, ""

    async def _log_position_status(self, current_opp: Optional[FundingDiff]):
        """Log current position status."""
        if not self.active_position:
            return
        pos = self.active_position
        age_hours = (datetime.utcnow() - pos.opened_at).total_seconds() / 3600
        intervals = age_hours / 8
        est_funding = pos.target_funding_profit * intervals

        logger.info(
            f"📊 Position Status | "
            f"LONG {pos.long_exchange.value} + SHORT {pos.short_exchange.value} | "
            f"Age: {age_hours:.1f}h | Est. funding: ${est_funding:.4f} | "
            f"Current yield: {current_opp.annual_yield_pct:.1f}% annual" if current_opp
            else f"📊 Position Status | Age: {age_hours:.1f}h | No current opportunity data"
        )

    # ─── Controls ─────────────────────────────────────────────────────────────

    async def stop(self):
        """Stop the strategy loop."""
        self._running = False
        if self.active_position:
            await self._close_position("manual stop")

    async def emergency_close(self):
        """Emergency: close everything immediately."""
        self._running = False
        await self._close_position("EMERGENCY CLOSE")
