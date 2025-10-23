"""
Risk-Based Trading Example

This example demonstrates how to use the built-in risk management
and trading strategy helpers in das-bridge to execute trades with
precise position sizing and automatic stop placement.

Features demonstrated:
- Calculate position size based on dollar risk
- Open long/short positions with automatic stops
- Close positions at market or limit prices
- Scale out of positions at multiple targets
- Validate buying power before trading
"""

import asyncio
import logging
from decimal import Decimal
from das_trader import (
    DASTraderClient,
    RiskCalculator,
    StrategyResult
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_risk_calculations():
    """Example: Pure risk calculations without trading."""
    logger.info("=" * 60)
    logger.info("EXAMPLE 1: Risk Calculations")
    logger.info("=" * 60)

    calc = RiskCalculator()

    # Example 1: Calculate shares for $200 risk
    entry = 150.00
    stop = 149.00
    risk_amount = 200.00

    shares = calc.calculate_shares_for_risk(
        entry_price=entry,
        stop_price=stop,
        risk_dollars=risk_amount
    )

    logger.info(f"\nPosition Sizing:")
    logger.info(f"  Entry Price: ${entry:.2f}")
    logger.info(f"  Stop Price: ${stop:.2f}")
    logger.info(f"  Risk Amount: ${risk_amount:.2f}")
    logger.info(f"  → Shares to buy: {shares}")
    logger.info(f"  → Position Value: ${entry * shares:.2f}")

    # Example 2: With slippage
    shares_with_slippage = calc.calculate_shares_for_risk(
        entry_price=entry,
        stop_price=stop,
        risk_dollars=risk_amount,
        slippage=0.05  # $0.05 slippage expected
    )

    logger.info(f"\nWith $0.05 Slippage:")
    logger.info(f"  → Shares to buy: {shares_with_slippage}")
    logger.info(f"  → Difference: {shares - shares_with_slippage} fewer shares")

    # Example 3: Calculate risk/reward ratio
    target = 152.00
    ratio = calc.calculate_risk_reward_ratio(
        entry_price=entry,
        stop_price=stop,
        target_price=target
    )

    logger.info(f"\nRisk/Reward Ratio:")
    logger.info(f"  Entry: ${entry:.2f}")
    logger.info(f"  Stop: ${stop:.2f} (${entry - stop:.2f} risk)")
    logger.info(f"  Target: ${target:.2f} (${target - entry:.2f} reward)")
    logger.info(f"  → Ratio: 1:{float(ratio):.1f}")

    # Example 4: Suggest stop price for desired risk
    suggested_stop = calc.suggest_stop_price(
        entry_price=entry,
        risk_dollars=200.00,
        shares=100,
        side="long"
    )

    logger.info(f"\nSuggest Stop Price:")
    logger.info(f"  Entry: ${entry:.2f}")
    logger.info(f"  Shares: 100")
    logger.info(f"  Desired Risk: $200")
    logger.info(f"  → Suggested Stop: ${float(suggested_stop):.2f}")


async def example_long_with_risk_stop(client: DASTraderClient):
    """Example: Open long position with automatic stop."""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 2: Long Position with Risk-Based Stop")
    logger.info("=" * 60)

    symbol = "AAPL"

    # Get current quote first
    quote = await client.market_data.get_quote(symbol)
    if not quote:
        logger.error(f"Could not get quote for {symbol}")
        return

    logger.info(f"\nCurrent Market for {symbol}:")
    logger.info(f"  Bid: ${quote.bid:.2f}")
    logger.info(f"  Ask: ${quote.ask:.2f}")
    logger.info(f"  Mid: ${quote.mid_price:.2f}")
    logger.info(f"  Last: ${quote.last:.2f}")

    # Define trade parameters
    entry_price = float(quote.mid_price)
    stop_price = entry_price - 1.00  # $1 stop
    risk_amount = 200.00  # Risk exactly $200

    logger.info(f"\nTrade Plan:")
    logger.info(f"  Entry: ${entry_price:.2f} (at mid)")
    logger.info(f"  Stop: ${stop_price:.2f}")
    logger.info(f"  Risk: ${risk_amount:.2f}")

    # Calculate position size
    position_size = client.risk.calculate_position_size(
        entry_price=entry_price,
        stop_price=stop_price,
        risk_dollars=risk_amount
    )

    logger.info(f"\nPosition Size Calculation:")
    logger.info(f"  Shares: {position_size.shares}")
    logger.info(f"  Position Value: ${float(position_size.position_value):.2f}")
    logger.info(f"  Actual Risk: ${float(position_size.risk_dollars):.2f}")
    logger.info(f"  Risk per Share: ${float(position_size.risk_per_share):.2f}")

    # Execute strategy
    logger.info(f"\nExecuting long strategy...")

    result = await client.strategies.buy_with_risk_stop(
        symbol=symbol,
        entry_price=entry_price,
        stop_price=stop_price,
        risk_amount=risk_amount,
        entry_type="mid"  # Enter at mid price
    )

    if result.success:
        logger.info(f"✓ Strategy executed successfully!")
        logger.info(f"  Entry Order ID: {result.entry_order_id}")
        logger.info(f"  Stop Order ID: {result.stop_order_id}")
        logger.info(f"  Message: {result.message}")
    else:
        logger.error(f"✗ Strategy failed: {result.message}")


async def example_short_with_target(client: DASTraderClient):
    """Example: Short position with stop and target."""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 3: Short Position with Stop and Target")
    logger.info("=" * 60)

    symbol = "TSLA"

    quote = await client.market_data.get_quote(symbol)
    if not quote:
        logger.error(f"Could not get quote for {symbol}")
        return

    logger.info(f"\nCurrent Market for {symbol}:")
    logger.info(f"  Bid: ${quote.bid:.2f}")
    logger.info(f"  Ask: ${quote.ask:.2f}")
    logger.info(f"  Mid: ${quote.mid_price:.2f}")

    # Short setup: sell at mid, stop above, target below
    entry_price = float(quote.mid_price)
    stop_price = entry_price + 2.00  # Stop $2 above entry
    target_price = entry_price - 4.00  # Target $4 below (2:1 R:R)
    risk_amount = 300.00

    logger.info(f"\nShort Trade Plan:")
    logger.info(f"  Entry: ${entry_price:.2f}")
    logger.info(f"  Stop: ${stop_price:.2f} (+${stop_price - entry_price:.2f})")
    logger.info(f"  Target: ${target_price:.2f} (-${entry_price - target_price:.2f})")
    logger.info(f"  Risk: ${risk_amount:.2f}")

    # Check risk/reward ratio
    rr_ratio = client.risk.calculate_risk_reward_ratio(
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price
    )
    logger.info(f"  Risk/Reward: 1:{float(rr_ratio):.1f}")

    # Execute short strategy with target
    result = await client.strategies.sell_with_risk_stop(
        symbol=symbol,
        entry_price=entry_price,
        stop_price=stop_price,
        risk_amount=risk_amount,
        entry_type="mid",
        target_price=target_price  # Add profit target
    )

    if result.success:
        logger.info(f"\n✓ Short strategy executed!")
        logger.info(f"  Entry Order: {result.entry_order_id}")
        logger.info(f"  Stop Order: {result.stop_order_id}")
        logger.info(f"  Target Order: {result.target_order_id}")
    else:
        logger.error(f"\n✗ Strategy failed: {result.message}")


async def example_close_position(client: DASTraderClient):
    """Example: Close existing position."""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 4: Close Position")
    logger.info("=" * 60)

    symbol = "AAPL"

    # Check current position
    position = client.positions.get_position(symbol)
    if not position or position.quantity == 0:
        logger.warning(f"No open position for {symbol}")
        return

    logger.info(f"\nCurrent Position for {symbol}:")
    logger.info(f"  Shares: {position.quantity}")
    logger.info(f"  Avg Cost: ${float(position.avg_cost):.2f}")
    logger.info(f"  Current Price: ${float(position.current_price):.2f}")
    logger.info(f"  Unrealized P&L: ${float(position.unrealized_pnl):.2f}")

    # Option 1: Close at market
    logger.info(f"\nClosing 50% at market...")
    result = await client.strategies.close_position(
        symbol=symbol,
        exit_type="market",
        percentage=50.0
    )

    if result.success:
        logger.info(f"✓ {result.message}")
        logger.info(f"  Order ID: {result.entry_order_id}")
    else:
        logger.error(f"✗ {result.message}")


async def example_scale_out(client: DASTraderClient):
    """Example: Scale out at multiple targets."""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 5: Scale Out Strategy")
    logger.info("=" * 60)

    symbol = "AAPL"

    position = client.positions.get_position(symbol)
    if not position or position.quantity == 0:
        logger.warning(f"No open position for {symbol}")
        return

    logger.info(f"\nCurrent Position: {position.quantity} shares of {symbol}")
    logger.info(f"Avg Cost: ${float(position.avg_cost):.2f}")

    # Define scale-out targets
    # Sell 1/3 at each level
    entry = float(position.avg_cost)
    targets = [
        (entry + 1.00, 33.3),  # First third at +$1
        (entry + 2.00, 33.3),  # Second third at +$2
        (entry + 3.00, 33.4),  # Final third at +$3
    ]

    logger.info(f"\nScale-out Targets:")
    for price, pct in targets:
        shares = int(abs(position.quantity) * (pct / 100.0))
        logger.info(f"  ${price:.2f}: {pct:.1f}% ({shares} shares)")

    # Execute scale-out
    result = await client.strategies.scale_out(
        symbol=symbol,
        targets=targets,
        cancel_stops=True
    )

    if result.success:
        logger.info(f"\n✓ {result.message}")
        logger.info(f"  Orders placed: {len(result.details.get('order_ids', []))}")
    else:
        logger.error(f"\n✗ {result.message}")


async def example_buying_power_check(client: DASTraderClient):
    """Example: Validate position against buying power."""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 6: Buying Power Validation")
    logger.info("=" * 60)

    # Get current buying power
    bp = await client.positions.get_buying_power()
    logger.info(f"\nCurrent Buying Power: ${float(bp):.2f}")

    # Test different position sizes
    symbol = "AAPL"
    entry_price = 150.00

    test_cases = [100, 500, 1000, 5000]

    for shares in test_cases:
        is_valid, msg = client.risk.validate_position_against_buying_power(
            entry_price=entry_price,
            shares=shares,
            buying_power=float(bp),
            margin_requirement=1.0  # Cash account (no margin)
        )

        position_value = entry_price * shares
        status = "✓" if is_valid else "✗"

        logger.info(f"\n{status} {shares} shares @ ${entry_price:.2f}")
        logger.info(f"  Position Value: ${position_value:,.2f}")
        logger.info(f"  {msg}")

    # Calculate max shares for available BP
    max_shares = client.risk.calculate_max_shares_for_buying_power(
        entry_price=entry_price,
        buying_power=float(bp),
        margin_requirement=1.0
    )

    logger.info(f"\nMaximum Shares:")
    logger.info(f"  You can buy up to {max_shares} shares of {symbol}")
    logger.info(f"  Total Value: ${entry_price * max_shares:,.2f}")


async def example_extended_hours_trading(client: DASTraderClient):
    """Example: Trading in premarket/after-hours."""
    logger.info("\n" + "=" * 60)
    logger.info("EXAMPLE 7: Extended Hours Trading")
    logger.info("=" * 60)

    from das_trader.strategies import get_current_session, is_extended_hours

    # Check current session
    session = get_current_session()
    logger.info(f"\nCurrent Session: {session}")

    if not is_extended_hours():
        logger.warning("Not currently in extended hours. This example shows how it would work.")

    symbol = "AAPL"
    entry_price = 150.0
    stop_price = 149.0
    risk_amount = 200.0

    # Attempt 1: Default behavior (will fail in extended hours)
    logger.info("\n--- Attempt 1: Default (will reject in extended hours) ---")
    result = await client.strategies.buy_with_risk_stop(
        symbol=symbol,
        entry_price=entry_price,
        stop_price=stop_price,
        risk_amount=risk_amount
    )

    if not result.success:
        logger.warning(f"❌ {result.message}")

    # Attempt 2: With allow_extended_hours=True
    logger.info("\n--- Attempt 2: With allow_extended_hours=True ---")
    result = await client.strategies.buy_with_risk_stop(
        symbol=symbol,
        entry_price=entry_price,
        stop_price=stop_price,
        risk_amount=risk_amount,
        entry_type="limit",
        allow_extended_hours=True  # Enable extended hours
    )

    if result.success:
        logger.info("✓ Strategy executed successfully")
        logger.info(f"  Entry Order: {result.entry_order_id}")
        logger.info(f"  Stop Order: {result.stop_order_id or 'NOT PLACED'}")
        logger.info(f"  Session: {result.details['session']}")
        logger.info(f"  Stop Placed: {result.details['stop_placed']}")

        if result.details['suggested_stop']:
            logger.warning(f"\n⚠️  Manual Stop Required: ${result.details['suggested_stop']:.2f}")

        logger.info(f"\n{result.message}")
    else:
        logger.error(f"✗ {result.message}")

    # Show what happens at different times
    logger.info("\n" + "-" * 60)
    logger.info("Session Behavior Summary:")
    logger.info("-" * 60)
    logger.info("⏰ Premarket (4:00 AM - 9:30 AM):")
    logger.info("   ✅ Entry limit order placed")
    logger.info("   ❌ Stop order NOT placed (restriction)")
    logger.info("   📝 User must manage stop manually")
    logger.info("\n⏰ RTH (9:30 AM - 4:00 PM):")
    logger.info("   ✅ Entry order placed (market or limit)")
    logger.info("   ✅ Stop order placed automatically")
    logger.info("   ✅ Full strategy support")
    logger.info("\n⏰ After-Hours (4:00 PM - 8:00 PM):")
    logger.info("   ✅ Entry limit order placed")
    logger.info("   ❌ Stop order NOT placed (restriction)")
    logger.info("   📝 User must manage stop manually")


async def main():
    """Run all examples."""
    # Example 1: Pure calculations (no client needed)
    await example_risk_calculations()

    # For remaining examples, you would need an active DAS connection:
    # Uncomment and configure these when you have DAS Trader running

    """
    async with DASTraderClient(
        host="localhost",
        port=9910,
        log_level="INFO"
    ) as client:
        # Connect to DAS
        await client.connect(
            username="your_username",
            password="your_password",
            account="your_account"
        )

        # Run trading examples
        await example_long_with_risk_stop(client)
        await example_short_with_target(client)
        await example_close_position(client)
        await example_scale_out(client)
        await example_buying_power_check(client)
        await example_extended_hours_trading(client)  # New example
    """

    logger.info("\n" + "=" * 60)
    logger.info("Examples completed!")
    logger.info("=" * 60)
    logger.info("\nTo run the trading examples:")
    logger.info("1. Ensure DAS Trader Pro is running")
    logger.info("2. Uncomment the client section in main()")
    logger.info("3. Configure your credentials")
    logger.info("4. Run the script")


if __name__ == "__main__":
    asyncio.run(main())
