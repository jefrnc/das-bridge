"""
Smart Locate Manager Example

Demonstrates how to use SmartLocateManager to analyze and request
stock locates for short selling with intelligent cost and volume controls.
"""
import asyncio
from das_trader import DASTraderClient


async def main():
    # Create client with SmartLocateManager (configured with defaults)
    # Default settings:
    #   - max_volume_pct: 1.0% of daily volume
    #   - max_cost_pct: 1.5% of position value
    #   - max_total_cost: $2.50 per 100 shares
    #   - block_size: 100 shares

    async with DASTraderClient(
        host="localhost",
        port=9910,
        log_level="INFO"
    ) as client:
        # Connect to DAS Trader
        await client.connect(
            username="your_username",
            password="your_password",
            account="your_account"
        )

        print("=" * 70)
        print("SMART LOCATE MANAGER - EXAMPLE")
        print("=" * 70)
        print()

        # Example 1: Analyze locate cost and availability
        print("Example 1: Analyze Locate")
        print("-" * 70)

        symbol = "AAPL"
        desired_shares = 500

        analysis = await client.locate_manager.analyze_locate(
            symbol=symbol,
            desired_shares=desired_shares
        )

        print(f"Symbol: {analysis['symbol']}")
        print(f"Desired Shares: {analysis['desired_shares']}")
        print(f"Allowed Shares: {analysis['allowed_shares']} (volume control)")
        print(f"Locate Shares: {analysis['locate_shares']} (rounded to block size)")
        print(f"Current Price: ${analysis['current_price']:.2f}")
        print(f"Daily Volume: {analysis.get('volume', 0):,}")
        print()

        if analysis.get('is_etb'):
            print("Status: Easy to Borrow (ETB) - FREE!")
        elif 'locate_total_cost' in analysis:
            print(f"Locate Rate: ${analysis['locate_rate']:.4f}/share")
            print(f"Total Cost: ${analysis['locate_total_cost']:.2f}")
            print(f"Cost % of Position: {analysis['cost_pct_of_position']:.2f}%")

        print(f"Recommendation: {analysis['recommendation']}")
        print(f"Reasons: {', '.join(analysis['reasons'])}")
        print()

        # Example 2: Ensure locate is available (analysis only)
        print("Example 2: Ensure Locate (Check Only)")
        print("-" * 70)

        result = await client.locate_manager.ensure_locate(
            symbol=symbol,
            shares_needed=100,
            auto_purchase=False  # Just check, don't buy
        )

        if result['success']:
            print(f"Locate is available for {symbol}")
            if result.get('already_available'):
                print(f"Already have {result['current_locates']} shares located")
            else:
                print(f"Locate can be purchased: ${result['locate_total_cost']:.2f}")
        else:
            print(f"Locate not available: {', '.join(result['reasons'])}")
        print()

        # Example 3: Auto-purchase approved locate
        print("Example 3: Ensure Locate with Auto-Purchase")
        print("-" * 70)

        # CAUTION: This will actually purchase the locate if approved!
        result = await client.locate_manager.ensure_locate(
            symbol="TSLA",
            shares_needed=100,
            auto_purchase=True  # Will purchase if approved
        )

        if result['success']:
            if result.get('purchase_submitted'):
                print(f"Locate purchased for TSLA!")
                print(f"Cost: ${result['locate_total_cost']:.2f}")

                if result.get('purchase_confirmed'):
                    print(f"Purchase confirmed - now have {result['current_locates']} shares")
                else:
                    print("Purchase submitted (pending confirmation)")
            elif result.get('already_available'):
                print(f"Already have sufficient locates: {result['current_locates']} shares")
        else:
            print(f"Locate purchase failed: {', '.join(result['reasons'])}")
        print()

        # Example 4: Custom configuration
        print("Example 4: Custom SmartLocateManager Configuration")
        print("-" * 70)

        # Create client with custom locate settings
        custom_client = DASTraderClient(
            host="localhost",
            port=9910,
            # Custom locate manager settings
            locate_manager_config={
                "max_volume_pct": 0.5,       # Only 0.5% of daily volume
                "max_cost_pct": 1.0,         # Max 1% cost (stricter)
                "max_total_cost": 1.00,      # Max $1 per 100 shares
                "block_size": 100
            }
        )

        print("Configured SmartLocateManager with stricter limits:")
        print("  - Max 0.5% of daily volume (default: 1%)")
        print("  - Max 1% cost of position (default: 1.5%)")
        print("  - Max $1.00 total cost (default: $2.50)")
        print()

        # Example 5: Simple locate price inquiry
        print("Example 5: Direct Locate Price Inquiry")
        print("-" * 70)

        locate_info = await client.inquire_locate_price(
            symbol="NVDA",
            quantity=100,
            route="ALLROUTE"
        )

        if locate_info:
            rate = float(locate_info.get("rate", 0) or 0)
            available = locate_info.get("available", False)

            print(f"Symbol: NVDA")
            print(f"Quantity: 100 shares")
            print(f"Available: {available}")
            print(f"Rate: ${rate:.4f}/share")
            print(f"Total: ${rate * 100:.2f}")
        else:
            print("No locate pricing available")
        print()

        print("=" * 70)
        print("EXAMPLE COMPLETED")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
