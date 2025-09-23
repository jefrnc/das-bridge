"""
Unit tests for order management module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from decimal import Decimal

from das_trader.orders import OrderManager, Order
from das_trader.constants import OrderSide, OrderType, OrderStatus, TimeInForce
from das_trader.exceptions import DASOrderError


class TestOrder:
    """Test Order class."""

    def test_order_creation(self):
        """Test creating an order."""
        order = Order(
            order_id="ORD123",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=150.00
        )

        assert order.order_id == "ORD123"
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.quantity == 100
        assert order.order_type == OrderType.LIMIT
        assert order.price == 150.00
        assert order.status == OrderStatus.PENDING

    def test_order_fill(self):
        """Test filling an order."""
        order = Order(
            order_id="ORD123",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )

        order.fill(filled_quantity=100, fill_price=149.99)

        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == 100
        assert order.fill_price == 149.99
        assert order.is_filled()

    def test_partial_fill(self):
        """Test partial order fill."""
        order = Order(
            order_id="ORD123",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=150.00
        )

        order.fill(filled_quantity=50, fill_price=150.00)

        assert order.status == OrderStatus.PARTIAL
        assert order.filled_quantity == 50
        assert not order.is_filled()
        assert order.remaining_quantity == 50

    def test_order_cancellation(self):
        """Test canceling an order."""
        order = Order(
            order_id="ORD123",
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=155.00
        )

        order.cancel()

        assert order.status == OrderStatus.CANCELLED
        assert order.is_cancelled()

    def test_order_validation(self):
        """Test order validation."""
        # Test invalid quantity
        with pytest.raises(ValueError):
            Order(
                order_id="ORD123",
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=-10,  # Invalid
                order_type=OrderType.MARKET
            )

        # Test limit order without price
        with pytest.raises(ValueError):
            Order(
                order_id="ORD123",
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=100,
                order_type=OrderType.LIMIT
                # Missing price
            )


class TestOrderManager:
    """Test OrderManager class."""

    @pytest.fixture
    def connection(self):
        """Create mock connection."""
        mock = AsyncMock()
        mock.send_command = AsyncMock()
        return mock

    @pytest.fixture
    def order_manager(self, connection):
        """Create OrderManager instance."""
        return OrderManager(connection)

    @pytest.mark.asyncio
    async def test_send_order(self, order_manager, connection):
        """Test sending an order."""
        connection.send_command.return_value = "ORDER_12345"

        order_id = await order_manager.send_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )

        assert order_id == "ORDER_12345"
        assert "ORDER_12345" in order_manager._orders
        connection.send_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_limit_order(self, order_manager, connection):
        """Test sending a limit order."""
        connection.send_command.return_value = "ORDER_67890"

        order_id = await order_manager.send_order(
            symbol="TSLA",
            side=OrderSide.SELL,
            quantity=50,
            order_type=OrderType.LIMIT,
            price=250.00,
            time_in_force=TimeInForce.GTC
        )

        assert order_id == "ORDER_67890"
        order = order_manager.get_order("ORDER_67890")
        assert order.price == 250.00
        assert order.time_in_force == TimeInForce.GTC

    @pytest.mark.asyncio
    async def test_cancel_order(self, order_manager, connection):
        """Test canceling an order."""
        # First create an order
        connection.send_command.return_value = "ORDER_111"
        order_id = await order_manager.send_order(
            "AAPL", OrderSide.BUY, 100, OrderType.MARKET
        )

        # Then cancel it
        connection.send_command.return_value = "CANCELLED"
        result = await order_manager.cancel_order(order_id)

        assert result is True
        order = order_manager.get_order(order_id)
        assert order.status == OrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_all_orders(self, order_manager, connection):
        """Test canceling all orders."""
        # Create multiple orders
        connection.send_command.return_value = "ORDER_1"
        await order_manager.send_order("AAPL", OrderSide.BUY, 100, OrderType.MARKET)

        connection.send_command.return_value = "ORDER_2"
        await order_manager.send_order("TSLA", OrderSide.SELL, 50, OrderType.LIMIT, price=250)

        # Cancel all
        connection.send_command.return_value = "ALL_CANCELLED"
        result = await order_manager.cancel_all_orders()

        assert result is True
        # All orders should be cancelled
        for order in order_manager.get_all_orders():
            assert order.status == OrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_modify_order(self, order_manager, connection):
        """Test modifying an order."""
        # Create an order
        connection.send_command.return_value = "ORDER_999"
        order_id = await order_manager.send_order(
            "AAPL", OrderSide.BUY, 100, OrderType.LIMIT, price=150.00
        )

        # Modify it
        connection.send_command.return_value = "MODIFIED"
        result = await order_manager.modify_order(
            order_id,
            new_quantity=150,
            new_price=149.50
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_get_pending_orders(self, order_manager, connection):
        """Test getting pending orders."""
        mock_response = """
        ORDER_1|AAPL|BUY|100|LIMIT|150.00|PENDING
        ORDER_2|TSLA|SELL|50|MARKET||PENDING
        """
        connection.send_command.return_value = mock_response

        orders = await order_manager.get_pending_orders()

        assert isinstance(orders, list)
        connection.send_command.assert_called()

    @pytest.mark.asyncio
    async def test_get_executed_orders(self, order_manager, connection):
        """Test getting executed orders."""
        mock_response = """
        ORDER_3|AAPL|BUY|100|MARKET||EXECUTED|150.50
        ORDER_4|TSLA|SELL|50|LIMIT|250.00|EXECUTED|250.00
        """
        connection.send_command.return_value = mock_response

        orders = await order_manager.get_executed_orders()

        assert isinstance(orders, list)

    def test_order_callbacks(self, order_manager):
        """Test order callbacks."""
        callback_data = None

        def on_order_filled(order):
            nonlocal callback_data
            callback_data = order

        order_manager.register_callback("order_filled", on_order_filled)

        # Create and fill an order
        order = Order("ORD123", "AAPL", OrderSide.BUY, 100, OrderType.MARKET)
        order.fill(100, 150.00)

        # Trigger callback
        order_manager._trigger_callback("order_filled", order)

        assert callback_data == order

    def test_get_orders_by_symbol(self, order_manager):
        """Test getting orders by symbol."""
        # Add some orders
        order1 = Order("ORD1", "AAPL", OrderSide.BUY, 100, OrderType.MARKET)
        order2 = Order("ORD2", "AAPL", OrderSide.SELL, 50, OrderType.LIMIT, price=155)
        order3 = Order("ORD3", "TSLA", OrderSide.BUY, 25, OrderType.MARKET)

        order_manager._orders = {
            "ORD1": order1,
            "ORD2": order2,
            "ORD3": order3
        }

        aapl_orders = order_manager.get_orders_by_symbol("AAPL")
        assert len(aapl_orders) == 2
        assert all(o.symbol == "AAPL" for o in aapl_orders)

    def test_get_open_orders(self, order_manager):
        """Test getting open orders."""
        # Add orders with different statuses
        order1 = Order("ORD1", "AAPL", OrderSide.BUY, 100, OrderType.MARKET)
        order1.status = OrderStatus.PENDING

        order2 = Order("ORD2", "TSLA", OrderSide.SELL, 50, OrderType.LIMIT, price=250)
        order2.status = OrderStatus.FILLED

        order3 = Order("ORD3", "NVDA", OrderSide.BUY, 25, OrderType.MARKET)
        order3.status = OrderStatus.PARTIAL

        order_manager._orders = {
            "ORD1": order1,
            "ORD2": order2,
            "ORD3": order3
        }

        open_orders = order_manager.get_open_orders()
        assert len(open_orders) == 2  # PENDING and PARTIAL
        assert "ORD2" not in [o.order_id for o in open_orders]

    @pytest.mark.asyncio
    async def test_order_error_handling(self, order_manager, connection):
        """Test error handling in order operations."""
        connection.send_command.side_effect = DASOrderError("Insufficient buying power")

        with pytest.raises(DASOrderError):
            await order_manager.send_order(
                "AAPL", OrderSide.BUY, 1000, OrderType.MARKET
            )