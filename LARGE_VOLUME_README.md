# Large Volume Trading for Decibel Exchange

Execute large orders with minimal slippage and market impact.

## Features

- **Order Slicing**: Split large orders into smaller chunks
- **TWAP**: Time-Weighted Average Price execution
- **Limit Ladder**: Place orders at multiple price levels
- **Slippage Protection**: Monitor and control slippage
- **Configurable Strategies**: Customize execution parameters

## Installation

Already included in the Decibel bot. No additional installation needed.

## Quick Start

### Simple Market Slice Execution

```python
import asyncio
from bot_trade.exchanges.decibel_large_volume import execute_large_volume
from bot_trade.models import OrderSide

async def trade():
    # Execute 0.01 BTC LONG in 0.001 BTC chunks
    orders = await execute_large_volume(
        symbol='BTC',
        side=OrderSide.LONG,
        size=0.01,
        max_chunk_size=0.001,
        slice_delay=2.0
    )
    print(f"Executed {len(orders)} orders")

asyncio.run(trade())
```

### Advanced Configuration

```python
import asyncio
from bot_trade.exchanges.decibel_large_volume import (
    LargeVolumeTrader,
    LargeVolumeConfig,
    ExecutionStrategy
)
from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide

async def trade():
    # Initialize exchange
    exchange = DecibelExchange()

    # Configure execution parameters
    config = LargeVolumeConfig(
        max_single_order_size=0.001,  # Max size per order
        slice_delay_seconds=2.0,  # Delay between slices
        slippage_tolerance_percent=0.5,  # Max slippage
        price_spread_percent=0.1,  # Spread for limit ladder
        num_ladder_rungs=5  # Number of ladder rungs
    )

    # Create trader
    trader = LargeVolumeTrader(exchange, config)

    # Execute using TWAP strategy
    orders = await trader.execute_large_order(
        symbol='BTC',
        side=OrderSide.LONG,
        total_size=0.01,
        strategy=ExecutionStrategy.TWAP
    )

    # Check results
    print(f"Total filled: {trader.get_total_filled_size():.6f} BTC")
    avg_price = trader.get_average_fill_price()
    if avg_price:
        print(f"Average price: ${avg_price:.2f}")

asyncio.run(trade())
```

## Execution Strategies

### 1. Market Slice (Default)

Splits large orders into smaller market orders with delays between slices.

**Best for:**
- Fast execution
- Orders that need to fill quickly
- Liquid markets

**Configuration:**
```python
config = LargeVolumeConfig(
    max_single_order_size=0.001,  # Max size per slice
    slice_delay_seconds=2.0  # Delay between slices
)
```

### 2. Limit Ladder

Places limit orders at multiple price levels to fill gradually.

**Best for:**
- Reducing slippage
- Patient execution
- Volatile markets

**Configuration:**
```python
config = LargeVolumeConfig(
    max_single_order_size=0.001,
    num_ladder_rungs=5,  # Number of price levels
    price_spread_percent=0.1  # Spread between levels
)
```

### 3. TWAP (Time-Weighted Average Price)

Spreads order execution over time to achieve average price.

**Best for:**
- Large orders
- Minimizing market impact
- Achieving fair average price

**Configuration:**
```python
config = LargeVolumeConfig(
    max_single_order_size=0.001
)
# TWAP automatically calculates delays for 5-minute duration
```

## API Reference

### LargeVolumeConfig

Configuration for large volume trading.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_single_order_size` | float | 0.01 | Max size per single order (in BTC) |
| `slice_delay_seconds` | float | 1.0 | Delay between slices |
| `slippage_tolerance_percent` | float | 0.5 | Max acceptable slippage |
| `price_spread_percent` | float | 0.1 | Spread for limit ladder |
| `num_ladder_rungs` | int | 5 | Number of rungs in limit ladder |

### LargeVolumeTrader

Main class for executing large volume orders.

#### Methods

##### `execute_large_order(symbol, side, total_size, strategy, leverage, reduce_only)`

Execute a large order using the specified strategy.

**Parameters:**
- `symbol` (str): Trading pair (e.g., 'BTC')
- `side` (OrderSide): Order side (LONG or SHORT)
- `total_size` (float): Total size to execute
- `strategy` (ExecutionStrategy): Execution strategy
- `leverage` (int, optional): Leverage multiplier (default: 1)
- `reduce_only` (bool, optional): If True, only reduce existing position (default: False)

**Returns:** List[Order] - List of executed orders

##### `get_executed_orders()`

Get all orders executed by this trader.

**Returns:** List[Order]

##### `get_average_fill_price()`

Calculate the average fill price of all executed orders.

**Returns:** Optional[float] - Average fill price, or None if no orders executed

##### `get_total_filled_size()`

Get total filled size across all orders.

**Returns:** float - Total filled size

##### `get_total_slippage(expected_price)`

Calculate total slippage relative to expected price.

**Parameters:**
- `expected_price` (float): The expected average price

**Returns:** Optional[float] - Slippage in percent, or None if no orders executed

### ExecutionStrategy

Enum for order execution strategies.

| Value | Description |
|-------|-------------|
| `MARKET_SLICE` | Split into market orders |
| `LIMIT_LADDER` | Place limit orders at different prices |
| `TWAP` | Time-Weighted Average Price |

## Examples

### Example 1: Execute 0.01 BTC LONG with Market Slices

```python
from bot_trade.exchanges.decibel_large_volume import execute_large_volume
from bot_trade.models import OrderSide

orders = await execute_large_volume(
    symbol='BTC',
    side=OrderSide.LONG,
    size=0.01,
    strategy=ExecutionStrategy.MARKET_SLICE,
    max_chunk_size=0.001,
    slice_delay=2.0
)
```

### Example 2: Execute 0.005 BTC SHORT with Limit Ladder

```python
from bot_trade.exchanges.decibel_large_volume import (
    LargeVolumeTrader,
    LargeVolumeConfig,
    ExecutionStrategy
)
from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide

exchange = DecibelExchange()
config = LargeVolumeConfig(
    max_single_order_size=0.001,
    num_ladder_rungs=5,
    price_spread_percent=0.1
)
trader = LargeVolumeTrader(exchange, config)

orders = await trader.execute_large_order(
    symbol='BTC',
    side=OrderSide.SHORT,
    total_size=0.005,
    strategy=ExecutionStrategy.LIMIT_LADDER
)
```

### Example 3: Execute 0.01 BTC LONG with TWAP

```python
from bot_trade.exchanges.decibel_large_volume import (
    LargeVolumeTrader,
    ExecutionStrategy
)
from bot_trade.exchanges.decibel import DecibelExchange
from bot_trade.models import OrderSide

exchange = DecibelExchange()
trader = LargeVolumeTrader(exchange)

orders = await trader.execute_large_order(
    symbol='BTC',
    side=OrderSide.LONG,
    total_size=0.01,
    strategy=ExecutionStrategy.TWAP
)
```

## Testing

Run the test suite:

```bash
cd /home/ubuntu/tradebot
/home/ubuntu/tradebot/.venv/bin/python test_large_volume.py
```

Run the examples:

```bash
cd /home/ubuntu/tradebot
/home/ubuntu/tradebot/.venv/bin/python example_large_volume.py
```

## Important Notes

1. **Position Size**: Adjust `max_single_order_size` based on your risk tolerance and market liquidity.

2. **Delays**: Longer delays between slices reduce slippage but increase execution time.

3. **Slippage**: Monitor slippage and adjust parameters accordingly.

4. **Market Conditions**: Different strategies work better in different market conditions.

5. **Testing**: Always test with small sizes before executing large orders.

## Troubleshooting

### Orders not filling

- Check if limit orders are placed at reasonable prices
- Increase `price_spread_percent` for limit ladder
- Consider using market slice for faster execution

### High slippage

- Reduce `max_single_order_size` for smaller chunks
- Increase `slice_delay_seconds` for more time between slices
- Use limit ladder or TWAP instead of market slice

### Execution too slow

- Reduce `slice_delay_seconds`
- Reduce `num_ladder_rungs` for limit ladder
- Use market slice for fastest execution

## License

MIT License - See LICENSE file for details.
