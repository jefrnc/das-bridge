"""Tests for trading strategies module."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from decimal import Decimal

from das_trader.strategies import TradingStrategies, StrategyResult
from das_trader.orders import Order, OrderType, OrderSide, OrderStatus
from das_trader.positions import Position
from das_trader.market_data import Quote
from das_trader.constants import TimeInForce


class TestTradingStrategies:
    """Test trading strategy helpers."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock client
        self.mock_client = Mock()

        # Mock managers
        self.mock_client.orders = Mock()
        self.mock_client.positions = Mock()
        self.mock_client.market_data = Mock()
        self.mock_client.risk = Mock()

        # Create strategies instance
        self.strategies = TradingStrategies(self.mock_client)

    def _create_mock_quote(self, bid=149.50, ask=150.50, last=150.00):
        """Helper to create mock quote."""
        quote = Quote(
            symbol="AAPL",
            bid=Decimal(str(bid)),
            ask=Decimal(str(ask)),
            last=Decimal(str(last)),
            bid_size=100,
            ask_size=100,
            volume=1000000
        )
        return quote

    def _create_mock_order(self, order_id="ORD123", symbol="AAPL", side=OrderSide.BUY):
        """Helper to create mock order."""
        return Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=200,
            order_type=OrderType.MARKET,
            status=OrderStatus.NEW
        )

    def _create_mock_position(self, symbol="AAPL", quantity=200, avg_cost=150.0):
        """Helper to create mock position."""
        return Position(
            symbol=symbol,
            quantity=quantity,
            avg_cost=Decimal(str(avg_cost)),
            current_price=Decimal("151.0")
        )

    @pytest.mark.asyncio
    async def test_buy_with_risk_stop_success(self):
        """Test successful long entry with stop."""
        # Setup mocks
        quote = self._create_mock_quote(bid=149.50, ask=150.50)
        self.mock_client.market_data.get_quote = AsyncMock(return_value=quote)

        # Mock position size calculation
        mock_position_size = Mock()
        mock_position_size.shares = 200
        mock_position_size.risk_dollars = Decimal("200.0")
        mock_position_size.to_dict = Mock(return_value={
            "shares": 200,
            "risk_dollars": 200.0
        })
        self.mock_client.risk.calculate_position_size = Mock(return_value=mock_position_size)

        # Mock buying power check
        self.mock_client.positions.get_buying_power = AsyncMock(return_value=Decimal("50000.0"))
        self.mock_client.risk.validate_position_against_buying_power = Mock(
            return_value=(True, "Valid")
        )

        # Mock order placement
        entry_order = self._create_mock_order(order_id="ENTRY1")
        stop_order = self._create_mock_order(order_id="STOP1", side=OrderSide.SELL)
        self.mock_client.orders.send_order = AsyncMock(side_effect=[entry_order, stop_order])

        # Execute strategy
        result = await self.strategies.buy_with_risk_stop(
            symbol="AAPL",
            entry_price=150.0,
            stop_price=149.0,
            risk_amount=200.0,
            entry_type="mid"
        )

        # Assertions
        assert result.success is True
        assert result.entry_order_id == "ENTRY1"
        assert result.stop_order_id == "STOP1"
        assert "AAPL" in result.message

    @pytest.mark.asyncio
    async def test_buy_with_risk_stop_no_quote(self):
        """Test handling when quote is unavailable."""
        # Mock no quote available
        self.mock_client.market_data.get_quote = AsyncMock(return_value=None)

        result = await self.strategies.buy_with_risk_stop(
            symbol="AAPL",
            entry_price=150.0,
            stop_price=149.0,
            risk_amount=200.0
        )

        assert result.success is False
        assert "Could not get quote" in result.message

    @pytest.mark.asyncio
    async def test_buy_with_risk_stop_invalid_entry_type(self):
        """Test handling of invalid entry type."""
        quote = self._create_mock_quote()
        self.mock_client.market_data.get_quote = AsyncMock(return_value=quote)

        result = await self.strategies.buy_with_risk_stop(
            symbol="AAPL",
            entry_price=150.0,
            stop_price=149.0,
            risk_amount=200.0,
            entry_type="invalid_type"
        )

        assert result.success is False
        assert "Invalid entry_type" in result.message

    @pytest.mark.asyncio
    async def test_buy_with_risk_stop_insufficient_bp(self):
        """Test handling of insufficient buying power."""
        quote = self._create_mock_quote()
        self.mock_client.market_data.get_quote = AsyncMock(return_value=quote)

        mock_position_size = Mock()
        mock_position_size.shares = 200
        self.mock_client.risk.calculate_position_size = Mock(return_value=mock_position_size)

        # Mock insufficient buying power
        self.mock_client.positions.get_buying_power = AsyncMock(return_value=Decimal("1000.0"))
        self.mock_client.risk.validate_position_against_buying_power = Mock(
            return_value=(False, "Insufficient buying power")
        )

        result = await self.strategies.buy_with_risk_stop(
            symbol="AAPL",
            entry_price=150.0,
            stop_price=149.0,
            risk_amount=200.0,
            validate_buying_power=True
        )

        assert result.success is False
        assert "Insufficient buying power" in result.message

    @pytest.mark.asyncio
    async def test_buy_with_target_price(self):
        """Test long entry with target price."""
        quote = self._create_mock_quote()
        self.mock_client.market_data.get_quote = AsyncMock(return_value=quote)

        mock_position_size = Mock()
        mock_position_size.shares = 200
        mock_position_size.to_dict = Mock(return_value={"shares": 200})
        self.mock_client.risk.calculate_position_size = Mock(return_value=mock_position_size)

        self.mock_client.positions.get_buying_power = AsyncMock(return_value=Decimal("50000.0"))
        self.mock_client.risk.validate_position_against_buying_power = Mock(return_value=(True, "Valid"))

        entry_order = self._create_mock_order(order_id="ENTRY1")
        stop_order = self._create_mock_order(order_id="STOP1")
        target_order = self._create_mock_order(order_id="TARGET1")
        self.mock_client.orders.send_order = AsyncMock(
            side_effect=[entry_order, stop_order, target_order]
        )

        result = await self.strategies.buy_with_risk_stop(
            symbol="AAPL",
            entry_price=150.0,
            stop_price=149.0,
            risk_amount=200.0,
            entry_type="mid",
            target_price=152.0
        )

        assert result.success is True
        assert result.target_order_id == "TARGET1"

    @pytest.mark.asyncio
    async def test_sell_with_risk_stop_success(self):
        """Test successful short entry with stop."""
        quote = self._create_mock_quote()
        self.mock_client.market_data.get_quote = AsyncMock(return_value=quote)

        mock_position_size = Mock()
        mock_position_size.shares = 200
        mock_position_size.risk_dollars = Decimal("200.0")
        mock_position_size.to_dict = Mock(return_value={"shares": 200})
        self.mock_client.risk.calculate_position_size = Mock(return_value=mock_position_size)

        self.mock_client.positions.get_buying_power = AsyncMock(return_value=Decimal("50000.0"))
        self.mock_client.risk.validate_position_against_buying_power = Mock(return_value=(True, "Valid"))

        entry_order = self._create_mock_order(order_id="ENTRY1", side=OrderSide.SHORT)
        stop_order = self._create_mock_order(order_id="STOP1", side=OrderSide.COVER)
        self.mock_client.orders.send_order = AsyncMock(side_effect=[entry_order, stop_order])

        result = await self.strategies.sell_with_risk_stop(
            symbol="AAPL",
            entry_price=150.0,
            stop_price=151.0,
            risk_amount=200.0,
            entry_type="mid"
        )

        assert result.success is True
        assert result.entry_order_id == "ENTRY1"
        assert result.stop_order_id == "STOP1"

    @pytest.mark.asyncio
    async def test_close_position_success(self):
        """Test closing position at market."""
        position = self._create_mock_position(quantity=200)
        self.mock_client.positions.get_position = Mock(return_value=position)

        self.mock_client.orders.cancel_all_orders = AsyncMock()

        close_order = self._create_mock_order(order_id="CLOSE1", side=OrderSide.SELL)
        self.mock_client.orders.send_order = AsyncMock(return_value=close_order)

        result = await self.strategies.close_position(
            symbol="AAPL",
            exit_type="market"
        )

        assert result.success is True
        assert result.entry_order_id == "CLOSE1"
        assert "200 shares" in result.message

    @pytest.mark.asyncio
    async def test_close_position_no_position(self):
        """Test closing when no position exists."""
        # Mock no position
        self.mock_client.positions.get_position = Mock(return_value=None)

        result = await self.strategies.close_position(symbol="AAPL")

        assert result.success is False
        assert "No open position" in result.message

    @pytest.mark.asyncio
    async def test_close_position_partial(self):
        """Test closing partial position."""
        position = self._create_mock_position(quantity=200)
        self.mock_client.positions.get_position = Mock(return_value=position)

        self.mock_client.orders.cancel_all_orders = AsyncMock()

        close_order = self._create_mock_order(order_id="CLOSE1")
        self.mock_client.orders.send_order = AsyncMock(return_value=close_order)

        result = await self.strategies.close_position(
            symbol="AAPL",
            exit_type="market",
            percentage=50.0
        )

        assert result.success is True
        assert result.details["shares_closed"] == 100  # 50% of 200
        assert result.details["percentage"] == 50.0

    @pytest.mark.asyncio
    async def test_close_position_short(self):
        """Test closing short position."""
        # Negative quantity = short position
        position = self._create_mock_position(quantity=-200)
        self.mock_client.positions.get_position = Mock(return_value=position)

        self.mock_client.orders.cancel_all_orders = AsyncMock()

        # Should use COVER side for shorts
        close_order = self._create_mock_order(order_id="CLOSE1", side=OrderSide.COVER)
        self.mock_client.orders.send_order = AsyncMock(return_value=close_order)

        result = await self.strategies.close_position(
            symbol="AAPL",
            exit_type="market"
        )

        assert result.success is True
        assert result.details["side"] == OrderSide.COVER.value

    @pytest.mark.asyncio
    async def test_close_position_at_limit(self):
        """Test closing position with limit order."""
        position = self._create_mock_position(quantity=200)
        self.mock_client.positions.get_position = Mock(return_value=position)

        self.mock_client.orders.cancel_all_orders = AsyncMock()

        close_order = self._create_mock_order(order_id="CLOSE1")
        self.mock_client.orders.send_order = AsyncMock(return_value=close_order)

        result = await self.strategies.close_position(
            symbol="AAPL",
            exit_type="limit",
            limit_price=151.0
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_close_position_at_mid(self):
        """Test closing position at mid price."""
        position = self._create_mock_position(quantity=200)
        self.mock_client.positions.get_position = Mock(return_value=position)

        quote = self._create_mock_quote(bid=150.0, ask=151.0)
        self.mock_client.market_data.get_quote = AsyncMock(return_value=quote)

        self.mock_client.orders.cancel_all_orders = AsyncMock()

        close_order = self._create_mock_order(order_id="CLOSE1")
        self.mock_client.orders.send_order = AsyncMock(return_value=close_order)

        result = await self.strategies.close_position(
            symbol="AAPL",
            exit_type="mid"
        )

        assert result.success is True
        # Verify it calculated mid price (150.0 + 151.0) / 2 = 150.5

    @pytest.mark.asyncio
    async def test_scale_out_success(self):
        """Test scale out strategy."""
        position = self._create_mock_position(quantity=300)
        self.mock_client.positions.get_position = Mock(return_value=position)

        self.mock_client.orders.cancel_all_orders = AsyncMock()

        # Mock order placement for each target
        order1 = self._create_mock_order(order_id="SCALE1")
        order2 = self._create_mock_order(order_id="SCALE2")
        order3 = self._create_mock_order(order_id="SCALE3")
        self.mock_client.orders.send_order = AsyncMock(
            side_effect=[order1, order2, order3]
        )

        targets = [
            (151.0, 33.3),
            (152.0, 33.3),
            (153.0, 33.4)
        ]

        result = await self.strategies.scale_out(
            symbol="AAPL",
            targets=targets
        )

        assert result.success is True
        assert len(result.details["order_ids"]) == 3
        assert "3 scale-out orders" in result.message

    @pytest.mark.asyncio
    async def test_scale_out_no_position(self):
        """Test scale out when no position exists."""
        self.mock_client.positions.get_position = Mock(return_value=None)

        result = await self.strategies.scale_out(
            symbol="AAPL",
            targets=[(151.0, 50.0), (152.0, 50.0)]
        )

        assert result.success is False
        assert "No open position" in result.message

    @pytest.mark.asyncio
    async def test_strategy_result_to_dict(self):
        """Test StrategyResult serialization."""
        result = StrategyResult(
            success=True,
            entry_order_id="ENTRY1",
            stop_order_id="STOP1",
            target_order_id="TARGET1",
            message="Test message",
            details={"shares": 200}
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["entry_order_id"] == "ENTRY1"
        assert result_dict["stop_order_id"] == "STOP1"
        assert result_dict["target_order_id"] == "TARGET1"
        assert result_dict["message"] == "Test message"
        assert result_dict["details"]["shares"] == 200

    @pytest.mark.asyncio
    async def test_buy_limit_order_type(self):
        """Test buy with limit order type."""
        quote = self._create_mock_quote()
        self.mock_client.market_data.get_quote = AsyncMock(return_value=quote)

        mock_position_size = Mock()
        mock_position_size.shares = 200
        mock_position_size.to_dict = Mock(return_value={"shares": 200})
        self.mock_client.risk.calculate_position_size = Mock(return_value=mock_position_size)

        self.mock_client.positions.get_buying_power = AsyncMock(return_value=Decimal("50000.0"))
        self.mock_client.risk.validate_position_against_buying_power = Mock(return_value=(True, "Valid"))

        entry_order = self._create_mock_order(order_id="ENTRY1")
        stop_order = self._create_mock_order(order_id="STOP1")
        self.mock_client.orders.send_order = AsyncMock(side_effect=[entry_order, stop_order])

        result = await self.strategies.buy_with_risk_stop(
            symbol="AAPL",
            entry_price=150.0,
            stop_price=149.0,
            risk_amount=200.0,
            entry_type="limit"  # Use limit order
        )

        assert result.success is True
        # Verify send_order was called with LIMIT order type
        calls = self.mock_client.orders.send_order.call_args_list
        assert calls[0].kwargs["order_type"] == OrderType.LIMIT
