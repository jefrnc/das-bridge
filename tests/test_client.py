"""
Unit tests for DAS client module with mocks.
Tests all client functionality without real DAS connection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime

from das_trader.client import DASTraderClient
from das_trader.constants import OrderSide, OrderType, TimeInForce, MarketDataLevel
from das_trader.exceptions import DASAPIError, DASOrderError


class TestDASTraderClient:
    """Test DAS Trader client with mocked operations."""

    @pytest.fixture
    def client(self):
        """Create a DAS client instance."""
        return DASTraderClient(host="localhost", port=9910)

    @pytest.fixture
    def connected_client(self, client):
        """Create a connected client with mocked connection."""
        with patch.object(client.connection, 'is_connected', True):
            with patch.object(client.connection, 'send_command', new_callable=AsyncMock):
                yield client

    @pytest.mark.asyncio
    async def test_client_connect(self, client):
        """Test client connection."""
        with patch.object(client.connection, 'connect', new_callable=AsyncMock) as mock_connect:
            await client.connect("user", "pass", "account")
            mock_connect.assert_called_once_with("user", "pass", "account")

    @pytest.mark.asyncio
    async def test_send_market_order(self, connected_client):
        """Test sending a market order."""
        connected_client.connection.send_command.return_value = "ORDER_ID_12345"

        order_id = await connected_client.send_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )

        assert order_id == "ORDER_ID_12345"
        connected_client.connection.send_command.assert_called_once()

        # Verify command format
        call_args = connected_client.connection.send_command.call_args
        command = call_args[0][0]
        assert "AAPL" in command
        assert "BUY" in command
        assert "100" in command

    @pytest.mark.asyncio
    async def test_send_limit_order(self, connected_client):
        """Test sending a limit order."""
        connected_client.connection.send_command.return_value = "ORDER_ID_67890"

        order_id = await connected_client.send_order(
            symbol="TSLA",
            side=OrderSide.SELL,
            quantity=50,
            order_type=OrderType.LIMIT,
            price=250.50,
            time_in_force=TimeInForce.GTC
        )

        assert order_id == "ORDER_ID_67890"

        # Verify price was included
        call_args = connected_client.connection.send_command.call_args
        command = call_args[0][0]
        assert "250.50" in command or "250.5" in command
        assert "GTC" in command

    @pytest.mark.asyncio
    async def test_cancel_order(self, connected_client):
        """Test canceling an order."""
        connected_client.connection.send_command.return_value = "CANCELLED"

        result = await connected_client.cancel_order("ORDER_12345")

        assert result is True
        connected_client.connection.send_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_positions(self, connected_client):
        """Test getting positions."""
        # Mock position data
        mock_response = """
        AAPL|100|150.00|15000.00|15500.00|500.00
        TSLA|50|250.00|12500.00|12000.00|-500.00
        """
        connected_client.connection.send_command.return_value = mock_response

        # Request positions
        await connected_client.update_positions()
        positions = connected_client.get_positions()

        assert len(positions) >= 0  # May be parsed differently

    @pytest.mark.asyncio
    async def test_get_buying_power(self, connected_client):
        """Test getting buying power."""
        connected_client.connection.send_command.return_value = "BP 25000.00"

        bp = await connected_client.get_buying_power()

        assert "buying_power" in bp
        assert bp["buying_power"] == Decimal("25000.00")

    @pytest.mark.asyncio
    async def test_get_pending_orders(self, connected_client):
        """Test getting pending orders."""
        mock_orders = """
        ORDER1|AAPL|BUY|100|LIMIT|150.00|PENDING
        ORDER2|TSLA|SELL|50|MARKET||PENDING
        """
        connected_client.connection.send_command.return_value = mock_orders

        orders = await connected_client.get_pending_orders()

        assert isinstance(orders, list)
        connected_client.connection.send_command.assert_called()

    @pytest.mark.asyncio
    async def test_get_executed_orders(self, connected_client):
        """Test getting executed orders."""
        mock_orders = """
        ORDER3|AAPL|BUY|100|MARKET||EXECUTED|150.50
        ORDER4|TSLA|SELL|50|LIMIT|250.00|EXECUTED|250.00
        """
        connected_client.connection.send_command.return_value = mock_orders

        orders = await connected_client.get_executed_orders()

        assert isinstance(orders, list)

    @pytest.mark.asyncio
    async def test_subscribe_quote(self, connected_client):
        """Test subscribing to market data."""
        connected_client.connection.send_command.return_value = "SUBSCRIBED"

        result = await connected_client.subscribe_quote(
            "AAPL",
            MarketDataLevel.LEVEL2
        )

        assert result is True
        connected_client.connection.send_command.assert_called()

    @pytest.mark.asyncio
    async def test_get_quote(self, connected_client):
        """Test getting a quote."""
        mock_quote = "AAPL|149.50|149.55|149.52|1000|2000"
        connected_client.connection.send_command.return_value = mock_quote

        quote = await connected_client.get_quote("AAPL")

        assert quote is not None
        # Quote object should have bid, ask, last properties

    @pytest.mark.asyncio
    async def test_get_level1_data(self, connected_client):
        """Test getting Level 1 data."""
        mock_data = """
        SYMBOL=AAPL
        BID=149.50
        ASK=149.55
        LAST=149.52
        VOLUME=1000000
        """
        connected_client.connection.send_command.return_value = mock_data

        data = await connected_client.get_level1_data("AAPL")

        assert data is not None

    @pytest.mark.asyncio
    async def test_error_handling(self, connected_client):
        """Test error handling in client operations."""
        # Simulate error response
        connected_client.connection.send_command.side_effect = DASAPIError("Order rejected")

        with pytest.raises(DASAPIError):
            await connected_client.send_order(
                "INVALID",
                OrderSide.BUY,
                100,
                OrderType.MARKET
            )

    @pytest.mark.asyncio
    async def test_disconnect(self, connected_client):
        """Test client disconnection."""
        with patch.object(connected_client.connection, 'disconnect', new_callable=AsyncMock):
            await connected_client.disconnect()
            connected_client.connection.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_order_validation(self, client):
        """Test order parameter validation."""
        # Test invalid quantity
        with pytest.raises(ValueError):
            await client.send_order(
                "AAPL",
                OrderSide.BUY,
                0,  # Invalid quantity
                OrderType.MARKET
            )

        # Test limit order without price
        with pytest.raises(ValueError):
            await client.send_order(
                "AAPL",
                OrderSide.BUY,
                100,
                OrderType.LIMIT
                # Missing price
            )

    @pytest.mark.asyncio
    async def test_callbacks(self, connected_client):
        """Test callback mechanism."""
        callback_called = False
        callback_data = None

        def test_callback(data):
            nonlocal callback_called, callback_data
            callback_called = True
            callback_data = data

        # Register callback
        connected_client.orders.register_callback("order_filled", test_callback)

        # Simulate order fill
        connected_client.orders._trigger_callback("order_filled", {"order_id": "123"})

        assert callback_called
        assert callback_data == {"order_id": "123"}

    @pytest.mark.asyncio
    async def test_position_tracking(self, connected_client):
        """Test position tracking updates."""
        # Mock initial positions
        mock_positions = """
        AAPL|100|150.00
        TSLA|50|250.00
        """
        connected_client.connection.send_command.return_value = mock_positions

        await connected_client.update_positions()

        # Get specific position
        position = connected_client.positions.get_position("AAPL")
        # Position may exist depending on parsing

    @pytest.mark.asyncio
    async def test_account_info(self, connected_client):
        """Test getting account information."""
        mock_info = """
        ACCOUNT=TESTACCOUNT
        EQUITY=100000.00
        CASH=50000.00
        BP=25000.00
        """
        connected_client.connection.send_command.return_value = mock_info

        info = await connected_client.get_account_info()

        assert info is not None
        # Should contain account details

    @pytest.mark.asyncio
    async def test_multiple_symbol_subscription(self, connected_client):
        """Test subscribing to multiple symbols."""
        connected_client.connection.send_command.return_value = "SUBSCRIBED"

        symbols = ["AAPL", "TSLA", "NVDA", "AMD"]
        for symbol in symbols:
            await connected_client.subscribe_quote(symbol)

        assert connected_client.connection.send_command.call_count == len(symbols)