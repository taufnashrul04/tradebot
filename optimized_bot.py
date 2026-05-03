#!/usr/bin/env python3
"""
Optimized CCXT + Decibel Trading Bot with TP/SL
- Better signal logic (more selective)
- Auto Take Profit / Stop Loss
- Alternating LONG/SHORT for hedging
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide, Order

# Load environment
load_dotenv()


class OptimizedCCXTDecibelBot:
    """Optimized trading bot with TP/SL and better signals"""

    def __init__(
        self,
        analysis_exchange: str = "binance",
        symbol: str = "BTC/USDT",
        timeframe: str = "1m",
        leverage: int = 40,
        balance_usd: float = 20.0,
        per_position_usd: float = 5.0,
        take_profit_percent: float = 0.3,  # 0.3% TP
        stop_loss_percent: float = 0.5,  # 0.5% SL
        check_interval_seconds: float = 2.0,  # Check every 2 seconds
    ):
        self.analysis_exchange_name = analysis_exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.leverage = leverage
        self.balance_usd = balance_usd
        self.per_position_usd = per_position_usd
        self.take_profit_percent = take_profit_percent
        self.stop_loss_percent = stop_loss_percent
        self.check_interval_seconds = check_interval_seconds

        # Initialize CCXT exchange for analysis
        self.ccxt_exchange = getattr(ccxt, analysis_exchange)({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
        })

        # Initialize Decibel for execution
        self.decibel = DecibelExchange()

        # Trading state
        self.positions: List[Order] = []
        self.total_volume = 0.0
        self.total_pnl = 0.0
        self.cycle_count = 0
        self.last_direction = None  # Track last direction for alternating

    async def initialize(self):
        """Initialize exchanges"""
        print(f"🔧 Initializing {self.analysis_exchange_name} for analysis...")
        await self.ccxt_exchange.load_markets()

        print(f"🔧 Initializing Decibel for execution...")
        print(f"   TP: {self.take_profit_percent}%, SL: {self.stop_loss_percent}%")
        print(f"   Check interval: {self.check_interval_seconds}s")

        print("✅ Bot initialized!")

    async def fetch_market_data(self, limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV data from CCXT exchange"""
        print(f"📊 Fetching {self.symbol} data from {self.analysis_exchange_name}...")

        ohlcv = await self.ccxt_exchange.fetch_ohlcv(
            self.symbol,
            timeframe=self.timeframe,
            limit=limit
        )

        df = pd.DataFrame(
            ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        print(f"✅ Fetched {len(df)} candles")
        return df

    def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate technical indicators"""
        print("🧮 Calculating indicators...")

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        histogram = macd - signal

        # Bollinger Bands
        sma_20 = df['close'].rolling(window=20).mean()
        std_20 = df['close'].rolling(window=20).std()
        upper_band = sma_20 + (std_20 * 2)
        lower_band = sma_20 - (std_20 * 2)

        # Moving Averages
        sma_50 = df['close'].rolling(window=50).mean()
        ema_9 = df['close'].ewm(span=9).mean()

        # Price momentum
        price_change = df['close'].pct_change(5).iloc[-1] * 100  # 5-candle momentum

        indicators = {
            'rsi': rsi.iloc[-1] if len(rsi) > 0 else 50,
            'macd': macd.iloc[-1] if len(macd) > 0 else 0,
            'signal': signal.iloc[-1] if len(signal) > 0 else 0,
            'histogram': histogram.iloc[-1] if len(histogram) > 0 else 0,
            'upper_band': upper_band.iloc[-1] if len(upper_band) > 0 else 0,
            'lower_band': lower_band.iloc[-1] if len(lower_band) > 0 else 0,
            'sma_50': sma_50.iloc[-1] if len(sma_50) > 0 else 0,
            'ema_9': ema_9.iloc[-1] if len(ema_9) > 0 else 0,
            'current_price': df['close'].iloc[-1] if len(df) > 0 else 0,
            'price_change': price_change,
        }

        print(f"✅ RSI: {indicators['rsi']:.2f}, MACD: {indicators['macd']:.4f}, Price Change: {indicators['price_change']:.2f}%")
        return indicators

    def generate_signal(self, indicators: Dict) -> Tuple[str, float]:
        """Generate trading signal with better logic"""
        rsi = indicators['rsi']
        macd = indicators['macd']
        signal = indicators['signal']
        histogram = indicators['histogram']
        current_price = indicators['current_price']
        upper_band = indicators['upper_band']
        lower_band = indicators['lower_band']
        price_change = indicators['price_change']

        # Signal strength (0-100)
        strength = 0

        # RSI signals (more selective)
        if rsi < 30:
            strength += 30  # Strongly oversold - potential LONG
        elif rsi > 70:
            strength += 30  # Strongly overbought - potential SHORT
        elif rsi < 40:
            strength += 15  # Mildly oversold
        elif rsi > 60:
            strength += 15  # Mildly overbought

        # MACD signals (stronger weight)
        if macd > signal and histogram > 0:
            strength += 35  # Bullish momentum - LONG
        elif macd < signal and histogram < 0:
            strength += 35  # Bearish momentum - SHORT

        # Bollinger Bands
        if current_price < lower_band:
            strength += 20  # Price below lower band - LONG
        elif current_price > upper_band:
            strength += 20  # Price above upper band - SHORT

        # Price momentum (new)
        if price_change > 0.5:
            strength += 15  # Strong upward momentum - LONG
        elif price_change < -0.5:
            strength += 15  # Strong downward momentum - SHORT

        # Trend direction
        if macd > 0:
            strength += 10  # Uptrend bias
        else:
            strength -= 10  # Downtrend bias

        # Determine direction (higher threshold for more selective signals)
        if strength >= 70:
            return "LONG", strength
        elif strength <= 30:
            return "SHORT", 100 - strength
        else:
            # If neutral, alternate based on last direction
            if self.last_direction == "LONG":
                return "SHORT", 45
            elif self.last_direction == "SHORT":
                return "LONG", 55
            else:
                # First trade - use MACD direction
                if macd > signal:
                    return "LONG", 52
                else:
                    return "SHORT", 48

    async def execute_trade(
        self,
        side: str,
        size_btc: float,
        limit_price: Optional[float] = None,
        use_market: bool = False,
    ) -> Optional[Order]:
        """Execute trade on Decibel"""
        print(f"🚀 Executing {side} order: {size_btc:.6f} BTC")

        order_side = OrderSide.LONG if side == "LONG" else OrderSide.SHORT

        try:
            if not use_market:
                # Try limit order first (maker fee - cheaper)
                if limit_price:
                    price = limit_price
                else:
                    # Get current price from Decibel ticker
                    try:
                        ticker = await self.decibel.fetch_ticker('BTC')
                        current_price = ticker.last if ticker.last else ticker.mark_price

                        if current_price > 0:
                            # Set limit price very close to current (0.01% away)
                            if side == "LONG":
                                price = current_price * 0.9999  # 0.01% below current
                            else:
                                price = current_price * 1.0001  # 0.01% above current
                        else:
                            price = None
                    except Exception as e:
                        print(f"⚠️  Failed to fetch ticker: {e}")
                        price = None

                if price:
                    print(f"   📝 Limit order at ${price:.2f} (maker fee: 0.0110%)")

                    try:
                        order = await self.decibel.place_limit_order(
                            symbol='BTC',
                            side=order_side,
                            size=size_btc,
                            price=price,
                            leverage=self.leverage,
                        )
                        print(f"✅ Limit order placed: {order.order_id}")

                        # Wait and check if filled
                        await asyncio.sleep(2)  # Wait 2 seconds for fill

                        # Check if position exists (means order filled)
                        positions = await self.decibel.fetch_positions()
                        if positions:
                            print(f"✅ Limit order filled!")
                            self.positions.append(order)
                            self.total_volume += size_btc * price
                            self.last_direction = side
                            return order
                        else:
                            print(f"⚠️  Limit order not filled - falling back to market order")

                    except Exception as e:
                        print(f"⚠️  Limit order failed: {e} - falling back to market order")

            # Fallback to market order (taker fee - more expensive but reliable)
            print(f"   📊 Market order (taker fee: 0.0340%)")
            order = await self.decibel.place_market_order(
                symbol='BTC',
                side=order_side,
                size=size_btc,
                leverage=self.leverage,
            )
            print(f"✅ Market order placed: {order.order_id}")

            self.positions.append(order)
            self.total_volume += size_btc * order.price if order.price else 0
            self.last_direction = side

            return order

        except Exception as e:
            print(f"❌ Order failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def monitor_and_close_positions(
        self,
        btc_size: float,
        hold_time_seconds: float = 30.0,
    ) -> Dict:
        """Monitor positions and close on TP/SL or timeout"""
        print(f"👀 Monitoring positions (TP: {self.take_profit_percent}%, SL: {self.stop_loss_percent}%)...")

        start_time = time.time()
        total_profit = 0.0
        total_loss = 0.0
        closed_count = 0

        try:
            while True:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= hold_time_seconds:
                    print(f"⏱️  Timeout after {elapsed:.1f}s - closing remaining positions")
                    break

                # Get current positions
                positions = await self.decibel.fetch_positions()

                if not positions:
                    print("✅ All positions closed")
                    break

                # Get current price
                try:
                    ticker = await self.decibel.fetch_ticker('BTC')
                    current_price = ticker.last if ticker.last else ticker.mark_price
                except:
                    print("⚠️  Failed to fetch ticker - using last known price")
                    current_price = None

                if not current_price:
                    await asyncio.sleep(self.check_interval_seconds)
                    continue

                # Check each position
                for pos in positions:
                    try:
                        # Calculate PnL
                        if pos.entry_price:
                            if pos.side == OrderSide.LONG:
                                pnl_percent = ((current_price - pos.entry_price) / pos.entry_price) * 100
                            else:
                                pnl_percent = ((pos.entry_price - current_price) / pos.entry_price) * 100

                            position_value = pos.size * pos.entry_price * self.leverage
                            pnl_usd = pnl_percent * position_value / 100

                            print(f"   {pos.side}: PnL {pnl_percent:+.3f}% (${pnl_usd:+.4f})")

                            # Check TP/SL
                            if pnl_percent >= self.take_profit_percent:
                                print(f"   🎯 TAKE PROFIT triggered! ({pnl_percent:.3f}% >= {self.take_profit_percent}%)")
                                await self.close_single_position(pos, current_price)
                                total_profit += pnl_usd
                                closed_count += 1

                            elif pnl_percent <= -self.stop_loss_percent:
                                print(f"   🛑 STOP LOSS triggered! ({pnl_percent:.3f}% <= -{self.stop_loss_percent}%)")
                                await self.close_single_position(pos, current_price)
                                total_loss += abs(pnl_usd)
                                closed_count += 1

                    except Exception as e:
                        print(f"   ⚠️  Error monitoring position: {e}")

                # Wait before next check
                await asyncio.sleep(self.check_interval_seconds)

            # Close any remaining positions
            remaining_positions = await self.decibel.fetch_positions()
            if remaining_positions:
                print(f"🔄 Closing {len(remaining_positions)} remaining position(s)...")
                for pos in remaining_positions:
                    try:
                        await self.close_single_position(pos, None)
                    except Exception as e:
                        print(f"   ❌ Failed to close: {e}")

            return {
                'total_profit': total_profit,
                'total_loss': total_loss,
                'closed_count': closed_count,
                'elapsed_time': elapsed,
            }

        except Exception as e:
            print(f"❌ Error monitoring positions: {e}")
            return {
                'total_profit': total_profit,
                'total_loss': total_loss,
                'closed_count': closed_count,
                'elapsed_time': elapsed,
            }

    async def close_single_position(self, pos: Order, current_price: Optional[float]):
        """Close a single position"""
        close_side = OrderSide.SHORT if pos.side == OrderSide.LONG else OrderSide.LONG

        try:
            close_order = await self.decibel.place_market_order(
                symbol='BTC',
                side=close_side,
                size=pos.size,
                leverage=self.leverage,
                reduce_only=True,
            )
            print(f"   ✅ Closed position: {close_order.order_id}")
        except Exception as e:
            print(f"   ❌ Failed to close: {e}")

    async def close_all_positions(self) -> float:
        """Close ALL open positions and return total PnL"""
        print(f"🔄 Checking and closing all positions...")

        total_pnl = 0.0

        try:
            positions = await self.decibel.fetch_positions()

            if not positions:
                print("✅ No open positions")
                return total_pnl

            print(f"📊 Found {len(positions)} open position(s)")

            for pos in positions:
                print(f"   Closing {pos.side} position: {pos.size:.6f} BTC")

                close_side = OrderSide.SHORT if pos.side == OrderSide.LONG else OrderSide.LONG

                try:
                    close_order = await self.decibel.place_market_order(
                        symbol='BTC',
                        side=close_side,
                        size=pos.size,
                        leverage=self.leverage,
                        reduce_only=True,
                    )

                    # Calculate PnL
                    if pos.entry_price and close_order.price:
                        if pos.side == OrderSide.LONG:
                            pnl = (close_order.price - pos.entry_price) * pos.size
                        else:
                            pnl = (pos.entry_price - close_order.price) * pos.size
                        total_pnl += pnl
                        print(f"   ✅ Closed: PnL ${pnl:.4f}")

                except Exception as e:
                    print(f"   ❌ Failed to close: {e}")

            print(f"✅ All positions closed. Total PnL: ${total_pnl:.4f}")
            return total_pnl

        except Exception as e:
            print(f"❌ Error closing positions: {e}")
            return total_pnl

    async def cancel_all_limit_orders(self) -> int:
        """Cancel all pending limit orders (NOT SUPPORTED by Decibel API)"""
        print("⚠️  Decibel API does NOT support canceling limit orders")
        print("   Pending limit orders must be canceled manually in the UI")
        print("   https://app.decibel.trade/")
        return 0

    async def run_cycle(self, hold_time_seconds: float = 30.0):
        """Run one trading cycle with TP/SL"""
        print(f"\n{'='*60}")
        print(f"🔄 Cycle {self.cycle_count + 1}")
        print(f"{'='*60}")

        # 0. Close any existing positions first
        await self.close_all_positions()

        # 0.5. Try to cancel any pending limit orders (not supported by API)
        await self.cancel_all_limit_orders()

        # 1. Fetch market data
        df = await self.fetch_market_data()

        # 2. Calculate indicators
        indicators = self.calculate_indicators(df)

        # 3. Generate signal
        signal, strength = self.generate_signal(indicators)
        print(f"📈 Signal: {signal} (strength: {strength:.0f}/100)")

        if signal == "NEUTRAL":
            print("⏸️  No signal - skipping this cycle")
            return

        # 4. Calculate position size
        position_value = self.per_position_usd * self.leverage
        size_btc = position_value / indicators['current_price']

        # 5. Execute trade (try limit first for fee savings)
        order = await self.execute_trade(signal, size_btc, use_market=False)

        if not order:
            return

        # 6. Monitor and close positions with TP/SL
        result = await self.monitor_and_close_positions(
            btc_size=size_btc,
            hold_time_seconds=hold_time_seconds,
        )

        # 7. Try to cancel any pending limit orders again
        await self.cancel_all_limit_orders()

        # 8. Update stats
        self.cycle_count += 1
        cycle_pnl = result['total_profit'] - result['total_loss']
        self.total_pnl += cycle_pnl

        print(f"\n📊 Cycle Summary:")
        print(f"   Total Volume: ${self.total_volume:.2f}")
        print(f"   Total PnL: ${self.total_pnl:.4f}")
        print(f"   Cycles: {self.cycle_count}")
        print(f"   TP Hits: {result['closed_count']}")
        print(f"   Time: {result['elapsed_time']:.1f}s")

    async def run_strategy(
        self,
        target_volume_usd: float = 100000.0,
        hold_time_seconds: float = 30.0,
        max_cycles: Optional[int] = None,
    ):
        """Run trading strategy until target reached"""
        print(f"\n🎯 Starting Optimized Strategy")
        print(f"   Target Volume: ${target_volume_usd:,.2f}")
        print(f"   Hold Time: {hold_time_seconds}s")
        print(f"   Max Cycles: {max_cycles or 'Unlimited'}")
        print(f"   Leverage: {self.leverage}x")
        print(f"   Balance: ${self.balance_usd}")
        print(f"   Per Position: ${self.per_position_usd}")
        print(f"   TP: {self.take_profit_percent}%")
        print(f"   SL: {self.stop_loss_percent}%")

        await self.initialize()

        cycle = 0
        while True:
            # Check max cycles
            if max_cycles and cycle >= max_cycles:
                print(f"\n🏁 Reached max cycles ({max_cycles})")
                break

            # Check target volume
            if self.total_volume >= target_volume_usd:
                print(f"\n🎉 Target volume reached! ${self.total_volume:,.2f}")
                break

            # Run cycle
            await self.run_cycle(hold_time_seconds)
            cycle += 1

            # Small delay between cycles
            await asyncio.sleep(2.0)

        # Final summary
        print(f"\n{'='*60}")
        print(f"🏁 Strategy Complete")
        print(f"{'='*60}")
        print(f"   Total Volume: ${self.total_volume:,.2f}")
        print(f"   Total PnL: ${self.total_pnl:.4f}")
        print(f"   Total Cycles: {self.cycle_count}")
        print(f"   Avg PnL/Cycle: ${self.total_pnl/self.cycle_count:.4f}" if self.cycle_count > 0 else "")

    async def close(self):
        """Close connections"""
        print("🔌 Closing connections...")
        await self.ccxt_exchange.close()
        print("✅ Closed!")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Optimized CCXT + Decibel Trading Bot")
    parser.add_argument("--exchange", default="binance", help="Analysis exchange")
    parser.add_argument("--symbol", default="BTC/USDT", help="Trading symbol")
    parser.add_argument("--timeframe", default="1m", help="Timeframe")
    parser.add_argument("--leverage", type=int, default=40, help="Leverage")
    parser.add_argument("--balance", type=float, default=20.0, help="Balance USD")
    parser.add_argument("--per-position", type=float, default=5.0, help="Per position USD")
    parser.add_argument("--target-volume", type=float, default=100000.0, help="Target volume USD")
    parser.add_argument("--hold-time", type=float, default=30.0, help="Hold time seconds")
    parser.add_argument("--max-cycles", type=int, default=None, help="Max cycles")
    parser.add_argument("--tp", type=float, default=0.3, help="Take Profit %")
    parser.add_argument("--sl", type=float, default=0.5, help="Stop Loss %")

    args = parser.parse_args()

    bot = OptimizedCCXTDecibelBot(
        analysis_exchange=args.exchange,
        symbol=args.symbol,
        timeframe=args.timeframe,
        leverage=args.leverage,
        balance_usd=args.balance,
        per_position_usd=args.per_position,
        take_profit_percent=args.tp,
        stop_loss_percent=args.sl,
    )

    try:
        await bot.run_strategy(
            target_volume_usd=args.target_volume,
            hold_time_seconds=args.hold_time,
            max_cycles=args.max_cycles,
        )
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
