# MT5 Trade Alerts - Telegram Notifications

Get real-time Telegram alerts for your MetaTrader 5 trades, orders, and price levels. Never miss important trading events again!

## Features

- **Trade Alerts**: Get notified when positions are opened or closed
- **Order Alerts**: Monitor buy limits, sell limits, stop orders, and more
- **Price Level Alerts**: Set custom price levels and get alerts when they're reached
- **Profit Tracking**: See profit/loss information in real-time
- **Real-time Monitoring**: Continuous monitoring with configurable intervals
- **Interactive Commands**: Full Telegram bot with commands for trade management
- **Trade Automation**: Close, modify, and partially close positions via Telegram
- **Historical Analytics**: Trade history database with charts and statistics
- **ML-based Suggestions**: AI learns from your trading patterns to suggest optimal exits
- **Volatility Analysis**: Position sizing suggestions based on market volatility
- **Trade Journal**: Add notes to trades for later review
- **CSV Export**: Export trade data for external analysis
- **Multiple Accounts**: Run separate bot instances for multiple MT5 accounts simultaneously
- **Break-Even Automation**: Move stop loss to entry price manually or automatically when profit threshold is hit
- **Trailing Stops**: Software trailing stop that follows price and updates SL automatically
- **Economic Calendar**: Auto-alerts before high-impact news events, plus `/news` command to view the week ahead
- **Grid/DCA Tracking**: Detects multiple positions on the same symbol, shows average entry and total exposure via `/grid`
- **Correlation Alerts**: Alerts when normally-correlated pairs (e.g. XAUUSD/XAGUSD) diverge, with `/correlation` to view current readings

## How it works

1. Monitors configured symbols for price movements
2. Tracks all your active trades and orders automatically
3. Sends alerts when trades open and close
4. Sends alerts when orders are placed or executed
5. Suggests partial profit-taking when positions are profitable

## Prerequisites

- Python 3.8 or higher
- MetaTrader 5 terminal installed
- MT5 account credentials
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))
- Telegram Chat ID (your user ID or group ID)

## Installation

1. **Clone or download this repository**

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure the application**:
   - Copy `config.example.env` to `config.env`
   - Fill in your MT5 and Telegram credentials

4. **Get Telegram Bot Token**:
   - Open Telegram and search for [@BotFather](https://t.me/botfather)
   - Send `/newbot` and follow instructions
   - Copy the bot token to `config.env`

5. **Get Telegram Chat ID**:
   - Start a chat with your bot
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find your chat ID in the response (it's the `id` field in the `chat` object)

## Configuration

### config.env

```env
# Account label shown in all alerts (e.g. "Live", "Demo", "GoatFunded 1")
ACCOUNT_LABEL=My Account

# MT5 Configuration
MT5_LOGIN=your_mt5_login
MT5_PASSWORD=your_mt5_password
MT5_SERVER=your_mt5_server
MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Alert Settings
PRICE_CHECK_INTERVAL=5
ENABLE_TRADE_ALERTS=true
ENABLE_ORDER_ALERTS=true
ENABLE_PRICE_ALERTS=true
```

### price_levels.json

Configure price levels you want to monitor:

```json
{
  "EURUSD": [
    {
      "id": "resistance_1",
      "price": 1.1000,
      "type": "above",
      "description": "Key resistance level"
    },
    {
      "id": "support_1",
      "price": 1.0900,
      "type": "below",
      "description": "Key support level"
    }
  ]
}
```

**Price Level Types:**
- `above`: Alert when price goes above the level
- `below`: Alert when price goes below the level
- `both`: Alert when price reaches the level from either direction

## Usage

### Single Account

```bash
python main.py
```

This uses `config.env` by default.

### Specifying a Config File

```bash
python main.py --config configs/account1.env
```

### Multiple Accounts

You can run separate bot instances for multiple MT5 accounts simultaneously. Each instance connects to its own MT5 terminal, uses its own Telegram bot, and maintains its own trade history database.

#### Step 1 — Create a config file per account

Store account configs in the `configs/` folder:

```
configs/
  account1.env
  account2.env
  account3.env
```

Use `configs/example.env` as a template. Key fields to set per account:

```env
ACCOUNT_LABEL=GoatFunded 1        # Shows in every alert so you know which account
MT5_LOGIN=314712725
MT5_PASSWORD=your_password
MT5_SERVER=GoatFunded-Server
MT5_PATH=C:\MT5\GF1\terminal64.exe  # Unique terminal path per account
TELEGRAM_BOT_TOKEN=your_bot_token   # Unique bot token per account
TELEGRAM_CHAT_ID=your_chat_id
TRADE_HISTORY_DB_PATH=data/account1_trades.db  # Unique DB per account
```

All `configs/*.env` files are git-ignored so credentials are never committed.

#### Step 2 — Create separate MT5 terminal installations

Each bot instance needs its own MT5 terminal folder so they can run independently. MT5 does not allow two processes to share the same installation directory.

**For accounts on the same broker**, copy the terminal folder once per account:

```powershell
Copy-Item "C:\Program Files\MetaTrader 5" "C:\MT5\GF1" -Recurse
Copy-Item "C:\Program Files\MetaTrader 5" "C:\MT5\GF2" -Recurse
Copy-Item "C:\Program Files\MetaTrader 5" "C:\MT5\GF3" -Recurse
# ... repeat for each account
```

Then set `MT5_PATH` in each config to the corresponding `terminal64.exe`:

```env
MT5_PATH=C:\MT5\GF1\terminal64.exe
```

**For accounts on different brokers** (e.g., one GoatFunded account and one Deriv account), their MT5 terminals are already separate installations, so no copying is needed — just point each config to its own terminal path.

#### Step 3 — Create a separate Telegram bot per account

Each account needs its own bot token so the instances do not conflict. Go to [@BotFather](https://t.me/botfather), create a bot for each account, and set the token in the corresponding config file.

#### Step 4 — Enable algorithmic trading in each terminal

This must be done in every terminal instance, including each copied folder. The bot cannot place or manage trades without it.

In each MT5 terminal:

1. Go to Tools > Options > Expert Advisors
2. Check "Allow automated trading"
3. Check "Allow DLL imports"
4. Click OK
5. Make sure the AutoTrading button in the toolbar is enabled (green)

#### Step 5 — Run all accounts

Open a separate terminal window per account and run:

```bash
python main.py --config configs/account1.env
python main.py --config configs/account2.env
python main.py --config configs/account3.env
```

Each process will launch its MT5 terminal, log in automatically using the credentials in the config, connect its Telegram bot, and start monitoring independently.

The startup message sent to Telegram will show the account label, login number, server, balance, and equity so you can immediately confirm which account is running.

## Telegram Commands

The bot supports various commands for monitoring and managing your trades. Send commands directly to your bot in telegram.

### Account & Position Commands

#### `/status`
View your account status including balance, equity, margin, and open positions count.

#### `/positions`
List all open positions with current profit/loss information.

#### `/orders`
List all pending orders (buy limits, sell limits, stop orders, etc.).

#### `/summary`
Get a daily/weekly P/L summary with trade statistics.

### Trade Management Commands

#### `/close <ticket>`
Close a specific position by ticket number.

```
/close 12345678
```

#### `/closeall`
Close all open positions at once.

#### `/closeallorders`
Cancel all pending orders at once.

#### `/cancelorder <ticket>`
Cancel a specific pending order by ticket number.

```
/cancelorder 12345678
```

#### `/modify <ticket> <sl> <tp>`
Modify stop loss and/or take profit for a position.

**Parameters:**

- `ticket`: Position ticket number
- `sl`: New stop loss price (use `0` to remove, omit to keep current)
- `tp`: New take profit price (use `0` to remove, omit to keep current)

**Examples:**

```
/modify 12345678 1.0950 1.1050
/modify 12345678 0 1.1050    # Remove SL, set TP
/modify 12345678 1.0950 0    # Set SL, remove TP
```

#### `/partial <ticket> <volume>`
Partially close a position.

**Parameters:**

- `ticket`: Position ticket number
- `volume`: Volume to close (must be less than position volume)

**Example:**

```
/partial 12345678 0.5
```

#### `/breakeven <ticket>`
Move the stop loss to the entry price (break-even) for a position.

```
/breakeven 12345678
```

#### `/trail <ticket> <distance>`

Enable a software trailing stop on a position. The stop loss follows price as it moves in your favour, maintaining the specified distance.

**Parameters:**

- `ticket`: Position ticket number
- `distance`: Trail distance in price units (e.g. `2.0` for gold = $2.00, `0.0010` for EURUSD = 10 pips)
- Use `off` instead of a distance to disable trailing

**Examples:**

```
/trail 12345678 2.0          # Gold: $2 trailing stop
/trail 12345678 0.0010       # Forex: 10 pips trailing stop
/trail 12345678 10           # Index: 10 point trailing stop
/trail 12345678 off          # Disable trailing stop
```

### Analytics & History Commands

#### `/chart [type] [days]`
Generate and send performance charts as images.

```
/chart                    # Summary chart for last 30 days
/chart equity 30          # Equity curve for last 30 days
/chart daily 14           # Daily P/L chart for last 14 days
/chart distribution 30    # Win/loss distribution for last 30 days
```

#### `/history [days=X] [symbol=X] [limit=X]`
View your trade history with optional filters.

**Parameters:**

- `days=X`: Number of days to look back (default: 7)
- `symbol=X`: Filter by symbol (e.g., `EURUSD`)
- `limit=X`: Maximum number of trades to show (default: 20)

**Examples:**

```
/history
/history days=30
/history symbol=EURUSD
/history days=7 limit=10
```

#### `/note <ticket> <note>`
Add a note to a trade in your journal.

```
/note 12345678 Good entry, followed trend perfectly
```

#### `/export [days=X] [symbol=X]`
Export trade history to CSV file.

```
/export
/export days=30
/export symbol=EURUSD
```

### Smart Features Commands

#### `/mlinsights [symbol]`
View ML-learned trading insights and patterns including win rate, average profit targets, hold times, and risk/reward ratios.

#### `/volatility <symbol>`
View volatility metrics and position sizing suggestions based on ATR and standard deviation.

#### `/grid [symbol]`

View a summary of all symbols where you have 2 or more positions open (grid or DCA scenario). Shows average entry price, total volume, and per-position breakdown.

```
/grid               # All multi-position symbols
/grid XAUUSD        # Only XAUUSD
```

#### `/correlation`

View the current Pearson correlation between your configured pairs based on the last 50 H1 bars. The bot also sends automatic alerts when a pair diverges below the configured threshold.

Configure pairs in `config.env`:

```env
ENABLE_CORRELATION_ALERTS=true
CORRELATION_PAIRS=XAUUSD:XAGUSD,NAS100:US30
CORRELATION_LOOKBACK_BARS=50
CORRELATION_ALERT_THRESHOLD=0.5
```

#### `/news`

View today's medium and high-impact economic events. Automatically filtered to currencies relevant to your open positions.

```
/news                    # Today's events (auto-detected currencies)
/news week               # Full week calendar
/news USD EUR            # Filter by specific currencies
/news USD week           # Full week for USD events
```

The bot also sends automatic alerts 15 minutes before any high-impact event that affects your monitored symbols. Configure in `config.env`:

```env
ENABLE_NEWS_ALERTS=true
NEWS_MIN_IMPACT=High          # Low, Medium, or High
NEWS_ALERT_ADVANCE_MINUTES=15
NEWS_CURRENCIES=              # Leave empty to auto-detect from positions/symbols
```

### Help

#### `/help` or `/start`
Show the complete list of available commands.

## Command Summary

| Category | Commands |
|----------|----------|
| Account Info | `/status`, `/positions`, `/orders`, `/summary` |
| Trade Management | `/close`, `/closeall`, `/modify`, `/partial`, `/breakeven`, `/trail` |
| Order Management | `/closeallorders`, `/cancelorder` |
| Analytics | `/chart`, `/history`, `/note`, `/export` |
| Smart Features | `/mlinsights`, `/volatility`, `/grid`, `/correlation`, `/news` |
| Help | `/help`, `/start` |

## Project Structure

```
mt5-trade-alerts/
├── main.py                      # Entry point
├── config.env                   # Default single-account config (git-ignored)
├── config.example.env           # Config template
├── configs/                     # Per-account config files (all git-ignored)
│   └── example.env              # Template for account configs
├── src/
│   ├── core/alert_management.py
│   ├── services/alert_service.py
│   ├── notifiers/               # Telegram, Discord, Email, Webhook
│   ├── analytics/               # Trade history, charts, ML, volatility
│   ├── monitoring/mt5_monitor.py
│   └── utils/                   # Config, manage_levels
├── data/                        # Databases, JSON, CSV exports
└── scripts/                     # Utility scripts
```

## Troubleshooting

### MT5 Connection Issues

- Ensure the MT5 terminal at `MT5_PATH` exists
- Verify your login credentials are correct
- Make sure algorithmic trading is enabled in the terminal (Tools > Options > Expert Advisors)
- For multiple accounts, confirm each account has its own terminal folder

### Telegram Conflicts (409 error)

- Each account must use a unique bot token
- Only one process per bot token can poll for updates at a time
- Create separate bots via [@BotFather](https://t.me/botfather)

### No Alerts Received

- Check `mt5_alerts.log` for errors
- Verify alert types are enabled in the config file
- Ensure you have active trades/orders or configured price levels

## Logs

All activity is logged to:
- Console output (stdout)
- `mt5_alerts.log` file

## Security Notes

- Never commit `config.env` or `configs/*.env` to version control (both are git-ignored)
- Keep your MT5 credentials and Telegram bot tokens secure
- Use a separate bot token for each account to avoid conflicts

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## Support

For issues or questions, check the logs first. If you still need help:

- [Create an issue](https://github.com/1cbyc/mt5-trade-alerts/issues/new) on GitHub
- Or reach me on [x.com/1cbyc](https://x.com/1cbyc)
