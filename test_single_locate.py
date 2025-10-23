"""
✅ SAFE TEST - Can be run without crashing DAS

Test ONE SINGLE locate command - ULTRA SAFE
This demonstrates that a single SLPRICEINQUIRE command works correctly.

PURPOSE: Baseline test to verify single locate inquiry is safe
RESULT: Works perfectly - DAS remains stable
NOTE: Multiple locate inquiries WILL crash DAS (see test_two_locates.py)

This test is safe to run.
"""
import asyncio
from das_trader import DASTraderClient


async def test_single_locate():
    """Test ONLY ONE locate command and exit immediately."""
    print("🔬 ULTRA SAFE TEST - ONE COMMAND ONLY")
    print("=" * 70)
    print("This will send ONE locate inquiry and stop.")
    print("After running, CHECK if DAS is still open!")
    print()

    async with DASTraderClient(
        host='10.211.55.3',
        port=9910,
        log_level='INFO'
    ) as client:
        try:
            await client.connect(
                username='YOUR_ACCOUNT',
                password='YOUR_PASSWORD_HERE',
                account='YOUR_ACCOUNT'
            )
            print("✅ Connected to DAS")
            print()

            symbol = "GSIT"
            shares = 100

            # ONLY ONE COMMAND
            print("=" * 70)
            print(f"📡 Sending: SLPRICEINQUIRE {symbol} {shares} ALLROUTE")
            print("=" * 70)
            print()

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

            print()
            print("=" * 70)
            print("✅ TEST COMPLETE - CHECK DAS!")
            print("=" * 70)
            print()
            print("🔍 NOW CHECK:")
            print("   1. Is DAS Trader still open?")
            print("   2. Can you still see your account?")
            print("   3. No error messages in DAS?")
            print()
            print("If DAS is OPEN: ✅ This command is SAFE")
            print("If DAS is CLOSED: ❌ This command CRASHES DAS")
            print()

            # Wait a bit before disconnecting
            await asyncio.sleep(2)

        except Exception as e:
            print()
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_single_locate())
