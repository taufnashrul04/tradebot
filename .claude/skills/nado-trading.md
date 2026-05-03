---
name: nado-trading
description: |
  Skill for interacting with Nado Protocol perpetual DEX on Ink blockchain.
  Use this when user wants to: trade on Nado, check Nado funding rates, generate volume on Nado,
  use Nado market data, or run indicator strategies on Nado.
  Nado supports: BTC, ETH, SOL perpetual futures with TWAP, trigger orders, TP/SL.
---

# Nado Protocol Trading Skill

Nado is a perpetual DEX on Ink blockchain (EVM L2). It has both a CLI tool and Python SDK.

## Available Markets

| Symbol | Product ID | Type |
|--------|-----------|------|
| BTC | 1 | Perpetual |
| ETH | 3 | Perpetual |
| SOL | 5 | Perpetual |

## Funding Rate Info

- Funding interval: **8 hours** (UTC 00:00, 08:00, 16:00)
- Positive funding = longs pay shorts
- Negative funding = shorts pay longs
- Check with: `nado market funding BTC`

## CLI Commands Reference

```bash
# Market Data (no auth needed)
nado market price BTC              # current price
nado market tickers                # all markets
nado market funding BTC            # funding rate
nado market orderbook BTC          # order book
nado market candles BTC --period 3600  # 1h candles

# Account (needs private key setup via `nado setup`)
nado account summary               # balance overview
nado account positions             # open positions

# Trading
nado trade long BTC 0.001 --leverage 2 --force    # open long
nado trade short BTC 0.001 --leverage 2 --force   # open short
nado trade close BTC --force                       # close position
```

## Bot Commands for Nado

```bash
# Working dir: d:\bot\bot trade

# Scan Nado funding only
python -m bot_trade funding --exchanges nado --symbols BTC,ETH,SOL

# Volume generation on Nado
python -m bot_trade volume --exchange nado --symbol BTC --target 10000 --duration 3600

# Indicator trading on Nado
python -m bot_trade indicator --exchange nado --strategy rsi --timeframe 15m --size 200

# Account status
python -m bot_trade status --exchange nado
```

## TWAP Order on Nado

Nado has **native TWAP** via the TriggerClient:
```bash
# Bot uses native TWAP by default
python -m bot_trade volume --exchange nado --twap --slices 20 --duration 3600
```

The TWAP splits the total order into N slices at regular intervals, with configurable
slippage tolerance. This is the most efficient way to generate large volumes.

## Supported Order Types

| Type | Description | Use Case |
|------|-------------|----------|
| Market | Execute immediately at best price | Volume gen, quick entry/exit |
| Limit | Execute at specific price | Market making, precise entries |
| TWAP | Time-weighted average price | Large orders, volume generation |
| Stop Loss | Close position at loss limit | Risk management |
| Take Profit | Close position at profit target | Automated profit taking |

## Risk Notes

- Max leverage on Nado: depends on asset (up to 20x for BTC)
- Bot limits to `MAX_LEVERAGE` from `.env` (default: 5)
- Use leverage 1 for delta-neutral (no amplification of slippage)
