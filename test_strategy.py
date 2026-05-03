#!/usr/bin/env python3
"""
Test Cepat Strategi Volume Tinggi

Versi sederhana untuk testing tanpa eksekusi penuh.
"""
import asyncio
from strategy_high_volume import HighVolumeStrategy


async def test_strategy():
    """Test strategi tanpa eksekusi trading."""
    print("\n" + "="*70)
    print("TEST STRATEGI VOLUME TINGGI")
    print("="*70)

    # Buat strategi
    strategy = HighVolumeStrategy(
        balance_usd=20.0,
        per_position_usd=5.0,
        leverage=40,
        target_daily_volume_usd=100000.0
    )

    print("\n📊 Perhitungan:")
    print(f"   Saldo: ${strategy.balance_usd:.2f}")
    print(f"   Per posisi: ${strategy.per_position_usd:.2f}")
    print(f"   Leverage: {strategy.leverage}x")
    print(f"   Nilai per posisi: ${strategy.position_value_usd:.2f}")
    print(f"   Maks posisi: {strategy.max_positions}")
    print(f"   Volume per cycle: ${strategy.total_cycle_volume_usd:.2f}")
    print(f"   Cycles dibutuhkan: {strategy.required_cycles}")

    # Simulasi waktu
    cycle_time = 60  # 1 menit per cycle (buka + hold + tutup)
    total_time_minutes = strategy.required_cycles * cycle_time
    total_time_hours = total_time_minutes / 60

    print(f"\n⏱️  Estimasi waktu:")
    print(f"   Waktu per cycle: {cycle_time} detik")
    print(f"   Total waktu: {total_time_minutes:.1f} menit ({total_time_hours:.1f} jam)")

    # Alternatif dengan cycle lebih cepat
    cycle_time_fast = 30  # 30 detik per cycle
    total_time_fast = strategy.required_cycles * cycle_time_fast
    total_time_fast_hours = total_time_fast / 3600

    print(f"\n⚡ Dengan cycle 30 detik:")
    print(f"   Total waktu: {total_time_fast / 60:.1f} menit ({total_time_fast_hours:.1f} jam)")

    # Alternatif dengan leverage lebih tinggi
    print(f"\n💡 Alternatif dengan leverage 40x (maksimal):")
    print(f"   Sudah menggunakan leverage maksimal!")

    print("\n" + "="*70)
    print("✅ TEST SELESAI")
    print("="*70)


async def main():
    """Main function."""
    await test_strategy()


if __name__ == "__main__":
    asyncio.run(main())
