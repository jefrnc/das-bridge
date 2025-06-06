"""Simple trading bot example using DAS Trader API."""

import asyncio
import logging
from decimal import Decimal
from das_trader import DASTraderClient, OrderType, OrderSide, MarketDataLevel

# Set up logging
logging.basicConfig(level=logging.INFO)


class SimpleTradingBot:
    """A simple momentum trading bot."""
    
    def __init__(self, client: DASTraderClient):
        self.client = client
        self.symbol = "AAPL"
        self.position_size = 100
        self.stop_loss_pct = 0.02  # 2%
        self.take_profit_pct = 0.04  # 4%
        
        self.last_price = None
        self.entry_price = None
        self.position = None
        self.stop_order_id = None
        self.target_order_id = None
        
        self.price_history = []
        self.max_history = 10
    
    async def start(self):
        """Start the trading bot."""
        print(f"Starting trading bot for {self.symbol}")
        
        # Register callbacks
        self.client.on_quote_update(self.on_quote_update)
        self.client.on_order_update(self.on_order_update)
        self.client.on_position_update(self.on_position_update)
        
        # Subscribe to market data
        await self.client.subscribe_quote(self.symbol, MarketDataLevel.LEVEL1)
        
        # Get initial position
        self.position = self.client.get_position(self.symbol)
        if self.position and not self.position.is_flat():
            self.entry_price = self.position.avg_cost
            print(f"Found existing position: {self.position.quantity} shares at ${self.entry_price}")
        
        print("Trading bot started. Monitoring for signals...")
    
    async def on_quote_update(self, quote):
        """Handle quote updates and check for trading signals."""
        if quote.symbol != self.symbol:
            return
        
        self.last_price = quote.last
        self.price_history.append(float(quote.last))
        
        # Keep only recent history
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)
        
        # Check for signals
        await self.check_entry_signal()
        await self.check_exit_signal()
    
    async def check_entry_signal(self):
        """Check for entry signals."""
        if len(self.price_history) < self.max_history:
            return
        
        # Simple momentum signal: price above recent average
        if self.position and self.position.is_flat():
            recent_avg = sum(self.price_history[-5:]) / 5
            older_avg = sum(self.price_history[-10:-5]) / 5
            
            # Buy signal: recent average > older average
            if recent_avg > older_avg * 1.001:  # 0.1% threshold
                await self.enter_long()
    
    async def enter_long(self):
        """Enter a long position."""
        try:
            print(f"Entering long position: {self.position_size} shares of {self.symbol}")
            
            order_id = await self.client.send_order(
                symbol=self.symbol,
                side=OrderSide.BUY,
                quantity=self.position_size,
                order_type=OrderType.MARKET
            )
            
            print(f"Buy order sent: {order_id}")
            
        except Exception as e:
            print(f"Error entering position: {e}")
    
    async def check_exit_signal(self):
        """Check for exit signals."""
        if not self.position or self.position.is_flat() or not self.entry_price:
            return
        
        current_price = self.last_price
        if not current_price:
            return
        
        # Calculate P&L percentage
        if self.position.quantity > 0:  # Long position
            pnl_pct = (current_price - self.entry_price) / self.entry_price
            
            # Stop loss
            if pnl_pct <= -self.stop_loss_pct:
                await self.exit_position("Stop Loss")
            
            # Take profit
            elif pnl_pct >= self.take_profit_pct:
                await self.exit_position("Take Profit")
    
    async def exit_position(self, reason: str):
        """Exit the current position."""
        try:
            print(f"Exiting position ({reason}): {abs(self.position.quantity)} shares")
            
            side = OrderSide.SELL if self.position.quantity > 0 else OrderSide.COVER
            
            order_id = await self.client.send_order(
                symbol=self.symbol,
                side=side,
                quantity=abs(self.position.quantity),
                order_type=OrderType.MARKET
            )
            
            print(f"Exit order sent: {order_id}")
            
        except Exception as e:
            print(f"Error exiting position: {e}")
    
    async def on_order_update(self, order):
        """Handle order updates."""
        if order.symbol != self.symbol:
            return
        
        print(f"Order update: {order.order_id} - {order.status.value}")
        
        if order.status.value == "FILLED":
            print(f"Order filled: {order.filled_quantity} shares at ${order.avg_fill_price}")
    
    async def on_position_update(self, position):
        """Handle position updates."""
        if position.symbol != self.symbol:
            return
        
        self.position = position
        
        if not position.is_flat():
            self.entry_price = position.avg_cost
            print(f"Position updated: {position.quantity} shares, "
                  f"P&L: ${position.unrealized_pnl:.2f} ({position.pnl_percent:.2f}%)")
        else:
            print(f"Position closed. Realized P&L: ${position.realized_pnl:.2f}")
            self.entry_price = None


async def main():
    """Run the trading bot."""
    client = DASTraderClient(host="localhost", port=9910)
    bot = SimpleTradingBot(client)
    
    try:
        # Connect to DAS Trader
        await client.connect("TU_USUARIO_DAS", "TU_PASSWORD_DAS", "TU_CUENTA_DAS")
        print("Connected to DAS Trader")
        
        # Check buying power
        bp = await client.get_buying_power()
        print(f"Buying Power: ${bp['buying_power']:,.2f}")
        
        # Start the bot
        await bot.start()
        
        # Run for 5 minutes
        print("Bot running for 5 minutes...")
        await asyncio.sleep(300)
        
    except KeyboardInterrupt:
        print("\\nStopping trading bot...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cancel any open orders before disconnecting
        await client.cancel_all_orders()
        await client.disconnect()
        print("Trading bot stopped")


if __name__ == "__main__":
    asyncio.run(main())