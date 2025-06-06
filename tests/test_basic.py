"""Basic tests for DAS Trader API client."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal

from das_trader import (
    DASTraderClient, OrderType, OrderSide, OrderStatus,
    MarketDataLevel, DASConnectionError
)
from das_trader.utils import parse_message, calculate_pnl
from das_trader.orders import Order
from das_trader.positions import Position


class TestUtils:
    """Test utility functions."""
    
    def test_parse_order_message(self):
        """Test parsing order messages."""
        message = "%ORDER ORD123 AAPL BUY 100 150.00 LIMIT NEW 0 0.00 100"
        parsed = parse_message(message)
        
        assert parsed["type"] == "ORDER"
        assert parsed["order_id"] == "ORD123"
        assert parsed["symbol"] == "AAPL"
        assert parsed["side"] == "BUY"
        assert parsed["quantity"] == 100
        assert parsed["price"] == Decimal("150.00")
        assert parsed["order_type"] == "LIMIT"
        assert parsed["status"] == "NEW"
    
    def test_parse_quote_message(self):
        """Test parsing quote messages."""
        message = "$Quote AAPL 149.50 149.75 149.60 1000000 100 200"
        parsed = parse_message(message)
        
        assert parsed["type"] == "QUOTE"
        assert parsed["symbol"] == "AAPL"
        assert parsed["bid"] == Decimal("149.50")
        assert parsed["ask"] == Decimal("149.75")
        assert parsed["last"] == Decimal("149.60")
        assert parsed["volume"] == 1000000
        assert parsed["bid_size"] == 100
        assert parsed["ask_size"] == 200
    
    def test_parse_position_message(self):
        """Test parsing position messages."""
        message = "%POS AAPL 100 150.00 151.00 100.00 0.67"
        parsed = parse_message(message)
        
        assert parsed["type"] == "POSITION"
        assert parsed["symbol"] == "AAPL"
        assert parsed["quantity"] == 100
        assert parsed["avg_cost"] == Decimal("150.00")
        assert parsed["current_price"] == Decimal("151.00")
        assert parsed["pnl"] == Decimal("100.00")
    
    def test_calculate_pnl(self):
        """Test P&L calculation."""
        # Long position
        result = calculate_pnl(100, Decimal("150.00"), Decimal("155.00"))
        assert result["unrealized_pnl"] == Decimal("500.00")
        assert result["pnl_percent"] == Decimal("3.33")
        
        # Short position
        result = calculate_pnl(-100, Decimal("150.00"), Decimal("145.00"))
        assert result["unrealized_pnl"] == Decimal("500.00")


class TestOrder:
    """Test Order class."""
    
    def test_order_creation(self):
        """Test order creation."""
        order = Order(
            order_id="TEST123",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=Decimal("150.00")
        )
        
        assert order.order_id == "TEST123"
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.quantity == 100
        assert order.remaining_quantity == 100
        assert order.is_active()
    
    def test_order_fill(self):
        """Test order filling."""
        order = Order(
            order_id="TEST123",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=Decimal("150.00")
        )
        
        # Partial fill
        order.add_fill(50, Decimal("149.95"))
        assert order.filled_quantity == 50
        assert order.remaining_quantity == 50
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.avg_fill_price == Decimal("149.95")
        
        # Complete fill
        order.add_fill(50, Decimal("150.05"))
        assert order.filled_quantity == 100
        assert order.remaining_quantity == 0
        assert order.status == OrderStatus.FILLED
        assert order.avg_fill_price == Decimal("150.00")


class TestPosition:
    """Test Position class."""
    
    def test_position_creation(self):
        """Test position creation."""
        position = Position(
            symbol="AAPL",
            quantity=100,
            avg_cost=Decimal("150.00"),
            current_price=Decimal("155.00")
        )
        
        assert position.symbol == "AAPL"
        assert position.quantity == 100
        assert position.is_long()
        assert not position.is_short()
        assert not position.is_flat()
        assert position.unrealized_pnl == Decimal("500.00")
    
    def test_position_updates(self):
        """Test position price updates."""
        position = Position(
            symbol="AAPL",
            quantity=100,
            avg_cost=Decimal("150.00")
        )
        
        position.update_price(Decimal("155.00"))
        assert position.current_price == Decimal("155.00")
        assert position.unrealized_pnl == Decimal("500.00")
        assert position.pnl_percent == Decimal("3.33")
    
    def test_position_fills(self):
        """Test adding fills to position."""
        position = Position(
            symbol="AAPL",
            quantity=0,
            avg_cost=Decimal("0"),
            current_price=Decimal("150.00")
        )
        
        # First fill - establish position
        position.add_fill(100, Decimal("150.00"))
        assert position.quantity == 100
        assert position.avg_cost == Decimal("150.00")
        
        # Add to position
        position.add_fill(50, Decimal("151.00"))
        assert position.quantity == 150
        assert position.avg_cost == Decimal("150.33")
        
        # Partial close
        position.add_fill(-75, Decimal("152.00"))
        assert position.quantity == 75
        assert position.realized_pnl == Decimal("150.00")  # 75 * (152 - 150.33)


@pytest.mark.asyncio
class TestClient:
    """Test DAS Trader client."""
    
    async def test_client_creation(self):
        """Test client creation."""
        client = DASTraderClient(host="localhost", port=9910)
        assert client.connection.host == "localhost"
        assert client.connection.port == 9910
        assert not client.is_connected
        assert not client.is_authenticated
    
    @patch('das_trader.connection.ConnectionManager.connect')
    async def test_client_connect(self, mock_connect):
        """Test client connection."""
        mock_connect.return_value = None
        
        client = DASTraderClient()
        
        # Mock the connection state
        client.connection._connected = True
        client.connection._authenticated = True
        
        await client.connect("test_user", "test_pass", "test_account")
        mock_connect.assert_called_once_with("test_user", "test_pass", "test_account")
    
    @patch('das_trader.connection.ConnectionManager.send_command')
    async def test_send_order(self, mock_send):
        """Test sending an order."""
        mock_send.return_value = {"type": "ORDER_ACTION", "order_id": "TEST123"}
        
        client = DASTraderClient()
        client.connection._connected = True
        client.connection._authenticated = True
        
        order_id = await client.send_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=150.00
        )
        
        assert order_id is not None
        mock_send.assert_called_once()
    
    @patch('das_trader.connection.ConnectionManager.send_command')
    async def test_get_quote(self, mock_send):
        """Test getting a quote."""
        mock_send.return_value = {
            "type": "QUOTE",
            "symbol": "AAPL",
            "bid": Decimal("149.50"),
            "ask": Decimal("149.75"),
            "last": Decimal("149.60"),
            "bid_size": 100,
            "ask_size": 200,
            "volume": 1000000
        }
        
        client = DASTraderClient()
        client.connection._connected = True
        client.connection._authenticated = True
        
        quote = await client.get_quote("AAPL")
        
        assert quote is not None
        assert quote.symbol == "AAPL"
        assert quote.bid == Decimal("149.50")
        assert quote.ask == Decimal("149.75")
        mock_send.assert_called_once()
    
    async def test_context_manager(self):
        """Test using client as context manager."""
        with patch('das_trader.connection.ConnectionManager.connect') as mock_connect, \\
             patch('das_trader.connection.ConnectionManager.disconnect') as mock_disconnect:
            
            mock_connect.return_value = None
            mock_disconnect.return_value = None
            
            async with DASTraderClient() as client:
                client.connection._connected = True
                client.connection._authenticated = True
                assert client is not None
            
            # disconnect should be called when exiting context
            mock_disconnect.assert_called_once()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])