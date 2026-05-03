#!/usr/bin/env python3
"""
Quick Start - Jalankan 5 cycles untuk testing strategy dengan auto TP/SL.
"""
import asyncio
from strategy_with_tp import HighVolumeWithTPStrategy


async def quick_start():
    """Jalankan 5 cycles untuk testing."""
    print("\n" + "="*70)
    print("🚀 QUICK START - 5 CYCLES TESTING (LIMIT ORDER + AUTO TP/SL)")
    print("="*70)

    # Buat strategi
    strategy = HighVolumeWithTPStrategy(
        balance_usd=20.0,
        per_position_usd=5.0,
        leverage=40,
        target_daily_volume_usd=100000.0,
        take_profit_percent=0.5,  # 0.5% TP
        stop_loss_percent=1.0  # 1% SL
    )

    # Jalankan 5 cycles
    print("\n⚠️  Ini adalah test dengan 5 cycles")
    print("   Untuk production, jalankan tanpa batas cycles")
    print("   atau sesuaikan jumlah cycles")

    await strategy.run_strategy(
        hold_time_seconds=30.0,
        max_cycles=5
    )


if __name__ == "__main__":
    asyncio.run(quick_start())
