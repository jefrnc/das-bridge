# DAS Bridge

A Python bridge/wrapper for DAS Trader Pro's CMD API, enabling automated trading, real-time market data streaming, and comprehensive order management.

## Overview

DAS Bridge provides a clean, asyncio-based Python interface to interact with DAS Trader Pro's Frontend CMD API. It handles the low-level TCP communication and protocol details, offering a simple and intuitive API for building trading applications, algorithms, and automation tools.

## Features

- 🚀 **Full Trading Capabilities**: Place, modify, and cancel orders (Market, Limit, Stop, Peg orders)
- 📊 **Real-time Market Data**: Stream Level 1, Level 2, and Time & Sales data
- 📈 **Historical Data**: Access day and minute charts
- 💼 **Position Management**: Track positions, P&L, and buying power in real-time
- 🔄 **Auto-reconnection**: Robust connection handling with automatic reconnection
- ⚡ **Async/Await Support**: Built on asyncio for high-performance concurrent operations
- 🛡️ **Type Safety**: Full type hints for better IDE support and code reliability
- 📝 **Comprehensive Logging**: Detailed logging for debugging and monitoring

## Quick Start

```python
from das_bridge import DASTraderAPI

# Initialize and connect
das = DASTraderAPI(host='localhost', port=9910)
await das.connect('username', 'password', 'account')

# Place an order
order_id = await das.send_order('AAPL', 'BUY', 100, order_type='LIMIT', price=150.00)

# Subscribe to real-time quotes
await das.subscribe_quote('AAPL', level='Lv1')
das.on_quote_update = lambda quote: print(f"AAPL: {quote.last_price}")

# Get positions
positions = await das.get_positions()
```

## Requirements

- Python 3.8+
- DAS Trader Pro with CMD API enabled
- Valid DAS Trader account

## Use Cases

- Automated trading strategies
- Risk management tools
- Market data collection and analysis
- Order execution algorithms
- Trading system integration
- Custom trading interfaces
