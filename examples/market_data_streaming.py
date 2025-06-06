"""Market data streaming example for DAS Trader API client."""

import asyncio
import logging
from das_trader import DASTraderClient, MarketDataLevel

# Set up logging
logging.basicConfig(level=logging.INFO)


class MarketDataHandler:
    """Handler for market data events."""
    
    def __init__(self):
        self.quote_count = 0
        self.level2_count = 0
        self.ts_count = 0
    
    async def on_quote_update(self, quote):
        """Handle quote updates."""
        self.quote_count += 1
        print(f"[{self.quote_count}] {quote.symbol} Quote - "
              f"Bid: ${quote.bid:.2f} ({quote.bid_size}), "
              f"Ask: ${quote.ask:.2f} ({quote.ask_size}), "
              f"Last: ${quote.last:.2f}")
    
    async def on_level2_update(self, data):
        """Handle Level 2 updates."""
        self.level2_count += 1
        symbol = data["symbol"]
        quote = data["quote"]
        print(f"[{self.level2_count}] {symbol} L2 - "
              f"{quote.side}: ${quote.price:.2f} x {quote.size} ({quote.mmid})")
    
    async def on_time_sales(self, sale):
        """Handle time and sales."""
        self.ts_count += 1
        print(f"[{self.ts_count}] {sale.symbol} Trade - "
              f"${sale.price:.2f} x {sale.size} at {sale.timestamp}")


async def main():
    """Market data streaming example."""
    # Create client and handler
    client = DASTraderClient(host="localhost", port=9910)
    handler = MarketDataHandler()
    
    # Register callbacks
    client.on_quote_update(handler.on_quote_update)
    client.on_level2_update(handler.on_level2_update)
    client.on_time_sales(handler.on_time_sales)
    
    try:
        # Connect
        await client.connect("TU_USUARIO_DAS", "TU_PASSWORD_DAS", "TU_CUENTA_DAS")
        print("Connected to DAS Trader for market data streaming")
        
        # Subscribe to multiple symbols
        symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
        
        for symbol in symbols:
            await client.subscribe_quote(symbol, MarketDataLevel.LEVEL1)
            await client.subscribe_quote(symbol, MarketDataLevel.LEVEL2)
            await client.subscribe_quote(symbol, MarketDataLevel.TIME_SALES)
            print(f"Subscribed to {symbol} market data")
        
        print("\\nStreaming market data... Press Ctrl+C to stop")
        
        # Stream for 60 seconds
        await asyncio.sleep(60)
        
        print(f"\\nReceived {handler.quote_count} quotes, "
              f"{handler.level2_count} L2 updates, "
              f"{handler.ts_count} trades")
        
    except KeyboardInterrupt:
        print("\\nStopping market data stream...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())