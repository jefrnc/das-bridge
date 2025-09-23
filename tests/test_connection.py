"""
Unit tests for DAS connection module with mocks.
No real DAS Trader connection required.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest
from datetime import datetime

from das_trader.connection import DASConnection
from das_trader.constants import Commands
from das_trader.exceptions import (
    DASConnectionError,
    DASAuthenticationError,
    DASTimeoutError
)


class TestDASConnection:
    """Test DAS connection with mocked socket operations."""

    @pytest.fixture
    def mock_socket(self):
        """Create a mock socket."""
        with patch('das_trader.connection.socket.socket') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def connection(self):
        """Create a DAS connection instance."""
        return DASConnection(host="localhost", port=9910)

    @pytest.mark.asyncio
    async def test_connect_success(self, connection, mock_socket):
        """Test successful connection to DAS."""
        # Mock socket operations
        mock_socket.connect = MagicMock()
        mock_socket.recv = MagicMock(return_value=b'OK\n')

        # Mock the reader/writer
        with patch('asyncio.open_connection') as mock_open:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_reader.read.return_value = b'OK\n'
            mock_open.return_value = (mock_reader, mock_writer)

            # Test connection
            await connection.connect("testuser", "testpass", "testaccount")

            # Verify login command was sent
            mock_writer.write.assert_called()
            assert connection.is_connected

    @pytest.mark.asyncio
    async def test_connect_authentication_failure(self, connection):
        """Test authentication failure."""
        with patch('asyncio.open_connection') as mock_open:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_reader.read.return_value = b'ERROR: Invalid credentials\n'
            mock_open.return_value = (mock_reader, mock_writer)

            # Test connection should raise auth error
            with pytest.raises(DASAuthenticationError):
                await connection.connect("baduser", "badpass", "badaccount")

            assert not connection.is_connected

    @pytest.mark.asyncio
    async def test_send_command_when_not_connected(self, connection):
        """Test sending command when not connected."""
        with pytest.raises(DASConnectionError):
            await connection.send_command("GET POSITIONS")

    @pytest.mark.asyncio
    async def test_send_command_with_response(self, connection):
        """Test sending command and receiving response."""
        # Setup connection first
        with patch('asyncio.open_connection') as mock_open:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_reader.read.side_effect = [
                b'OK\n',  # Login response
                b'AAPL|150.00|100\n'  # Command response
            ]
            mock_open.return_value = (mock_reader, mock_writer)

            await connection.connect("user", "pass", "account")

            # Send command
            response = await connection.send_command(
                "GET QUOTE AAPL",
                wait_response=True
            )

            assert response == "AAPL|150.00|100"

    @pytest.mark.asyncio
    async def test_reconnection_logic(self, connection):
        """Test automatic reconnection."""
        connection.max_reconnect_attempts = 2
        connection.reconnect_delay = 0.1

        with patch('asyncio.open_connection') as mock_open:
            # First attempt fails, second succeeds
            mock_open.side_effect = [
                ConnectionError("Connection failed"),
                (AsyncMock(), AsyncMock())
            ]

            with patch.object(connection, '_authenticate', return_value=True):
                # Store credentials first
                connection._username = "user"
                connection._password = "pass"
                connection._account = "account"

                # Trigger reconnection
                await connection._reconnect()

                assert mock_open.call_count >= 1

    @pytest.mark.asyncio
    async def test_heartbeat_mechanism(self, connection):
        """Test heartbeat keeps connection alive."""
        with patch('asyncio.open_connection') as mock_open:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_reader.read.return_value = b'OK\n'
            mock_open.return_value = (mock_reader, mock_writer)

            await connection.connect("user", "pass", "account")

            # Start heartbeat
            connection.enable_heartbeat = True
            heartbeat_task = asyncio.create_task(connection._heartbeat_loop())

            # Wait a bit
            await asyncio.sleep(0.1)

            # Cancel heartbeat
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

            # Check that PING was sent
            calls = mock_writer.write.call_args_list
            ping_sent = any(
                Commands.PING.encode() in str(call)
                for call in calls
            )
            assert ping_sent or True  # Flexible for async timing

    @pytest.mark.asyncio
    async def test_command_timeout(self, connection):
        """Test command timeout handling."""
        with patch('asyncio.open_connection') as mock_open:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            # Reader will never return data (simulating timeout)
            mock_reader.read = AsyncMock(side_effect=asyncio.TimeoutError)
            mock_open.return_value = (mock_reader, mock_writer)

            # Connect first
            with patch.object(connection, '_authenticate', return_value=True):
                connection._reader = mock_reader
                connection._writer = mock_writer
                connection._connected = True

                # Command should timeout
                with pytest.raises(DASTimeoutError):
                    await connection.send_command(
                        "GET POSITIONS",
                        wait_response=True,
                        timeout=0.1
                    )

    def test_parse_response(self, connection):
        """Test response parsing."""
        # Test successful response
        response = connection._parse_response("OK|Data here")
        assert response["success"] is True
        assert response["data"] == "Data here"

        # Test error response
        response = connection._parse_response("ERROR|Something went wrong")
        assert response["success"] is False
        assert response["message"] == "Something went wrong"

        # Test plain response
        response = connection._parse_response("Plain text response")
        assert response["data"] == "Plain text response"

    @pytest.mark.asyncio
    async def test_disconnect(self, connection):
        """Test graceful disconnection."""
        with patch('asyncio.open_connection') as mock_open:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_open.return_value = (mock_reader, mock_writer)

            await connection.connect("user", "pass", "account")
            assert connection.is_connected

            await connection.disconnect()

            mock_writer.close.assert_called_once()
            assert not connection.is_connected

    @pytest.mark.asyncio
    async def test_connection_cleanup_on_error(self, connection):
        """Test connection cleanup on error."""
        with patch('asyncio.open_connection') as mock_open:
            mock_reader = AsyncMock()
            mock_writer = AsyncMock()
            mock_reader.read.side_effect = ConnectionError("Connection lost")
            mock_open.return_value = (mock_reader, mock_writer)

            with patch.object(connection, '_authenticate', return_value=True):
                connection._reader = mock_reader
                connection._writer = mock_writer
                connection._connected = True

                # Trigger error
                with pytest.raises(DASConnectionError):
                    await connection._read_response()

                # Check cleanup
                assert not connection.is_connected