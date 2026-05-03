---
name: delta-neutral
description: |
  Deep knowledge skill for cross-exchange delta-neutral funding rate arbitrage strategy.
  Use when user wants to: run delta neutral, exploit funding rate differences between exchanges,
  find funding arb opportunities, or understand how the strategy works.
  This skill covers: funding rate math, opportunity detection, position management, when to close.
---

# Delta-Neutral Cross-Exchange Funding Arb

## What Is Delta Neutral?

A delta-neutral position has **zero net directional exposure** — it doesn't care if BTC goes up or down.

In this bot, we achieve delta-neutral by:
- Going **LONG** on Exchange A (e.g., Decibel)
- Going **SHORT** on Exchange B (e.g., Nado)
- **Same size** on both sides → net delta = 0

## Why This Makes Money: Funding Rate Arb

**Funding rates differ between exchanges** because they reflect different market sentiment and liquidity on each platform.

```
Example (all rates per 8h interval):

  Nado BTC funding:    +0.05%   ← longs PAY shorts 0.05%
  Decibel BTC funding: -0.02%   ← shorts PAY longs 0.02%

Our position:
  SHORT on Nado    → we RECEIVE +0.05% every 8h
  LONG on Decibel  → we RECEIVE +0.02% every 8h (shorts paying us)

Net per 8h:     +0.07%
Net per day:    +0.21%  (3 intervals)
Net per year:   +7.6%   (annualized)

On $1000 position:
  Per 8h:  $0.70
  Per day: $2.10
  Per year: $76 (on $1000 = 7.6% APY)
```

## The Math

```python
# For exchange pair (A, B):
# Always SHORT on higher-rate exchange, LONG on lower-rate

net_per_interval = rate_high - rate_low

# Annualize:
intervals_per_year = 8760 / interval_hours   # 8760h/year / 8h = 1095 intervals
annual_yield_pct = net_per_interval * intervals_per_year * 100

# Profitable condition:
is_profitable = (net_per_interval > 0) and (annual_yield_pct >= min_yield_threshold)
```

## All Pairs Checked by Bot

The bot automatically checks **all combinations**:
- Nado vs Decibel (BTC, ETH, SOL)
- Nado vs Rise (BTC, ETH, SOL)
- Decibel vs Rise (BTC, ETH, SOL)

And ranks them by highest annual yield.

## Running the Strategy

### Step 1: Scan First (Always)
```bash
python -m bot_trade funding --symbols BTC,ETH --exchanges nado,decibel,rise
```
Read the "Delta-Neutral Opportunities" table. Look for rows with `annual_yield > 5%`.

### Step 2: Start the Bot
```bash
# If best opportunity is Nado vs Decibel:
python -m bot_trade delta-neutral \
  --exchanges nado,decibel \
  --size 200 \
  --min-yield 5.0 \
  --max-hours 24 \
  --leverage 1
```

### Step 3: Monitor
```bash
# In another terminal: keep watching rates
python -m bot_trade funding --watch --exchanges nado,decibel

# Check position status
python -m bot_trade status
```

## When Bot Closes Position

| Trigger | Condition | Reason |
|---------|-----------|--------|
| Yield degraded | Current yield < 30% of threshold | Not profitable anymore |
| Max duration | Age > --max-hours | Automatic timeout |
| Manual stop | Ctrl+C | Graceful close |
| Emergency | Critical error | Auto-close both legs |

## Scenarios

### Scenario A: Both positive funding (most common)
```
Nado:    +0.05%/8h
Decibel: +0.01%/8h

SHORT on Nado (higher) → collect +0.05%
LONG on Decibel (lower) → PAY 0.01%

Net: +0.04%/8h = 4.4% annual
```

### Scenario B: One positive, one negative (best case)
```
Nado:    +0.05%/8h
Decibel: -0.02%/8h

SHORT on Nado    → collect +0.05%
LONG on Decibel  → collect +0.02% (shorts paying us!)

Net: +0.07%/8h = 7.6% annual
```

### Scenario C: Both negative (still can profit)
```
Nado:    -0.01%/8h
Decibel: -0.04%/8h

LONG on Nado (higher, -0.01%) → collect +0.01%... wait
SHORT on Decibel (lower, -0.04%) → collect +0.04%

Net: 0.04% - 0.01% = +0.03%/8h = 3.3% annual
```

## Real-World Considerations

### Execution Costs
```
Opening costs:
  - 2 market orders (1 per exchange)
  - Typical taker fee: 0.05% per trade
  - Total: ~0.10% of notional to open

Break-even analysis (at 0.10% open + 0.10% close costs):
  Total cost = 0.20% of notional
  At +0.07%/8h → break even in ~29 hours
  After 29h → pure profit
```

### Choosing the Right Size
```
Conservative:  $50-200 per leg (test the strategy)
Moderate:     $200-500 per leg
Aggressive:   $500-1000 per leg (max config limit)

Note: Both legs combined = 2x your --size value in total exposure
```

### Best Exchange Pairs to Watch
```
Priority 1: Nado vs Decibel   ← Both have clear funding mechanisms
Priority 2: Nado vs Rise      ← EVM to EVM, lower gas costs
Priority 3: Decibel vs Rise   ← Higher complexity, more gas costs
```

## Frequently Asked Questions

**Q: What if BTC price dumps 20% while I'm in the trade?**
A: Your long and short cancel out. If you have equal-size long on Decibel and short on Nado, a 20% price dump means:
- Long loses: -20% of size
- Short gains: +20% of size
- Net PnL from price: $0

Only variable is slippage at open/close and the funding profit accumulated.

**Q: What is the minimum funding diff worth trading?**
A: After accounting for fees (~0.10% per open+close), you need at least:
- `annual_yield > 3%` for long positions (> 7 days)
- `annual_yield > 8%` for short positions (< 2 days)

**Q: Can rates flip suddenly?**
A: Yes. If market sentiment shifts, funding can flip direction within one 8h interval.
Bot monitors this and will close if yield drops below 30% of threshold.

**Q: Max risk per trade?**
A: Worst case is if one exchange goes down during the trade (orphaned leg).
Bot handles this by auto-closing the remaining leg and alerting. Actual market risk = ~0.
