"""
⚠️  DEMONSTRATION ONLY - DO NOT USE IN PRODUCTION ⚠️

Test locate commands STEP BY STEP to find what causes DAS to close
This file demonstrates the DAS Trader crash bug with systematic testing.

PURPOSE: Documentation and reference only
RESULT: DAS crashes on the second or third SLPRICEINQUIRE command
WORKAROUND: Use only ALLROUTE (see locate_manager.py and KNOWN_ISSUES.md)

DO NOT call this in production code!
"""
import asyncio
from das_trader import DASTraderClient


async def test_locate_carefully():
    """Test locate commands one at a time."""
    print("🔬 CAREFUL STEP-BY-STEP LOCATE TEST")
    print("=" * 70)
    print("Testing each command individually to find what causes crash")
    print()

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

            symbol = "GSIT"
            shares = 100

            # STEP 1: Single locate inquiry (ALLROUTE)
            print("=" * 70)
            print("STEP 1: Single SLPRICEINQUIRE with ALLROUTE")
            print("=" * 70)
            print(f"Symbol: {symbol}, Shares: {shares}, Route: ALLROUTE")
            print()

            try:
                locate_info = await client.inquire_locate_price(
                    symbol,
                    shares,
                    route="ALLROUTE"
                )

                if locate_info:
                    rate = float(locate_info.get("rate", 0) or 0)
                    print(f"✅ SUCCESS! Got response:")
                    print(f"   Rate: ${rate:.6f}/share")
                    print(f"   Total: ${rate * shares:.2f}")
                else:
                    print("⚠️  No response (but no crash)")
            except Exception as e:
                print(f"❌ Error: {e}")

            print()
            print("⏸️  Waiting 3 seconds...")
            await asyncio.sleep(3)
            print()

            # STEP 2: Second locate inquiry (ARCA)
            print("=" * 70)
            print("STEP 2: Second SLPRICEINQUIRE with ARCA")
            print("=" * 70)
            print(f"Symbol: {symbol}, Shares: {shares}, Route: ARCA")
            print()

            try:
                locate_info = await client.inquire_locate_price(
                    symbol,
                    shares,
                    route="ARCA"
                )

                if locate_info:
                    rate = float(locate_info.get("rate", 0) or 0)
                    print(f"✅ SUCCESS! Got response:")
                    print(f"   Rate: ${rate:.6f}/share")
                    print(f"   Total: ${rate * shares:.2f}")
                else:
                    print("⚠️  No response (but no crash)")
            except Exception as e:
                print(f"❌ Error: {e}")

            print()
            print("⏸️  Waiting 3 seconds...")
            await asyncio.sleep(3)
            print()

            # STEP 3: Third locate inquiry (NASDAQ)
            print("=" * 70)
            print("STEP 3: Third SLPRICEINQUIRE with NASDAQ")
            print("=" * 70)
            print(f"Symbol: {symbol}, Shares: {shares}, Route: NASDAQ")
            print()

            try:
                locate_info = await client.inquire_locate_price(
                    symbol,
                    shares,
                    route="NASDAQ"
                )

                if locate_info:
                    rate = float(locate_info.get("rate", 0) or 0)
                    print(f"✅ SUCCESS! Got response:")
                    print(f"   Rate: ${rate:.6f}/share")
                    print(f"   Total: ${rate * shares:.2f}")
                else:
                    print("⚠️  No response (but no crash)")
            except Exception as e:
                print(f"❌ Error: {e}")

            print()
            print("=" * 70)
            print("✅ TEST COMPLETED - DAS STILL RUNNING!")
            print("=" * 70)
            print()
            print("If you see this message, DAS did NOT crash!")
            print()

        except Exception as e:
            print()
            print("=" * 70)
            print(f"❌ FATAL ERROR: {e}")
            print("=" * 70)
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_locate_carefully())
