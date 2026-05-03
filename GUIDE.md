# Bot Trade — Complete Guide
# Nado x Rise x Decibel — Multi-Exchange DEX Trading Bot

---

## Daftar Isi

1. [Overview & Arsitektur](#1-overview--arsitektur)
2. [Prerequisites & Instalasi](#2-prerequisites--instalasi)
3. [Konfigurasi .env](#3-konfigurasi-env)
4. [Setup Per Exchange](#4-setup-per-exchange)
5. [Cara Jalankan Bot](#5-cara-jalankan-bot)
6. [Mode Trading](#6-mode-trading)
7. [Delta Neutral: Penjelasan Lengkap](#7-delta-neutral-penjelasan-lengkap)
8. [Minara AI Skill](#8-minara-ai-skill)
9. [Troubleshooting](#9-troubleshooting)
10. [Risk Management](#10-risk-management)

---

## 1. Overview & Arsitektur

Bot ini mendukung 3 exchange DEX perpetual sekaligus:

| Exchange | Blockchain | Native Currency | Trading Method |
|---|---|---|---|
| **Nado** | Ink Chain (EVM L2) | ETH | nado-cli + Python SDK |
| **Rise Trade** | Rise Chain (EVM L2) | ETH | REST API |
| **Decibel** | Aptos | APT / USDC | On-chain Move transactions |

### Cara Kerja Bot

```
┌─────────────────────────────────────────────────────────┐
│                    CLI (bot_trade)                       │
│  funding │ delta-neutral │ volume │ indicator │ status   │
└──────────────────────┬──────────────────────────────────┘
                       │
           ┌───────────▼───────────┐
           │   Strategy Engine     │
           │ ┌─────────────────┐  │
           │ │ FundingScanner  │  │  ← compare semua exchange
           │ │ DeltaNeutral    │  │  ← auto open/close positions
           │ │ VolumeGenerator │  │  ← TWAP volume farming
           │ │ IndicatorTrader │  │  ← RSI/EMA/MACD signal
           │ └─────────────────┘  │
           └──────────┬────────────┘
                      │
      ┌───────────────┼───────────────┐
      ▼               ▼               ▼
 ┌─────────┐   ┌─────────────┐  ┌──────────┐
 │  Nado   │   │   Decibel   │  │   Rise   │
 │Exchange │   │  Exchange   │  │ Exchange │
 └─────────┘   └─────────────┘  └──────────┘
 nado-cli +    REST(read) +      REST API
 Python SDK    Aptos on-chain
```

### File Struktur

```
d:\bot\bot trade\
├── .env                          ← BUAT INI (copy dari .env.example)
├── .env.example                  ← template
├── requirements.txt
├── pyproject.toml
├── README.md
├── GUIDE.md                      ← file ini
│
├── skills/                       ← Minara AI skill files
│   ├── SKILL.md                  ← master skill descriptor
│   ├── nado-trading.md
│   ├── decibel-trading.md
│   ├── rise-trading.md
│   └── delta-neutral.md
│
└── bot_trade/
    ├── config.py
    ├── models.py
    ├── cli.py                    ← entry point
    ├── exchanges/
    │   ├── base.py               ← abstract interface
    │   ├── nado.py
    │   ├── decibel.py
    │   └── rise.py
    └── strategies/
        ├── funding_scanner.py    ← INTI: cari perbedaan funding
        ├── delta_neutral.py
        ├── volume_generator.py
        └── indicator_trader.py
```

---

## 2. Prerequisites & Instalasi

### System Requirements
- Python 3.10+
- Node.js 18+ (untuk nado-cli)
- pip, npm

### Langkah Instalasi

```powershell
# 1. Clone / masuk ke direktori bot
cd "d:\bot\bot trade"

# 2. Install Python core dependencies
pip install aiohttp httpx typer rich python-dotenv pandas numpy loguru nado-protocol

# 3. Install dependencies opsional per exchange
pip install aptos-sdk          # untuk Decibel (Aptos)
pip install web3 eth-account   # untuk Rise Trade (EVM)
pip install pandas-ta          # untuk indicator trading (RSI, EMA, MACD, dll)

# 4. Install Nado CLI (Node.js)
npm install -g @nadohq/nado-cli

# 5. Verifikasi instalasi
python -m bot_trade --help
nado --version
```

### Verifikasi Import

```powershell
python -c "from bot_trade.exchanges import get_all_exchanges; print('OK')"
# Output: OK
```

---

## 3. Konfigurasi .env

```powershell
# Copy template
Copy-Item .env.example .env

# Edit file
notepad .env
```

### Isi .env Lengkap

```env
# ─── NADO (Ink Blockchain) ───────────────────────────────────
NADO_PRIVATE_KEY=0xYOUR_INK_PRIVATE_KEY
NADO_SUBACCOUNT_OWNER=0x...         # opsional, jika pakai linked signer
NADO_ENV=nadoMainnet                 # nadoMainnet | nadoTestnet
NADO_SUBACCOUNT_NAME=default

# ─── DECIBEL (Aptos Blockchain) ──────────────────────────────
DECIBEL_PRIVATE_KEY=0xYOUR_APTOS_ED25519_KEY
DECIBEL_SUBACCOUNT_ADDR=0x...       # Decibel subaccount address kamu
DECIBEL_ENV=mainnet                  # mainnet | testnet

# ─── RISE TRADE (Rise Chain / EVM) ───────────────────────────
RISE_PRIVATE_KEY=0xYOUR_RISE_EVM_KEY
RISE_API_KEY=                        # jika diperlukan
RISE_RPC_URL=https://mainnet.riselabs.xyz
RISE_ENV=mainnet

# ─── BOT CONFIG ──────────────────────────────────────────────
LOG_LEVEL=INFO
DB_PATH=./bot_trade.db

# Risk Management
MAX_POSITION_USD=1000               # maksimal total posisi dalam USD
MAX_DRAWDOWN_PCT=5.0                # bot berhenti jika drawdown > X%
MAX_LEVERAGE=5                      # maksimal leverage

# Funding Arb Config
MIN_FUNDING_DIFF=0.01               # min selisih funding (%) untuk trigger arb
FUNDING_CHECK_INTERVAL=60           # detik antar pengecekan funding
```

> **PENTING:** Jangan pernah commit file `.env` ke git! Pastikan `.env` ada di `.gitignore`.

---

## 4. Setup Per Exchange

### 4.1 Nado (Ink Blockchain)

**Step 1: Install & Setup CLI**
```powershell
npm install -g @nadohq/nado-cli
nado setup
# Wizard akan minta private key dan pilih network
```

**Step 2: Test Koneksi (No Auth)**
```powershell
nado market price BTC
nado market tickers
nado market funding BTC
```

**Step 3: Test Account (Butuh Private Key)**
```powershell
nado account summary
nado account positions
```

**Cara Dapat Private Key Nado:**
1. Buka https://nado.xyz
2. Connect wallet → Settings → Export Subaccount Key
3. Copy ke `NADO_PRIVATE_KEY` di `.env`

---

### 4.2 Decibel (Aptos Blockchain)

**Decibel punya mekanisme khusus: Delegation Model**

```
User Wallet (owner)
    │
    └─ Delegate trading rights → Bot Wallet
           │
           └─ Bot bisa: place orders, open/close positions
           └─ Bot TIDAK bisa: withdraw funds, transfer assets
```

**Step 1: Setup Aptos Wallet**
```powershell
# Install Aptos CLI
pip install aptos-sdk

# Generate keypair jika belum punya
python -c "
from aptos_sdk.account import Account
acc = Account.generate()
print('Address:', acc.address())
print('Private Key:', acc.private_key.hex())
"
```

**Step 2: Setup Subaccount di Decibel**
1. Buka https://decibel.trade
2. Connect wallet Aptos kamu
3. Create subaccount → Settings → Get Subaccount Address
4. Isi `DECIBEL_SUBACCOUNT_ADDR` di `.env`

**Step 3: Delegasi ke Bot Wallet**
Bot wallet (dari private key di .env) perlu di-delegasi trading rights oleh main wallet kamu:
```python
# Jalankan sekali untuk setup delegasi
# (akan dibuat helper script)
python -m bot_trade setup-decibel
```

---

### 4.3 Rise Trade (Rise Chain)

**Step 1: Daftar API Access**
1. Buka https://developer.rise.trade
2. Login / Register
3. Buat API Key
4. Copy ke `RISE_API_KEY` di `.env`

**Step 2: Siapkan EVM Wallet**
- Gunakan private key dari wallet EVM (MetaMask, dll)
- Pastikan wallet sudah funded dengan ETH di Rise Chain
- Set `RISE_PRIVATE_KEY` di `.env`

**Test Koneksi:**
```powershell
python -m bot_trade status --exchange rise
```

---

## 5. Cara Jalankan Bot

### Semua perintah dijalankan dari direktori bot:

```powershell
cd "d:\bot\bot trade"
```

### Perintah Dasar

```powershell
# Lihat semua perintah
python -m bot_trade --help

# Lihat help untuk perintah tertentu
python -m bot_trade funding --help
python -m bot_trade delta-neutral --help
python -m bot_trade volume --help
python -m bot_trade indicator --help
python -m bot_trade status --help
```

---

## 6. Mode Trading

### Mode 1: Funding Rate Scanner

Scan funding rates semua exchange, tampilkan peluang delta-neutral.

```powershell
# Scan sekali (snapshot)
python -m bot_trade funding

# Watch mode (auto-refresh setiap 60 detik)
python -m bot_trade funding --watch

# Custom: hanya BTC, Nado vs Decibel
python -m bot_trade funding --symbols BTC --exchanges nado,decibel

# Filter: tampilkan hanya yang yield > 5% annual
python -m bot_trade funding --min-yield 5.0
```

**Output:**
```
╔══ Current Funding Rates ═══════╦══ Delta-Neutral Opportunities ═════╗
║ Exchange  Symbol  Rate/8h  APR ║ Symbol  Long@  Short@  Net  Yield  ║
║ NADO      BTC     +0.05%   5.5%║ BTC     decibel nado  0.07% 7.6%  ║
║ DECIBEL   BTC     -0.02%  -2.2%║ ETH     rise   nado  0.03% 3.3%  ║
║ RISE      BTC     +0.01%   1.1%║                                    ║
╚════════════════════════════════╩════════════════════════════════════╝
```

---

### Mode 2: Delta-Neutral (Cross-Exchange Funding Arb)

Otomatis buka posisi LONG + SHORT di exchange berbeda untuk collect funding rate difference.

```powershell
# Default: BTC, Nado+Decibel, $100/leg
python -m bot_trade delta-neutral

# Custom
python -m bot_trade delta-neutral \
  --exchanges nado,decibel \
  --size 500 \
  --min-yield 3.0 \
  --max-hours 24 \
  --leverage 1

# Dengan Rise Trade
python -m bot_trade delta-neutral \
  --exchanges nado,rise \
  --size 200 \
  --min-yield 5.0
```

**Parameter:**
| Parameter | Default | Keterangan |
|---|---|---|
| `--exchanges` | nado,decibel | Exchange yang digunakan (2) |
| `--size` | 100 | USD per leg (total exposure = 2x) |
| `--min-yield` | 5.0 | Min APR% untuk buka posisi |
| `--max-hours` | 24 | Maksimal durasi posisi terbuka |
| `--leverage` | 1 | Leverage (1 = no leverage) |
| `--interval` | 60 | Detik antar pengecekan |

---

### Mode 3: Volume Generator

Generate trading volume tinggi untuk farming points/reward exchange.

```powershell
# Nado BTC, target $10k volume, 1 jam
python -m bot_trade volume \
  --exchange nado \
  --symbol BTC \
  --target 10000 \
  --duration 3600

# Decibel ETH, target $50k, 2 jam, 30 slices
python -m bot_trade volume \
  --exchange decibel \
  --symbol ETH \
  --target 50000 \
  --duration 7200 \
  --slices 30

# Rise Trade tanpa native TWAP (simulated)
python -m bot_trade volume \
  --exchange rise \
  --target 5000 \
  --no-twap
```

---

### Mode 4: Indicator Trader

Trade berdasarkan sinyal teknikal.

```powershell
# RSI Mean Reversion (paling umum)
python -m bot_trade indicator \
  --exchange nado \
  --symbol BTC \
  --strategy rsi \
  --timeframe 15m \
  --size 100 \
  --rsi-low 30 \
  --rsi-high 70

# EMA Crossover
python -m bot_trade indicator \
  --strategy ema \
  --ema-fast 9 \
  --ema-slow 21 \
  --timeframe 1h

# MACD Momentum
python -m bot_trade indicator --strategy macd --timeframe 4h

# Bollinger Band
python -m bot_trade indicator --strategy bb --timeframe 15m

# VWAP
python -m bot_trade indicator --strategy vwap --timeframe 5m
```

**Strategi & Sinyal:**

| Strategy | Signal Long | Signal Short | Close |
|---|---|---|---|
| RSI | RSI < 30 (oversold) | RSI > 70 (overbought) | RSI kembali ke 50 |
| EMA | Fast cross above Slow | Fast cross below Slow | Arah EMA berbalik |
| MACD | Histogram positif | Histogram negatif | Histogram balik arah |
| BB | Harga touch lower band | Harga touch upper band | Harga ke midline |
| VWAP | Harga cross above VWAP | Harga cross below VWAP | — |

---

### Mode 5: Status

```powershell
# Semua exchange
python -m bot_trade status

# Satu exchange
python -m bot_trade status --exchange nado
```

---

## 7. Delta Neutral: Penjelasan Lengkap

### Konsep Dasar

**Funding Rate** adalah biaya yang dibayar oleh trader perp kepada lawan posisinya, dibayar setiap 8 jam (umumnya).

- Funding **positif** (+0.05%/8h): Longs **membayar** shorts
- Funding **negatif** (-0.02%/8h): Shorts **membayar** longs

### Cara Kerja Delta Neutral Cross-Exchange

```
Contoh situasi:
  Nado BTC funding:    +0.05%/8h
  Decibel BTC funding: -0.02%/8h

Aksi bot:
  SHORT BTC di Nado    → dapat receive +0.05%/8h
  LONG  BTC di Decibel → dapat receive +0.02%/8h (karena shorts membayar kita)

Total per 8 jam:   +0.07%
Total per hari:    +0.21%
Total per tahun:   ~7.6% (annualized)

Risiko harga: 0 (karena SHORT = LONG dalam notional yang sama)
```

### Kapan Bot Buka Posisi?

```
if annual_yield >= min_yield (default 5%):
    buka posisi
```

### Kapan Bot Tutup Posisi?

1. **Yield drop**: Annual yield turun < 30% dari threshold
2. **Max duration**: Sudah melewati --max-hours
3. **Manual**: Ctrl+C (graceful close)
4. **Emergency**: Bot auto-close jika ada error critical

### Risiko yang Perlu Diperhatikan

| Risiko | Penjelasan | Mitigasi |
|---|---|---|
| **Slippage** | Harga bergerak saat eksekusi | Gunakan leverage rendah, size kecil |
| **Funding flip** | Rate berubah arah mendadak | Bot auto-close jika yield < threshold |
| **Exchange risk** | Salah satu exchange down | Bot tutup leg yang masih terbuka |
| **Liquidation** | Posisi terlalu besar | MAX_LEVERAGE, MAX_POSITION_USD |
| **Gas fee** | Biaya transaksi on-chain | Pastikan ada APT untuk Decibel |

---

## 8. Minara AI Skill

Minara adalah AI agent framework. Skill files memungkinkan AI (Claude, Gemini, GPT) untuk memahami dan mengeksekusi perintah trading otomatis.

### Apa yang Bisa Dilakukan dengan Minara Skill?

Kamu bisa memberi perintah natural language ke AI agent:

```
"Scan funding rates di Nado dan Decibel untuk BTC"
"Jalankan delta neutral dengan size $200 jika ada opportunity"
"Generate 10k volume di Nado dalam 1 jam"
"Trade BTC pakai RSI strategy di Nado"
```

### Cara Setup

1. Install Minara CLI (jika ingin pakai Minara agent):
   ```bash
   npm install -g minara
   minara login
   ```

2. Atau gunakan dengan Claude Code / Cursor:
   ```
   Skill files sudah ada di: d:\bot\bot trade\skills\
   Claude akan otomatis detect dan gunakan skill ini
   ```

3. Tambahkan ke Claude Code:
   ```bash
   # Letakkan skill di .claude/skills/
   mkdir -p .claude/skills
   Copy-Item skills\* .claude\skills\
   ```

Lihat folder `skills/` untuk file skill yang sudah dibuat.

---

## 9. Troubleshooting

### Error: `charmap codec can't encode`
```powershell
# Windows encoding fix
$env:PYTHONIOENCODING = "utf-8"
python -m bot_trade funding
```

### Error: `nado not found`
```powershell
npm install -g @nadohq/nado-cli
# Restart terminal
nado --version
```

### Error: `aptos-sdk not installed`
```powershell
pip install aptos-sdk
```

### Error: `No exchange configured`
```
Pastikan file .env sudah dibuat dan diisi:
- NADO_PRIVATE_KEY untuk Nado
- DECIBEL_PRIVATE_KEY + DECIBEL_SUBACCOUNT_ADDR untuk Decibel
- RISE_PRIVATE_KEY untuk Rise
```

### Error: `Decibel market order failed`
```
Decibel butuh:
1. Subaccount sudah dibuat di decibel.trade
2. Bot wallet sudah di-delegasi trading rights
3. Ada USDC di subaccount
4. Ada APT untuk gas fee
```

### Bot tidak menemukan opportunity
```
Normal jika funding rates semua exchange mirip.
Coba turunkan --min-yield:
python -m bot_trade delta-neutral --min-yield 1.0

Atau pantau dulu tanpa trading:
python -m bot_trade funding --watch
```

---

## 10. Risk Management

### Parameter Penting di .env

```env
MAX_POSITION_USD=500    ← Mulai kecil dulu
MAX_DRAWDOWN_PCT=3.0    ← Lebih konservatif
MAX_LEVERAGE=1          ← No leverage untuk pemula
```

### Best Practices

1. **Test di Testnet dulu**
   ```env
   NADO_ENV=nadoTestnet
   DECIBEL_ENV=testnet
   ```

2. **Mulai dengan size kecil** — $50-100 per leg sebelum naik

3. **Monitor funding sebelum trade**
   ```powershell
   python -m bot_trade funding --watch
   # Amati selama beberapa jam sebelum eksekusi
   ```

4. **Jangan tinggalkan bot tanpa pantauan** di awal

5. **Set max-hours yang reasonable** — jangan terlalu lama jika market volatile

6. **Backup .env** di tempat aman (password manager)

---

*Guide ini dibuat untuk bot-trade v1.0 | Nado x Rise x Decibel*
