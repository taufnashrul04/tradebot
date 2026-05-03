#!/usr/bin/env python3
"""
Strategi Trading Volume Tinggi dengan Limit Order + Auto Take Profit

Fitur:
- Limit order (maker fee 0.0110%)
- Auto close ketika profit tercapai
- Stop loss protection
- Real-time PnL monitoring
"""
import asyncio
import time
from typing import List, Dict, Optional
from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide, Order


class HighVolumeWithTPStrategy:
    """
    Strategi trading volume tinggi dengan limit order dan auto take profit.

    Features:
    - Limit order (maker fee 0.0110%)
    - Auto close ketika profit target tercapai
    - Stop loss protection
    - Real-time PnL monitoring
    """

    def __init__(
        self,
        balance_usd: float = 20.0,
        per_position_usd: float = 5.0,
        leverage: int = 40,
        target_daily_volume_usd: float = 100000.0,
        maker_fee_percent: float = 0.0110,
        taker_fee_percent: float = 0.0340,
        take_profit_percent: float = 0.5,  # 0.5% profit target
        stop_loss_percent: float = 1.0,  # 1% stop loss
        check_interval_seconds: float = 2.0  # Check PnL every 2 seconds
    ):
        self.balance_usd = balance_usd
        self.per_position_usd = per_position_usd
        self.leverage = leverage
        self.target_daily_volume_usd = target_daily_volume_usd
        self.maker_fee_percent = maker_fee_percent
        self.taker_fee_percent = taker_fee_percent
        self.take_profit_percent = take_profit_percent
        self.stop_loss_percent = stop_loss_percent
        self.check_interval_seconds = check_interval_seconds

        # Hitung parameter
        self.max_positions = int(balance_usd / per_position_usd)
        self.position_value_usd = per_position_usd * leverage
        self.total_cycle_volume_usd = self.position_value_usd * self.max_positions
        self.required_cycles = int(target_daily_volume_usd / self.total_cycle_volume_usd)

        # Hitung fee savings
        self.fee_savings_percent = taker_fee_percent - maker_fee_percent
        self.fee_savings_per_cycle = self.total_cycle_volume_usd * (self.fee_savings_percent / 100)

        # Tracking
        self.total_volume_usd = 0.0
        self.total_cycles = 0
        self.total_profit_usd = 0.0
        self.total_loss_usd = 0.0
        self.start_time = None
        self.positions: List[Order] = []

        print("\n" + "="*70)
        print("STRATEGI VOLUME TINGGI - LIMIT ORDER + AUTO TAKE PROFIT")
        print("="*70)
        print(f"💰 Saldo: ${balance_usd:.2f}")
        print(f"📊 Per posisi: ${per_position_usd:.2f}")
        print(f"⚡ Leverage: {leverage}x")
        print(f"🎯 Target volume: ${target_daily_volume_usd:,.0f}")
        print(f"📈 Maks posisi: {self.max_positions}")
        print(f"💵 Nilai per posisi: ${self.position_value_usd:.2f}")
        print(f"🔄 Volume per cycle: ${self.total_cycle_volume_usd:.2f}")
        print(f"🎯 Cycles dibutuhkan: {self.required_cycles}")
        print(f"\n💰 Fee Comparison:")
        print(f"   Maker fee: {maker_fee_percent:.4f}%")
        print(f"   Taker fee: {taker_fee_percent:.4f}%")
        print(f"   Savings: {self.fee_savings_percent:.4f}%")
        print(f"   Savings per cycle: ${self.fee_savings_per_cycle:.4f}")
        print(f"   Total savings: ${self.fee_savings_per_cycle * self.required_cycles:.2f}")
        print(f"\n🎯 Risk Management:")
        print(f"   Take Profit: {take_profit_percent:.2f}%")
        print(f"   Stop Loss: {stop_loss_percent:.2f}%")
        print(f"   Check Interval: {check_interval_seconds}s")
        print("="*70)

    async def get_btc_size_and_prices(self, exchange: DecibelExchange) -> tuple:
        """
        Hitung ukuran posisi BTC dan dapatkan harga.

        Returns:
            (btc_size, bid_price, ask_price, spread_percent)
        """
        ticker = await exchange.fetch_ticker('BTC')
        if not ticker or not ticker.last:
            raise ValueError("Tidak bisa mengambil harga BTC")

        btc_price = float(ticker.last)
        bid_price = float(ticker.bid) if ticker.bid else btc_price
        ask_price = float(ticker.ask) if ticker.ask else btc_price
        spread = ask_price - bid_price
        spread_percent = (spread / btc_price) * 100

        btc_size = self.per_position_usd * self.leverage / btc_price

        print(f"\n💰 Harga BTC: ${btc_price:.2f}")
        print(f"   Bid: ${bid_price:.2f}")
        print(f"   Ask: ${ask_price:.2f}")
        print(f"   Spread: {spread_percent:.4f}%")
        print(f"📊 Ukuran posisi: {btc_size:.6f} BTC")
        print(f"💵 Nilai posisi: ${btc_size * btc_price:.2f}")

        return btc_size, bid_price, ask_price, spread_percent

    def calculate_limit_price(
        self,
        side: OrderSide,
        bid_price: float,
        ask_price: float,
        spread_percent: float
    ) -> float:
        """
        Hitung harga limit untuk maker order.

        Untuk maker fee, order harus ditempatkan di order book:
        - LONG: sedikit di bawah bid price
        - SHORT: sedikit di atas ask price

        Args:
            side: Order side
            bid_price: Bid price
            ask_price: Ask price
            spread_percent: Spread percent

        Returns:
            Limit price
        """
        # Gunakan 50% dari spread untuk memastikan order terisi tapi tetap maker
        spread_buffer = (ask_price - bid_price) * 0.5

        if side == OrderSide.LONG:
            # LONG: limit di bawah bid (masih di order book)
            limit_price = bid_price - spread_buffer
        else:
            # SHORT: limit di atas ask (masih di order book)
            limit_price = ask_price + spread_buffer

        return limit_price

    async def open_position(
        self,
        exchange: DecibelExchange,
        side: OrderSide,
        btc_size: float,
        limit_price: float
    ) -> Order:
        """Buka posisi dengan limit order (maker fee)."""
        print(f"\n🚀 Membuka posisi {side.value} {btc_size:.6f} BTC @ ${limit_price:.2f}")

        order = await exchange.place_limit_order(
            symbol='BTC',
            side=side,
            size=btc_size,
            price=limit_price,
            leverage=self.leverage
        )

        print(f"✅ Posisi dibuka: {order.order_id}")
        print(f"   Harga: ${order.price:.2f}")
        print(f"   Ukuran: {order.size:.6f} BTC")

        return order

    async def close_position(
        self,
        exchange: DecibelExchange,
        side: OrderSide,
        btc_size: float,
        limit_price: float
    ) -> Order:
        """Tutup posisi dengan limit order (maker fee)."""
        print(f"\n🔒 Menutup posisi {side.value} {btc_size:.6f} BTC @ ${limit_price:.2f}")

        # Untuk menutup, kita buka posisi berlawanan
        close_side = OrderSide.SHORT if side == OrderSide.LONG else OrderSide.LONG

        order = await exchange.place_limit_order(
            symbol='BTC',
            side=close_side,
            size=btc_size,
            price=limit_price,
            leverage=self.leverage,
            reduce_only=True
        )

        print(f"✅ Posisi ditutup: {order.order_id}")
        print(f"   Harga: ${order.price:.2f}")

        return order

    async def monitor_and_close_positions(
        self,
        exchange: DecibelExchange,
        positions: List[Order],
        btc_size: float,
        hold_time_seconds: float = 30.0
    ) -> Dict:
        """
        Monitor posisi dan close ketika TP/SL tercapai.

        Args:
            exchange: Decibel exchange
            positions: List of open positions
            btc_size: Size of each position
            hold_time_seconds: Maximum time to monitor (default 30s)

        Returns:
            Dict with results
        """
        print(f"\n👀 Monitoring {len(positions)} posisi...")
        print(f"   Take Profit: {self.take_profit_percent:.2f}%")
        print(f"   Stop Loss: {self.stop_loss_percent:.2f}%")
        print(f"   Check interval: {self.check_interval_seconds}s")
        print(f"   Max hold time: {hold_time_seconds}s")

        closed_positions = []
        total_profit = 0.0
        total_loss = 0.0
        start_time = time.time()

        while positions:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= hold_time_seconds:
                print(f"\n⏱️  Timeout monitoring setelah {elapsed:.1f}s")
                print(f"   {len(positions)} posisi belum ter-close")
                break

            # Dapatkan harga saat ini
            ticker = await exchange.fetch_ticker('BTC')
            if not ticker or not ticker.last:
                await asyncio.sleep(self.check_interval_seconds)
                continue

            current_price = float(ticker.last)

            # Cek setiap posisi
            positions_to_close = []

            for i, pos in enumerate(positions):
                # Hitung PnL
                if pos.side == OrderSide.LONG:
                    pnl_percent = ((current_price - pos.price) / pos.price) * 100
                else:  # SHORT
                    pnl_percent = ((pos.price - current_price) / pos.price) * 100

                pnl_usd = pnl_percent * self.position_value_usd / 100

                # Cek TP/SL
                if pnl_percent >= self.take_profit_percent:
                    print(f"\n✨ TAKE PROFIT! Posisi {i+1} ({pos.side.value})")
                    print(f"   Entry: ${pos.price:.2f}")
                    print(f"   Current: ${current_price:.2f}")
                    print(f"   PnL: {pnl_percent:.2f}% (${pnl_usd:.2f})")
                    positions_to_close.append((i, pos, 'tp', pnl_usd))

                elif pnl_percent <= -self.stop_loss_percent:
                    print(f"\n🛑 STOP LOSS! Posisi {i+1} ({pos.side.value})")
                    print(f"   Entry: ${pos.price:.2f}")
                    print(f"   Current: ${current_price:.2f}")
                    print(f"   PnL: {pnl_percent:.2f}% (${pnl_usd:.2f})")
                    positions_to_close.append((i, pos, 'sl', pnl_usd))

            # Close posisi yang mencapai TP/SL
            if positions_to_close:
                # Sort by index descending untuk avoid index shifting
                positions_to_close.sort(key=lambda x: x[0], reverse=True)

                for idx, pos, reason, pnl in positions_to_close:
                    try:
                        # Hitung limit price untuk close
                        ticker = await exchange.fetch_ticker('BTC')
                        if ticker and ticker.bid and ticker.ask:
                            bid_price = float(ticker.bid)
                            ask_price = float(ticker.ask)
                            spread_percent = ((ask_price - bid_price) / float(ticker.last)) * 100

                            close_side = OrderSide.SHORT if pos.side == OrderSide.LONG else OrderSide.LONG
                            limit_price = self.calculate_limit_price(close_side, bid_price, ask_price, spread_percent)

                            order = await self.close_position(exchange, close_side, pos.size, limit_price)
                            closed_positions.append(order)

                            if reason == 'tp':
                                total_profit += pnl
                            else:
                                total_loss += abs(pnl)

                            # Remove from positions list
                            positions.pop(idx)

                            # Delay antar close
                            await asyncio.sleep(2.0)

                    except Exception as e:
                        print(f"❌ Gagal close posisi {idx}: {e}")

            # Jika semua posisi sudah close, break
            if not positions:
                break

            # Delay sebelum check lagi
            await asyncio.sleep(self.check_interval_seconds)

        return {
            "closed_count": len(closed_positions),
            "total_profit": total_profit,
            "total_loss": total_loss,
            "net_pnl": total_profit - total_loss
        }

    async def execute_cycle(
        self,
        exchange: DecibelExchange,
        btc_size: float,
        hold_time_seconds: float = 30.0
    ) -> Dict:
        """
        Eksekusi satu cycle trading dengan limit order dan auto TP/SL.

        Cycle = Buka semua posisi -> Monitor -> Auto close TP/SL -> Manual close sisa
        """
        cycle_start = time.time()
        print("\n" + "="*70)
        print(f"CYCLE #{self.total_cycles + 1}")
        print("="*70)

        # Dapatkan harga
        btc_size, bid_price, ask_price, spread_percent = await self.get_btc_size_and_prices(exchange)

        # Buka semua posisi
        print(f"\n📈 Membuka {self.max_positions} posisi dengan limit order...")
        positions = []

        for i in range(self.max_positions):
            # Alternate LONG/SHORT untuk hedging
            side = OrderSide.LONG if i % 2 == 0 else OrderSide.SHORT

            # Hitung limit price
            limit_price = self.calculate_limit_price(side, bid_price, ask_price, spread_percent)

            try:
                order = await self.open_position(exchange, side, btc_size, limit_price)
                positions.append(order)
                self.positions.append(order)

                # Delay kecil antar posisi
                await asyncio.sleep(1.0)

            except Exception as e:
                print(f"❌ Gagal buka posisi {i+1}: {e}")
                continue

        if not positions:
            print("❌ Tidak ada posisi yang berhasil dibuka")
            return {"success": False, "volume": 0.0}

        # Hitung volume cycle ini
        cycle_volume_usd = len(positions) * self.position_value_usd
        print(f"\n📊 Volume cycle ini: ${cycle_volume_usd:.2f}")
        print(f"💰 Fee savings: ${self.fee_savings_per_cycle:.4f}")

        # Monitor dan auto close TP/SL
        monitor_result = await self.monitor_and_close_positions(exchange, positions, btc_size, hold_time_seconds)

        # Close sisa posisi yang belum ter-close
        if positions:
            print(f"\n📉 Menutup {len(positions)} posisi sisa...")

            # Dapatkan harga baru
            ticker = await exchange.fetch_ticker('BTC')
            if ticker and ticker.bid and ticker.ask:
                bid_price = float(ticker.bid)
                ask_price = float(ticker.ask)
                spread_percent = ((ask_price - bid_price) / float(ticker.last)) * 100

            for i, pos in enumerate(positions):
                try:
                    close_side = OrderSide.SHORT if pos.side == OrderSide.LONG else OrderSide.LONG
                    limit_price = self.calculate_limit_price(close_side, bid_price, ask_price, spread_percent)

                    order = await self.close_position(exchange, close_side, pos.size, limit_price)

                    # Delay antar penutupan
                    await asyncio.sleep(2.0)

                except Exception as e:
                    print(f"❌ Gagal tutup posisi {i+1}: {e}")
                    continue

        cycle_time = time.time() - cycle_start
        self.total_cycles += 1
        self.total_volume_usd += cycle_volume_usd
        self.total_profit_usd += monitor_result["total_profit"]
        self.total_loss_usd += monitor_result["total_loss"]

        # Progress
        progress = (self.total_volume_usd / self.target_daily_volume_usd) * 100
        eta_seconds = (self.required_cycles - self.total_cycles) * cycle_time
        eta_minutes = eta_seconds / 60

        print("\n" + "="*70)
        print(f"✅ CYCLE #{self.total_cycles} SELESAI")
        print("="*70)
        print(f"⏱️  Waktu cycle: {cycle_time:.1f} detik")
        print(f"📊 Volume cycle: ${cycle_volume_usd:.2f}")
        print(f"💰 Fee savings: ${self.fee_savings_per_cycle:.4f}")
        print(f"💵 Profit: ${monitor_result['total_profit']:.2f}")
        print(f"📉 Loss: ${monitor_result['total_loss']:.2f}")
        print(f"📊 Net PnL: ${monitor_result['net_pnl']:.2f}")
        print(f"📈 Total volume: ${self.total_volume_usd:,.2f}")
        print(f"💰 Total profit: ${self.total_profit_usd:.2f}")
        print(f"📉 Total loss: ${self.total_loss_usd:.2f}")
        print(f"📊 Total net PnL: ${self.total_profit_usd - self.total_loss_usd:.2f}")
        print(f"🎯 Progress: {progress:.1f}%")
        print(f"⏰ ETA: {eta_minutes:.1f} menit")
        print(f"🔄 Cycles tersisa: {self.required_cycles - self.total_cycles}")
        print("="*70)

        return {
            "success": True,
            "volume": cycle_volume_usd,
            "time": cycle_time,
            "positions": len(positions),
            "profit": monitor_result["total_profit"],
            "loss": monitor_result["total_loss"],
            "net_pnl": monitor_result["net_pnl"]
        }

    async def run_strategy(
        self,
        hold_time_seconds: float = 30.0,
        max_cycles: int = None
    ):
        """
        Jalankan strategi trading volume tinggi dengan limit order dan auto TP/SL.

        Args:
            hold_time_seconds: Waktu menahan posisi (detik)
            max_cycles: Maksimum cycles (None = sampai target tercapai)
        """
        self.start_time = time.time()

        print("\n" + "="*70)
        print("🚀 MEMULAI STRATEGI VOLUME TINGGI - LIMIT ORDER + AUTO TP/SL")
        print("="*70)
        print(f"⏱️  Waktu hold: {hold_time_seconds} detik")
        print(f"🎯 Target cycles: {max_cycles if max_cycles else self.required_cycles}")
        print(f"💰 Maker fee: {self.maker_fee_percent:.4f}%")
        print(f"🎯 Take Profit: {self.take_profit_percent:.2f}%")
        print(f"🛑 Stop Loss: {self.stop_loss_percent:.2f}%")
        print("="*70)

        exchange = DecibelExchange()
        btc_size, _, _, _ = await self.get_btc_size_and_prices(exchange)

        cycle_count = 0
        target_cycles = max_cycles if max_cycles else self.required_cycles

        try:
            while cycle_count < target_cycles:
                result = await self.execute_cycle(
                    exchange,
                    btc_size,
                    hold_time_seconds
                )

                if not result["success"]:
                    print("❌ Cycle gagal, mencoba lagi...")
                    await asyncio.sleep(5.0)
                    continue

                cycle_count += 1

                # Delay kecil antar cycles
                await asyncio.sleep(2.0)

        except KeyboardInterrupt:
            print("\n\n⚠️  Strategi dihentikan oleh user")

        except Exception as e:
            print(f"\n\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Summary
            total_time = time.time() - self.start_time
            total_minutes = total_time / 60
            total_hours = total_minutes / 60

            total_fee_savings = self.fee_savings_per_cycle * self.total_cycles
            total_net_pnl = self.total_profit_usd - self.total_loss_usd

            print("\n" + "="*70)
            print("📊 SUMMARY STRATEGI")
            print("="*70)
            print(f"⏱️  Total waktu: {total_hours:.1f} jam ({total_minutes:.1f} menit)")
            print(f"🔄 Total cycles: {self.total_cycles}")
            print(f"📈 Total volume: ${self.total_volume_usd:,.2f}")
            print(f"🎯 Target: ${self.target_daily_volume_usd:,.0f}")
            print(f"📊 Progress: {(self.total_volume_usd / self.target_daily_volume_usd) * 100:.1f}%")
            print(f"💰 Total fee savings: ${total_fee_savings:.2f}")
            print(f"💵 Total profit: ${self.total_profit_usd:.2f}")
            print(f"📉 Total loss: ${self.total_loss_usd:.2f}")
            print(f"📊 Total net PnL: ${total_net_pnl:.2f}")
            print(f"⚡ Rata-rata per cycle: ${self.total_volume_usd / self.total_cycles:.2f}")
            print("="*70)


async def main():
    """Main function."""
    import sys

    # Parse arguments
    balance = 20.0
    per_position = 5.0
    leverage = 40
    target_volume = 100000.0
    hold_time = 30.0
    max_cycles = None
    take_profit = 0.5
    stop_loss = 1.0

    if len(sys.argv) > 1:
        try:
            balance = float(sys.argv[1])
        except:
            pass

    if len(sys.argv) > 2:
        try:
            per_position = float(sys.argv[2])
        except:
            pass

    if len(sys.argv) > 3:
        try:
            leverage = int(sys.argv[3])
        except:
            pass

    if len(sys.argv) > 4:
        try:
            target_volume = float(sys.argv[4])
        except:
            pass

    if len(sys.argv) > 5:
        try:
            hold_time = float(sys.argv[5])
        except:
            pass

    if len(sys.argv) > 6:
        try:
            take_profit = float(sys.argv[6])
        except:
            pass

    if len(sys.argv) > 7:
        try:
            stop_loss = float(sys.argv[7])
        except:
            pass

    if len(sys.argv) > 8:
        try:
            max_cycles = int(sys.argv[8])
        except:
            pass

    # Buat strategi
    strategy = HighVolumeWithTPStrategy(
        balance_usd=balance,
        per_position_usd=per_position,
        leverage=leverage,
        target_daily_volume_usd=target_volume,
        take_profit_percent=take_profit,
        stop_loss_percent=stop_loss
    )

    # Jalankan strategi
    await strategy.run_strategy(
        hold_time_seconds=hold_time,
        max_cycles=max_cycles
    )


if __name__ == "__main__":
    asyncio.run(main())
