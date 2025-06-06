"""Basic usage example for DAS Trader API client."""

import asyncio
import logging
from das_trader import DASTraderClient, OrderType, OrderSide, MarketDataLevel

# Set up logging
logging.basicConfig(level=logging.INFO)


async def main():
    """Basic usage example."""
    # Create client
    client = DASTraderClient(
        host="localhost",
        port=9910,
        auto_reconnect=True
    )
    
    try:
        # Connect to DAS Trader
        await client.connect("TU_USUARIO_DAS", "TU_PASSWORD_DAS", "TU_CUENTA_DAS")
        print("Connected to DAS Trader!")
        
        # Get account information
        buying_power = await client.get_buying_power()
        print(f"Buying Power: ${buying_power['buying_power']:,.2f}")
        
        # Subscribe to market data
        await client.subscribe_quote("AAPL", MarketDataLevel.LEVEL1)
        print("Subscribed to AAPL quotes")
        
        # Get a quote
        quote = await client.get_quote("AAPL")
        if quote:
            print(f"AAPL Quote - Bid: ${quote.bid}, Ask: ${quote.ask}, Last: ${quote.last}")
        
        # Send a limit order
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
        for position in positions:
            if not position.is_flat():
                print(f"Position: {position.symbol} - "
                      f"Qty: {position.quantity}, "
                      f"P&L: ${position.unrealized_pnl:.2f}")
        
        # Wait a bit for updates
        await asyncio.sleep(5)
        
        # Cancel all orders
        cancelled = await client.cancel_all_orders()
        print(f"Cancelled {cancelled} orders")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Disconnect
        await client.disconnect()
        print("Disconnected from DAS Trader")


if __name__ == "__main__":
    asyncio.run(main())