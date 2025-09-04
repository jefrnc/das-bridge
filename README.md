# DAS Trader Python API Client

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

[English](README.md) | [Español](README.es.md)

</div>

Complete Python client for the DAS Trader Pro CMD API that enables automated trading, real-time order management, position tracking, and market data streaming.

## 🚀 Key Features

- **Complete Trading**: Send, modify, and cancel orders (Market, Limit, Stop, Peg, etc.)
- **Real-Time Market Data**: Level 1, Level 2, and Time & Sales streaming
- **Position Management**: Automatic position tracking and real-time P&L
- **Historical Data**: Access to daily and minute charts
- **Automatic Reconnection**: Robust connection handling with auto-reconnect
- **Multi-Platform Notifications**: 7 different notification types
- **Native Asyncio**: High performance with concurrent operations
- **Type Safety**: Fully typed for better IDE support
- **Comprehensive Logging**: Detailed logging system for debugging

## 📋 Requirements

- Python 3.8+
- DAS Trader Pro with CMD API enabled
- Valid DAS Trader account

## ⚡ Quick Installation

```bash
git clone https://github.com/jefrnc/das-bridge.git
cd das-bridge
pip install -e .
```

### Optional Dependencies

```bash
# For notifications
pip install aiohttp

# For data analysis
pip install numpy pandas matplotlib

# For Windows desktop notifications
pip install win10toast  # Windows only

# For configuration management
pip install python-dotenv
```

## 🔧 Configuration

### 1. Environment Variables
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Basic Configuration
```python
# .env
DAS_HOST=localhost
DAS_PORT=9910
DAS_USERNAME=your_das_username
DAS_PASSWORD=your_das_password
DAS_ACCOUNT=your_das_account
```

## 🎯 Basic Usage

```python
import asyncio
from das_trader import DASTraderClient, OrderSide, OrderType, MarketDataLevel

async def main():
    # Create client
    client = DASTraderClient(host="localhost", port=9910)
    
    try:
        # Connect to DAS Trader
        await client.connect("your_username", "your_password", "your_account")
        
        # Get buying power
        bp = await client.get_buying_power()
        print(f"Buying Power: ${bp['buying_power']:,.2f}")
        
        # Subscribe to market data
        await client.subscribe_quote("AAPL", MarketDataLevel.LEVEL1)
        
        # Get quote
        quote = await client.get_quote("AAPL")
        print(f"AAPL: Bid ${quote.bid} | Ask ${quote.ask} | Last ${quote.last}")
        
        # Send order
        order_id = await client.send_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=150.00
        )
        print(f"Order sent: {order_id}")
        
        # Check positions
        positions = client.get_positions()
        for pos in positions:
            if not pos.is_flat():
                print(f"{pos.symbol}: {pos.quantity} shares, "
                      f"P&L: ${pos.unrealized_pnl:.2f}")
        
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📊 Supported Order Types

```python
# Market Order
await client.send_order("AAPL", OrderSide.BUY, 100, OrderType.MARKET)

# Limit Order
await client.send_order("AAPL", OrderSide.BUY, 100, OrderType.LIMIT, price=150.00)

# Stop Loss
await client.send_order("AAPL", OrderSide.SELL, 100, OrderType.STOP, stop_price=145.00)

# Stop Limit
await client.send_order("AAPL", OrderSide.SELL, 100, OrderType.STOP_LIMIT, 
                       price=148.00, stop_price=145.00)

# Trailing Stop
await client.send_order("AAPL", OrderSide.SELL, 100, OrderType.TRAILING_STOP,
                       trail_amount=2.00)
```

## 📱 Notification System

Supports 7 different notification types:

### 📧 Email
```python
NOTIFICATION_TYPE=email
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
```

### 🎮 Discord
```python
NOTIFICATION_TYPE=discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN
```

### 📱 Telegram
```python
NOTIFICATION_TYPE=telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 📲 Pushover (Mobile Notifications)
```python
NOTIFICATION_TYPE=pushover
PUSHOVER_USER_KEY=your_user_key
PUSHOVER_APP_TOKEN=your_app_token
```

### 💼 Slack
```python
NOTIFICATION_TYPE=slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK
```

### 🖥️ Desktop (Windows/macOS/Linux)
```python
NOTIFICATION_TYPE=desktop
ENABLE_DESKTOP_NOTIFICATIONS=true
```

### 🌐 Custom Webhook
```python
NOTIFICATION_TYPE=webhook
CUSTOM_WEBHOOK_URL=https://your-server.com/webhook
WEBHOOK_AUTH_TOKEN=your_token
```

## 📈 Callbacks and Events

```python
# Order callbacks
def on_order_filled(order):
    print(f"Order filled: {order.symbol}")

def on_order_rejected(order):
    print(f"Order rejected: {order.symbol}")

client.orders.register_callback("order_filled", on_order_filled)
client.orders.register_callback("order_rejected", on_order_rejected)

# Position callbacks
def on_position_update(position):
    print(f"Position updated: {position.symbol} P&L: ${position.unrealized_pnl:.2f}")

client.positions.register_callback("position_updated", on_position_update)

# Market data callbacks
def on_quote_update(quote):
    print(f"{quote.symbol}: ${quote.last}")

client.market_data.register_callback("quote_update", on_quote_update)
```

## 🤖 Advanced Examples

### Basic Trading Bot
```python
# See examples/trading_bot.py
python examples/trading_bot.py
```

### Portfolio Monitor
```python
# See examples/portfolio_monitor.py
python examples/portfolio_monitor.py
```

### Market Data Streaming
```python
# See examples/market_data_streaming.py
python examples/market_data_streaming.py
```

### Notification System
```python
# See examples/notifications_example.py
python examples/notifications_example.py
```

## 🛡️ Risk Management

```python
# Configuration in config.example.py
MAX_POSITION_SIZE = 1000
MAX_ORDER_VALUE = 50000.0
STOP_LOSS_PERCENT = 0.02  # 2%
TAKE_PROFIT_PERCENT = 0.04  # 4%

# Paper Trading Mode
PAPER_TRADING_MODE = True
PAPER_TRADING_INITIAL_BALANCE = 100000.0
```

## 📚 API Documentation

### Main Classes

- **`DASTraderClient`**: Main client for interacting with DAS Trader
- **`OrderManager`**: Order management and status tracking
- **`PositionManager`**: Position tracking and P&L
- **`MarketDataManager`**: Market data streaming and caching
- **`ConnectionManager`**: TCP connection handling and reconnection
- **`NotificationManager`**: Multi-platform notification system

### Main Enums

- **`OrderType`**: MARKET, LIMIT, STOP, STOP_LIMIT, PEG, TRAILING_STOP
- **`OrderSide`**: BUY, SELL, SHORT, COVER
- **`OrderStatus`**: PENDING, NEW, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED
- **`TimeInForce`**: DAY, GTC, IOC, FOK, MOO, MOC
- **`MarketDataLevel`**: LEVEL1, LEVEL2, TIME_SALES

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=das_trader --cov-report=html
```

## 🔐 Security

- **Never** commit credentials in code
- Use environment variables for sensitive configuration
- The `.env` file is in `.gitignore`
- Consider using paper trading mode for testing

## 📝 Logging

```python
import logging
logging.basicConfig(level=logging.INFO)

# The client includes detailed logging:
# - Connections and authentication
# - Sent and received orders
# - Market data streaming
# - Errors and reconnections
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

## 📄 License

This project is under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for educational and development purposes. Automated trading carries significant financial risks. Use at your own risk and always consider:

- Thorough testing in paper trading mode
- Proper risk management
- Constant position monitoring
- Compliance with local regulations

## 🔗 Related Projects

- **[das-api-examples](https://github.com/jefrnc/das-api-examples)**: Practical examples and tests for the DAS Trader Pro CMD API
  - Direct TCP connection tests
  - API feature verification
  - Configuration guides and troubleshooting

## 📚 Useful Links

- [DAS Trader Pro Documentation](https://dastrader.com)
- [CMD API Manual](CMD%20API%20Manual.pdf)
- [Usage Examples](examples/)
- [Tests](tests/)

## 📞 Support

To report bugs or request features:
- Open an [Issue](https://github.com/jefrnc/das-bridge/issues)
- Check the [documentation](examples/)
- Consult the [examples](examples/)

---

**Developed with ❤️ for the algorithmic trading community**