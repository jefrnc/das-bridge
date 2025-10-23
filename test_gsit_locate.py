"""
Test GSIT locate pricing and route comparison
"""
import asyncio
from das_trader import DASTraderClient


async def test_gsit_locate():
    """Test GSIT locate with route comparison."""
    print("📍 GSIT LOCATE TESTING - 100 SHARES")
    print("=" * 70)
    print()

    symbol = "GSIT"
    shares = 100

    async with DASTraderClient(
        host='10.211.55.3',
        port=9910,
        log_level='INFO'
    ) as client:
        try:
            await client.connect(
                username='YOUR_USERNAME_HERE',
                password='YOUR_PASSWORD_HERE',
                account='YOUR_USERNAME_HERE'
            )
            print("✅ Connected to DAS")
            print()

            # TEST 1: Smart Locate Analysis
            print("=" * 70)
            print("TEST 1: Smart Locate Analysis")
            print("=" * 70)
            print()

            analysis = await client.locate_manager.analyze_locate(symbol, shares)

            print(f"📊 Analysis for {symbol} ({shares} shares):")
            print(f"   Current Price: ${analysis.get('current_price', 0):.2f}")
            print(f"   Volume: {analysis.get('volume', 0):,}")
            print()

            if analysis.get("is_etb"):
                print("✅ ETB (Easy to Borrow) - FREE!")
            elif analysis.get("locate_rate") is not None:
                rate = analysis["locate_rate"]
                total = analysis.get("locate_total_cost", 0)
                pct = analysis.get("cost_pct_of_position", 0)

                print(f"💰 Locate Pricing:")
                print(f"   Rate: ${rate:.6f}/share")
                print(f"   Total Cost: ${total:.2f}")
                print(f"   Cost % of Position: {pct:.3f}%")
                print()

            print(f"🎯 Recommendation: {analysis['recommendation']}")
            if analysis.get("reasons"):
                print(f"   Reasons:")
                for reason in analysis["reasons"]:
                    print(f"      - {reason}")
            print()

            # TEST 2: Route Comparison (DEPRECATED)
            print("=" * 70)
            print("TEST 2: Route Comparison - DEPRECATED")
            print("=" * 70)
            print()
            print("⚠️  NOTE: compare_routes() is DEPRECATED")
            print("   Multiple SLPRICEINQUIRE commands crash DAS Trader")
            print("   See KNOWN_ISSUES.md for details")
            print()
            print("   Using single ALLROUTE inquiry instead...")
            print()

            # Use single inquiry with ALLROUTE (safe approach)
            locate_info = await client.inquire_locate_price(
                symbol,
                shares,
                route="ALLROUTE"
            )

            if locate_info:
                rate = float(locate_info.get("rate", 0) or 0)
                available = locate_info.get("available", False)
                total_cost = rate * shares
                is_etb = (rate == 0) or (rate < 0.00001)

                print("✅ Locate Inquiry Complete (ALLROUTE only)")
                print()
                print(f"📊 Result:")
                print(f"   Route: ALLROUTE")
                print(f"   Available: {available}")
                print(f"   Rate: ${rate:.6f}/share")
                print(f"   Total Cost: ${total_cost:.2f}")

                if is_etb:
                    print(f"   🎉 ETB (Easy to Borrow) - FREE!")

                print()
                print("ℹ️  Route comparison unavailable due to DAS API limitation")
                print("   All locate inquiries must use ALLROUTE to avoid crashes")
            else:
                print(f"❌ Locate inquiry failed")

            print()

            # TEST 3: Ensure Locate (no purchase)
            print("=" * 70)
            print("TEST 3: Ensure Locate Availability (NO PURCHASE)")
            print("=" * 70)
            print()

            result = await client.locate_manager.ensure_locate(
                symbol=symbol,
                shares_needed=shares,
                auto_purchase=False  # Just check, don't buy
            )

            if result["success"]:
                print("✅ Locate Check Complete!")
                print(f"   Current Locates: {result.get('current_locates', 0)}")

                if result.get("already_available"):
                    print(f"   ✅ Already have sufficient locates!")
                else:
                    print(f"   📌 Would need to purchase: {result['locate_shares']} shares")
                    if result.get("locate_total_cost") is not None:
                        print(f"   💰 Estimated Cost: ${result['locate_total_cost']:.2f}")
            else:
                print(f"❌ Locate check failed")
                for reason in result.get("reasons", []):
                    print(f"   - {reason}")

            print()
            print("=" * 70)
            print("✅ ALL TESTS COMPLETED!")
            print("=" * 70)
            print()
            print("📌 NOTE: No locates were actually purchased (auto_purchase=False)")
            print("   This was just an inquiry and route comparison")
            print()

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_gsit_locate())
