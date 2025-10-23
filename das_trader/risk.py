"""Risk management and position sizing utilities for DAS Trader API."""

import logging
from typing import Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PositionSizeResult:
    """Result of position sizing calculation."""
    shares: int
    risk_dollars: Decimal
    risk_per_share: Decimal
    entry_price: Decimal
    stop_price: Decimal
    position_value: Decimal

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "shares": self.shares,
            "risk_dollars": float(self.risk_dollars),
            "risk_per_share": float(self.risk_per_share),
            "entry_price": float(self.entry_price),
            "stop_price": float(self.stop_price),
            "position_value": float(self.position_value)
        }


class RiskCalculator:
    """
    Position sizing and risk management calculations.

    Provides utilities for calculating position sizes based on dollar risk,
    stop prices, and other risk management parameters.
    """

    def __init__(self):
        """Initialize risk calculator."""
        pass

    def calculate_shares_for_risk(
        self,
        entry_price: float,
        stop_price: float,
        risk_dollars: float,
        slippage: float = 0.0,
        min_shares: int = 1,
        max_shares: Optional[int] = None
    ) -> int:
        """
        Calculate number of shares to achieve exact dollar risk.

        Args:
            entry_price: Expected entry price
            stop_price: Stop loss price
            risk_dollars: Maximum dollar amount to risk
            slippage: Expected slippage in dollars per share (default: 0.0)
            min_shares: Minimum shares to return (default: 1)
            max_shares: Maximum shares allowed (optional)

        Returns:
            Number of shares to trade

        Examples:
            >>> calc = RiskCalculator()
            >>> # Risk $200 on AAPL at $150 with stop at $149
            >>> shares = calc.calculate_shares_for_risk(150.0, 149.0, 200.0)
            >>> shares
            200

            >>> # With slippage
            >>> shares = calc.calculate_shares_for_risk(150.0, 149.0, 200.0, slippage=0.05)
            >>> shares
            190
        """
        entry = Decimal(str(entry_price))
        stop = Decimal(str(stop_price))
        risk = Decimal(str(risk_dollars))
        slip = Decimal(str(slippage))

        # Calculate risk per share including slippage
        risk_per_share = abs(entry - stop) + slip

        if risk_per_share <= 0:
            logger.warning(
                f"Invalid risk calculation: entry={entry}, stop={stop}, slippage={slip}"
            )
            return min_shares

        # Calculate shares
        shares = risk / risk_per_share
        shares_int = int(shares)  # Round down to be conservative

        # Apply constraints
        if shares_int < min_shares:
            logger.warning(
                f"Calculated shares ({shares_int}) below minimum ({min_shares}), using minimum"
            )
            shares_int = min_shares

        if max_shares and shares_int > max_shares:
            logger.warning(
                f"Calculated shares ({shares_int}) above maximum ({max_shares}), using maximum"
            )
            shares_int = max_shares

        return shares_int

    def calculate_position_risk(
        self,
        entry_price: float,
        stop_price: float,
        shares: int,
        slippage: float = 0.0
    ) -> Decimal:
        """
        Calculate total dollar risk for a given position.

        Args:
            entry_price: Entry price
            stop_price: Stop loss price
            shares: Number of shares
            slippage: Expected slippage in dollars per share

        Returns:
            Total dollar risk

        Examples:
            >>> calc = RiskCalculator()
            >>> risk = calc.calculate_position_risk(150.0, 149.0, 200)
            >>> float(risk)
            200.0
        """
        entry = Decimal(str(entry_price))
        stop = Decimal(str(stop_price))
        slip = Decimal(str(slippage))

        risk_per_share = abs(entry - stop) + slip
        total_risk = risk_per_share * shares

        return total_risk

    def suggest_stop_price(
        self,
        entry_price: float,
        risk_dollars: float,
        shares: int,
        side: str = "long",
        slippage: float = 0.0
    ) -> Decimal:
        """
        Calculate stop price needed to achieve desired dollar risk.

        Args:
            entry_price: Expected entry price
            risk_dollars: Desired dollar risk
            shares: Number of shares
            side: Position side ("long" or "short")
            slippage: Expected slippage in dollars per share

        Returns:
            Suggested stop price

        Examples:
            >>> calc = RiskCalculator()
            >>> stop = calc.suggest_stop_price(150.0, 200.0, 200, side="long")
            >>> float(stop)
            149.0
        """
        entry = Decimal(str(entry_price))
        risk = Decimal(str(risk_dollars))
        slip = Decimal(str(slippage))

        if shares <= 0:
            raise ValueError("Shares must be positive")

        # Calculate risk per share needed
        risk_per_share = risk / shares

        # Subtract slippage to get actual stop distance
        stop_distance = risk_per_share - slip

        if side.lower() == "long":
            stop_price = entry - stop_distance
        elif side.lower() == "short":
            stop_price = entry + stop_distance
        else:
            raise ValueError(f"Invalid side: {side}. Must be 'long' or 'short'")

        return stop_price

    def calculate_position_size(
        self,
        entry_price: float,
        stop_price: float,
        risk_dollars: float,
        slippage: float = 0.0,
        min_shares: int = 1,
        max_shares: Optional[int] = None
    ) -> PositionSizeResult:
        """
        Calculate complete position sizing with all details.

        Args:
            entry_price: Expected entry price
            stop_price: Stop loss price
            risk_dollars: Maximum dollar amount to risk
            slippage: Expected slippage in dollars per share
            min_shares: Minimum shares (default: 1)
            max_shares: Maximum shares allowed (optional)

        Returns:
            PositionSizeResult with all calculation details

        Examples:
            >>> calc = RiskCalculator()
            >>> result = calc.calculate_position_size(150.0, 149.0, 200.0)
            >>> result.shares
            200
            >>> float(result.risk_dollars)
            200.0
            >>> float(result.position_value)
            30000.0
        """
        shares = self.calculate_shares_for_risk(
            entry_price=entry_price,
            stop_price=stop_price,
            risk_dollars=risk_dollars,
            slippage=slippage,
            min_shares=min_shares,
            max_shares=max_shares
        )

        entry = Decimal(str(entry_price))
        stop = Decimal(str(stop_price))
        slip = Decimal(str(slippage))

        risk_per_share = abs(entry - stop) + slip
        actual_risk = risk_per_share * shares
        position_value = entry * shares

        return PositionSizeResult(
            shares=shares,
            risk_dollars=actual_risk,
            risk_per_share=risk_per_share,
            entry_price=entry,
            stop_price=stop,
            position_value=position_value
        )

    def calculate_risk_reward_ratio(
        self,
        entry_price: float,
        stop_price: float,
        target_price: float
    ) -> Decimal:
        """
        Calculate risk/reward ratio for a trade.

        Args:
            entry_price: Entry price
            stop_price: Stop loss price
            target_price: Target profit price

        Returns:
            Risk/reward ratio (e.g., 1:2 returns Decimal("2.0"))

        Examples:
            >>> calc = RiskCalculator()
            >>> # Entry at 150, stop at 149, target at 152 = 1:2 ratio
            >>> ratio = calc.calculate_risk_reward_ratio(150.0, 149.0, 152.0)
            >>> float(ratio)
            2.0
        """
        entry = Decimal(str(entry_price))
        stop = Decimal(str(stop_price))
        target = Decimal(str(target_price))

        risk = abs(entry - stop)
        reward = abs(target - entry)

        if risk <= 0:
            raise ValueError("Risk must be positive")

        return reward / risk

    def validate_position_against_buying_power(
        self,
        entry_price: float,
        shares: int,
        buying_power: float,
        margin_requirement: float = 1.0
    ) -> Tuple[bool, str]:
        """
        Validate if position size is within buying power limits.

        Args:
            entry_price: Entry price
            shares: Number of shares
            buying_power: Available buying power
            margin_requirement: Margin requirement (1.0 = cash, 0.25 = 4x margin)

        Returns:
            Tuple of (is_valid, message)

        Examples:
            >>> calc = RiskCalculator()
            >>> valid, msg = calc.validate_position_against_buying_power(
            ...     entry_price=150.0,
            ...     shares=100,
            ...     buying_power=20000.0,
            ...     margin_requirement=1.0
            ... )
            >>> valid
            True
        """
        entry = Decimal(str(entry_price))
        bp = Decimal(str(buying_power))
        margin = Decimal(str(margin_requirement))

        position_value = entry * shares
        required_bp = position_value * margin

        if required_bp > bp:
            shortage = required_bp - bp
            return False, (
                f"Insufficient buying power. Required: ${required_bp:.2f}, "
                f"Available: ${bp:.2f}, Short: ${shortage:.2f}"
            )

        return True, "Position size is within buying power limits"

    def calculate_max_shares_for_buying_power(
        self,
        entry_price: float,
        buying_power: float,
        margin_requirement: float = 1.0
    ) -> int:
        """
        Calculate maximum shares that can be purchased with available buying power.

        Args:
            entry_price: Entry price
            buying_power: Available buying power
            margin_requirement: Margin requirement (1.0 = cash, 0.25 = 4x margin)

        Returns:
            Maximum number of shares

        Examples:
            >>> calc = RiskCalculator()
            >>> max_shares = calc.calculate_max_shares_for_buying_power(
            ...     entry_price=150.0,
            ...     buying_power=20000.0,
            ...     margin_requirement=1.0
            ... )
            >>> max_shares
            133
        """
        entry = Decimal(str(entry_price))
        bp = Decimal(str(buying_power))
        margin = Decimal(str(margin_requirement))

        if entry <= 0:
            raise ValueError("Entry price must be positive")

        # Calculate max shares: BP / (price * margin_req)
        max_shares = bp / (entry * margin)

        return int(max_shares)  # Round down to be conservative
