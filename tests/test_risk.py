"""Tests for risk management module."""

import pytest
from decimal import Decimal
from das_trader.risk import RiskCalculator, PositionSizeResult


class TestRiskCalculator:
    """Test risk calculation utilities."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calc = RiskCalculator()

    def test_calculate_shares_for_risk_basic(self):
        """Test basic position sizing calculation."""
        # Risk $200 on AAPL at $150 with stop at $149 = 200 shares
        shares = self.calc.calculate_shares_for_risk(
            entry_price=150.0,
            stop_price=149.0,
            risk_dollars=200.0
        )
        assert shares == 200

    def test_calculate_shares_for_risk_with_slippage(self):
        """Test position sizing with slippage."""
        # With $0.05 slippage, risk per share increases
        shares = self.calc.calculate_shares_for_risk(
            entry_price=150.0,
            stop_price=149.0,
            risk_dollars=200.0,
            slippage=0.05
        )
        # Risk per share = $1.00 + $0.05 = $1.05
        # Shares = $200 / $1.05 = 190 (rounded down)
        assert shares == 190

    def test_calculate_shares_for_risk_short(self):
        """Test position sizing for short position."""
        # Short at $150, stop at $151, risk $300
        shares = self.calc.calculate_shares_for_risk(
            entry_price=150.0,
            stop_price=151.0,
            risk_dollars=300.0
        )
        assert shares == 300

    def test_calculate_shares_for_risk_min_shares(self):
        """Test minimum shares constraint."""
        # Very small risk should still return min_shares
        shares = self.calc.calculate_shares_for_risk(
            entry_price=150.0,
            stop_price=149.0,
            risk_dollars=0.50,  # Less than 1 share worth
            min_shares=10
        )
        assert shares == 10

    def test_calculate_shares_for_risk_max_shares(self):
        """Test maximum shares constraint."""
        shares = self.calc.calculate_shares_for_risk(
            entry_price=150.0,
            stop_price=149.0,
            risk_dollars=5000.0,  # Would calculate to 5000 shares
            max_shares=1000
        )
        assert shares == 1000

    def test_calculate_shares_for_risk_invalid_prices(self):
        """Test handling of invalid price (entry = stop)."""
        shares = self.calc.calculate_shares_for_risk(
            entry_price=150.0,
            stop_price=150.0,  # Same as entry
            risk_dollars=200.0,
            min_shares=1
        )
        # Should return min_shares when risk calculation is invalid
        assert shares == 1

    def test_calculate_position_risk(self):
        """Test position risk calculation."""
        risk = self.calc.calculate_position_risk(
            entry_price=150.0,
            stop_price=149.0,
            shares=200
        )
        assert risk == Decimal("200.0")

    def test_calculate_position_risk_with_slippage(self):
        """Test position risk calculation with slippage."""
        risk = self.calc.calculate_position_risk(
            entry_price=150.0,
            stop_price=149.0,
            shares=200,
            slippage=0.05
        )
        # Risk = (1.00 + 0.05) * 200 = 210
        assert risk == Decimal("210.0")

    def test_suggest_stop_price_long(self):
        """Test stop price suggestion for long position."""
        stop = self.calc.suggest_stop_price(
            entry_price=150.0,
            risk_dollars=200.0,
            shares=200,
            side="long"
        )
        # Risk per share = $200 / 200 = $1
        # Stop = $150 - $1 = $149
        assert float(stop) == 149.0

    def test_suggest_stop_price_short(self):
        """Test stop price suggestion for short position."""
        stop = self.calc.suggest_stop_price(
            entry_price=150.0,
            risk_dollars=300.0,
            shares=200,
            side="short"
        )
        # Risk per share = $300 / 200 = $1.50
        # Stop = $150 + $1.50 = $151.50
        assert float(stop) == 151.5

    def test_suggest_stop_price_with_slippage(self):
        """Test stop price suggestion with slippage."""
        stop = self.calc.suggest_stop_price(
            entry_price=150.0,
            risk_dollars=200.0,
            shares=200,
            side="long",
            slippage=0.10
        )
        # Risk per share = $200 / 200 = $1
        # Subtract slippage: $1 - $0.10 = $0.90
        # Stop = $150 - $0.90 = $149.10
        assert float(stop) == 149.10

    def test_suggest_stop_price_invalid_side(self):
        """Test that invalid side raises ValueError."""
        with pytest.raises(ValueError, match="Invalid side"):
            self.calc.suggest_stop_price(
                entry_price=150.0,
                risk_dollars=200.0,
                shares=200,
                side="invalid"
            )

    def test_suggest_stop_price_zero_shares(self):
        """Test that zero shares raises ValueError."""
        with pytest.raises(ValueError, match="Shares must be positive"):
            self.calc.suggest_stop_price(
                entry_price=150.0,
                risk_dollars=200.0,
                shares=0,
                side="long"
            )

    def test_calculate_position_size_complete(self):
        """Test complete position size calculation."""
        result = self.calc.calculate_position_size(
            entry_price=150.0,
            stop_price=149.0,
            risk_dollars=200.0
        )

        assert isinstance(result, PositionSizeResult)
        assert result.shares == 200
        assert result.risk_dollars == Decimal("200.0")
        assert result.risk_per_share == Decimal("1.0")
        assert result.entry_price == Decimal("150.0")
        assert result.stop_price == Decimal("149.0")
        assert result.position_value == Decimal("30000.0")

    def test_position_size_result_to_dict(self):
        """Test PositionSizeResult serialization."""
        result = self.calc.calculate_position_size(
            entry_price=150.0,
            stop_price=149.0,
            risk_dollars=200.0
        )

        result_dict = result.to_dict()

        assert result_dict["shares"] == 200
        assert result_dict["risk_dollars"] == 200.0
        assert result_dict["risk_per_share"] == 1.0
        assert result_dict["entry_price"] == 150.0
        assert result_dict["stop_price"] == 149.0
        assert result_dict["position_value"] == 30000.0

    def test_calculate_risk_reward_ratio(self):
        """Test risk/reward ratio calculation."""
        # Entry at 150, stop at 149 (risk $1), target at 152 (reward $2)
        # Ratio should be 2:1
        ratio = self.calc.calculate_risk_reward_ratio(
            entry_price=150.0,
            stop_price=149.0,
            target_price=152.0
        )
        assert float(ratio) == 2.0

    def test_calculate_risk_reward_ratio_short(self):
        """Test risk/reward ratio for short position."""
        # Short at 150, stop at 151 (risk $1), target at 147 (reward $3)
        # Ratio should be 3:1
        ratio = self.calc.calculate_risk_reward_ratio(
            entry_price=150.0,
            stop_price=151.0,
            target_price=147.0
        )
        assert float(ratio) == 3.0

    def test_calculate_risk_reward_ratio_invalid(self):
        """Test that zero risk raises ValueError."""
        with pytest.raises(ValueError, match="Risk must be positive"):
            self.calc.calculate_risk_reward_ratio(
                entry_price=150.0,
                stop_price=150.0,  # Same price = zero risk
                target_price=152.0
            )

    def test_validate_position_against_buying_power_valid(self):
        """Test position validation with sufficient buying power."""
        is_valid, msg = self.calc.validate_position_against_buying_power(
            entry_price=150.0,
            shares=100,
            buying_power=20000.0,
            margin_requirement=1.0  # Cash account
        )
        # Position value = $15,000, BP = $20,000
        assert is_valid is True
        assert "within buying power limits" in msg

    def test_validate_position_against_buying_power_invalid(self):
        """Test position validation with insufficient buying power."""
        is_valid, msg = self.calc.validate_position_against_buying_power(
            entry_price=150.0,
            shares=1000,
            buying_power=20000.0,
            margin_requirement=1.0
        )
        # Position value = $150,000, BP = $20,000
        assert is_valid is False
        assert "Insufficient buying power" in msg

    def test_validate_position_with_margin(self):
        """Test position validation with margin account."""
        is_valid, msg = self.calc.validate_position_against_buying_power(
            entry_price=150.0,
            shares=500,
            buying_power=20000.0,
            margin_requirement=0.25  # 4x margin
        )
        # Position value = $75,000
        # Required BP = $75,000 * 0.25 = $18,750
        # Available BP = $20,000
        assert is_valid is True

    def test_calculate_max_shares_for_buying_power(self):
        """Test maximum shares calculation."""
        max_shares = self.calc.calculate_max_shares_for_buying_power(
            entry_price=150.0,
            buying_power=20000.0,
            margin_requirement=1.0  # Cash account
        )
        # $20,000 / $150 = 133.33, rounded down to 133
        assert max_shares == 133

    def test_calculate_max_shares_with_margin(self):
        """Test maximum shares calculation with margin."""
        max_shares = self.calc.calculate_max_shares_for_buying_power(
            entry_price=150.0,
            buying_power=20000.0,
            margin_requirement=0.25  # 4x margin
        )
        # $20,000 / ($150 * 0.25) = $20,000 / $37.50 = 533.33
        assert max_shares == 533

    def test_calculate_max_shares_invalid_price(self):
        """Test that zero or negative price raises ValueError."""
        with pytest.raises(ValueError, match="Entry price must be positive"):
            self.calc.calculate_max_shares_for_buying_power(
                entry_price=0.0,
                buying_power=20000.0
            )

    def test_decimal_precision(self):
        """Test that calculations maintain decimal precision."""
        result = self.calc.calculate_position_size(
            entry_price=150.33,
            stop_price=149.17,
            risk_dollars=250.50
        )

        # Verify all values are Decimal type
        assert isinstance(result.risk_dollars, Decimal)
        assert isinstance(result.risk_per_share, Decimal)
        assert isinstance(result.entry_price, Decimal)
        assert isinstance(result.stop_price, Decimal)
        assert isinstance(result.position_value, Decimal)

    def test_large_position_sizes(self):
        """Test calculations with large position sizes."""
        shares = self.calc.calculate_shares_for_risk(
            entry_price=10.0,
            stop_price=9.50,
            risk_dollars=50000.0
        )
        # Risk per share = $0.50
        # Shares = $50,000 / $0.50 = 100,000
        assert shares == 100000

    def test_small_price_differences(self):
        """Test calculations with very tight stops."""
        shares = self.calc.calculate_shares_for_risk(
            entry_price=100.00,
            stop_price=99.95,  # Only $0.05 stop
            risk_dollars=100.0
        )
        # Risk per share = $0.05
        # Shares = $100 / $0.05 = 2000
        assert shares == 2000
