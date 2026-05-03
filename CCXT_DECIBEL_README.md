# CCXT + Decibel Trading Bot

## 🎯 Overview

Bot trading yang menggabungkan kekuatan CCXT (market data & technical analysis) dengan Decibel DEX (on-chain execution).

**Arsitektur:**
```
CCXT (Binance/Bybit/etc) → Market Data + Technical Analysis
                          ↓
                    Signal Generation
                          ↓
Decibel DEX (Aptos)      → On-chain Execution
```

## ✨ Fitur

- **Multi-Exchange Analysis**: Gunakan data dari Binance, Bybit, OKX, dll
- **Technical Indicators**: RSI, MACD, Bollinger Bands, Moving Averages
- **Signal Generation**: Otomatis generate LONG/SHORT signals
- **On-Chain Execution**: Eksekusi di Decibel DEX dengan 40x leverage
- **Limit Orders**: Maker fee 0.0110% (hemat ~$23 per $100k)
- **Auto TP/SL**: Bisa diintegrasikan dengan strategy_with_tp.py

## 📦 Installation

```bash
cd /home/ubuntu/tradebot

# Install dependencies
/home/ubuntu/tradebot/.venv/bin/pip install ccxt pandas numpy

# Verify installation
/home/ubuntu/tradebot/.venv/bin/python -c "import ccxt, pandas, numpy; print('OK')"
```

## 🚀 Quick Start

### Test 5 Cycles

```bash
cd /home/ubuntu/tradebot
/home/ubuntu/tradebot/.venv/bin/python quick_start_ccxt.py
```

### Full Strategy (Target $100k Volume)

```bash
# Default settings (30s hold time)
/home/ubuntu/tradebot/.venv/bin/python ccxt_decibel_bot.py

# Custom settings
/home/ubuntu/tradebot/.venv/bin/python ccxt_decibel_bot.py \
    --exchange binance \
    --symbol BTC/USDT \
    --timeframe 1m \
    --leverage 40 \
    --balance 20.0 \
    --per-position 5.0 \
    --target-volume 100000.0 \
    --hold-time 30.0 \
    --max-cycles 125
```

## 📊 Technical Indicators

### RSI (Relative Strength Index)
- **Oversold (< 30)**: Potensi LONG
- **Overbought (> 70)**: Potensi SHORT

### MACD (Moving Average Convergence Divergence)
- **MACD > Signal + Histogram > 0**: Bullish momentum → LONG
- **MACD < Signal + Histogram < 0**: Bearish momentum → SHORT

### Bollinger Bands
- **Price < Lower Band**: Oversold → LONG
- **Price > Upper Band**: Overbought → SHORT

### Signal Strength (0-100)
- **≥ 70**: Strong LONG signal
- **≤ 30**: Strong SHORT signal
- **30-70**: NEUTRAL (skip cycle)

## 💡 Usage Examples

### Example 1: Conservative Trading

```bash
/home/ubuntu/tradebot/.venv/bin/python ccxt_decibel_bot.py \
    --exchange binance \
    --leverage 20 \
    --balance 20.0 \
    --per-position 5.0 \
    --hold-time 60.0 \
    --target-volume 50000.0
```

### Example 2: Aggressive Trading

```bash
/home/ubuntu/tradebot/.venv/bin/python ccxt_decibel_bot.py \
    --exchange bybit \
    --leverage 40 \
    --balance 20.0 \
    --per-position 5.0 \
    --hold-time 10.0 \
    --target-volume 100000.0
```

### Example 3: Multi-Timeframe Analysis

```bash
# 5-minute timeframe
/home/ubuntu/tradebot/.venv/bin/python ccxt_decibel_bot.py \
    --timeframe 5m \
    --hold-time 300.0

# 15-minute timeframe
/home/ubuntu/tradebot/.venv/bin/python ccxt_decibel_bot.py \
    --timeframe 15m \
    --hold-time 900.0
```

## 🎛️ Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--exchange` | binance | Exchange untuk market data (binance, bybit, okx, etc) |
| `--symbol` | BTC/USDT | Trading pair |
| `--timeframe` | 1m | Timeframe untuk analysis (1m, 5m, 15m, 1h) |
| `--leverage` | 40 | Leverage (1-40) |
| `--balance` | 20.0 | Total balance USD |
| `--per-position` | 5.0 | Balance per position USD |
| `--target-volume` | 100000.0 | Target daily volume USD |
| `--hold-time` | 30.0 | Hold time per cycle (seconds) |
| `--max-cycles` | None | Max cycles (None = unlimited) |

## 📈 Strategy Calculations

### Volume per Cycle

```
Balance: $20
Per Position: $5
Leverage: 40x
Position Value: $5 x 40x = $200
Max Positions: 4 ($20 / $5 = 4)
Volume per Cycle: 4 x $200 = $800
```

### Cycles for $100k Target

```
Target Volume: $100,000
Volume per Cycle: $800
Cycles Needed: 100,000 / 800 = 125 cycles
```

### Time Estimates

| Hold Time | Per Cycle | Total Time | Volume/Hour |
|-----------|-----------|------------|-------------|
| 10s | ~20s | ~42 min | ~$143k |
| 30s | ~40s | ~83 min | ~$72k |
| 60s | ~70s | ~146 min | ~$41k |

## 🔧 Advanced Usage

### Custom Signal Logic

Edit `ccxt_decibel_bot.py` dan modifikasi `generate_signal()`:

```python
def generate_signal(self, indicators: Dict) -> Tuple[str, float]:
    """Custom signal logic"""
    rsi = indicators['rsi']
    macd = indicators['macd']

    # Custom logic
    if rsi < 25 and macd > 0:
        return "LONG", 90  # Very strong LONG
    elif rsi > 75 and macd < 0:
        return "SHORT", 90  # Very strong SHORT
    else:
        return "NEUTRAL", 50
```

### Add More Indicators

```python
def calculate_indicators(self, df: pd.DataFrame) -> Dict:
    """Add custom indicators"""

    # Existing indicators...
    indicators = {
        'rsi': rsi.iloc[-1],
        'macd': macd.iloc[-1],
        # ...
    }

    # Add Stochastic
    low_14 = df['low'].rolling(window=14).min()
    high_14 = df['high'].rolling(window=14).max()
    k_percent = 100 * ((df['close'] - low_14) / (high_14 - low_14))
    d_percent = k_percent.rolling(window=3).mean()

    indicators['stoch_k'] = k_percent.iloc[-1]
    indicators['stoch_d'] = d_percent.iloc[-1]

    return indicators
```

### Integrate with TP/SL Strategy

Gunakan `strategy_with_tp.py` untuk auto take profit/stop loss:

```python
from strategy_with_tp import HighVolumeWithTPStrategy

strategy = HighVolumeWithTPStrategy(
    balance_usd=20.0,
    per_position_usd=5.0,
    leverage=40,
    target_daily_volume_usd=100000.0,
    take_profit_percent=0.5,  # 0.5% TP
    stop_loss_percent=1.0,  # 1% SL
)

await strategy.run_strategy(hold_time_seconds=30.0)
```

## 🐛 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'ccxt'"

**Solution:**
```bash
/home/ubuntu/tradebot/.venv/bin/pip install ccxt
```

### Issue: "Rate limit exceeded"

**Cause:** Terlalu banyak request ke exchange

**Solution:**
- Tambah delay antara cycles
- Gunakan timeframe yang lebih besar (5m instead of 1m)
- Kurangi max cycles

### Issue: "No signal - skipping this cycle"

**Cause:** Market conditions tidak memenuhi kriteria signal

**Solution:**
- Tunggu sampai market lebih volatile
- Adjust signal threshold di `generate_signal()`
- Gunakan timeframe yang lebih besar

### Issue: Positions not closing

**Cause:** Slippage atau network delay

**Solution:**
- Tambah hold time
- Kurangi position size
- Cek network connection

## 📚 Related Skills

- `decibel-trading`: Decibel DEX trading skill
- `strategy_with_tp.py`: Auto TP/SL strategy
- `strategy_high_volume.py`: High volume strategy

## ⚠️ Risks

- **High Leverage**: 40x leverage = 2.5% price move can liquidate
- **Slippage**: Fast trading causes slippage
- **Fees**: Many transactions = high fees
- **Market Risk**: Technical analysis tidak selalu akurat

## 🎓 Best Practices

1. **Test First**: Jalankan quick_start_ccxt.py (5 cycles) sebelum full strategy
2. **Start Small**: Mulai dengan leverage lebih kecil (20x)
3. **Monitor**: Watch positions dan PnL secara aktif
4. **Adjust**: Sesuaikan parameters berdasarkan market conditions
5. **Take Breaks**: Jangan trading 24/7

## 📞 Support

Jika ada masalah:
1. Cek logs di terminal
2. Verifikasi environment variables di `.env`
3. Pastikan Decibel wallet punya cukup USDC
4. Cek network connection

## 📝 License

MIT License - Gunakan dengan risiko sendiri!
