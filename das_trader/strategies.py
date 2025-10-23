"""Trading strategy helpers and pre-built patterns for DAS Trader API."""

import asyncio
import logging
from typing import Optional, Tuple, Dict, Any, List
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

from .constants import OrderType, OrderSide, TimeInForce, Exchange
from .risk import RiskCalculator
from .exceptions import DASOrderError, DASInvalidSymbolError
from .utils import parse_decimal, validate_symbol

logger = logging.getLogger(__name__)


# Session detection constants (same as premarket.py)
PREMARKET_START = time(4, 0)   # 4:00 AM ET
PREMARKET_END = time(9, 30)    # 9:30 AM ET
RTH_START = time(9, 30)        # 9:30 AM ET
RTH_END = time(16, 0)          # 4:00 PM ET
AFTERHOURS_START = time(16, 0) # 4:00 PM ET
AFTERHOURS_END = time(20, 0)   # 8:00 PM ET


def get_current_session() -> str:
    """
    Get current market session in Eastern Time.

    Returns:
        "premarket", "rth", "afterhours", or "closed"

    Note:
        Always uses US/Eastern timezone regardless of system timezone.
    """
    # Get current time in Eastern Time (handles EDT/EST automatically)
    et_now = datetime.now(ZoneInfo("America/New_York"))
    now = et_now.time()

    if PREMARKET_START <= now < PREMARKET_END:
        return "premarket"
    elif RTH_START <= now < RTH_END:
        return "rth"
    elif AFTERHOURS_START <= now < AFTERHOURS_END:
        return "afterhours"
    else:
        return "closed"


def is_extended_hours() -> bool:
    """Check if currently in extended hours (premarket or after-hours)."""
    session = get_current_session()
    return session in ("premarket", "afterhours")


def validate_order_type_for_session(order_type: OrderType, session: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate if order type is allowed in current/specified session.

    Args:
        order_type: Type of order to validate
        session: Session to check ("premarket", "rth", "afterhours", "closed")
                If None, uses current session

    Returns:
        Tuple of (is_valid, error_message)

    Extended Hours Limitations:
        - Premarket & After-hours: Only LIMIT orders allowed
        - NO Market, Stop, or Trailing orders in extended hours
    """
    if session is None:
        session = get_current_session()

    # RTH allows all order types
    if session == "rth":
        return True, ""

    # Extended hours restrictions
    if session in ("premarket", "afterhours"):
        # Only limit orders allowed in extended hours
        allowed_types = [OrderType.LIMIT]

        if order_type not in allowed_types:
            session_name = "premarket" if session == "premarket" else "after-hours"
            return False, (
                f"{order_type.value} orders are not allowed in {session_name}. "
                f"Only LIMIT orders are supported in extended hours."
            )

    # Market closed
    if session == "closed":
        return False, "Market is currently closed. Trading hours: 4:00 AM - 8:00 PM ET"

    return True, ""


@dataclass
class StrategyResult:
    """Result of strategy execution."""
    success: bool
    entry_order_id: Optional[str] = None
    stop_order_id: Optional[str] = None
    target_order_id: Optional[str] = None
    message: str = ""
    details: Optional[Dict[str, Any]] = None

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "success": self.success,
            "entry_order_id": self.entry_order_id,
            "stop_order_id": self.stop_order_id,
            "target_order_id": self.target_order_id,
            "message": self.message,
            "details": self.details or {}
        }


class TradingStrategies:
    """
    Pre-built trading strategies with risk management.

    Provides common trading patterns like buying/selling with automatic
    stop placement and position sizing based on dollar risk.
    """

    def __init__(self, client):
        """
        Initialize trading strategies.

        Args:
            client: DASTraderClient instance
        """
        self.client = client
        self.risk_calc = RiskCalculator()

    async def buy_with_risk_stop(
        self,
        symbol: str,
        entry_price: float,
        stop_price: float,
        risk_amount: float = 200.0,
        entry_type: str = "mid",
        slippage: float = 0.05,
        target_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.DAY,
        validate_buying_power: bool = True,
        allow_extended_hours: bool = False
    ) -> StrategyResult:
        """
        Open long position with automatic stop loss and position sizing.

        This strategy:
        1. Validates current market session and order types
        2. Calculates shares based on dollar risk
        3. Places entry order at specified price level
        4. Places stop loss order (RTH only - NOT in extended hours)
        5. Optionally places target profit order

        Args:
            symbol: Stock symbol
            entry_price: Expected entry price (or reference for mid/bid/ask)
            stop_price: Stop loss price (used for position sizing)
            risk_amount: Maximum dollar amount to risk (default: $200)
            entry_type: Entry price type - "mid", "bid", "ask", or "limit" (default: "mid")
            slippage: Expected slippage in dollars per share (default: $0.05)
            target_price: Optional profit target price
            time_in_force: Order time in force (default: DAY)
            validate_buying_power: Check buying power before placing order (default: True)
            allow_extended_hours: Allow strategy in premarket/after-hours (default: False)
                                 NOTE: Stop orders will NOT be placed in extended hours

        Returns:
            StrategyResult with order IDs and execution details

        Extended Hours Behavior:
            - Only LIMIT entry orders are placed (no market orders)
            - Stop orders are NOT placed (extended hours restriction)
            - Target orders ARE placed if specified (limit orders allowed)
            - User must manually manage stops or wait for RTH

        Examples:
            >>> # RTH - Full strategy with entry + stop
            >>> result = await client.strategies.buy_with_risk_stop(
            ...     symbol="AAPL",
            ...     entry_price=150.0,
            ...     stop_price=149.0,
            ...     risk_amount=200.0,
            ...     entry_type="mid"
            ... )

            >>> # Premarket - Entry only, no stop (must use allow_extended_hours=True)
            >>> result = await client.strategies.buy_with_risk_stop(
            ...     symbol="AAPL",
            ...     entry_price=150.0,
            ...     stop_price=149.0,  # Used for position sizing only
            ...     risk_amount=200.0,
            ...     entry_type="limit",
            ...     allow_extended_hours=True
            ... )
        """
        try:
            if not validate_symbol(symbol):
                raise DASInvalidSymbolError(f"Invalid symbol: {symbol}")

            # Validate session and order types
            current_session = get_current_session()
            in_extended_hours = current_session in ("premarket", "afterhours")

            # Check if extended hours trading is allowed
            if in_extended_hours and not allow_extended_hours:
                session_name = "premarket" if current_session == "premarket" else "after-hours"
                return StrategyResult(
                    success=False,
                    message=(
                        f"Cannot execute strategy in {session_name} (session validation failed). "
                        f"Stop orders are not supported in extended hours. "
                        f"Use allow_extended_hours=True to place entry limit order only (without stop)."
                    )
                )

            # Get current quote to determine actual entry price
            quote = await self.client.market_data.get_quote(symbol)
            if not quote:
                return StrategyResult(
                    success=False,
                    message=f"Could not get quote for {symbol}"
                )

            # Calculate actual entry price based on entry_type
            if entry_type.lower() == "mid":
                actual_entry = float((quote.bid + quote.ask) / 2)
            elif entry_type.lower() == "bid":
                actual_entry = float(quote.bid)
            elif entry_type.lower() == "ask":
                actual_entry = float(quote.ask)
            elif entry_type.lower() == "limit":
                actual_entry = entry_price
            else:
                return StrategyResult(
                    success=False,
                    message=f"Invalid entry_type: {entry_type}. Use 'mid', 'bid', 'ask', or 'limit'"
                )

            # Apply slippage to entry price for conservative position sizing
            entry_with_slippage = actual_entry + slippage

            # Calculate position size
            position_size = self.risk_calc.calculate_position_size(
                entry_price=entry_with_slippage,
                stop_price=stop_price,
                risk_dollars=risk_amount,
                slippage=slippage
            )

            logger.info(
                f"Buy strategy for {symbol}: {position_size.shares} shares @ ${actual_entry:.2f}, "
                f"stop @ ${stop_price:.2f}, risk = ${float(position_size.risk_dollars):.2f}"
            )

            # Validate buying power if requested
            if validate_buying_power:
                bp = await self.client.positions.get_buying_power()
                if bp:
                    is_valid, msg = self.risk_calc.validate_position_against_buying_power(
                        entry_price=actual_entry,
                        shares=position_size.shares,
                        buying_power=float(bp)
                    )
                    if not is_valid:
                        return StrategyResult(success=False, message=msg)

            # Place entry order
            # In extended hours, force LIMIT orders only
            if in_extended_hours:
                if entry_type.lower() not in ("limit", "bid", "ask", "mid"):
                    return StrategyResult(
                        success=False,
                        message="Extended hours requires entry_type to be 'limit', 'bid', 'ask', or 'mid'"
                    )
                # Always use limit orders in extended hours
                entry_order = await self.client.orders.send_order(
                    symbol=symbol,
                    side=OrderSide.BUY,
                    quantity=position_size.shares,
                    order_type=OrderType.LIMIT,
                    price=actual_entry,
                    time_in_force=time_in_force
                )
            else:
                # RTH - allow both limit and market orders
                if entry_type.lower() == "limit":
                    entry_order = await self.client.orders.send_order(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        quantity=position_size.shares,
                        order_type=OrderType.LIMIT,
                        price=actual_entry,
                        time_in_force=time_in_force
                    )
                else:
                    # Market order for mid/bid/ask
                    entry_order = await self.client.orders.send_order(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        quantity=position_size.shares,
                        order_type=OrderType.MARKET,
                        time_in_force=time_in_force
                    )

            if not entry_order:
                return StrategyResult(
                    success=False,
                    message="Failed to place entry order"
                )

            # Place stop loss order (RTH only - NOT in extended hours)
            stop_order = None
            stop_warning = ""

            if not in_extended_hours:
                # Only place stop orders during RTH
                stop_order = await self.client.orders.send_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=position_size.shares,
                    order_type=OrderType.STOP_MARKET,
                    stop_price=stop_price,
                    time_in_force=time_in_force
                )
            else:
                # Extended hours - stop order NOT placed
                session_name = "premarket" if current_session == "premarket" else "after-hours"
                stop_warning = (
                    f" WARNING: Stop order NOT placed ({session_name} restriction). "
                    f"Suggested stop: ${stop_price:.2f}. "
                    f"You must manage stop manually or wait for RTH to place stop."
                )

            target_order_id = None
            if target_price:
                # Place target profit order (limit orders allowed in extended hours)
                target_order = await self.client.orders.send_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=position_size.shares,
                    order_type=OrderType.LIMIT,
                    price=target_price,
                    time_in_force=time_in_force
                )
                target_order_id = target_order.order_id if target_order else None

            # Build success message
            success_message = f"Long position opened: {position_size.shares} shares of {symbol}{stop_warning}"

            return StrategyResult(
                success=True,
                entry_order_id=entry_order.order_id,
                stop_order_id=stop_order.order_id if stop_order else None,
                target_order_id=target_order_id,
                message=success_message,
                details={
                    **position_size.to_dict(),
                    "session": current_session,
                    "stop_placed": stop_order is not None,
                    "suggested_stop": stop_price if in_extended_hours else None
                }
            )

        except Exception as e:
            logger.error(f"Error executing buy_with_risk_stop: {e}")
            return StrategyResult(success=False, message=str(e))

    async def sell_with_risk_stop(
        self,
        symbol: str,
        entry_price: float,
        stop_price: float,
        risk_amount: float = 200.0,
        entry_type: str = "mid",
        slippage: float = 0.05,
        target_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.DAY,
        validate_buying_power: bool = True,
        allow_extended_hours: bool = False
    ) -> StrategyResult:
        """
        Open short position with automatic stop loss and position sizing.

        This strategy:
        1. Validates current market session and order types
        2. Calculates shares based on dollar risk
        3. Places short entry order
        4. Places stop loss order (buy to cover) - RTH only
        5. Optionally places target profit order

        Args:
            symbol: Stock symbol
            entry_price: Expected entry price (or reference for mid/bid/ask)
            stop_price: Stop loss price (higher than entry for shorts)
            risk_amount: Maximum dollar amount to risk (default: $200)
            entry_type: Entry price type - "mid", "bid", "ask", or "limit" (default: "mid")
            slippage: Expected slippage in dollars per share (default: $0.05)
            target_price: Optional profit target price (lower than entry)
            time_in_force: Order time in force (default: DAY)
            validate_buying_power: Check buying power before placing order (default: True)
            allow_extended_hours: Allow strategy in premarket/after-hours (default: False)
                                 NOTE: Stop orders will NOT be placed in extended hours

        Returns:
            StrategyResult with order IDs and execution details

        Extended Hours Behavior:
            - Only LIMIT entry orders are placed (no market orders)
            - Stop orders are NOT placed (extended hours restriction)
            - Target orders ARE placed if specified (limit orders allowed)
            - User must manually manage stops or wait for RTH

        Examples:
            >>> # RTH - Full short strategy with entry + stop
            >>> result = await client.strategies.sell_with_risk_stop(
            ...     symbol="AAPL",
            ...     entry_price=150.0,
            ...     stop_price=151.0,
            ...     risk_amount=200.0,
            ...     target_price=148.0
            ... )

            >>> # Premarket - Short entry only, no stop
            >>> result = await client.strategies.sell_with_risk_stop(
            ...     symbol="AAPL",
            ...     entry_price=150.0,
            ...     stop_price=151.0,
            ...     risk_amount=200.0,
            ...     entry_type="limit",
            ...     allow_extended_hours=True
            ... )
        """
        try:
            if not validate_symbol(symbol):
                raise DASInvalidSymbolError(f"Invalid symbol: {symbol}")

            # Validate session and order types
            current_session = get_current_session()
            in_extended_hours = current_session in ("premarket", "afterhours")

            # Check if extended hours trading is allowed
            if in_extended_hours and not allow_extended_hours:
                session_name = "premarket" if current_session == "premarket" else "after-hours"
                return StrategyResult(
                    success=False,
                    message=(
                        f"Cannot execute strategy in {session_name} (session validation failed). "
                        f"Stop orders are not supported in extended hours. "
                        f"Use allow_extended_hours=True to place entry limit order only (without stop)."
                    )
                )

            # Get current quote
            quote = await self.client.market_data.get_quote(symbol)
            if not quote:
                return StrategyResult(
                    success=False,
                    message=f"Could not get quote for {symbol}"
                )

            # Calculate actual entry price
            if entry_type.lower() == "mid":
                actual_entry = float((quote.bid + quote.ask) / 2)
            elif entry_type.lower() == "bid":
                actual_entry = float(quote.bid)
            elif entry_type.lower() == "ask":
                actual_entry = float(quote.ask)
            elif entry_type.lower() == "limit":
                actual_entry = entry_price
            else:
                return StrategyResult(
                    success=False,
                    message=f"Invalid entry_type: {entry_type}"
                )

            # Apply slippage (subtract for shorts)
            entry_with_slippage = actual_entry - slippage

            # Calculate position size
            position_size = self.risk_calc.calculate_position_size(
                entry_price=entry_with_slippage,
                stop_price=stop_price,
                risk_dollars=risk_amount,
                slippage=slippage
            )

            logger.info(
                f"Short strategy for {symbol}: {position_size.shares} shares @ ${actual_entry:.2f}, "
                f"stop @ ${stop_price:.2f}, risk = ${float(position_size.risk_dollars):.2f}"
            )

            # Validate buying power
            if validate_buying_power:
                bp = await self.client.positions.get_buying_power()
                if bp:
                    is_valid, msg = self.risk_calc.validate_position_against_buying_power(
                        entry_price=actual_entry,
                        shares=position_size.shares,
                        buying_power=float(bp)
                    )
                    if not is_valid:
                        return StrategyResult(success=False, message=msg)

            # Place short entry order
            # In extended hours, force LIMIT orders only
            if in_extended_hours:
                if entry_type.lower() not in ("limit", "bid", "ask", "mid"):
                    return StrategyResult(
                        success=False,
                        message="Extended hours requires entry_type to be 'limit', 'bid', 'ask', or 'mid'"
                    )
                # Always use limit orders in extended hours
                entry_order = await self.client.orders.send_order(
                    symbol=symbol,
                    side=OrderSide.SHORT,
                    quantity=position_size.shares,
                    order_type=OrderType.LIMIT,
                    price=actual_entry,
                    time_in_force=time_in_force
                )
            else:
                # RTH - allow both limit and market orders
                if entry_type.lower() == "limit":
                    entry_order = await self.client.orders.send_order(
                        symbol=symbol,
                        side=OrderSide.SHORT,
                        quantity=position_size.shares,
                        order_type=OrderType.LIMIT,
                        price=actual_entry,
                        time_in_force=time_in_force
                    )
                else:
                    entry_order = await self.client.orders.send_order(
                        symbol=symbol,
                        side=OrderSide.SHORT,
                        quantity=position_size.shares,
                        order_type=OrderType.MARKET,
                        time_in_force=time_in_force
                    )

            if not entry_order:
                return StrategyResult(
                    success=False,
                    message="Failed to place entry order"
                )

            # Place stop loss order (buy to cover) - RTH only
            stop_order = None
            stop_warning = ""

            if not in_extended_hours:
                # Only place stop orders during RTH
                stop_order = await self.client.orders.send_order(
                    symbol=symbol,
                    side=OrderSide.COVER,
                    quantity=position_size.shares,
                    order_type=OrderType.STOP_MARKET,
                    stop_price=stop_price,
                    time_in_force=time_in_force
                )
            else:
                # Extended hours - stop order NOT placed
                session_name = "premarket" if current_session == "premarket" else "after-hours"
                stop_warning = (
                    f" WARNING: Stop order NOT placed ({session_name} restriction). "
                    f"Suggested stop: ${stop_price:.2f}. "
                    f"You must manage stop manually or wait for RTH to place stop."
                )

            target_order_id = None
            if target_price:
                # Place target profit order (buy to cover at lower price)
                target_order = await self.client.orders.send_order(
                    symbol=symbol,
                    side=OrderSide.COVER,
                    quantity=position_size.shares,
                    order_type=OrderType.LIMIT,
                    price=target_price,
                    time_in_force=time_in_force
                )
                target_order_id = target_order.order_id if target_order else None

            # Build success message
            success_message = f"Short position opened: {position_size.shares} shares of {symbol}{stop_warning}"

            return StrategyResult(
                success=True,
                entry_order_id=entry_order.order_id,
                stop_order_id=stop_order.order_id if stop_order else None,
                target_order_id=target_order_id,
                message=success_message,
                details={
                    **position_size.to_dict(),
                    "session": current_session,
                    "stop_placed": stop_order is not None,
                    "suggested_stop": stop_price if in_extended_hours else None
                }
            )

        except Exception as e:
            logger.error(f"Error executing sell_with_risk_stop: {e}")
            return StrategyResult(success=False, message=str(e))

    async def close_position(
        self,
        symbol: str,
        exit_type: str = "market",
        limit_price: Optional[float] = None,
        percentage: float = 100.0
    ) -> StrategyResult:
        """
        Close existing position (long or short).

        Args:
            symbol: Stock symbol
            exit_type: Exit order type - "market", "limit", "mid", "bid", or "ask"
            limit_price: Limit price (required if exit_type="limit")
            percentage: Percentage of position to close (default: 100%)

        Returns:
            StrategyResult with order details

        Examples:
            >>> # Close entire AAPL position at market
            >>> result = await client.strategies.close_position("AAPL")

            >>> # Close 50% at limit price
            >>> result = await client.strategies.close_position(
            ...     "AAPL",
            ...     exit_type="limit",
            ...     limit_price=151.0,
            ...     percentage=50.0
            ... )
        """
        try:
            # Get current position
            position = self.client.positions.get_position(symbol)
            if not position or position.quantity == 0:
                return StrategyResult(
                    success=False,
                    message=f"No open position for {symbol}"
                )

            # Calculate shares to close
            shares_to_close = int(abs(position.quantity) * (percentage / 100.0))
            if shares_to_close == 0:
                return StrategyResult(
                    success=False,
                    message=f"Percentage too small, resulting in 0 shares"
                )

            # Determine side (opposite of current position)
            if position.quantity > 0:
                # Long position - sell to close
                side = OrderSide.SELL
            else:
                # Short position - buy to cover
                side = OrderSide.COVER

            # Cancel all pending orders for this symbol first
            await self.client.orders.cancel_all_orders(symbol=symbol)

            # Determine order type and price
            if exit_type.lower() == "market":
                order = await self.client.orders.send_order(
                    symbol=symbol,
                    side=side,
                    quantity=shares_to_close,
                    order_type=OrderType.MARKET
                )
            elif exit_type.lower() == "limit":
                if limit_price is None:
                    return StrategyResult(
                        success=False,
                        message="limit_price required for limit orders"
                    )
                order = await self.client.orders.send_order(
                    symbol=symbol,
                    side=side,
                    quantity=shares_to_close,
                    order_type=OrderType.LIMIT,
                    price=limit_price
                )
            else:
                # mid, bid, or ask
                quote = await self.client.market_data.get_quote(symbol)
                if not quote:
                    return StrategyResult(
                        success=False,
                        message=f"Could not get quote for {symbol}"
                    )

                if exit_type.lower() == "mid":
                    price = float((quote.bid + quote.ask) / 2)
                elif exit_type.lower() == "bid":
                    price = float(quote.bid)
                elif exit_type.lower() == "ask":
                    price = float(quote.ask)
                else:
                    return StrategyResult(
                        success=False,
                        message=f"Invalid exit_type: {exit_type}"
                    )

                order = await self.client.orders.send_order(
                    symbol=symbol,
                    side=side,
                    quantity=shares_to_close,
                    order_type=OrderType.LIMIT,
                    price=price
                )

            if not order:
                return StrategyResult(
                    success=False,
                    message="Failed to place exit order"
                )

            return StrategyResult(
                success=True,
                entry_order_id=order.order_id,
                message=f"Closing {shares_to_close} shares of {symbol} ({percentage}%)",
                details={
                    "shares_closed": shares_to_close,
                    "total_shares": abs(position.quantity),
                    "percentage": percentage,
                    "side": side.value
                }
            )

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return StrategyResult(success=False, message=str(e))

    async def scale_out(
        self,
        symbol: str,
        targets: List[Tuple[float, float]],
        cancel_stops: bool = True
    ) -> StrategyResult:
        """
        Scale out of position at multiple target levels.

        Args:
            symbol: Stock symbol
            targets: List of (price, percentage) tuples
                    e.g., [(151.0, 33.3), (152.0, 33.3), (153.0, 33.4)]
            cancel_stops: Cancel existing stop orders (default: True)

        Returns:
            StrategyResult with all order IDs

        Examples:
            >>> # Scale out in thirds
            >>> result = await client.strategies.scale_out(
            ...     "AAPL",
            ...     targets=[
            ...         (151.0, 33.3),  # Sell 33.3% at $151
            ...         (152.0, 33.3),  # Sell 33.3% at $152
            ...         (153.0, 33.4)   # Sell remaining at $153
            ...     ]
            ... )
        """
        try:
            position = self.client.positions.get_position(symbol)
            if not position or position.quantity == 0:
                return StrategyResult(
                    success=False,
                    message=f"No open position for {symbol}"
                )

            if cancel_stops:
                await self.client.orders.cancel_all_orders(symbol=symbol)

            total_shares = abs(position.quantity)
            side = OrderSide.SELL if position.quantity > 0 else OrderSide.COVER

            order_ids = []
            for price, percentage in targets:
                shares = int(total_shares * (percentage / 100.0))
                if shares > 0:
                    order = await self.client.orders.send_order(
                        symbol=symbol,
                        side=side,
                        quantity=shares,
                        order_type=OrderType.LIMIT,
                        price=price
                    )
                    if order:
                        order_ids.append(order.order_id)

            if not order_ids:
                return StrategyResult(
                    success=False,
                    message="Failed to place any scale-out orders"
                )

            return StrategyResult(
                success=True,
                message=f"Placed {len(order_ids)} scale-out orders for {symbol}",
                details={
                    "order_ids": order_ids,
                    "targets": targets
                }
            )

        except Exception as e:
            logger.error(f"Error scaling out: {e}")
            return StrategyResult(success=False, message=str(e))
