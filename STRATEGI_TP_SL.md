# Strategi Volume Tinggi dengan Auto Take Profit

## 🎯 Fitur

- ✅ **Limit Order** - Maker fee 0.0110% (hemat $23)
- ✅ **Auto Take Profit** - Close otomatis ketika profit tercapai
- ✅ **Stop Loss** - Protection dari loss besar
- ✅ **Real-time Monitoring** - Cek PnL setiap 2 detik
- ✅ **Volume Target** - $100k per hari

## 💰 Fee Comparison

| Tipe | Fee | Total Fee ($100k) | Savings |
|------|-----|-------------------|---------|
| Taker (Market) | 0.0340% | $34.00 | - |
| Maker (Limit) | 0.0110% | $11.00 | **$23.00** |

## 🚀 Cara Pakai

### 1. Test 5 Cycles
```bash
cd /home/ubuntu/tradebot
/home/ubuntu/tradebot/.venv/bin/python quick_start_tp.py
```

### 2. Full Strategy (Default)
```bash
/home/ubuntu/tradebot/.venv/bin/python strategy_with_tp.py
```

**Parameter default:**
- Saldo: $20
- Per posisi: $5
- Leverage: 40x
- Target: $100k
- Take Profit: 0.5%
- Stop Loss: 1.0%
- Hold time: 30 detik

### 3. Custom Parameter

```bash
# Custom TP/SL
/home/ubuntu/tradebot/.venv/bin/python strategy_with_tp.py 20 5 40 100000 30 0.5 1.0

# Custom TP 1%, SL 2%
/home/ubuntu/tradebot/.venv/bin/python strategy_with_tp.py 20 5 40 100000 30 1.0 2.0

# Custom TP 0.3%, SL 0.5% (lebih agresif)
/home/ubuntu/tradebot/.venv/bin/python strategy_with_tp.py 20 5 40 100000 30 0.3 0.5

# Batasi cycles untuk testing
/home/ubuntu/tradebot/.venv/bin/python strategy_with_tp.py 20 5 40 100000 30 0.5 1.0 5
```

## 📊 Parameter

| Parameter | Default | Deskripsi |
|-----------|---------|-----------|
| `balance` | 20.0 | Saldo total (USD) |
| `per_position` | 5.0 | Per posisi (USD) |
| `leverage` | 40 | Leverage multiplier |
| `target_volume` | 100000.0 | Target volume (USD) |
| `hold_time` | 30.0 | Waktu hold (detik) |
| `take_profit` | 0.5 | Take profit (%) |
| `stop_loss` | 1.0 | Stop loss (%) |
| `max_cycles` | None | Maks cycles (None = unlimited) |

## 📈 Cara Kerja

### 1. Buka Posisi
- Buka 4 posisi (2 LONG, 2 SHORT)
- Gunakan limit order (maker fee)
- Setiap posisi: $5 x 40x = $200

### 2. Monitor PnL
- Cek PnL setiap 2 detik
- Hitung profit/loss real-time

### 3. Auto Take Profit
- Close otomatis ketika profit ≥ 0.5%
- Simpan profit

### 4. Stop Loss
- Close otomatis ketika loss ≥ 1.0%
- Minimalkan loss

### 5. Close Sisa
- Close posisi yang belum ter-close
- Ulangi cycle

## 💡 Tips TP/SL

### Konservatif (Safe)
```bash
# TP 0.3%, SL 0.5%
/home/ubuntu/tradebot/.venv/bin/python strategy_with_tp.py 20 5 40 100000 30 0.3 0.5
```
- Profit lebih kecil tapi lebih sering
- Loss lebih kecil
- Win rate lebih tinggi

### Moderat (Balanced)
```bash
# TP 0.5%, SL 1.0% (default)
/home/ubuntu/tradebot/.venv/bin/python strategy_with_tp.py
```
- Balance antara profit dan risk
- Cocok untuk most traders

### Agresif (High Risk)
```bash
# TP 1.0%, SL 2.0%
/home/ubuntu/tradebot/.venv/bin/python strategy_with_tp.py 20 5 40 100000 30 1.0 2.0
```
- Profit lebih besar
- Loss lebih besar
- Win rate lebih rendah

## 📊 Monitoring Output

```
======================================================================
STRATEGI VOLUME TINGGI - LIMIT ORDER + AUTO TAKE PROFIT
======================================================================
💰 Saldo: $20.00
📊 Per posisi: $5.00
⚡ Leverage: 40x
🎯 Target volume: $100,000
📈 Maks posisi: 4
💵 Nilai per posisi: $200.00
🔄 Volume per cycle: $800.00
🎯 Cycles dibutuhkan: 125

💰 Fee Comparison:
   Maker fee: 0.0110%
   Taker fee: 0.0340%
   Savings: 0.0230%
   Savings per cycle: $0.1840
   Total savings: $23.00

🎯 Risk Management:
   Take Profit: 0.50%
   Stop Loss: 1.00%
   Check Interval: 2.0s
======================================================================

🚀 MEMULAI STRATEGI VOLUME TINGGI - LIMIT ORDER + AUTO TP/SL
======================================================================

📈 Membuka 4 posisi dengan limit order...
🚀 Membuka posisi long 0.002605 BTC @ $76768.64
✅ Posisi dibuka
🚀 Membuka posisi short 0.002605 BTC @ $76799.36
✅ Posisi dibuka
...

👀 Monitoring 4 posisi...
   Take Profit: 0.50%
   Stop Loss: 1.00%
   Check Interval: 2.0s

✨ TAKE PROFIT! Posisi 1 (long)
   Entry: $76768.64
   Current: $77107.00
   PnL: 0.44% ($0.88)
🔒 Menutup posisi short 0.002605 BTC @ $77107.00
✅ Posisi ditutup

...

======================================================================
✅ CYCLE #1 SELESAI
======================================================================
⏱️  Waktu cycle: 45.2 detik
📊 Volume cycle: $800.00
💰 Fee savings: $0.1840
💵 Profit: $1.50
📉 Loss: $0.50
📊 Net PnL: $1.00
📈 Total volume: $800.00
💰 Total profit: $1.50
📉 Total loss: $0.50
📊 Total net PnL: $1.00
🎯 Progress: 0.8%
⏰ ETA: 93.8 menit
🔄 Cycles tersisa: 124
======================================================================
```

## ⚠️ Risiko dan Peringatan

### 1. Likuidasi
- Leverage 40x = pergerakan 2.5% bisa likuidasi
- **Solusi**: Stop loss 1% untuk protection

### 2. Slippage
- Limit order bisa tidak terisi
- **Solusi**: Gunakan spread buffer 50%

### 3. Fee
- Banyak transaksi = banyak fee
- **Solusi**: Maker fee 0.0110% (hemat $23)

### 4. TP/SL Tidak Ter-trigger
- Market bisa bergerak cepat
- **Solusi**: Check interval 2 detik

## 🔧 Troubleshooting

### TP/SL Tidak Ter-trigger
- Kurangi check interval
- Pastikan koneksi internet stabil
- Cek apakah posisi masih ada

### Posisi Tidak Ter-close
- Cek limit price
- Pastikan reduce_only = True
- Cek saldo cukup

### Profit Kecil
- Kurangi TP target
- Tambah leverage (jika memungkinkan)
- Tambah hold time

### Loss Besar
- Kurangi SL target
- Tambah SL protection
- Kurangi leverage

## 📝 File yang Dibuat

| File | Deskripsi |
|------|-----------|
| `strategy_with_tp.py` | Strategi dengan auto TP/SL |
| `quick_start_tp.py` | Quick start 5 cycles |

## 🎯 Rekomendasi

### Step 1: Test
```bash
/home/ubuntu/tradebot/.venv/bin/python quick_start_tp.py
```
- Test 5 cycles
- Monitor TP/SL
- Sesuaikan parameter

### Step 2: Jalankan
```bash
/home/ubuntu/tradebot/.venv/bin/python strategy_with_tp.py
```
- TP 0.5%, SL 1.0%
- Default parameters
- Balance risk/reward

### Step 3: Optimasi
```bash
# Lebih agresif
/home/ubuntu/tradebot/.venv/bin/python strategy_with_tp.py 20 5 40 100000 30 1.0 2.0

# Lebih konservatif
/home/ubuntu/tradebot/.venv/bin/python strategy_with_tp.py 20 5 40 100000 30 0.3 0.5
```

## ✅ Checklist

Sebelum menjalankan:
- [x] Saldo cukup ($20)
- [x] API key valid
- [x] Koneksi internet stabil
- [x] Paham risiko leverage 40x
- [x] Siap monitoring TP/SL
- [x] Paham fee maker vs taker

Selama menjalankan:
- [ ] Monitor TP/SL trigger
- [ ] Cek net PnL
- [ ] Watch out untuk likuidasi
- [ ] Istirahat jika perlu

Setelah selesai:
- [ ] Review hasil
- [ ] Hitung total profit/loss
- [ ] Evaluasi TP/SL
- [ ] Sesuaikan untuk next time

## 🎉 Selamat Trading!

Dengan strategi ini, kamu bisa:
- ✅ Mencapai $100k volume per hari
- ✅ Hemat $23 fee dengan maker order
- ✅ Auto take profit untuk secure profit
- ✅ Stop loss untuk protection
- ✅ Real-time monitoring

**Ingat:** Leverage tinggi = risiko tinggi. Trading dengan bijak!
