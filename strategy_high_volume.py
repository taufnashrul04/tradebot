#!/usr/bin/env python3
"""
Strategi Trading Volume Tinggi dengan Saldo Kecil ($20)

Target: 100k volume per hari
Saldo: $20
Per posisi: $5
Leverage: 40x (maksimal di Decibel)

Perhitungan:
- 4 posisi simultan ($20 / $5 = 4)
- Dengan leverage 40x: $5 x 40 = $200 per posisi
- Volume per posisi: $200 / harga BTC (~$76k) = ~0.0026 BTC
- Total volume per cycle: 4 x $200 = $800
- Untuk 100k volume: 100k / $800 = 125 cycles
- Jika setiap cycle 5 menit: 125 x 5 = 625 menit = ~10.4 jam
"""
import asyncio
import time
from typing import List, Dict
from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.exchanges.decibel_large_volume import (
    LargeVolumeTrader,
    LargeVolumeConfig,
    ExecutionStrategy
)
from bot_trade.models import OrderSide, Order


class HighVolumeStrategy:
    """
    Strategi trading volume tinggi dengan saldo kecil.

    Menggunakan leverage maksimal dan rotasi posisi untuk mencapai
    target volume harian.
    """

    def __init__(
        self,
        balance_usd: float = 20.0,
        per_position_usd: float = 5.0,
        leverage: int = 40,
        target_daily_volume_usd: float = 100000.0
    ):
        self.balance_usd = balance_usd
        self.per_position_usd = per_position_usd
        self.leverage = leverage
        self.target_daily_volume_usd = target_daily_volume_usd

        # Hitung parameter
        self.max_positions = int(balance_usd / per_position_usd)
        self.position_value_usd = per_position_usd * leverage
        self.total_cycle_volume_usd = self.position_value_usd * self.max_positions
        self.required_cycles = int(target_daily_volume_usd / self.total_cycle_volume_usd)

        # Tracking
        self.total_volume_usd = 0.0
        self.total_cycles = 0
        self.start_time = None
        self.positions: List[Order] = []

        print("\n" + "="*70)
        print("STRATEGI VOLUME TINGGI - KONFIGURASI")
        print("="*70)
        print(f"💰 Saldo: ${balance_usd:.2f}")
        print(f"📊 Per posisi: ${per_position_usd:.2f}")
        print(f"⚡ Leverage: {leverage}x")
        print(f"🎯 Target volume: ${target_daily_volume_usd:,.0f}")
        print(f"📈 Maks posisi: {self.max_positions}")
        print(f"💵 Nilai per posisi: ${self.position_value_usd:.2f}")
        print(f"🔄 Volume per cycle: ${self.total_cycle_volume_usd:.2f}")
        print(f"🎯 Cycles dibutuhkan: {self.required_cycles}")
        print("="*70)

    async def get_btc_size(self, exchange: DecibelExchange) -> float:
        """Hitung ukuran posisi BTC berdasarkan nilai USD."""
        ticker = await exchange.fetch_ticker('BTC')
        if not ticker or not ticker.last:
            raise ValueError("Tidak bisa mengambil harga BTC")

        btc_price = float(ticker.last)
        btc_size = self.per_position_usd * self.leverage / btc_price

        print(f"\n💰 Harga BTC: ${btc_price:.2f}")
        print(f"📊 Ukuran posisi: {btc_size:.6f} BTC")
        print(f"💵 Nilai posisi: ${btc_size * btc_price:.2f}")

        return btc_size

    async def open_position(
        self,
        exchange: DecibelExchange,
        side: OrderSide,
        btc_size: float
    ) -> Order:
        """Buka posisi dengan ukuran tertentu."""
        print(f"\n🚀 Membuka posisi {side.value} {btc_size:.6f} BTC")

        order = await exchange.place_market_order(
            symbol='BTC',
            side=side,
            size=btc_size,
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
        btc_size: float
    ) -> Order:
        """Tutup posisi."""
        print(f"\n🔒 Menutup posisi {side.value} {btc_size:.6f} BTC")

        # Untuk menutup, kita buka posisi berlawanan
        close_side = OrderSide.SHORT if side == OrderSide.LONG else OrderSide.LONG

        order = await exchange.place_market_order(
            symbol='BTC',
            side=close_side,
            size=btc_size,
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
        Eksekusi satu cycle trading.

        Cycle = Buka semua posisi -> Tahan -> Tutup semua posisi
        """
        cycle_start = time.time()
        print("\n" + "="*70)
        print(f"CYCLE #{self.total_cycles + 1}")
        print("="*70)

        # Buka semua posisi
        print(f"\n📈 Membuka {self.max_positions} posisi...")
        positions = []

        for i in range(self.max_positions):
            # Alternate LONG/SHORT untuk hedging
            side = OrderSide.LONG if i % 2 == 0 else OrderSide.SHORT

            try:
                order = await self.open_position(exchange, side, btc_size)
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

        # Tahan posisi
        print(f"\n⏱️  Menahan posisi selama {hold_time_seconds} detik...")
        await asyncio.sleep(hold_time_seconds)

        # Tutup semua posisi
        print(f"\n📉 Menutup {len(positions)} posisi...")
        closed_positions = []

        for i, pos in enumerate(positions):
            try:
                # Tutup posisi (berlawanan dengan posisi asli)
                close_side = OrderSide.SHORT if pos.side == OrderSide.LONG else OrderSide.LONG

                order = await self.close_position(exchange, close_side, pos.size)
                closed_positions.append(order)

                # Delay antar penutupan (lebih lama untuk avoid rate limit)
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
        Jalankan strategi trading volume tinggi.

        Args:
            hold_time_seconds: Waktu menahan posisi (detik)
            max_cycles: Maksimum cycles (None = sampai target tercapai)
        """
        self.start_time = time.time()

        print("\n" + "="*70)
        print("🚀 MEMULAI STRATEGI VOLUME TINGGI")
        print("="*70)
        print(f"⏱️  Waktu hold: {hold_time_seconds} detik")
        print(f"🎯 Target cycles: {max_cycles if max_cycles else self.required_cycles}")
        print("="*70)

        exchange = DecibelExchange()
        btc_size = await self.get_btc_size(exchange)

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

            print("\n" + "="*70)
            print("📊 SUMMARY STRATEGI")
            print("="*70)
            print(f"⏱️  Total waktu: {total_hours:.1f} jam ({total_minutes:.1f} menit)")
            print(f"🔄 Total cycles: {self.total_cycles}")
            print(f"📈 Total volume: ${self.total_volume_usd:,.2f}")
            print(f"🎯 Target: ${self.target_daily_volume_usd:,.0f}")
            print(f"📊 Progress: {(self.total_volume_usd / self.target_daily_volume_usd) * 100:.1f}%")
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
    strategy = HighVolumeStrategy(
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
