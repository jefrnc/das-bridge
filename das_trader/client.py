"""Main DAS Trader API client."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, date
from decimal import Decimal

from .connection import ConnectionManager
from .orders import OrderManager, Order, OrderType, OrderSide, OrderStatus
from .positions import PositionManager, Position
from .market_data import MarketDataManager, Quote, MarketDataLevel, ChartType
from .notifications import NotificationManager
from .constants import TimeInForce, Exchange, Commands
from .exceptions import DASAPIError, DASConnectionError
from .utils import parse_decimal, validate_symbol
# Note: Importing premarket after class definition to avoid circular imports
from .indicators import TechnicalIndicators, PremarketIndicators

logger = logging.getLogger(__name__)


class DASTraderClient:
    """Main client for interacting with DAS Trader API."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9910,
        timeout: float = 30.0,
        heartbeat_interval: float = 30.0,
        auto_reconnect: bool = True,
        log_level: str = "INFO",
        notification_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize DAS Trader client.
        
        Args:
            host: DAS API host address
            port: DAS API port
            timeout: Connection timeout in seconds
            heartbeat_interval: Heartbeat interval in seconds
            auto_reconnect: Enable automatic reconnection
            log_level: Logging level
        """
        # TODO: Add support for multiple accounts
        # FIXME: Heartbeat sometimes fails silently after long periods
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        self.connection = ConnectionManager(
            host=host,
            port=port,
            timeout=timeout,
            heartbeat_interval=heartbeat_interval,
            auto_reconnect=auto_reconnect
        )
        
        self.orders = OrderManager(self.connection)
        self.positions = PositionManager(self.connection)
        self.market_data = MarketDataManager(self.connection)
        
        self.notifications = NotificationManager(notification_config or {}) if notification_config else None
        
        # Add indicators support
        self.indicators = TechnicalIndicators()
        self.premarket_indicators = PremarketIndicators()

        # Initialize premarket after to avoid circular imports
        self.premarket = None
        self.premarket_scanner = None
        self._init_premarket_components()
        
        self._short_info_cache = {}  # symbol -> short info
        self._locate_info = {}  # symbol -> locate data
        
        # TODO: implement cache expiration for short info
        
        self._register_handlers()

    def _init_premarket_components(self):
        """Initialize premarket components to avoid circular imports."""
        try:
            from .premarket import PremarketSession, PremarketScanner
            self.premarket = PremarketSession(self)
            self.premarket_scanner = PremarketScanner(self)
        except ImportError:
            # Premarket components not available
            pass
    
    def _register_handlers(self):
        # Register message handlers
        # NOTE: Order matters here - DAS sends these in specific sequence
        self.connection.register_handler("SHORT_INFO", self._handle_short_info)
        self.connection.register_handler("LOCATE_INFO", self._handle_locate_info)
        self.connection.register_handler("LOCATE_RETURN", self._handle_locate_return)
        self.connection.register_handler("LOCATE_ORDER", self._handle_locate_order)
        self.connection.register_handler("LOCATE_AVAIL", self._handle_locate_avail)
        self.connection.register_handler("LIMIT_DOWN_UP", self._handle_limit_down_up)
        self.connection.register_handler("WATCH_ORDER", self._handle_watch_order)
        self.connection.register_handler("WATCH_POSITION", self._handle_watch_position)
        self.connection.register_handler("WATCH_TRADE", self._handle_watch_trade)
        
        if self.notifications:
            self._setup_notification_callbacks()
    
    def _setup_notification_callbacks(self):
        """Setup automatic notification callbacks."""
        self.orders.register_callback("order_filled", self._on_order_filled_notification)
        self.orders.register_callback("order_rejected", self._on_order_rejected_notification)
        self.orders.register_callback("order_cancelled", self._on_order_cancelled_notification)
        
        self.positions.register_callback("position_opened", self._on_position_opened_notification)
        self.positions.register_callback("position_closed", self._on_position_closed_notification)
        self.positions.register_callback("position_updated", self._on_position_updated_notification)
    
    async def _on_order_filled_notification(self, order):
        if self.notifications:
            await self.notifications.send_order_notification(order, "filled")
    
    async def _on_order_rejected_notification(self, order):
        if self.notifications:
            await self.notifications.send_order_notification(order, "rejected")
    
    async def _on_order_cancelled_notification(self, order):
        if self.notifications:
            await self.notifications.send_order_notification(order, "cancelled")
    
    async def _on_position_opened_notification(self, position):
        if self.notifications:
            await self.notifications.send_position_notification(position, "opened")
    
    async def _on_position_closed_notification(self, position):
        if self.notifications:
            await self.notifications.send_position_notification(position, "closed")
    
    async def _on_position_updated_notification(self, position):
        if self.notifications and abs(position.pnl_percent) > 2.0:
            await self.notifications.send_position_notification(position, "updated")

    async def connect(self, username: str, password: str, account: str):
        """Connect and authenticate with DAS Trader API.
        
        Args:
            username: DAS Trader username
            password: DAS Trader password
            account: Trading account number
        """
        await self.connection.connect(username, password, account)
        
        if self.notifications:
            await self.notifications.send_notification(
                "DAS Trader Conectado",
                f"Conexión exitosa a DAS Trader API\nCuenta: {account}",
                "success"
            )
        
        await self.positions.refresh_positions()
        await self.positions.get_buying_power()
    
    async def disconnect(self):
        """Disconnect from DAS Trader API."""
        if self.notifications:
            await self.notifications.send_notification(
                "DAS Trader Desconectado",
                "Desconectado del API de DAS Trader",
                "info"
            )
        
        await self.market_data.unsubscribe_all()
        await self.connection.disconnect()
    
    @property
    def is_connected(self) -> bool:
        return self.connection.is_connected
    
    @property
    def is_authenticated(self) -> bool:
        # TODO: Add better auth check - sometimes reports true when disconnected
        return self.connection.is_authenticated
    
    async def send_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: TimeInForce = TimeInForce.DAY,
        exchange: Exchange = Exchange.AUTO,
        **kwargs
    ) -> str:
        """Send a new order.
        
        Args:
            symbol: Stock symbol
            side: Order side (BUY, SELL, SHORT, COVER)
            quantity: Number of shares
            order_type: Type of order
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            time_in_force: Order duration
            exchange: Exchange routing
            **kwargs: Additional order parameters
            
        Returns:
            Order ID
        """
        return await self.orders.send_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            exchange=exchange,
            **kwargs
        )
    
    async def send_oco_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        stop_price: float,
        target_price: float,
        time_in_force: TimeInForce = TimeInForce.GTC
    ) -> Dict[str, Any]:
        """Send OCO (One Cancels Other) order.
        
        Args:
            symbol: Stock symbol
            side: Order side
            quantity: Number of shares
            stop_price: Stop loss price
            target_price: Take profit price
            time_in_force: Time in force (GTC recommended for premarket)
            
        Returns:
            Dict with order result
        """
        return await self.orders.send_oco_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            stop_price=stop_price,
            target_price=target_price,
            time_in_force=time_in_force
        )
    
    async def cancel_order(self, order_id: str) -> bool:
        return await self.orders.cancel_order(order_id)
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all orders or all orders for a symbol."""
        # FIXME: Sometimes misses orders placed right before this call
        return await self.orders.cancel_all_orders(symbol)
    
    async def replace_order(
        self,
        order_id: str,
        new_quantity: Optional[int] = None,
        new_price: Optional[float] = None,
        new_stop_price: Optional[float] = None
    ) -> str:
        """Replace/modify an existing order."""
        return await self.orders.replace_order(
            order_id, new_quantity, new_price, new_stop_price
        )
    
    def get_orders(self, **kwargs) -> List[Order]:
        """Get orders with optional filters."""
        return self.orders.get_orders(**kwargs)

    def get_active_orders(self) -> List[Order]:
        """Get all active orders."""
        return self.orders.get_active_orders()

    async def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get pending orders using specific DAS command like short-fade-das."""
        return await self.orders.get_pending_orders()

    async def get_executed_orders(self) -> List[Dict[str, Any]]:
        """Get executed orders using specific DAS command like short-fade-das."""
        return await self.orders.get_executed_orders()

    async def get_level1_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get Level 1 market data using correct DAS format like short-fade-das."""
        return await self.market_data.get_level1_data(symbol)

    async def get_montage_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get montage data using DAS montage command."""
        return await self.market_data.get_montage_data(symbol)
    
    def get_positions(self) -> List[Position]:
        """Get all positions."""
        return self.positions.get_all_positions()
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        return self.positions.get_position(symbol)
    
    async def refresh_positions(self):
        # Force refresh from DAS
        await self.positions.refresh_positions()
    
    def get_total_pnl(self) -> Dict[str, Decimal]:
        """Get total P&L across all positions."""
        return self.positions.get_total_pnl()
    
    async def get_buying_power(self) -> Dict[str, Decimal]:
        """Get current buying power with enhanced parsing like short-fade-das."""
        try:
            response = await self.connection.send_command(
                Commands.GET_BP,
                wait_response=True,
                timeout=5.0
            )

            if response:
                # Use enhanced buying power parsing
                from .utils import parse_buying_power_response
                bp_data = parse_buying_power_response(str(response))

                if bp_data.get("success"):
                    buying_power = bp_data.get("buying_power", Decimal("0"))
                    return {
                        "buying_power": buying_power,
                        "day_trading_bp": buying_power,
                        "overnight_bp": buying_power,
                    }

            # Fallback to original method
            return await self.positions.get_buying_power()

        except Exception as e:
            logger.error(f"Failed to get buying power: {e}")
            # Fallback to original method
            return await self.positions.get_buying_power()

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information from DAS Trader.

        Returns:
            Dict with account details like account_id, account_type, etc.
        """
        try:
            response = await self.connection.send_command(
                Commands.GET_ACCOUNT_INFO,
                wait_response=True,
                timeout=5.0
            )

            if response:
                # DAS returns account info in multiple formats
                # Parse the response into a structured dict
                return {
                    "account_id": self.connection._account if hasattr(self.connection, '_account') else None,
                    "account_type": response.get("account_type", "N/A"),
                    "raw_response": response
                }

            return {
                "account_id": self.connection._account if hasattr(self.connection, '_account') else None,
                "account_type": "N/A"
            }

        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {
                "account_id": self.connection._account if hasattr(self.connection, '_account') else None,
                "account_type": "N/A",
                "error": str(e)
            }

    async def subscribe_quote(
        self,
        symbol: str,
        level: MarketDataLevel = MarketDataLevel.LEVEL1
    ):
        """Subscribe to market data for a symbol."""
        await self.market_data.subscribe_quote(symbol, level)
    
    async def unsubscribe_quote(
        self,
        symbol: str,
        level: MarketDataLevel = MarketDataLevel.LEVEL1
    ):
        """Unsubscribe from market data for a symbol."""
        await self.market_data.unsubscribe_quote(symbol, level)
    
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get current quote for a symbol."""
        return await self.market_data.get_quote(symbol)
    
    async def get_chart_data(
        self,
        symbol: str,
        chart_type: ChartType,
        **kwargs
    ) -> List[Any]:
        """Get historical chart data."""
        return await self.market_data.get_chart_data(
            symbol, chart_type, **kwargs
        )
    
    async def get_short_info(self, symbol: str) -> Dict[str, Any]:
        """Get short sale information for a symbol.
        
        Returns:
            Dict with:
            - shortable: bool
            - rate: Decimal (borrow rate)
            - available_shares: int
        """
        if not validate_symbol(symbol):
            raise DASAPIError(f"Invalid symbol: {symbol}")
        
        symbol = symbol.upper()
        
        if symbol in self._short_info_cache:
            cache_entry = self._short_info_cache[symbol]
            if (datetime.now() - cache_entry["timestamp"]).seconds < 300:
                return cache_entry["data"]
        
        try:
            command = f"{Commands.GET_SHORT_INFO} {symbol}"
            response = await self.connection.send_command(
                command,
                wait_response=True,
                response_type="SHORT_INFO"
            )
            
            if response and response.get("type") == "SHORT_INFO":
                short_info = {
                    "shortable": response.get("shortable", False),
                    "rate": response.get("rate", Decimal("0")),
                    "available_shares": response.get("available_shares", 0),
                }
                
                self._short_info_cache[symbol] = {
                    "data": short_info,
                    "timestamp": datetime.now()
                }
                
                return short_info
            
            return {"shortable": False, "rate": Decimal("0"), "available_shares": 0}
            
        except Exception as e:
            logger.error(f"Failed to get short info for {symbol}: {e}")
            return {"shortable": False, "rate": Decimal("0"), "available_shares": 0}
    
    async def inquire_locate_price(self, symbol: str, quantity: int, route: str = "ALLROUTE") -> Dict[str, Any]:
        if not validate_symbol(symbol):
            raise DASAPIError(f"Invalid symbol: {symbol}")
        
        symbol = symbol.upper()
        
        try:
            command = f"{Commands.LOCATE_INQUIRE} {symbol} {quantity} {route}"
            response = await self.connection.send_command(
                command,
                wait_response=True,
                response_type="LOCATE_RETURN"
            )
            
            if response and response.get("type") == "LOCATE_RETURN":
                return {
                    "symbol": response.get("symbol", symbol),
                    "quantity": response.get("quantity", quantity),
                    "rate": response.get("rate", Decimal("0")),
                    "available": response.get("available", False),
                    "route": response.get("route", route),
                }
            
            return {"symbol": symbol, "quantity": quantity, "available": False, "rate": Decimal("0")}
            
        except Exception as e:
            logger.error(f"Failed to inquire locate price for {symbol}: {e}")
            raise DASAPIError(f"Failed to inquire locate price: {e}")

    async def locate_stock(self, symbol: str, quantity: int, route: str = "AUTO") -> Dict[str, Any]:
        """Request a short locate for a symbol.
        
        Args:
            symbol: Stock symbol
            quantity: Number of shares to locate
            route: Specific route for locate
        
        Returns:
            Dict with:
            - located: bool
            - quantity: int
            - rate: Decimal
            - locate_id: str
        """
        # TODO: Add locate caching to avoid repeated requests
        # NOTE: Some brokers have daily locate limits
        if not validate_symbol(symbol):
            raise DASAPIError(f"Invalid symbol: {symbol}")
        
        symbol = symbol.upper()
        
        try:
            command = f"{Commands.LOCATE_STOCK} {symbol} {quantity} {route}"
            response = await self.connection.send_command(
                command,
                wait_response=True,
                response_type="LOCATE_ORDER"
            )
            
            if response and response.get("type") == "LOCATE_ORDER":
                locate_info = {
                    "located": response.get("located", False),
                    "quantity": response.get("quantity", 0),
                    "rate": response.get("rate", Decimal("0")),
                    "locate_id": response.get("locate_id", ""),
                    "route": response.get("route", route),
                }
                
                if locate_info["located"]:
                    self._locate_info[symbol] = locate_info
                
                return locate_info
            
            return {"located": False, "quantity": 0, "rate": Decimal("0"), "locate_id": ""}
            
        except Exception as e:
            logger.error(f"Failed to locate stock {symbol}: {e}")
            raise DASAPIError(f"Failed to locate stock: {e}")
    
    async def cancel_locate_order(self, locate_order_id: str) -> bool:
        """Cancel a locate order.
        
        Args:
            locate_order_id: The locate order ID to cancel
            
        Returns:
            True if successfully cancelled
        """
        try:
            command = f"{Commands.LOCATE_CANCEL} {locate_order_id}"
            response = await self.connection.send_command(
                command,
                wait_response=True,
                response_type="LOCATE_ORDER"
            )
            
            if response and response.get("type") != "ERROR":
                logger.info(f"Locate order cancelled: {locate_order_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cancel locate order {locate_order_id}: {e}")
            return False
    
    async def accept_locate_offer(self, locate_order_id: str, accept: bool = True) -> bool:
        """Accept or reject a locate offer.
        
        Args:
            locate_order_id: The locate order ID
            accept: True to accept, False to reject
            
        Returns:
            True if operation successful
        """
        try:
            action = "Accept" if accept else "Reject"
            command = f"{Commands.LOCATE_ACCEPT} {locate_order_id} {action}"
            response = await self.connection.send_command(
                command,
                wait_response=True,
                response_type="LOCATE_ORDER"
            )
            
            if response and response.get("type") != "ERROR":
                logger.info(f"Locate offer {action.lower()}ed: {locate_order_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to {action.lower()} locate offer {locate_order_id}: {e}")
            return False
    
    async def query_available_locate(self, account: str, symbol: str) -> Dict[str, Any]:
        """Query available locate shares for an account and symbol.
        
        Args:
            account: Trading account
            symbol: Stock symbol
            
        Returns:
            Dict with available locate information
        """
        if not validate_symbol(symbol):
            raise DASAPIError(f"Invalid symbol: {symbol}")
        
        symbol = symbol.upper()
        
        try:
            command = f"{Commands.LOCATE_QUERY} {account} {symbol}"
            response = await self.connection.send_command(
                command,
                wait_response=True,
                response_type="LOCATE_AVAIL"
            )
            
            if response and response.get("type") == "LOCATE_AVAIL":
                return {
                    "symbol": response.get("symbol", symbol),
                    "available_shares": response.get("available_shares", 0),
                    "rate": response.get("rate", Decimal("0")),
                    "account": response.get("account", account),
                }
            
            return {"symbol": symbol, "available_shares": 0, "rate": Decimal("0"), "account": account}
            
        except Exception as e:
            logger.error(f"Failed to query available locate for {symbol}: {e}")
            return {"symbol": symbol, "available_shares": 0, "rate": Decimal("0"), "account": account}
    
    async def get_locate_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get existing locate information for a symbol."""
        symbol = symbol.upper()
        
        if symbol in self._locate_info:
            return self._locate_info[symbol]
        
        try:
            command = f"{Commands.GET_LOCATE_INFO} {symbol}"
            response = await self.connection.send_command(
                command,
                wait_response=True,
                response_type="LOCATE_INFO"
            )
            
            if response and response.get("type") == "LOCATE_INFO":
                return {
                    "located": response.get("located", False),
                    "quantity": response.get("quantity", 0),
                    "rate": response.get("rate", Decimal("0")),
                    "locate_id": response.get("locate_id", ""),
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get locate info for {symbol}: {e}")
            return None
    
    async def execute_script(
        self,
        window_name: str,
        script_command: str,
        global_script: bool = False
    ) -> bool:
        """Execute a DAS script.
        
        Args:
            window_name: Target window name (or "GLOBALSCRIPT" for global)
            script_command: Script command to execute
            global_script: If True, execute as global script
            
        Returns:
            True if successful
            
        Examples:
            await client.execute_script("Montage1", "SYMBOL MSFT")
            await client.execute_script("GLOBALSCRIPT", "SwitchDesktop default", True)
        """
        try:
            if global_script:
                command = f"{Commands.GLOBAL_SCRIPT} {script_command}"
            else:
                command = f"{Commands.SCRIPT} {window_name} {script_command}"
            
            response = await self.connection.send_command(
                command,
                wait_response=False
            )
            
            logger.info(f"Script executed: {script_command}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute script '{script_command}': {e}")
            return False
    
    async def change_montage_symbol(self, window_name: str, symbol: str) -> bool:
        """Change symbol in a montage window.
        
        Args:
            window_name: Name of the montage window
            symbol: New symbol to display
            
        Returns:
            True if successful
        """
        return await self.execute_script(window_name, f"SYMBOL {symbol.upper()}")
    
    async def switch_desktop(self, desktop_name: str) -> bool:
        """Switch to a different desktop layout.
        
        Args:
            desktop_name: Name of the desktop to switch to
            
        Returns:
            True if successful
        """
        return await self.execute_script("GLOBALSCRIPT", f"SwitchDesktop {desktop_name}", True)
    
    def on_order_update(self, callback: Callable):
        """Register callback for order updates."""
        self.orders.register_callback("order_new", callback)
        self.orders.register_callback("order_filled", callback)
        self.orders.register_callback("order_partially_filled", callback)
        self.orders.register_callback("order_cancelled", callback)
        self.orders.register_callback("order_rejected", callback)
    
    def on_position_update(self, callback: Callable):
        """Register callback for position updates."""
        self.positions.register_callback("position_updated", callback)
    
    def on_quote_update(self, callback: Callable):
        """Register callback for quote updates."""
        self.market_data.register_callback("quote_update", callback)
    
    def on_level2_update(self, callback: Callable):
        """Register callback for Level 2 updates."""
        self.market_data.register_callback("level2_update", callback)
    
    def on_time_sales(self, callback: Callable):
        """Register callback for time and sales."""
        self.market_data.register_callback("time_sales", callback)
    
    async def send_notification(
        self,
        title: str,
        message: str,
        level: str = "info",
        data: Optional[Dict[str, Any]] = None
    ):
        """Send a custom notification."""
        if self.notifications:
            await self.notifications.send_notification(title, message, level, data)
    
    async def send_alert(self, symbol: str, price: float, condition: str):
        """Send a price alert notification."""
        if self.notifications:
            await self.notifications.send_alert(symbol, price, condition)
    
    def configure_notifications(self, config: Dict[str, Any]):
        """Configure or reconfigure notifications."""
        self.notifications = NotificationManager(config)
        self._setup_notification_callbacks()
    
    def enable_notifications(self):
        """Enable notifications if they were previously disabled."""
        if self.notifications:
            self.notifications.enabled = True
    
    def disable_notifications(self):
        """Disable notifications temporarily."""
        if self.notifications:
            self.notifications.enabled = False
    
    async def _handle_short_info(self, message: Dict[str, Any]):
        symbol = message.get("symbol")
        if symbol:
            self._short_info_cache[symbol] = {
                "data": {
                    "shortable": message.get("shortable", False),
                    "rate": message.get("rate", Decimal("0")),
                    "available_shares": message.get("available_shares", 0),
                },
                "timestamp": datetime.now()
            }
    
    async def _handle_locate_info(self, message: Dict[str, Any]):
        symbol = message.get("symbol")
        if symbol and message.get("located"):
            self._locate_info[symbol] = {
                "located": True,
                "quantity": message.get("quantity", 0),
                "rate": message.get("rate", Decimal("0")),
                "locate_id": message.get("locate_id", ""),
            }
    
    async def _handle_locate_return(self, message: Dict[str, Any]):
        pass
    
    async def _handle_locate_order(self, message: Dict[str, Any]):
        pass
    
    async def _handle_locate_avail(self, message: Dict[str, Any]):
        pass
    
    async def _handle_limit_down_up(self, message: Dict[str, Any]):
        pass
    
    async def _handle_watch_order(self, message: Dict[str, Any]):
        pass
    
    async def _handle_watch_position(self, message: Dict[str, Any]):
        pass
    
    async def _handle_watch_trade(self, message: Dict[str, Any]):
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()