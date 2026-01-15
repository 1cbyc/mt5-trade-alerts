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

## How it works
1. Monitors Volatility 25 Index and Step Index for price movements
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
  ],
  "GBPUSD": [
    {
      "id": "target_1",
      "price": 1.2500,
      "type": "both",
      "description": "Take profit level"
    }
  ]
}
```

**Price Level Types:**
- `above`: Alert when price goes above the level
- `below`: Alert when price goes below the level
- `both`: Alert when price reaches the level (exact match)

## Usage

### Start the Service

```bash
python main.py
```

The service will:
1. Connect to your MT5 terminal
2. Connect to Telegram
3. Start monitoring trades, orders, and price levels
4. Send alerts to your Telegram chat
5. Enable interactive Telegram commands for trade management and analytics

### Stop the Service

Press `Ctrl+C` to gracefully shutdown the service.

## Alert Examples

### Trade Alert
```
🟢 Trade OPENED (BUY)

Ticket: 12345678
Symbol: EURUSD
Type: BUY
Volume: 0.10
Open Price: 1.0950
Current Price: 1.0955
Profit: 💰 5.00
Time: 2024-01-15 10:30:00
```

### Order Alert
```
📋 Order Alert

Ticket: 87654321
Symbol: GBPUSD
Type: BUY LIMIT
Volume: 0.10
Price: 1.2500
Current Price: 1.2480
Setup Time: 2024-01-15 10:00:00
Expiration: 2024-01-15 18:00:00
```

### Price Level Alert
```
🎯 Price Level Reached

Symbol: EURUSD
Level ID: resistance_1
Target Price: 1.1000
Current Price: 1.1001
Direction: above
Time: 2024-01-15 11:00:00
```

## Managing Price Levels

You can edit `price_levels.json` directly or use the provided utility script:

```bash
python manage_levels.py
```

## Telegram Commands

The bot supports various commands for monitoring and managing your trades. Send these commands directly to your bot in Telegram.

### Account & Position Commands

#### `/status`
View your account status including balance, equity, margin, and open positions count.

**Example:**
```
/status
```

#### `/positions`
List all open positions with current profit/loss information.

**Example:**
```
/positions
```

#### `/orders`
List all pending orders (buy limits, sell limits, stop orders, etc.).

**Example:**
```
/orders
```

#### `/summary`
Get a daily/weekly P/L summary with trade statistics.

**Example:**
```
/summary
```

### Trade Management Commands

#### `/close <ticket>`
Close a specific position by ticket number.

**Example:**
```
/close 12345678
```

#### `/closeall`
Close all open positions at once.

**Example:**
```
/closeall
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

### Analytics & History Commands

#### `/chart [type] [days]`
Generate and send performance charts as images.

**Parameters:**
- `type`: Chart type - `summary` (default), `equity`, `daily`, or `distribution`
- `days`: Number of days to analyze (default: 30)

**Examples:**
```
/chart                    # Summary chart for last 30 days
/chart summary 60         # Summary chart for last 60 days
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
/history                          # Last 7 days, 20 trades
/history days=30                  # Last 30 days
/history symbol=EURUSD            # Only EURUSD trades
/history days=7 limit=10          # Last 7 days, top 10 trades
/history days=30 symbol=GBPUSD limit=5
```

#### `/note <ticket> <note>`
Add a note to a trade in your journal.

**Parameters:**
- `ticket`: Trade ticket number
- `note`: Your note text

**Example:**
```
/note 12345678 Good entry, followed trend perfectly
```

#### `/export [days=X] [symbol=X]`
Export trade history to CSV file.

**Parameters:**
- `days=X`: Number of days to export (default: all)
- `symbol=X`: Filter by symbol (optional)

**Examples:**
```
/export                    # Export all trades
/export days=30            # Export last 30 days
/export symbol=EURUSD     # Export only EURUSD trades
/export days=90 symbol=GBPUSD
```

### Smart Features Commands

#### `/mlinsights [symbol]`
View ML-learned trading insights and patterns.

**Parameters:**
- `symbol`: Optional symbol to analyze (default: all symbols)

**Examples:**
```
/mlinsights                # Overall insights
/mlinsights EURUSD         # Symbol-specific insights
```

**Shows:**
- Win rate and trade statistics
- Average profit targets
- Average hold times
- Risk/reward ratios
- Profit distribution patterns

#### `/volatility <symbol>`
View volatility metrics and position sizing suggestions.

**Parameters:**
- `symbol`: Trading symbol to analyze

**Example:**
```
/volatility EURUSD
```

**Shows:**
- Current volatility level (low/medium/high/very_high)
- ATR (Average True Range)
- Standard deviation
- Suggested position size based on volatility
- Risk calculations

### Help Command

#### `/help` or `/start`
Show the complete list of available commands with descriptions.

**Example:**
```
/help
```

## Command Categories Summary

| Category | Commands |
|----------|----------|
| **Account Info** | `/status`, `/positions`, `/orders`, `/summary` |
| **Trade Management** | `/close`, `/closeall`, `/modify`, `/partial` |
| **Analytics** | `/chart`, `/history`, `/note`, `/export` |
| **Smart Features** | `/mlinsights`, `/volatility` |
| **Help** | `/help`, `/start` |

## Troubleshooting

### MT5 Connection Issues
- Ensure MT5 terminal is installed and can be accessed
- Verify your login credentials are correct
- Check that the MT5_PATH points to the correct terminal executable
- Make sure MT5 terminal is running (or the path allows auto-start)

### Telegram Issues
- Verify your bot token is correct
- Ensure you've started a conversation with your bot
- Check that your chat ID is correct
- Test by sending a message to your bot manually

### No Alerts Received
- Check the log file `mt5_alerts.log` for errors
- Verify alert types are enabled in `config.env`
- Ensure you have active trades/orders or configured price levels
- Check that the monitoring interval is appropriate

## Logs

All activity is logged to:
- Console output (stdout)
- `mt5_alerts.log` file

## Security Notes

- Never commit `config.env` to version control (it's in `.gitignore`)
- Keep your MT5 credentials secure
- Don't share your Telegram bot token
- Use environment variables or secure vaults for production deployments

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## Support

For issues or questions, check the logs first. If you still need help, then:

- [Create an issue](https://github.com/1cbyc/mt5-trade-alerts/issues/new) on GitHub
- Or, reach me on [x.com/1cbyc](https://x.com/1cbyc)

Common issues are usually related to:
- Incorrect credentials
- MT5 terminal not accessible
- Telegram bot not properly configured

