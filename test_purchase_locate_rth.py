"""
Test REAL locate purchase during RTH
⚠️  This will SPEND MONEY - only runs if locate is cheap (<$0.50)
"""
import asyncio
from das_trader import DASTraderClient


async def test_purchase_locate():
    """Test actual locate purchase with safety checks."""
    print('💰 REAL LOCATE PURCHASE TEST (RTH)')
    print('=' * 70)
    print('⚠️  This test will PURCHASE a locate if approved')
    print('   Max cost allowed: $0.50 (very cheap only)')
    print('=' * 70)
    print()

    # Test symbol - using AZTR as example
    symbol = "AZTR"
    shares = 100  # Minimum quantity

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
            print('✅ Connected to DAS')
            print()

            # STEP 1: Analyze first (safety check)
            print(f'🔍 STEP 1: Analyzing locate for {symbol} ({shares} shares)')
            print('-' * 70)

            analysis = await client.locate_manager.analyze_locate(symbol, shares)

            print(f'Symbol: {symbol}')
            print(f'Desired: {shares} shares')
            print(f'Price: ${analysis.get("current_price", 0):.2f}')

            if analysis.get("is_etb"):
                print('✅ ETB (Easy to Borrow) - FREE!')
                print(f'Rate: $0.00/share')
                print(f'Total Cost: $0.00')
                approved = True
            elif "locate_total_cost" in analysis:
                rate = analysis.get("locate_rate", 0)
                total = analysis.get("locate_total_cost", 0)
                print(f'Rate: ${rate:.4f}/share')
                print(f'Total Cost: ${total:.2f}')

                # SAFETY: Only approve if very cheap
                if total <= 0.50:
                    approved = True
                    print(f'✅ APPROVED: Cost ${total:.2f} <= $0.50')
                else:
                    approved = False
                    print(f'❌ REJECTED: Cost ${total:.2f} > $0.50 (too expensive for test)')
            else:
                approved = False
                print(f'❌ No pricing available')

            print(f'Recommendation: {analysis.get("recommendation", "N/A")}')
            print()

            if not approved:
                print('=' * 70)
                print('🛑 TEST ABORTED - Locate too expensive or not available')
                print('=' * 70)
                return

            # STEP 2: Purchase locate
            print(f'💳 STEP 2: Purchasing locate (auto_purchase=True)')
            print('-' * 70)
            print(f'⚠️  THIS WILL SPEND MONEY!')
            print(f'   Cost: ${analysis.get("locate_total_cost", 0):.2f}')
            print()

            result = await client.locate_manager.ensure_locate(
                symbol=symbol,
                shares_needed=shares,
                auto_purchase=True  # ← REAL PURCHASE
            )

            print('=' * 70)
            print('📊 PURCHASE RESULT')
            print('=' * 70)

            if result.get("success"):
                print('✅ SUCCESS!')
                print()
                print(f'Symbol: {symbol}')
                print(f'Shares: {result.get("locate_shares", shares)}')
                print(f'Cost: ${result.get("locate_total_cost", 0):.2f}')
                print()

                if result.get("already_available"):
                    print('📌 Already had locates available')
                    print(f'   Current: {result.get("current_locates", 0)} shares')
                elif result.get("purchase_submitted"):
                    print('📌 Purchase submitted')
                    if result.get("purchase_confirmed"):
                        print('✅ Purchase CONFIRMED!')
                        print(f'   New balance: {result.get("current_locates", 0)} shares')
                    else:
                        print('⏳ Purchase pending verification')
            else:
                print('❌ FAILED')
                print(f'Reasons:')
                for reason in result.get("reasons", []):
                    print(f'   - {reason}')

            print()
            print('=' * 70)
            print('✅ TEST COMPLETED')
            print('=' * 70)

        except Exception as e:
            print()
            print('=' * 70)
            print(f'❌ ERROR: {e}')
            print('=' * 70)
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print()
    print('⚠️  WARNING: This test will purchase a locate if approved!')
    print('   It only purchases if cost is <= $0.50')
    print()

    asyncio.run(test_purchase_locate())
