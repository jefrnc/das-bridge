"""Order management for DAS Trader API."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from collections import defaultdict
import threading

from .constants import (
    OrderType, OrderSide, OrderStatus, TimeInForce,
    Exchange, Commands, MessagePrefix
)
from .exceptions import DASOrderError, DASInvalidSymbolError
from .utils import (
    generate_order_id, format_price, format_quantity,
    validate_symbol, parse_decimal
)

logger = logging.getLogger(__name__)


@dataclass
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    status: OrderStatus = OrderStatus.PENDING
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    exchange: Exchange = Exchange.AUTO
    filled_quantity: int = 0
    avg_fill_price: Optional[Decimal] = None
    remaining_quantity: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    fills: List[Dict[str, Any]] = field(default_factory=list)
    reject_reason: Optional[str] = None
    client_order_id: Optional[str] = None
    trail_amount: Optional[Decimal] = None
    trail_percent: Optional[float] = None
    peg_offset: Optional[Decimal] = None
    hidden_size: Optional[int] = None
    display_size: Optional[int] = None
    
    def __post_init__(self):
        self.remaining_quantity = self.quantity - self.filled_quantity
    
    def update_status(self, status: OrderStatus, reason: Optional[str] = None):
        self.status = status
        self.updated_at = datetime.now()
        if reason:
            self.reject_reason = reason
            # TODO: parse common reject reasons for better handling
    
    def add_fill(self, fill_qty: int, fill_price: Decimal):
        self.fills.append({
            "quantity": fill_qty,
            "price": fill_price,
            "timestamp": datetime.now()
        })
        
        self.filled_quantity += fill_qty
        self.remaining_quantity = self.quantity - self.filled_quantity
        
        # Calculate average fill price
        total_value = sum(f["quantity"] * f["price"] for f in self.fills)
        self.avg_fill_price = total_value / self.filled_quantity if self.filled_quantity > 0 else Decimal("0")
        # FIXME: This doesn't handle partial cancels correctly
        
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED
        
        self.updated_at = datetime.now()
    
    def is_active(self) -> bool:
        return self.status in [
            OrderStatus.PENDING,
            OrderStatus.NEW,
            OrderStatus.PARTIALLY_FILLED
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "price": float(self.price) if self.price else None,
            "stop_price": float(self.stop_price) if self.stop_price else None,
            "time_in_force": self.time_in_force.value,
            "exchange": self.exchange.value,
            "filled_quantity": self.filled_quantity,
            "avg_fill_price": float(self.avg_fill_price) if self.avg_fill_price else None,
            "remaining_quantity": self.remaining_quantity,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "fills": self.fills,
            "reject_reason": self.reject_reason,
            "client_order_id": self.client_order_id,
        }


class OrderManager:
    """Manages orders and order-related operations."""
    
    def __init__(self, connection_manager):
        self.connection = connection_manager
        self._orders: Dict[str, Order] = {}
        self._symbol_orders: Dict[str, List[str]] = defaultdict(list)
        self._order_lock = threading.RLock()
        
        self._order_callbacks: Dict[str, List[Callable]] = {
            "order_new": [],
            "order_filled": [],
            "order_partially_filled": [],
            "order_cancelled": [],
            "order_rejected": [],
            "order_replaced": [],
        }
        
        self._register_handlers()
    
    def _register_handlers(self):
        self.connection.register_handler("ORDER", self._handle_order_message)
        self.connection.register_handler("ORDER_ACTION", self._handle_order_action)
    
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
        client_order_id: Optional[str] = None,
        trail_amount: Optional[float] = None,
        trail_percent: Optional[float] = None,
        peg_offset: Optional[float] = None,
        hidden_size: Optional[int] = None,
        display_size: Optional[int] = None,
    ) -> str:
        """Send a new order to DAS Trader."""
        if not validate_symbol(symbol):
            raise DASInvalidSymbolError(f"Invalid symbol: {symbol}")
        
        if quantity <= 0:
            raise DASOrderError("Quantity must be greater than 0")
        
        MAX_POSITION_SIZE = getattr(self, 'max_position_size', 10000)
        if quantity > MAX_POSITION_SIZE:
            raise DASOrderError(f"Quantity {quantity} exceeds maximum position size {MAX_POSITION_SIZE}")
        
        if price is not None:
            if price <= 0:
                raise DASOrderError("Price must be greater than 0")
            if price > 999999:
                raise DASOrderError("Price exceeds reasonable limit")
        
        if stop_price is not None:
            if stop_price <= 0:
                raise DASOrderError("Stop price must be greater than 0")
            if price and stop_price:
                if side in [OrderSide.BUY] and stop_price > price:
                    raise DASOrderError("Stop price cannot be above limit price for buy orders")
                elif side in [OrderSide.SELL, OrderSide.SHORT] and stop_price < price:
                    raise DASOrderError("Stop price cannot be below limit price for sell orders")
        
        if order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and price is None:
            raise DASOrderError(f"{order_type.value} order requires a price")
        
        if order_type in [OrderType.STOP, OrderType.STOP_LIMIT, OrderType.STOP_TRAILING] and stop_price is None and trail_amount is None:
            raise DASOrderError(f"{order_type.value} order requires a stop price or trail amount")
        
        if trail_amount is not None and trail_amount <= 0:
            raise DASOrderError("Trail amount must be greater than 0")
        
        if trail_percent is not None and (trail_percent <= 0 or trail_percent >= 100):
            raise DASOrderError("Trail percent must be between 0 and 100")
        
        order_id = client_order_id or generate_order_id()
        
        order = Order(
            order_id=order_id,
            symbol=symbol.upper(),
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=parse_decimal(price) if price else None,
            stop_price=parse_decimal(stop_price) if stop_price else None,
            time_in_force=time_in_force,
            exchange=exchange,
            client_order_id=client_order_id,
            trail_amount=parse_decimal(trail_amount) if trail_amount else None,
            trail_percent=trail_percent,
            peg_offset=parse_decimal(peg_offset) if peg_offset else None,
            hidden_size=hidden_size,
            display_size=display_size,
        )
        
        cmd_parts = [
            Commands.NEW_ORDER,
            order_id,
            symbol.upper(),
            side.value,
            format_quantity(quantity),
            order_type.value,
            time_in_force.value,
            exchange.value,
        ]
        
        if price is not None:
            cmd_parts.append(f"PRICE={format_price(price)}")
        
        if stop_price is not None:
            cmd_parts.append(f"STOPPRICE={format_price(stop_price)}")
        
        if trail_amount is not None:
            cmd_parts.append(f"TRAILAMT={format_price(trail_amount)}")
        
        if trail_percent is not None:
            cmd_parts.append(f"TRAILPCT={trail_percent}")
        
        if peg_offset is not None:
            cmd_parts.append(f"PEGOFFSET={format_price(peg_offset)}")
        
        if hidden_size is not None:
            cmd_parts.append(f"HIDDEN={hidden_size}")
        
        if display_size is not None:
            cmd_parts.append(f"DISPLAY={display_size}")
        
        command = " ".join(cmd_parts)
        
        with self._order_lock:
            self._orders[order_id] = order
            self._symbol_orders[symbol.upper()].append(order_id)
        
        try:
            response = await self.connection.send_command(
                command,
                wait_response=True,
                response_type="ORDER_ACTION"
            )
            
            if response and response.get("type") == "ERROR":
                order.update_status(OrderStatus.REJECTED, response.get("message"))
                raise DASOrderError(f"Order rejected: {response.get('message')}")
            
            logger.info(f"Order sent successfully: {order_id}")
            return order_id
            
        except Exception as e:
            with self._order_lock:
                order.update_status(OrderStatus.REJECTED, str(e))
            raise DASOrderError(f"Failed to send order: {e}")
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a specific order."""
        with self._order_lock:
            order = self._orders.get(order_id)
            if not order:
                raise DASOrderError(f"Order not found: {order_id}")
            
            if not order.is_active():
                raise DASOrderError(f"Order is not active: {order_id} (status: {order.status.value})")
        
        try:
            command = f"{Commands.CANCEL_ORDER} {order_id}"
            response = await self.connection.send_command(
                command,
                wait_response=True,
                response_type="ORDER_ACTION"
            )
            
            if response and response.get("type") == "ERROR":
                raise DASOrderError(f"Cancel failed: {response.get('message')}")
            
            logger.info(f"Cancel request sent for order: {order_id}")
            return True
            
        except Exception as e:
            raise DASOrderError(f"Failed to cancel order: {e}")
    
    async def send_oco_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        stop_price: float,
        target_price: float,
        time_in_force: TimeInForce = TimeInForce.DAY
    ) -> Dict[str, Any]:
        """Send an OCO (One Cancels Other) order.
        
        OCO orders in DAS consist of a stop loss and a take profit order
        where execution of one automatically cancels the other.
        
        Args:
            symbol: Stock symbol
            side: Order side (BUY or SELL)
            quantity: Number of shares
            stop_price: Stop loss price
            target_price: Take profit price (limit)
            time_in_force: Order time in force
            
        Returns:
            Dict with order_ids and success status
        """
        try:
            # Validate inputs
            if not validate_symbol(symbol):
                raise DASOrderError(f"Invalid symbol: {symbol}")
            
            symbol = symbol.upper()
            
            # For OCO, we need to send a special command
            # Format: NEWORDER symbol side qty OCO stop_price target_price route TIF
            route = "ARCA"  # Default route, could be made configurable
            
            # Determine OCO side based on position side
            if side == OrderSide.BUY:
                # If buying, OCO will be sell orders
                oco_side = "S"
            else:
                # If selling/short, OCO will be buy orders  
                oco_side = "B"
            
            command = (
                f"NEWORDER {symbol} {oco_side} {quantity} OCO "
                f"{stop_price:.2f} {target_price:.2f} {route} {time_in_force.value}"
            )
            
            response = await self.connection.send_command(
                command,
                wait_response=True,
                response_type="ORDER_ACTION"
            )
            
            if response and response.get("type") == "ERROR":
                raise DASOrderError(f"OCO order rejected: {response.get('message')}")
            
            # Parse response to get order IDs
            order_ids = []
            if response and "order_id" in response:
                order_ids = response.get("order_id", [])
            
            logger.info(f"OCO order sent: {symbol} - Stop: ${stop_price:.2f}, Target: ${target_price:.2f}")
            
            return {
                "success": True,
                "order_ids": order_ids,
                "symbol": symbol,
                "stop_price": stop_price,
                "target_price": target_price
            }
            
        except Exception as e:
            logger.error(f"Failed to send OCO order: {e}")
            return {
                "success": False,
                "error": str(e),
                "order_ids": []
            }
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all orders or all orders for a specific symbol."""
        if symbol:
            command = f"{Commands.CANCEL_ALL} {symbol.upper()}"
            
            with self._order_lock:
                order_ids = self._symbol_orders.get(symbol.upper(), [])
                active_count = sum(1 for oid in order_ids 
                                 if self._orders[oid].is_active())
        else:
            command = Commands.CANCEL_ALL
            
            with self._order_lock:
                active_count = sum(1 for order in self._orders.values() 
                                 if order.is_active())
        
        try:
            response = await self.connection.send_command(
                command,
                wait_response=True,
                response_type="ORDER_ACTION"
            )
            
            if response and response.get("type") == "ERROR":
                raise DASOrderError(f"Cancel all failed: {response.get('message')}")
            
            logger.info(f"Cancel all request sent. Expected cancellations: {active_count}")
            return active_count
            
        except Exception as e:
            raise DASOrderError(f"Failed to cancel all orders: {e}")
    
    async def replace_order(
        self,
        order_id: str,
        new_quantity: Optional[int] = None,
        new_price: Optional[float] = None,
        new_stop_price: Optional[float] = None
    ) -> str:
        """Replace/modify an existing order."""
        with self._order_lock:
            order = self._orders.get(order_id)
            if not order:
                raise DASOrderError(f"Order not found: {order_id}")
            
            if not order.is_active():
                raise DASOrderError(f"Order is not active: {order_id}")
        
        cmd_parts = [Commands.REPLACE_ORDER, order_id]
        
        if new_quantity is not None:
            if new_quantity <= order.filled_quantity:
                raise DASOrderError("New quantity must be greater than filled quantity")
            cmd_parts.append(f"QTY={format_quantity(new_quantity)}")
        
        if new_price is not None:
            cmd_parts.append(f"PRICE={format_price(new_price)}")
        
        if new_stop_price is not None:
            cmd_parts.append(f"STOPPRICE={format_price(new_stop_price)}")
        
        if len(cmd_parts) == 2:
            raise DASOrderError("No modifications specified")
        
        command = " ".join(cmd_parts)
        
        try:
            response = await self.connection.send_command(
                command,
                wait_response=True,
                response_type="ORDER_ACTION"
            )
            
            if response and response.get("type") == "ERROR":
                raise DASOrderError(f"Replace failed: {response.get('message')}")
            
            new_order_id = generate_order_id()
            
            logger.info(f"Replace request sent for order: {order_id} -> {new_order_id}")
            return new_order_id
            
        except Exception as e:
            raise DASOrderError(f"Failed to replace order: {e}")
    
    def get_order(self, order_id: str) -> Optional[Order]:
        with self._order_lock:
            return self._orders.get(order_id)
    
    def get_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        active_only: bool = False
    ) -> List[Order]:
        with self._order_lock:
            orders = list(self._orders.values())
            
            if symbol:
                symbol = symbol.upper()
                orders = [o for o in orders if o.symbol == symbol]
            
            if status:
                orders = [o for o in orders if o.status == status]
            
            if active_only:
                orders = [o for o in orders if o.is_active()]
            
            return orders
    
    def get_active_orders(self) -> List[Order]:
        return self.get_orders(active_only=True)

    async def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get pending orders using specific DAS command like short-fade-das."""
        try:
            response = await self.connection.send_command(
                Commands.GET_PENDING_ORDERS,
                wait_response=True,
                timeout=10.0
            )

            if response:
                # Parse pending orders response
                orders = []
                if isinstance(response, dict) and "data" in response:
                    data = response["data"]
                    if isinstance(data, list):
                        for line in data:
                            if line.strip():
                                orders.append({"raw": line.strip()})
                    else:
                        for line in str(data).split('\n'):
                            if line.strip():
                                orders.append({"raw": line.strip()})

                logger.info(f"Retrieved {len(orders)} pending orders")
                return orders

            return []

        except Exception as e:
            logger.error(f"Failed to get pending orders: {e}")
            return []

    async def get_executed_orders(self) -> List[Dict[str, Any]]:
        """Get executed orders using specific DAS command like short-fade-das."""
        try:
            response = await self.connection.send_command(
                Commands.GET_EXECUTED_ORDERS,
                wait_response=True,
                timeout=10.0
            )

            if response:
                # Parse executed orders response
                orders = []
                if isinstance(response, dict) and "data" in response:
                    data = response["data"]
                    if isinstance(data, list):
                        for line in data:
                            if line.strip():
                                orders.append({"raw": line.strip()})
                    else:
                        for line in str(data).split('\n'):
                            if line.strip():
                                orders.append({"raw": line.strip()})

                logger.info(f"Retrieved {len(orders)} executed orders")
                return orders

            return []

        except Exception as e:
            logger.error(f"Failed to get executed orders: {e}")
            return []
    
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for order events."""
        if event in self._order_callbacks:
            self._order_callbacks[event].append(callback)
            logger.debug(f"Registered callback for event: {event}")
    
    def unregister_callback(self, event: str, callback: Callable):
        """Unregister a callback for order events."""
        if event in self._order_callbacks and callback in self._order_callbacks[event]:
            self._order_callbacks[event].remove(callback)
            logger.debug(f"Unregistered callback for event: {event}")
    
    async def _handle_order_message(self, message: Dict[str, Any]):
        """Handle order update messages."""
        order_id = message.get("order_id")
        if not order_id:
            return
        
        with self._order_lock:
            order = self._orders.get(order_id)
            if not order:
                order = self._create_order_from_message(message)
                if order:
                    self._orders[order_id] = order
                    self._symbol_orders[order.symbol].append(order_id)
            
            if order:
                self._update_order_from_message(order, message)
                
                await self._trigger_order_callbacks(order, message)
    
    async def _handle_order_action(self, message: Dict[str, Any]):
        """Handle order action messages."""
        order_id = message.get("order_id")
        action = message.get("action")
        status = message.get("status")
        
        if not order_id:
            return
        
        with self._order_lock:
            order = self._orders.get(order_id)
            if order:
                if action == "CANCELLED":
                    order.update_status(OrderStatus.CANCELLED)
                    await self._trigger_callbacks("order_cancelled", order)
                elif action == "REJECTED":
                    order.update_status(OrderStatus.REJECTED, message.get("details"))
                    await self._trigger_callbacks("order_rejected", order)
                elif action == "REPLACED":
                    order.update_status(OrderStatus.REPLACED)
                    await self._trigger_callbacks("order_replaced", order)
    
    def _create_order_from_message(self, message: Dict[str, Any]) -> Optional[Order]:
        try:
            return Order(
                order_id=message["order_id"],
                symbol=message["symbol"],
                side=OrderSide(message["side"]),
                quantity=message["quantity"],
                order_type=OrderType(message["order_type"]),
                status=OrderStatus(message["status"]),
                price=message.get("price"),
                filled_quantity=message.get("filled_qty", 0),
                avg_fill_price=message.get("avg_price"),
            )
        except Exception as e:
            logger.error(f"Failed to create order from message: {e}")
            return None
    
    def _update_order_from_message(self, order: Order, message: Dict[str, Any]):
        if "status" in message:
            try:
                new_status = OrderStatus(message["status"])
                order.status = new_status
            except ValueError:
                pass
        
        filled_qty = message.get("filled_qty", 0)
        if filled_qty > order.filled_quantity:
            fill_qty = filled_qty - order.filled_quantity
            fill_price = message.get("avg_price", order.price)
            if fill_price:
                order.add_fill(fill_qty, fill_price)
        
        order.updated_at = datetime.now()
    
    async def _trigger_order_callbacks(self, order: Order, message: Dict[str, Any]):
        if order.status == OrderStatus.NEW:
            await self._trigger_callbacks("order_new", order)
        elif order.status == OrderStatus.FILLED:
            await self._trigger_callbacks("order_filled", order)
        elif order.status == OrderStatus.PARTIALLY_FILLED:
            await self._trigger_callbacks("order_partially_filled", order)
        elif order.status == OrderStatus.CANCELLED:
            await self._trigger_callbacks("order_cancelled", order)
        elif order.status == OrderStatus.REJECTED:
            await self._trigger_callbacks("order_rejected", order)
    
    async def _trigger_callbacks(self, event: str, order: Order):
        callbacks = self._order_callbacks.get(event, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(order)
                else:
                    callback(order)
            except Exception as e:
                logger.error(f"Error in callback for {event}: {e}")
    
    def clear_orders(self):
        with self._order_lock:
            self._orders.clear()
            self._symbol_orders.clear()
            logger.info("Cleared all orders from memory")