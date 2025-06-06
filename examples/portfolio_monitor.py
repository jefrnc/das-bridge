"""Portfolio monitoring example for DAS Trader API."""

import asyncio
import logging
from datetime import datetime
from das_trader import DASTraderClient, MarketDataLevel

# Set up logging
logging.basicConfig(level=logging.INFO)


class PortfolioMonitor:
    """Real-time portfolio monitoring."""
    
    def __init__(self, client: DASTraderClient):
        self.client = client
        self.last_update = None
        self.start_time = datetime.now()
    
    async def start_monitoring(self):
        """Start portfolio monitoring."""
        print("Starting portfolio monitor...")
        
        # Register callbacks
        self.client.on_position_update(self.on_position_update)
        self.client.on_quote_update(self.on_quote_update)
        
        # Get initial positions and subscribe to quotes
        await self.refresh_portfolio()
        
        # Print initial portfolio status
        await self.print_portfolio_summary()
        
        print("\\nMonitoring portfolio... Press Ctrl+C to stop\\n")
    
    async def refresh_portfolio(self):
        """Refresh portfolio data and subscribe to position quotes."""
        await self.client.refresh_positions()
        
        # Subscribe to quotes for all positions
        positions = self.client.get_positions()
        for position in positions:
            if not position.is_flat():
                await self.client.subscribe_quote(position.symbol, MarketDataLevel.LEVEL1)
                print(f"Subscribed to {position.symbol} quotes")
    
    async def print_portfolio_summary(self):
        """Print current portfolio summary."""
        positions = self.client.get_positions()
        open_positions = [p for p in positions if not p.is_flat()]
        
        if not open_positions:
            print("No open positions")
            return
        
        print("=" * 80)
        print(f"PORTFOLIO SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Header
        print(f"{'Symbol':<8} {'Qty':<8} {'Avg Cost':<10} {'Current':<10} "
              f"{'P&L $':<12} {'P&L %':<8} {'Market Val':<12}")
        print("-" * 80)
        
        total_pnl = 0
        total_market_value = 0
        total_cost_basis = 0
        
        for position in open_positions:
            side_indicator = "L" if position.is_long() else "S"
            
            print(f"{position.symbol:<8} "
                  f"{position.quantity:>7}{side_indicator} "
                  f"${position.avg_cost:>9.2f} "
                  f"${position.current_price:>9.2f} "
                  f"${position.unrealized_pnl:>11.2f} "
                  f"{position.pnl_percent:>7.2f}% "
                  f"${position.market_value:>11.2f}")
            
            total_pnl += position.unrealized_pnl
            total_market_value += position.market_value
            total_cost_basis += position.cost_basis
        
        print("-" * 80)
        
        # Totals
        total_pnl_pct = (total_pnl / total_cost_basis * 100) if total_cost_basis != 0 else 0
        
        print(f"{'TOTAL':<8} "
              f"{len(open_positions):>7}P "
              f"${total_cost_basis:>9.2f} "
              f"{'':>10} "
              f"${total_pnl:>11.2f} "
              f"{total_pnl_pct:>7.2f}% "
              f"${total_market_value:>11.2f}")
        
        # Account info
        try:
            account_info = await self.client.get_buying_power()
            print(f"\\nBuying Power: ${account_info['buying_power']:,.2f}")
            print(f"Day Trading BP: ${account_info['day_trading_bp']:,.2f}")
            print(f"Cash: ${account_info['cash']:,.2f}")
        except Exception as e:
            print(f"Could not get account info: {e}")
        
        print("=" * 80)
    
    async def on_position_update(self, position):
        """Handle position updates."""
        self.last_update = datetime.now()
        
        if position.is_flat():
            print(f"\\n🔄 Position CLOSED: {position.symbol} - "
                  f"Realized P&L: ${position.realized_pnl:.2f}")
        else:
            side = "LONG" if position.is_long() else "SHORT"
            print(f"\\n🔄 Position UPDATE: {position.symbol} {side} "
                  f"{position.quantity} shares - "
                  f"P&L: ${position.unrealized_pnl:.2f} ({position.pnl_percent:.2f}%)")
    
    async def on_quote_update(self, quote):
        """Handle quote updates for monitored positions."""
        # Update position with new price
        position = self.client.get_position(quote.symbol)
        if position and not position.is_flat():
            # The position manager will handle the price update
            pass
    
    async def periodic_summary(self):
        """Print periodic portfolio summary."""
        while True:
            await asyncio.sleep(30)  # Every 30 seconds
            await self.print_portfolio_summary()


async def main():
    """Run the portfolio monitor."""
    client = DASTraderClient(host="localhost", port=9910)
    monitor = PortfolioMonitor(client)
    
    try:
        # Connect to DAS Trader
        await client.connect("TU_USUARIO_DAS", "TU_PASSWORD_DAS", "TU_CUENTA_DAS")
        print("Connected to DAS Trader")
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Run periodic summary in background
        summary_task = asyncio.create_task(monitor.periodic_summary())
        
        # Keep running until interrupted
        await summary_task
        
    except KeyboardInterrupt:
        print("\\nStopping portfolio monitor...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect()
        print("Portfolio monitor stopped")


if __name__ == "__main__":
    asyncio.run(main())