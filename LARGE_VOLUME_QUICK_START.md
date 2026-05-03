# Large Volume Trading Quick Reference

## Execute $100k Worth of BTC

```bash
cd /home/ubuntu/tradebot
/home/ubuntu/tradebot/.venv/bin/python execute_large_volume.py --100k-usd LONG
```

This will execute ~1.3 BTC worth of orders over time.

## Execute 100k BTC (EXTREME - $7.6 Billion)

```bash
cd /home/ubuntu/tradebot
/home/ubuntu/tradebot/.venv/bin/python execute_large_volume.py --100k-btc LONG
```

⚠️ **WARNING**: This is extremely large and will take a very long time.

## Custom Volume Execution

```bash
# Execute $50k worth of BTC
/home/ubuntu/tradebot/.venv/bin/python execute_large_volume.py 50000 USD LONG

# Execute 10 BTC
/home/ubuntu/tradebot/.venv/bin/python execute_large_volume.py 10 BTC LONG

# Execute 1000 contracts
/home/ubuntu/tradebot/.venv/bin/python execute_large_volume.py 1000 contracts SHORT

# Custom chunk size and delay
/home/ubuntu/tradebot/.venv/bin/python execute_large_volume.py 100000 USD LONG 0.0005 1.0
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `volume` | Total volume to execute | - |
| `unit` | Volume unit (BTC, USD, contracts) | - |
| `side` | Order side (LONG, SHORT) | - |
| `chunk_size` | Size per chunk (BTC) | 0.001 |
| `delay` | Delay between chunks (seconds) | 2.0 |

## Examples

### Example 1: Execute $100k USD worth of BTC

```bash
/home/ubuntu/tradebot/.venv/bin/python execute_large_volume.py --100k-usd LONG
```

**Output:**
```
======================================================================
VERY LARGE VOLUME EXECUTION
======================================================================
Symbol: BTC
Side: LONG
Total Volume: 100,000.00 USD
Strategy: twap
Chunk Size: 0.001 BTC
Delay: 2.0s
Max Time: 60 minutes
======================================================================

💰 Converting 100,000.00 USD to BTC @ $76,751.50
   = 1.302960 BTC

📈 Execution Plan:
   Total BTC: 1.302960
   Chunks: 1303
   Estimated time: 43.4 minutes

🚀 Starting execution at 18:30:00
✅ Slice 1: 0.001 BTC @ $76,751.50
✅ Slice 2: 0.001 BTC @ $76,752.30
...
```

### Example 2: Execute 10 BTC with custom parameters

```bash
/home/ubuntu/tradebot/.venv/bin/python execute_large_volume.py 10 BTC LONG 0.0005 1.0
```

This will:
- Execute 10 BTC total
- Use 0.0005 BTC chunks (20,000 chunks)
- 1.0 second delay between chunks
- Estimated time: ~5.5 hours

### Example 3: Execute $50k SHORT

```bash
/home/ubuntu/tradebot/.venv/bin/python execute_large_volume.py 50000 USD SHORT
```

## Python API

### Execute $100k USD

```python
import asyncio
from execute_large_volume import execute_100k_usd
from bot_trade.models import OrderSide

async def main():
    result = await execute_100k_usd(
        side=OrderSide.LONG,
        chunk_size=0.001,
        delay=2.0
    )
    print(f"Status: {result['status']}")
    print(f"Orders: {result['num_orders']}")
    print(f"Total filled: {result['total_filled']:.6f} BTC")

asyncio.run(main())
```

### Execute Custom Volume

```python
import asyncio
from execute_large_volume import execute_very_large_volume
from bot_trade.models import OrderSide

async def main():
    result = await execute_very_large_volume(
        symbol='BTC',
        side=OrderSide.LONG,
        total_volume=100000,
        volume_unit="USD",
        chunk_size=0.001,
        delay_between_chunks=2.0,
        max_execution_time_minutes=60
    )
    print(f"Status: {result['status']}")

asyncio.run(main())
```

## Important Notes

1. **Execution Time**: Large volumes take time to execute. Plan accordingly.

2. **Market Impact**: Very large orders can move the market. Use smaller chunks and longer delays to minimize impact.

3. **Slippage**: Monitor slippage and adjust parameters if needed.

4. **Rate Limits**: The script handles rate limits automatically, but very fast execution may still hit limits.

5. **Position Limits**: Check your position limits before executing large orders.

6. **Testing**: Always test with small volumes first.

## Troubleshooting

### Execution takes too long

- Increase `chunk_size` (e.g., 0.005 instead of 0.001)
- Reduce `delay` (e.g., 1.0 instead of 2.0)

### High slippage

- Decrease `chunk_size` (e.g., 0.0005 instead of 0.001)
- Increase `delay` (e.g., 3.0 instead of 2.0)
- Use limit ladder strategy instead of TWAP

### Rate limit errors

- Increase `delay` between chunks
- The script automatically handles rate limits by retrying

### Orders not filling

- Check market conditions
- Adjust chunk size
- Consider using limit ladder strategy

## Safety Features

1. **Time Limit Check**: Warns if estimated execution time exceeds max time
2. **User Confirmation**: Requires confirmation for extremely large orders
3. **Progress Tracking**: Shows progress during execution
4. **Error Handling**: Continues execution even if individual chunks fail

## Monitoring Execution

The script provides real-time feedback:

```
🚀 Starting execution at 18:30:00
✅ Slice 1: 0.001 BTC @ $76,751.50
✅ Slice 2: 0.001 BTC @ $76,752.30
✅ Slice 3: 0.001 BTC @ $76,753.10
...
```

After completion:

```
✅ Execution completed at 19:13:24
   Total time: 43.4 minutes
   Orders executed: 1303
   Total filled: 1.302960 BTC
   Average price: $76,752.45
   Total value: $100,000.12
```
