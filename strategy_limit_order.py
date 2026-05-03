#!/usr/bin/env python3
"""
Strategi Trading Volume Tinggi dengan Limit Order (Maker Fee)

Fee:
- Maker: 0.0110%
- Taker: 0.0340%

Dengan limit order, fee jauh lebih kecil!
"""
import asyncio
import time
from typing import List, Dict
from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide, Order


class HighVolumeLimitStrategy:
    """
    Strategi trading volume tinggi dengan limit order (maker fee).

    Menggunakan limit order untuk mengurangi fee dari 0.0340% ke 0.0110%.
    """

    def __init__(
        self,
        balance_usd: float = 20.0,
        per_position_usd: float = 5.0,
        leverage: int = 40,
        target_daily_volume_usd: float = 100000.0,
        maker_fee_percent: float = 0.0110,
        taker_fee_percent: float = 0.0340
    ):
        self.balance_usd = balance_usd
        self.per_position_usd = per_position_usd
        self.leverage = leverage
        self.target_daily_volume_usd = target_daily_volume_usd
        self.maker_fee_percent = maker_fee_percent
        self.taker_fee_percent = taker_fee_percent

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
        self.start_time = None
        self.positions: List[Order] = []

        print("\n" + "="*70)
        print("STRATEGI VOLUME TINGGI - LIMIT ORDER (MAKER FEE)")
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

    async def execute_cycle(
        self,
        exchange: DecibelExchange,
        btc_size: float,
        hold_time_seconds: float = 30.0
    ) -> Dict:
        """
        Eksekusi satu cycle trading dengan limit order.

        Cycle = Buka semua posisi -> Tahan -> Tutup semua posisi
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

        # Tahan posisi
        print(f"\n⏱️  Menahan posisi selama {hold_time_seconds} detik...")
        await asyncio.sleep(hold_time_seconds)

        # Dapatkan harga baru untuk penutupan
        ticker = await exchange.fetch_ticker('BTC')
        if ticker and ticker.bid and ticker.ask:
            bid_price = float(ticker.bid)
            ask_price = float(ticker.ask)
            spread_percent = ((ask_price - bid_price) / float(ticker.last)) * 100

        # Tutup semua posisi
        print(f"\n📉 Menutup {len(positions)} posisi dengan limit order...")
        closed_positions = []

        for i, pos in enumerate(positions):
            try:
                # Hitung limit price untuk penutupan
                close_side = OrderSide.SHORT if pos.side == OrderSide.LONG else OrderSide.LONG
                limit_price = self.calculate_limit_price(close_side, bid_price, ask_price, spread_percent)

                order = await self.close_position(exchange, close_side, pos.size, limit_price)
                closed_positions.append(order)

                # Delay antar penutupan
                await asyncio.sleep(2.0)

            except Exception as e:
                print(f"❌ Gagal tutup posisi {i+1}: {e}")
                continue

        cycle_time = time.time() - cycle_start
        self.total_cycles += 1
        self.total_volume_usd += cycle_volume_usd

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
        print(f"📈 Total volume: ${self.total_volume_usd:,.2f}")
        print(f"🎯 Progress: {progress:.1f}%")
        print(f"⏰ ETA: {eta_minutes:.1f} menit")
        print(f"🔄 Cycles tersisa: {self.required_cycles - self.total_cycles}")
        print("="*70)

        return {
            "success": True,
            "volume": cycle_volume_usd,
            "time": cycle_time,
            "positions": len(positions)
        }

    async def run_strategy(
        self,
        hold_time_seconds: float = 30.0,
        max_cycles: int = None
    ):
        """
        Jalankan strategi trading volume tinggi dengan limit order.

        Args:
            hold_time_seconds: Waktu menahan posisi (detik)
            max_cycles: Maksimum cycles (None = sampai target tercapai)
        """
        self.start_time = time.time()

        print("\n" + "="*70)
        print("🚀 MEMULAI STRATEGI VOLUME TINGGI - LIMIT ORDER")
        print("="*70)
        print(f"⏱️  Waktu hold: {hold_time_seconds} detik")
        print(f"🎯 Target cycles: {max_cycles if max_cycles else self.required_cycles}")
        print(f"💰 Maker fee: {self.maker_fee_percent:.4f}%")
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

            print("\n" + "="*70)
            print("📊 SUMMARY STRATEGI")
            print("="*70)
            print(f"⏱️  Total waktu: {total_hours:.1f} jam ({total_minutes:.1f} menit)")
            print(f"🔄 Total cycles: {self.total_cycles}")
            print(f"📈 Total volume: ${self.total_volume_usd:,.2f}")
            print(f"🎯 Target: ${self.target_daily_volume_usd:,.0f}")
            print(f"📊 Progress: {(self.total_volume_usd / self.target_daily_volume_usd) * 100:.1f}%")
            print(f"💰 Total fee savings: ${total_fee_savings:.2f}")
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
            max_cycles = int(sys.argv[6])
        except:
            pass

    # Buat strategi
    strategy = HighVolumeLimitStrategy(
        balance_usd=balance,
        per_position_usd=per_position,
        leverage=leverage,
        target_daily_volume_usd=target_volume
    )

    # Jalankan strategi
    await strategy.run_strategy(
        hold_time_seconds=hold_time,
        max_cycles=max_cycles
    )


if __name__ == "__main__":
    asyncio.run(main())
