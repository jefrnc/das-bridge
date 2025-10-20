"""Connection management for DAS Trader API."""

import asyncio
import logging
import socket
import ssl
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta
import json

from .constants import (
    DEFAULT_HOST, DEFAULT_PORT, DEFAULT_TIMEOUT,
    DEFAULT_HEARTBEAT_INTERVAL, DEFAULT_RECONNECT_DELAY,
    MAX_RECONNECT_ATTEMPTS, BUFFER_SIZE, MESSAGE_DELIMITER,
    Commands, MessagePrefix
)
from .exceptions import (
    DASConnectionError, DASAuthenticationError,
    DASTimeoutError, DASAPIError
)
from .utils import parse_message

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages TCP connection to DAS Trader API."""
    
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL,
        auto_reconnect: bool = True,
        use_ssl: bool = False
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.heartbeat_interval = heartbeat_interval
        self.auto_reconnect = auto_reconnect
        self.use_ssl = use_ssl
        
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._authenticated = False
        self._running = False
        
        self._username: Optional[str] = None
        self._password: Optional[str] = None
        self._account: Optional[str] = None
        
        self._msg_q = asyncio.Queue()  # incoming messages
        self._response_futures = {}  # pending responses
        self._message_handlers = {}
        
        self._reader_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        
        self._last_heartbeat = datetime.now()
        self._reconnect_attempts = 0
        
        self._order_server_connected = False
        self._quote_server_connected = False
        
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        # TODO: Add handler for ACCOUNT_UPDATE messages
        self.register_handler("ERROR", self._handle_error_message)
        self.register_handler("WARNING", self._handle_warning_message)
        self.register_handler("INFO", self._handle_info_message)
        self.register_handler("CONNECTION_STATUS", self._handle_connection_status)
        # FIXME: CONNECTION_STATUS sometimes not received on reconnect
    
    async def connect(self, username: str, password: str, account: str, watch_mode: bool = False):
        """Connect and authenticate with DAS Trader API."""
        # NOTE: watch_mode not fully implemented yet
        self._username = username
        self._password = password
        self._account = account
        self._watch_mode = watch_mode

        try:
            await self._establish_connection()
            # Start background tasks BEFORE authentication so message reader can receive LOGIN response
            self._start_background_tasks()
            await self._authenticate()
            logger.info(f"Successfully connected to DAS Trader API at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to DAS Trader API: {e}")
            await self.disconnect()
            raise
    
    async def _establish_connection(self):
        try:
            if self.use_ssl:
                ssl_context = ssl.create_default_context()
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(
                        self.host, self.port,
                        ssl=ssl_context
                    ),
                    timeout=self.timeout
                )
            else:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=self.timeout
                )
            
            self._connected = True
            self._reconnect_attempts = 0
            
        except asyncio.TimeoutError:
            raise DASTimeoutError(f"Connection timeout to {self.host}:{self.port}")
        except socket.error as e:
            raise DASConnectionError(f"Socket error: {e}")
        except Exception as e:
            raise DASConnectionError(f"Failed to establish connection: {e}")
    
    async def _authenticate(self):
        watch_flag = "1" if hasattr(self, '_watch_mode') and self._watch_mode else "0"
        login_cmd = f"{Commands.LOGIN} {self._username} {self._password} {self._account} {watch_flag}"

        try:
            response = await self.send_command(login_cmd, wait_response=True, response_type="LOGIN")

            if response.get("type") == "ERROR":
                raise DASAuthenticationError(f"Authentication failed: {response.get('message', 'Unknown error')}")

            if response.get("type") == "LOGIN":
                if not response.get("success", False):
                    raise DASAuthenticationError(f"Authentication failed: {response.get('message', 'Login failed')}")

            self._authenticated = True
            logger.info("Successfully authenticated with DAS Trader API")

            await self._check_connection_status()

        except Exception as e:
            self._authenticated = False
            raise DASAuthenticationError(f"Authentication failed: {e}")
    
    async def _check_connection_status(self):
        try:
            response = await self.send_command(Commands.CHECK_CONNECTION, wait_response=True)
            
            if response.get("type") == "CONNECTION_STATUS":
                self._order_server_connected = response.get("order_server", False)
                self._quote_server_connected = response.get("quote_server", False)
                
                logger.info(f"Connection status - Order Server: {self._order_server_connected}, "
                          f"Quote Server: {self._quote_server_connected}")
                
                if not self._order_server_connected:
                    logger.warning("Order server is not connected. Trading operations may fail.")
                if not self._quote_server_connected:
                    logger.warning("Quote server is not connected. Market data may be unavailable.")
                    
        except Exception as e:
            logger.error(f"Failed to check connection status: {e}")
    
    def _start_background_tasks(self):
        self._running = True
        self._reader_task = asyncio.create_task(self._read_messages())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def _read_messages(self):
        buffer = ""
        
        while self._running and self._connected:
            try:
                if not self._reader:
                    await asyncio.sleep(0.1)
                    continue
                
                try:
                    data = await asyncio.wait_for(
                        self._reader.read(BUFFER_SIZE),
                        timeout=1.0
                    )
                except (ConnectionResetError, ConnectionAbortedError) as e:
                    logger.error(f"Connection lost: {e}")
                    await self._handle_disconnect()
                    break
                except ssl.SSLError as e:
                    logger.error(f"SSL error: {e}")
                    await self._handle_disconnect()
                    break
                
                if not data:
                    logger.warning("Connection closed by server")
                    await self._handle_disconnect()
                    break
                
                try:
                    buffer += data.decode('utf-8', errors='replace')
                except UnicodeDecodeError as e:
                    logger.error(f"Unicode decode error: {e}")
                    continue
                
                if len(buffer) > BUFFER_SIZE * 10:
                    logger.warning("Buffer overflow, clearing buffer")
                    buffer = buffer[-BUFFER_SIZE:]
                    # TODO: Better buffer management needed here
                
                while MESSAGE_DELIMITER in buffer:
                    message, buffer = buffer.split(MESSAGE_DELIMITER, 1)
                    if message.strip():
                        try:
                            await self._process_message(message.strip())
                        except Exception as e:
                            logger.error(f"Error processing message '{message[:100]}...': {e}")
                        
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Unexpected error in message reader: {e}")
                await self._handle_disconnect()
                break
    
    async def _process_message(self, message: str):
        try:
            logger.debug(f"Received message: {message}")
            # logger.debug(f"RAW MSG: {repr(message)}")  # detailed debug
            
            parsed = parse_message(message)
            msg_type = parsed.get("type")
            
            if msg_type in self._response_futures:
                future = self._response_futures.pop(msg_type)
                if not future.done():
                    future.set_result(parsed)
            
            if msg_type in self._message_handlers:
                handler = self._message_handlers[msg_type]
                if asyncio.iscoroutinefunction(handler):
                    await handler(parsed)
                else:
                    handler(parsed)
            
            await self._msg_q.put(parsed)
            
        except Exception as e:
            logger.error(f"Error processing message '{message}': {e}")
    
    async def _heartbeat_loop(self):
        while self._running and self._connected:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                await self.send_command("PING", wait_response=False)
                self._last_heartbeat = datetime.now()
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
    
    async def send_command(
        self,
        command: str,
        wait_response: bool = False,
        response_type: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Send a command to DAS Trader API."""
        if not self._connected:
            raise DASConnectionError("Not connected to DAS Trader API")

        # Allow LOGIN command even when not authenticated
        if not self._authenticated and not command.startswith(Commands.LOGIN):
            raise DASAuthenticationError("Not authenticated with DAS Trader API")
        
        try:
            message = f"{command}{MESSAGE_DELIMITER}"
            self._writer.write(message.encode('utf-8'))
            await self._writer.drain()
            
            logger.debug(f"Sent command: {command}")
            
            if wait_response:
                response_type = response_type or command.split()[0]
                future = asyncio.Future()
                self._response_futures[response_type] = future
                
                timeout = timeout or self.timeout
                response = await asyncio.wait_for(future, timeout=timeout)
                return response
            
            return None
            
        except asyncio.TimeoutError:
            if response_type in self._response_futures:
                del self._response_futures[response_type]
            raise DASTimeoutError(f"Timeout waiting for response to command: {command}")
        except Exception as e:
            raise DASAPIError(f"Failed to send command: {e}")
    
    async def get_message(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Get next message from the message queue."""
        try:
            if timeout:
                return await asyncio.wait_for(self._message_queue.get(), timeout=timeout)
            else:
                return await self._message_queue.get()
        except asyncio.TimeoutError:
            return None
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for specific message types."""
        self._message_handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")
    
    def unregister_handler(self, message_type: str):
        """Unregister a handler for specific message types."""
        if message_type in self._message_handlers:
            del self._message_handlers[message_type]
            logger.debug(f"Unregistered handler for message type: {message_type}")
    
    async def _handle_disconnect(self):
        self._connected = False
        self._authenticated = False
        
        if self.auto_reconnect and self._running:
            logger.info("Attempting to reconnect...")
            self._reconnect_task = asyncio.create_task(self._auto_reconnect())
    
    async def _auto_reconnect(self):
        import random
        
        base_delay = DEFAULT_RECONNECT_DELAY
        
        while self._running and self._reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
            try:
                self._reconnect_attempts += 1
                delay = min(base_delay * (2 ** (self._reconnect_attempts - 1)), 60)
                jitter = random.uniform(0, 0.1) * delay
                actual_delay = delay + jitter
                
                logger.info(f"Reconnect attempt {self._reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS} "
                          f"in {actual_delay:.1f} seconds...")
                
                await asyncio.sleep(actual_delay)
                
                await self._cleanup_connection()
                
                await self.connect(self._username, self._password, self._account, 
                                 getattr(self, '_watch_mode', False))
                
                logger.info("Successfully reconnected to DAS Trader API")
                return
                
            except DASAuthenticationError as e:
                logger.error(f"Authentication failed during reconnect: {e}")
                break
            except Exception as e:
                logger.error(f"Reconnection attempt {self._reconnect_attempts} failed: {e}")
        
        logger.error(f"Failed to reconnect after {MAX_RECONNECT_ATTEMPTS} attempts")
        self._running = False
    
    async def _cleanup_connection(self):
        try:
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
        except Exception:
            pass
        
        self._reader = None
        self._writer = None
        self._connected = False
        self._authenticated = False
    
    async def disconnect(self):
        """Disconnect from DAS Trader API."""
        self._running = False
        
        tasks = [self._reader_task, self._heartbeat_task, self._reconnect_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        if self._connected and self._authenticated:
            try:
                await self.send_command(Commands.LOGOUT, wait_response=False)
            except Exception:
                pass
        
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        
        self._connected = False
        self._authenticated = False
        self._reader = None
        self._writer = None
        
        logger.info("Disconnected from DAS Trader API")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to DAS API."""
        return self._connected
    
    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated with DAS API."""
        return self._authenticated
    
    @property
    def order_server_connected(self) -> bool:
        """Check if Order Server is connected."""
        return self._order_server_connected
    
    @property
    def quote_server_connected(self) -> bool:
        """Check if Quote Server is connected."""
        return self._quote_server_connected
    
    async def _handle_error_message(self, message: Dict[str, Any]):
        error_msg = message.get("message", "Unknown error")
        logger.error(f"Server error: {error_msg}")
    
    async def _handle_warning_message(self, message: Dict[str, Any]):
        warning_msg = message.get("message", "Unknown warning")
        logger.warning(f"Server warning: {warning_msg}")
    
    async def _handle_info_message(self, message: Dict[str, Any]):
        info_msg = message.get("message", "Unknown info")
        logger.info(f"Server info: {info_msg}")
    
    async def _handle_connection_status(self, message: Dict[str, Any]):
        self._order_server_connected = message.get("order_server", False)
        self._quote_server_connected = message.get("quote_server", False)