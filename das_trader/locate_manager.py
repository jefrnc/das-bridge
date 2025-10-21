"""
Smart Locate Manager with volume and cost controls.

Based on patterns from short-fade-das Go implementation.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import DASTraderClient

logger = logging.getLogger(__name__)


class SmartLocateManager:
    """
    Smart locate manager with volume and cost controls.

    Features:
    - Volume control: Limits shares to max % of daily volume
    - Cost control: Rejects locates above max cost thresholds
    - ETB detection: Identifies Easy to Borrow (free) stocks
    - Safety checks: Validates pricing data integrity
    - Block sizing: Always requests in 100-share blocks

    Usage:
        # Via client
        analysis = await client.locate_manager.analyze_locate("AZTR", 100)

        # Ensure locate is available
        result = await client.locate_manager.ensure_locate(
            "AZTR",
            100,
            auto_purchase=True
        )
    """

    def __init__(
        self,
        client: 'DASTraderClient',
        max_volume_pct: float = 1.0,      # Max 1% of daily volume
        max_cost_pct: float = 1.5,        # Max 1.5% of position value
        max_total_cost: float = 2.50,     # Max $2.50 per 100 shares
        block_size: int = 100              # Always request in 100-share blocks
    ):
        """
        Initialize Smart Locate Manager.

        Args:
            client: DASTraderClient instance
            max_volume_pct: Maximum % of daily volume (default 1%)
            max_cost_pct: Maximum locate cost as % of position value (default 1.5%)
            max_total_cost: Maximum total cost per block_size shares (default $2.50)
            block_size: Share block size for locate requests (default 100)
        """
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

        Performs comprehensive analysis including:
        - Volume-based quantity control
        - Locate pricing inquiry
        - Cost evaluation against thresholds
        - ETB (Easy to Borrow) detection
        - Safety validations

        Args:
            symbol: Stock symbol
            desired_shares: Number of shares you want to short
            current_price: Current price (if None, will fetch from market data)

        Returns:
            Dictionary with analysis results:
            - success: bool - Whether locate is approved
            - symbol: str - Stock symbol
            - desired_shares: int - Requested shares
            - allowed_shares: int - Max shares based on volume control
            - locate_shares: int - Shares to request (rounded to block_size)
            - current_price: float - Stock price
            - position_value: float - Total position value
            - volume: int - Daily volume
            - is_etb: bool - Easy to borrow (free)
            - locate_rate: float - Rate per share
            - locate_total_cost: float - Total cost for locate
            - cost_pct_of_position: float - Cost as % of position value
            - recommendation: str - APPROVE or REJECT
            - reasons: List[str] - List of reasons for recommendation
        """
        logger.info(f"Analyzing locate for {symbol} ({desired_shares} shares)")

        analysis = {
            "symbol": symbol,
            "desired_shares": desired_shares,
            "success": False,
            "recommendation": "REJECT",
            "reasons": []
        }

        # Step 1: Get current price if not provided
        if current_price is None:
            logger.debug(f"Getting current market price for {symbol}")
            await self.client.market_data.subscribe_quote(symbol)
            await asyncio.sleep(0.5)

            quote = await self.client.market_data.get_quote(symbol)
            if quote and quote.last > 0:
                current_price = float(quote.last)
                analysis["volume"] = quote.volume
                logger.debug(f"Got price: ${current_price:.2f}, volume: {quote.volume:,}")
            else:
                logger.warning(f"No quote data for {symbol}, using fallback price")
                current_price = 1.0  # Fallback
                analysis["volume"] = 0
        else:
            # If price provided, try to get volume anyway
            quote = await self.client.market_data.get_quote(symbol)
            analysis["volume"] = quote.volume if quote else 0

        analysis["current_price"] = current_price

        # Step 2: Volume control - limit to max_volume_pct of daily volume
        if analysis["volume"] > 0:
            max_shares_by_volume = int(analysis["volume"] * (self.max_volume_pct / 100))
            allowed_shares = min(desired_shares, max_shares_by_volume)

            if desired_shares > max_shares_by_volume:
                analysis["reasons"].append(
                    f"Reduced from {desired_shares} to {allowed_shares} shares "
                    f"({self.max_volume_pct}% volume limit)"
                )
                logger.info(f"Volume control: limiting to {allowed_shares} shares "
                           f"({self.max_volume_pct}% of {analysis['volume']:,})")
        else:
            allowed_shares = min(desired_shares, 100)  # Conservative default
            analysis["reasons"].append("No volume data - limiting to 100 shares")
            logger.warning(f"No volume data, limiting to {allowed_shares} shares")

        analysis["allowed_shares"] = allowed_shares

        # Round to block size (100 shares)
        locate_shares = ((allowed_shares + self.block_size - 1) // self.block_size) * self.block_size
        if locate_shares < allowed_shares:
            locate_shares = self.block_size

        analysis["locate_shares"] = locate_shares
        logger.debug(f"Locate block size: {locate_shares} shares")

        # Step 3: Check locate pricing
        logger.debug(f"Checking locate pricing for {locate_shares} shares")
        try:
            locate_info = await self.client.inquire_locate_price(
                symbol,
                locate_shares,
                route="ALLROUTE"
            )

            if not locate_info:
                analysis["reasons"].append("No locate pricing available")
                logger.warning("No locate info returned")
                return analysis

            # Extract pricing info
            rate = float(locate_info.get("rate", 0) or 0)
            available = locate_info.get("available", False)

            analysis["locate_rate"] = rate
            analysis["available"] = available

            logger.debug(f"Locate rate: ${rate:.6f}/share, available: {available}")

            # CRITICAL: Detect if ETB (Easy to Borrow = FREE)
            is_etb = (rate == 0) or (rate < 0.00001)
            analysis["is_etb"] = is_etb

            if is_etb:
                logger.info(f"{symbol} is Easy to Borrow (ETB) - FREE!")
                analysis["locate_total_cost"] = 0.0
                analysis["cost_pct_of_position"] = 0.0
                analysis["recommendation"] = "APPROVE"
                analysis["success"] = True
                analysis["reasons"].append("ETB stock - no locate cost")
                return analysis

            # SAFETY CHECK: Reject if price is 0 but not ETB (data error)
            if rate == 0:
                analysis["reasons"].append("INVALID: Locate rate is $0 (data error)")
                logger.error(f"Invalid rate $0 for {symbol} - possible data error")
                return analysis

            # Calculate costs
            total_cost = rate * locate_shares
            position_value = current_price * locate_shares
            cost_pct = (total_cost / position_value) * 100 if position_value > 0 else 999

            analysis["locate_total_cost"] = total_cost
            analysis["position_value"] = position_value
            analysis["cost_pct_of_position"] = cost_pct

            logger.debug(f"Cost analysis: ${total_cost:.2f} ({cost_pct:.3f}% of ${position_value:.2f} position)")

            # Step 4: Cost evaluation
            reasons = []

            # Check 1: Total cost limit
            if total_cost > self.max_total_cost:
                reasons.append(
                    f"Total cost ${total_cost:.2f} > ${self.max_total_cost:.2f} max"
                )
                logger.info(f"REJECTED: Total cost ${total_cost:.2f} exceeds ${self.max_total_cost:.2f} max")

            # Check 2: Cost as % of position (max 1.5%)
            if cost_pct > self.max_cost_pct:
                reasons.append(
                    f"Cost {cost_pct:.2f}% > {self.max_cost_pct}% max"
                )
                logger.info(f"REJECTED: Cost {cost_pct:.2f}% exceeds {self.max_cost_pct}% max")

            # Decision
            if reasons:
                analysis["recommendation"] = "REJECT"
                analysis["reasons"].extend(reasons)
                logger.info(f"RECOMMENDATION: REJECT - {', '.join(reasons)}")
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
                logger.info(f"RECOMMENDATION: APPROVE - {tier} (${total_cost:.2f}, {cost_pct:.2f}%)")

        except Exception as e:
            analysis["reasons"].append(f"Error: {str(e)}")
            logger.error(f"Error during locate analysis: {e}", exc_info=True)
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
            Analysis dictionary with purchase status if auto_purchase=True:
            - All fields from analyze_locate()
            - current_locates: int - Currently available locates
            - already_available: bool - If we already have enough
            - purchase_submitted: bool - If purchase was submitted
            - purchase_confirmed: bool - If purchase was verified
            - purchase_failed: bool - If purchase failed
            - purchase_error: str - Error message if purchase failed
        """
        logger.info(f"Ensuring locate for {symbol} ({shares_needed} shares, auto_purchase={auto_purchase})")

        # First analyze
        analysis = await self.analyze_locate(symbol, shares_needed, current_price)

        if not analysis["success"]:
            logger.warning(f"Cannot proceed with locate for {symbol}: {', '.join(analysis['reasons'])}")
            return analysis

        # Check current availability
        logger.debug(f"Checking current locate availability for {symbol}")
        try:
            current_locates = await self._check_available_locates(symbol)
            logger.info(f"Currently available: {current_locates} locates for {symbol}")

            if current_locates >= shares_needed:
                logger.info(f"Already have sufficient locates ({current_locates} >= {shares_needed})")
                analysis["already_available"] = True
                analysis["current_locates"] = current_locates
                return analysis
        except Exception as e:
            logger.warning(f"Could not check availability: {e}")
            current_locates = 0

        analysis["current_locates"] = current_locates

        # Auto-purchase if enabled
        if auto_purchase and analysis["recommendation"] == "APPROVE":
            logger.info(f"AUTO-PURCHASING {analysis['locate_shares']} shares for {symbol} "
                       f"(cost: ${analysis['locate_total_cost']:.2f})")

            try:
                # Purchase locate
                result = await self.client.locate_stock(
                    symbol,
                    analysis["locate_shares"],
                    route="ALLROUTE"
                )

                if result:
                    logger.info(f"Locate purchase submitted for {symbol}")
                    analysis["purchase_submitted"] = True

                    # Wait and verify
                    await asyncio.sleep(2)
                    new_available = await self._check_available_locates(symbol)

                    if new_available >= shares_needed:
                        logger.info(f"Locate confirmed! Now have {new_available} shares for {symbol}")
                        analysis["purchase_confirmed"] = True
                    else:
                        logger.warning(f"Purchase pending, showing {new_available} shares for {symbol}")
                else:
                    logger.error(f"Locate purchase failed for {symbol}")
                    analysis["purchase_failed"] = True

            except Exception as e:
                logger.error(f"Purchase error for {symbol}: {e}", exc_info=True)
                analysis["purchase_error"] = str(e)
        else:
            if not auto_purchase:
                logger.debug("auto_purchase=False - No purchase made")

        return analysis

    async def compare_routes(
        self,
        symbol: str,
        shares: int,
        routes: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        ⚠️ DEPRECATED - DO NOT USE ⚠️

        This method causes DAS Trader to crash when querying multiple routes.

        ISSUE: The second SLPRICEINQUIRE command causes DAS to disconnect
        ("Connection reset by peer"), regardless of delay between queries.

        WORKAROUND: Use only ALLROUTE for locate price inquiries:
            locate_info = await client.inquire_locate_price(symbol, shares, "ALLROUTE")

        This method is kept for reference only. Do not call it in production.

        Args:
            symbol: Stock symbol
            shares: Number of shares to locate
            routes: List of routes to check (default: common routes)

        Returns:
            Error dictionary indicating method is deprecated
        """
        logger.error(
            "⚠️ compare_routes() is DEPRECATED and will crash DAS! "
            "Use single inquire_locate_price() with ALLROUTE instead."
        )

        return {
            "success": False,
            "error": "compare_routes() is deprecated - causes DAS to crash",
            "message": (
                "Multiple SLPRICEINQUIRE commands cause DAS to disconnect. "
                "Use client.inquire_locate_price(symbol, shares, 'ALLROUTE') instead."
            ),
            "workaround": "Use ALLROUTE only for locate pricing"
        }

        # Original code removed to prevent accidental use
        # See git history or KNOWN_ISSUES.md for original implementation

    async def _check_available_locates(self, symbol: str) -> int:
        """
        Check currently available locates for symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Number of shares currently located
        """
        # Use the account from the client connection
        account = self.client.connection._account

        cmd = f"SLAvailQuery {account} {symbol}"

        try:
            response = await self.client.connection.send_command(
                cmd,
                wait_response=True,
                timeout=10.0
            )

            if response and "$SLAvailQueryRet" in str(response):
                # Parse: $SLAvailQueryRet ACCOUNT SYMBOL SHARES
                parts = str(response).split()
                if len(parts) >= 4:
                    try:
                        shares = int(parts[3])
                        logger.debug(f"Available locates for {symbol}: {shares}")
                        return shares
                    except ValueError as e:
                        logger.error(f"Error parsing locate quantity: {e}")

            logger.debug(f"No locate availability data for {symbol}")
            return 0

        except Exception as e:
            logger.error(f"Error checking available locates for {symbol}: {e}")
            raise
