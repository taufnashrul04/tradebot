#!/usr/bin/env python3
"""
Quick Start - Jalankan 5 cycles untuk testing strategi volume tinggi.
"""
import asyncio
from strategy_high_volume import HighVolumeStrategy


async def quick_start():
    """Jalankan 5 cycles untuk testing."""
    print("\n" + "="*70)
    print("🚀 QUICK START - 5 CYCLES TESTING")
    print("="*70)

    # Buat strategi
    strategy = HighVolumeStrategy(
        balance_usd=20.0,
        per_position_usd=5.0,
        leverage=40,
        target_daily_volume_usd=100000.0
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
