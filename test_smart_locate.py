"""
Test smart locate functionality with volume and cost controls.

Based on patterns from /Users/Joseph/repos/TradingView/short-fade-das
"""
import asyncio
from decimal import Decimal
from typing import Dict, Any, Optional
from das_trader import DASTraderClient


class SmartLocateManager:
    """Smart locate manager with volume and cost controls."""

    def __init__(
        self,
        client: DASTraderClient,
        max_volume_pct: float = 1.0,  # Max 1% of daily volume
        max_cost_pct: float = 1.5,    # Max 1.5% of position value
        max_total_cost: float = 2.50,  # Max $2.50 per 100 shares
        block_size: int = 100          # Always request in 100-share blocks
    ):
        self.client = client
        self.max_volume_pct = max_volume_pct
        self.max_cost_pct = max_cost_pct
        self.max_total_cost = max_total_cost
        self.block_size = block_size

    async def analyze_locate(
        self,
        symbol: str,
        desired_shares: int,
        current_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyze locate availability and cost for a symbol.

        Args:
            symbol: Stock symbol
            desired_shares: Number of shares you want to short
            current_price: Current price (if None, will fetch from market data)

        Returns:
            Dictionary with analysis results including:
            - symbol: Stock symbol
            - desired_shares: Requested shares
            - allowed_shares: Max shares based on volume control
            - locate_shares: Shares to request from locate (rounded to block_size)
            - current_price: Stock price
            - position_value: Total position value
            - is_etb: Easy to borrow (free)
            - locate_rate: Rate per share
            - locate_total_cost: Total cost for locate
            - cost_pct_of_position: Cost as % of position value
            - recommendation: Action recommendation
            - reasons: List of reasons for recommendation
        """
        print(f"\n{'='*70}")
        print(f"🔍 SMART LOCATE ANALYSIS: {symbol}")
        print(f"{'='*70}\n")

        analysis = {
            "symbol": symbol,
            "desired_shares": desired_shares,
            "success": False,
            "recommendation": "REJECT",
            "reasons": []
        }

        # Step 1: Get current price if not provided
        if current_price is None:
            print("📊 Getting current market price...")
            await self.client.market_data.subscribe_quote(symbol)
            await asyncio.sleep(1)

            quote = await self.client.market_data.get_quote(symbol)
            if quote and quote.last > 0:
                current_price = float(quote.last)
                print(f"   Price: ${current_price:.2f}")
                analysis["volume"] = quote.volume
            else:
                print("   ⚠️  No quote data, using fallback")
                current_price = 1.0  # Fallback
                analysis["volume"] = 0
        else:
            # If price provided, try to get volume anyway
            quote = await self.client.market_data.get_quote(symbol)
            analysis["volume"] = quote.volume if quote else 0

        analysis["current_price"] = current_price
        print()

        # Step 2: Volume control - limit to max_volume_pct of daily volume
        print(f"📊 Volume Control Check (max {self.max_volume_pct}% of volume)...")

        if analysis["volume"] > 0:
            max_shares_by_volume = int(analysis["volume"] * (self.max_volume_pct / 100))
            print(f"   Daily Volume: {analysis['volume']:,}")
            print(f"   Max Shares ({self.max_volume_pct}%): {max_shares_by_volume:,}")

            allowed_shares = min(desired_shares, max_shares_by_volume)

            if desired_shares > max_shares_by_volume:
                analysis["reasons"].append(
                    f"Reduced from {desired_shares} to {allowed_shares} shares "
                    f"({self.max_volume_pct}% volume limit)"
                )
                print(f"   ⚠️  Limiting to {allowed_shares} shares (volume control)")
        else:
            allowed_shares = min(desired_shares, 100)  # Conservative default
            analysis["reasons"].append("No volume data - limiting to 100 shares")
            print(f"   ⚠️  No volume data, limiting to {allowed_shares} shares")

        analysis["allowed_shares"] = allowed_shares

        # Round to block size (100 shares)
        locate_shares = ((allowed_shares + self.block_size - 1) // self.block_size) * self.block_size
        if locate_shares < allowed_shares:
            locate_shares = self.block_size

        analysis["locate_shares"] = locate_shares
        print(f"   📦 Locate Block Size: {locate_shares} shares")
        print()

        # Step 3: Check locate pricing
        print(f"💰 Checking Locate Pricing for {locate_shares} shares...")

        try:
            locate_info = await self.client.inquire_locate_price(
                symbol,
                locate_shares,
                route="ALLROUTE"
            )

            if not locate_info:
                analysis["reasons"].append("No locate pricing available")
                print("   ❌ No locate info returned")
                return analysis

            # Extract pricing info
            rate = float(locate_info.get("rate", 0) or 0)
            available = locate_info.get("available", False)

            analysis["locate_rate"] = rate
            analysis["available"] = available

            print(f"   Rate: ${rate:.6f}/share")
            print(f"   Available: {available}")

            # CRITICAL: Detect if ETB (Easy to Borrow = FREE)
            # ETB stocks usually return rate = 0 or very low rate
            is_etb = (rate == 0) or (rate < 0.00001)
            analysis["is_etb"] = is_etb

            if is_etb:
                print(f"   ✅ Easy to Borrow (ETB) - FREE!")
                analysis["locate_total_cost"] = 0.0
                analysis["cost_pct_of_position"] = 0.0
                analysis["recommendation"] = "APPROVE"
                analysis["success"] = True
                analysis["reasons"].append("ETB stock - no locate cost")
                return analysis

            # SAFETY CHECK: Reject if price is 0 but not ETB (data error)
            if rate == 0:
                analysis["reasons"].append("INVALID: Locate rate is $0 (data error)")
                print(f"   ❌ INVALID: Rate is $0 - possible data error")
                return analysis

            # Calculate costs
            total_cost = rate * locate_shares
            position_value = current_price * locate_shares
            cost_pct = (total_cost / position_value) * 100 if position_value > 0 else 999

            analysis["locate_total_cost"] = total_cost
            analysis["position_value"] = position_value
            analysis["cost_pct_of_position"] = cost_pct

            print()
            print(f"📊 Cost Analysis:")
            print(f"   Position Value: ${position_value:,.2f}")
            print(f"   Total Locate Cost: ${total_cost:.2f}")
            print(f"   Cost % of Position: {cost_pct:.3f}%")
            print()

            # Step 4: Cost evaluation
            print(f"🎯 Cost Evaluation:")

            reasons = []

            # Check 1: Total cost limit (e.g., $2.50 for 100 shares)
            if total_cost > self.max_total_cost:
                reasons.append(
                    f"Total cost ${total_cost:.2f} > ${self.max_total_cost:.2f} max"
                )
                print(f"   ❌ TOO EXPENSIVE: ${total_cost:.2f} > ${self.max_total_cost:.2f} max")

            # Check 2: Cost as % of position (max 1.5%)
            if cost_pct > self.max_cost_pct:
                reasons.append(
                    f"Cost {cost_pct:.2f}% > {self.max_cost_pct}% max"
                )
                print(f"   ❌ TOO EXPENSIVE: {cost_pct:.2f}% > {self.max_cost_pct}% max")

            # Decision
            if reasons:
                analysis["recommendation"] = "REJECT"
                analysis["reasons"].extend(reasons)
                print(f"\n   🚫 RECOMMENDATION: REJECT - Locate too expensive")
            else:
                analysis["recommendation"] = "APPROVE"
                analysis["success"] = True

                if total_cost < 1.0:
                    tier = "VERY CHEAP"
                elif cost_pct < 0.5:
                    tier = "CHEAP"
                elif cost_pct < 1.0:
                    tier = "MODERATE"
                else:
                    tier = "ACCEPTABLE"

                analysis["reasons"].append(f"{tier}: ${total_cost:.2f} ({cost_pct:.2f}%)")
                print(f"   ✅ {tier}: ${total_cost:.2f} ({cost_pct:.2f}% of position)")
                print(f"\n   ✅ RECOMMENDATION: APPROVE - Cost acceptable")

        except Exception as e:
            analysis["reasons"].append(f"Error: {str(e)}")
            print(f"   ❌ Error: {e}")
            return analysis

        return analysis

    async def ensure_locate(
        self,
        symbol: str,
        shares_needed: int,
        current_price: Optional[float] = None,
        auto_purchase: bool = False
    ) -> Dict[str, Any]:
        """
        Ensure locate is available for shorting.

        This will:
        1. Analyze if locate is needed and affordable
        2. Check if we already have sufficient locates
        3. Optionally purchase if needed and approved

        Args:
            symbol: Stock symbol
            shares_needed: Shares you want to short
            current_price: Current price (optional)
            auto_purchase: If True, automatically purchase approved locates

        Returns:
            Analysis dictionary with purchase status if auto_purchase=True
        """
        # First analyze
        analysis = await self.analyze_locate(symbol, shares_needed, current_price)

        if not analysis["success"]:
            print(f"\n❌ Cannot proceed with locate for {symbol}")
            for reason in analysis["reasons"]:
                print(f"   - {reason}")
            return analysis

        # Check current availability
        print(f"\n📋 Checking Current Locate Availability...")
        try:
            current_locates = await self._check_available_locates(symbol)
            print(f"   Currently Available: {current_locates} shares")

            if current_locates >= shares_needed:
                print(f"   ✅ Already have sufficient locates!")
                analysis["already_available"] = True
                analysis["current_locates"] = current_locates
                return analysis
        except Exception as e:
            print(f"   ⚠️  Could not check availability: {e}")
            current_locates = 0

        analysis["current_locates"] = current_locates

        # Auto-purchase if enabled
        if auto_purchase and analysis["recommendation"] == "APPROVE":
            print(f"\n🛒 AUTO-PURCHASING {analysis['locate_shares']} shares...")
            print(f"   Total Cost: ${analysis['locate_total_cost']:.2f}")

            try:
                # Purchase locate
                result = await self.client.locate_stock(
                    symbol,
                    analysis["locate_shares"],
                    price=analysis["locate_rate"]
                )

                if result:
                    print(f"   ✅ Locate purchase submitted!")
                    analysis["purchase_submitted"] = True

                    # Wait and verify
                    await asyncio.sleep(2)
                    new_available = await self._check_available_locates(symbol)

                    if new_available >= shares_needed:
                        print(f"   ✅ Locate confirmed! Now have {new_available} shares")
                        analysis["purchase_confirmed"] = True
                    else:
                        print(f"   ⚠️  Purchase pending, showing {new_available} shares")
                else:
                    print(f"   ❌ Locate purchase failed")
                    analysis["purchase_failed"] = True

            except Exception as e:
                print(f"   ❌ Purchase error: {e}")
                analysis["purchase_error"] = str(e)
        else:
            if not auto_purchase:
                print(f"\n📌 auto_purchase=False - No purchase made")
                print(f"   To purchase, call with auto_purchase=True")

        return analysis

    async def _check_available_locates(self, symbol: str) -> int:
        """Check currently available locates for symbol."""
        # Use the account from the client connection
        account = self.client.connection._account

        cmd = f"SLAvailQuery {account} {symbol}"
        response = await self.client.connection.send_command(cmd, wait_response=True)

        if response and "$SLAvailQueryRet" in str(response):
            # Parse: $SLAvailQueryRet ACCOUNT SYMBOL SHARES
            parts = str(response).split()
            if len(parts) >= 4:
                try:
                    return int(parts[3])
                except:
                    pass

        return 0


async def test_smart_locate():
    """Test smart locate functionality."""
    print("🚀 SMART LOCATE MANAGER TEST")
    print("="*70)

    async with DASTraderClient(
        host='10.211.55.3',
        port=9910,
        log_level='WARNING'
    ) as client:
        await client.connect(
            username='YOUR_USERNAME_HERE',
            password='YOUR_PASSWORD_HERE',
            account='YOUR_USERNAME_HERE'
        )
        print("✅ Connected to DAS\n")

        # Create smart locate manager
        manager = SmartLocateManager(
            client=client,
            max_volume_pct=1.0,     # Max 1% of daily volume
            max_cost_pct=1.5,       # Max 1.5% of position value
            max_total_cost=2.50,    # Max $2.50 per 100 shares
            block_size=100
        )

        # Test cases
        test_symbols = [
            ("AZTR", 100),   # Small cap que sabemos tiene locates
            ("NERV", 50),    # Otro small cap
        ]

        for symbol, shares in test_symbols:
            print(f"\n{'='*70}")
            print(f"Testing: {symbol} ({shares} shares)")
            print(f"{'='*70}")

            analysis = await manager.ensure_locate(
                symbol=symbol,
                shares_needed=shares,
                auto_purchase=False  # Just analyze, don't buy yet
            )

            print(f"\n📊 FINAL ANALYSIS:")
            print(f"   Symbol: {analysis['symbol']}")
            print(f"   Desired Shares: {analysis['desired_shares']}")
            print(f"   Allowed Shares: {analysis.get('allowed_shares', 'N/A')}")
            print(f"   Locate Shares: {analysis.get('locate_shares', 'N/A')}")

            if "current_price" in analysis:
                print(f"   Current Price: ${analysis['current_price']:.2f}")
            if "locate_rate" in analysis:
                print(f"   Locate Rate: ${analysis['locate_rate']:.6f}/share")
            if "locate_total_cost" in analysis:
                print(f"   Total Cost: ${analysis['locate_total_cost']:.2f}")
            if "cost_pct_of_position" in analysis:
                print(f"   Cost % of Position: {analysis['cost_pct_of_position']:.3f}%")

            print(f"\n   Recommendation: {analysis['recommendation']}")
            if analysis["reasons"]:
                print(f"   Reasons:")
                for reason in analysis["reasons"]:
                    print(f"      - {reason}")

            print()

            # Wait between tests
            await asyncio.sleep(2)

        print("\n" + "="*70)
        print("✅ Smart Locate Tests Completed!")
        print("="*70)


if __name__ == "__main__":
    asyncio.run(test_smart_locate())
