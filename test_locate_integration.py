"""
Test integrated SmartLocateManager with route comparison.

Demonstrates:
1. Native access through client.locate_manager
2. Route comparison to find cheapest locate
3. Full workflow with smart decisions
"""
import asyncio
from das_trader import DASTraderClient


async def test_locate_integration():
    """Test the integrated SmartLocateManager functionality."""
    print("🚀 SMART LOCATE MANAGER INTEGRATION TEST")
    print("=" * 70)
    print()

    async with DASTraderClient(
        host='10.211.55.3',
        port=9910,
        log_level='INFO'
    ) as client:
        await client.connect(
            username='YOUR_USERNAME_HERE',
            password='YOUR_PASSWORD_HERE',
            account='YOUR_USERNAME_HERE'
        )
        print("✅ Connected to DAS")
        print()

        # TEST 1: Native Access
        print("=" * 70)
        print("TEST 1: Native Access through client.locate_manager")
        print("=" * 70)
        print()

        symbol = "AZTR"
        shares = 100

        print(f"📊 Analyzing locate for {symbol} ({shares} shares)...")
        analysis = await client.locate_manager.analyze_locate(symbol, shares)

        if analysis["success"]:
            print(f"✅ Analysis Result:")
            print(f"   Recommendation: {analysis['recommendation']}")
            print(f"   Locate Shares: {analysis['locate_shares']}")
            print(f"   Rate: ${analysis.get('locate_rate', 0):.6f}/share")
            print(f"   Total Cost: ${analysis.get('locate_total_cost', 0):.2f}")
            print(f"   Reasons:")
            for reason in analysis["reasons"]:
                print(f"      - {reason}")
        else:
            print(f"❌ Analysis failed:")
            for reason in analysis["reasons"]:
                print(f"   - {reason}")
        print()

        # TEST 2: Route Comparison
        print("=" * 70)
        print("TEST 2: Route Comparison - Find Cheapest Locate")
        print("=" * 70)
        print()

        print(f"🔍 Comparing locate prices across multiple routes...")
        print(f"   Symbol: {symbol}")
        print(f"   Shares: {shares}")
        print()

        # Compare routes to find cheapest
        comparison = await client.locate_manager.compare_routes(
            symbol,
            shares,
            routes=["ALLROUTE", "ARCA", "NASDAQ"]  # Test with 3 routes
        )

        if comparison["success"]:
            print(f"✅ Route Comparison Complete!")
            print(f"   Routes Checked: {comparison['routes_checked']}")
            print(f"   Best Route: {comparison['best_route']}")
            print(f"   Best Rate: ${comparison['best_rate']:.6f}/share")
            print(f"   Best Total Cost: ${comparison['best_total_cost']:.2f}")

            if comparison.get("savings"):
                print(f"   💰 Savings vs Worst: ${comparison['savings']:.2f}")

            print()
            print("📊 All Routes:")
            for route_info in comparison["all_routes"]:
                etb = " (ETB)" if route_info["is_etb"] else ""
                print(f"   {route_info['route']:12} ${route_info['rate']:.6f}/share = ${route_info['total_cost']:6.2f}{etb}")
        else:
            print(f"❌ Route comparison failed: {comparison.get('error')}")
        print()

        # TEST 3: Full Workflow with best route
        print("=" * 70)
        print("TEST 3: Full Workflow - Ensure Locate (No Purchase)")
        print("=" * 70)
        print()

        if comparison["success"]:
            best_route = comparison["best_route"]
            print(f"📋 Using best route: {best_route}")
            print()

        print(f"🔍 Ensuring locate availability...")
        result = await client.locate_manager.ensure_locate(
            symbol=symbol,
            shares_needed=shares,
            auto_purchase=False  # Just check, don't buy
        )

        if result["success"]:
            print(f"✅ Locate Check Complete!")
            print(f"   Current Locates: {result.get('current_locates', 0)}")

            if result.get("already_available"):
                print(f"   ✅ Already have sufficient locates!")
            else:
                print(f"   📌 Would need to purchase {result['locate_shares']} shares")
                print(f"   💰 Estimated Cost: ${result.get('locate_total_cost', 0):.2f}")
        else:
            print(f"❌ Locate check failed:")
            for reason in result["reasons"]:
                print(f"   - {reason}")
        print()

        print("=" * 70)
        print("✅ ALL TESTS COMPLETED!")
        print("=" * 70)
        print()
        print("📌 NOTE: No locates were actually purchased (auto_purchase=False)")
        print()


if __name__ == "__main__":
    asyncio.run(test_locate_integration())
