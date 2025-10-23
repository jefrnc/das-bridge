"""
⚠️  DEMONSTRATION ONLY - DO NOT USE IN PRODUCTION ⚠️

Test TWO locate commands in sequence - CRITICAL TEST
This file demonstrates the DAS Trader crash bug when multiple
SLPRICEINQUIRE commands are sent.

PURPOSE: Documentation and reference only
RESULT: DAS crashes on the second SLPRICEINQUIRE command
WORKAROUND: Use only ALLROUTE (see locate_manager.py and KNOWN_ISSUES.md)

DO NOT call this in production code!
"""
import asyncio
from das_trader import DASTraderClient


async def test_two_locates():
    """Test TWO locate commands with delay between them."""
    print("🔬 TWO LOCATE COMMANDS TEST")
    print("=" * 70)
    print("This will send TWO SLPRICEINQUIRE commands.")
    print("If DAS crashes, it will be during or after the SECOND command.")
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

            # ========== FIRST COMMAND ==========
            print("=" * 70)
            print("COMMAND #1: SLPRICEINQUIRE GSIT 100 ALLROUTE")
            print("=" * 70)
            print()

            try:
                locate1 = await client.inquire_locate_price(
                    symbol,
                    shares,
                    route="ALLROUTE"
                )

                if locate1:
                    rate = float(locate1.get("rate", 0) or 0)
                    print(f"✅ COMMAND #1 SUCCESS!")
                    print(f"   Rate: ${rate:.6f}/share")
                    print(f"   Total: ${rate * shares:.2f}")
                else:
                    print("⚠️  Command #1: No response")
            except Exception as e:
                print(f"❌ Command #1 ERROR: {e}")
                raise

            print()
            print("⏸️  Waiting 5 seconds before second command...")
            print("   (DAS should still be running...)")
            await asyncio.sleep(5)
            print()

            # ========== SECOND COMMAND ==========
            print("=" * 70)
            print("COMMAND #2: SLPRICEINQUIRE GSIT 100 ARCA")
            print("=" * 70)
            print("⚠️  THIS IS THE CRITICAL TEST!")
            print("   If DAS crashes, it will happen NOW.")
            print()

            try:
                locate2 = await client.inquire_locate_price(
                    symbol,
                    shares,
                    route="ARCA"
                )

                if locate2:
                    rate = float(locate2.get("rate", 0) or 0)
                    print(f"✅ COMMAND #2 SUCCESS!")
                    print(f"   Rate: ${rate:.6f}/share")
                    print(f"   Total: ${rate * shares:.2f}")
                    print()
                    print("=" * 70)
                    print("🎉 AMAZING! DAS DID NOT CRASH!")
                    print("=" * 70)
                    print("This means multiple SLPRICEINQUIRE commands ARE safe.")
                else:
                    print("⚠️  Command #2: No response (but no crash)")
                    print()
                    print("=" * 70)
                    print("✅ DAS STILL RUNNING!")
                    print("=" * 70)
            except asyncio.TimeoutError:
                print()
                print("=" * 70)
                print("❌ COMMAND #2 TIMED OUT")
                print("=" * 70)
                print("This usually means DAS crashed or connection lost.")
                print("Check if DAS Trader is still running!")
                print()
            except Exception as e:
                print()
                print("=" * 70)
                print(f"❌ COMMAND #2 ERROR: {e}")
                print("=" * 70)
                print("DAS likely crashed. Check if it's still running.")
                print()
                import traceback
                traceback.print_exc()

        except Exception as e:
            print()
            print("=" * 70)
            print(f"❌ FATAL ERROR: {e}")
            print("=" * 70)
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_two_locates())
