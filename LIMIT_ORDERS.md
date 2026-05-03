# Limit Order Management - Decibel DEX

## ⚠️ Critical Limitation

**Decibel API does NOT support canceling limit orders.**

This is a known limitation of the Decibel protocol:
- REST API is READ-ONLY for market data
- All trading happens on-chain via Aptos Move transactions
- No endpoint exists to list or cancel pending limit orders

## What This Means

1. **Limit orders that don't fill will remain open** until:
   - They get filled by the market
   - You cancel them manually in the UI
   - They expire (if expiration is set)

2. **Cannot check for pending orders via API** - no endpoint exists

3. **Bot cannot auto-cancel limit orders** - must be done manually

## How to Cancel Pending Limit Orders

### Manual Steps (Required)

1. Go to https://app.decibel.trade/
2. Navigate to the "Open Orders" tab
3. Find any pending limit orders
4. Click "Cancel" on each order

### Bot Behavior

The bot now includes:
- `cancel_all_limit_orders()` method (logs warning about API limitation)
- Called at start and end of each cycle
- Logs reminder to check UI for pending orders

## Current Status

Based on API checks:
- ✅ No open positions found
- ❓ Cannot verify pending limit orders (no API endpoint)
- ⚠️  User reports 2 limit SHORT orders still open

## Recommendations

### For Testing

1. **Cancel all pending limit orders manually** in Decibel UI before running bot
2. **Use market orders** for testing (more reliable, higher fees)
3. **Monitor UI** during bot runs to catch any stuck orders

### For Production

1. **Set limit order expiration** if supported
2. **Use smaller limit order sizes** to reduce risk
3. **Monitor positions actively** - don't leave bot unattended
4. **Consider using market orders** if reliability > fee savings

## Fee Comparison

| Order Type | Fee | Total Fee ($100k) | Savings |
|------------|-----|-------------------|---------|
| Taker (Market) | 0.0340% | $34.00 | - |
| Maker (Limit) | 0.0110% | $11.00 | **$23.00** |

**Trade-off:** Limit orders save $23 on $100k volume but can get stuck.

## Bot Updates

### Added Methods

```python
async def cancel_all_limit_orders(self) -> int:
    """Cancel all pending limit orders (NOT SUPPORTED by Decibel API)"""
    print("⚠️  Decibel API does NOT support canceling limit orders")
    print("   Pending limit orders must be canceled manually in the UI")
    print("   https://app.decibel.trade/")
    return 0
```

### Updated Cycle Flow

1. Close all positions
2. **Try to cancel limit orders** (logs warning)
3. Fetch market data
4. Calculate indicators
5. Generate signal
6. Execute trade
7. Hold position
8. Close all positions
9. **Try to cancel limit orders again** (logs warning)

## Next Steps

1. **Cancel the 2 pending SHORT orders manually** in Decibel UI
2. **Verify no pending orders** before running bot again
3. **Consider using market orders** for testing to avoid stuck orders
4. **Monitor UI** during bot runs

## Files Updated

- `/home/ubuntu/tradebot/ccxt_decibel_bot.py` - Added cancel_all_limit_orders()
- `/home/ubuntu/tradebot/check_pending_orders.py` - Script to check orders (shows limitation)
- `/home/ubuntu/tradebot/LIMIT_ORDERS.md` - This document
