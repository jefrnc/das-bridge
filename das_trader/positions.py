"""Position management and P&L tracking for DAS Trader API."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
import threading

from .constants import Commands, MessagePrefix
from .exceptions import DASPositionError
from .utils import parse_decimal, calculate_pnl

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents a trading position."""
    symbol: str
    quantity: int  # Positive for long, negative for short
    avg_cost: Decimal
    current_price: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    pnl_percent: Decimal = Decimal("0")
    market_value: Decimal = Decimal("0")
    cost_basis: Decimal = Decimal("0")
    last_update: datetime = field(default_factory=datetime.now)
    
    # Additional fields
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    open_price: Optional[Decimal] = None
    close_price: Optional[Decimal] = None
    volume: int = 0
    
    def __post_init__(self):
        self.update_pnl()
    
    def update_price(self, price: Decimal):
        self.current_price = price
        self.update_pnl()
        self.last_update = datetime.now()
    
    def update_pnl(self):
        if self.quantity == 0:
            self.unrealized_pnl = Decimal("0")
            self.pnl_percent = Decimal("0")
            self.market_value = Decimal("0")
            self.cost_basis = Decimal("0")
            return
        
        self.cost_basis = abs(self.quantity) * self.avg_cost
        self.market_value = abs(self.quantity) * self.current_price
        
        if self.quantity > 0:
            self.unrealized_pnl = self.market_value - self.cost_basis
        else:
            self.unrealized_pnl = self.cost_basis - self.market_value
        
        if self.cost_basis != 0:
            self.pnl_percent = (self.unrealized_pnl / self.cost_basis) * 100
        else:
            self.pnl_percent = Decimal("0")
    
    def add_fill(self, fill_quantity: int, fill_price: Decimal):
        if self.quantity == 0:
            self.quantity = fill_quantity
            self.avg_cost = fill_price
        elif (self.quantity > 0 and fill_quantity > 0) or (self.quantity < 0 and fill_quantity < 0):
            total_cost = (abs(self.quantity) * self.avg_cost) + (abs(fill_quantity) * fill_price)
            self.quantity += fill_quantity
            self.avg_cost = total_cost / abs(self.quantity)
        else:
            if abs(fill_quantity) >= abs(self.quantity):
                realized = abs(self.quantity) * (fill_price - self.avg_cost)
                if self.quantity < 0:
                    realized = -realized
                self.realized_pnl += realized
                
                remaining = fill_quantity + self.quantity
                if remaining != 0:
                    self.quantity = remaining
                    self.avg_cost = fill_price
                else:
                    self.quantity = 0
                    self.avg_cost = Decimal("0")
            else:
                close_qty = abs(fill_quantity)
                realized = close_qty * (fill_price - self.avg_cost)
                if self.quantity < 0:
                    realized = -realized
                self.realized_pnl += realized
                self.quantity += fill_quantity
        
        self.update_pnl()
        self.last_update = datetime.now()
    
    def is_long(self) -> bool:
        return self.quantity > 0
    
    def is_short(self) -> bool:
        return self.quantity < 0
    
    def is_flat(self) -> bool:
        return self.quantity == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_cost": float(self.avg_cost),
            "current_price": float(self.current_price),
            "realized_pnl": float(self.realized_pnl),
            "unrealized_pnl": float(self.unrealized_pnl),
            "pnl_percent": float(self.pnl_percent),
            "market_value": float(self.market_value),
            "cost_basis": float(self.cost_basis),
            "is_long": self.is_long(),
            "is_short": self.is_short(),
            "last_update": self.last_update.isoformat(),
        }


class PositionManager:
    """Manages positions and P&L tracking."""
    
    def __init__(self, connection_manager):
        self.connection = connection_manager
        self._positions: Dict[str, Position] = {}
        self._position_lock = threading.RLock()
        
        self._buying_power = Decimal("0")
        self._day_trading_bp = Decimal("0")
        self._overnight_bp = Decimal("0")
        self._cash = Decimal("0")
        self._total_pnl = Decimal("0")
        
        self._position_callbacks: Dict[str, List[Callable]] = {
            "position_opened": [],
            "position_closed": [],
            "position_updated": [],
            "pnl_updated": [],
        }
        
        self._position_quotes: Dict[str, bool] = {}
        
        self._register_handlers()
    
    def _register_handlers(self):
        self.connection.register_handler("POSITION", self._handle_position_message)
        self.connection.register_handler("BUYING_POWER", self._handle_buying_power_message)
        self.connection.register_handler("QUOTE", self._handle_quote_update)
    
    async def refresh_positions(self):
        """Request position refresh from DAS Trader."""
        try:
            await self.connection.send_command(Commands.POS_REFRESH, wait_response=False)
            logger.info("Position refresh requested")
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            raise DASPositionError(f"Failed to refresh positions: {e}")
    
    def get_position(self, symbol: str) -> Optional[Position]:
        with self._position_lock:
            return self._positions.get(symbol.upper())
    
    def get_all_positions(self) -> List[Position]:
        with self._position_lock:
            return list(self._positions.values())
    
    def get_open_positions(self) -> List[Position]:
        with self._position_lock:
            return [p for p in self._positions.values() if not p.is_flat()]
    
    def get_long_positions(self) -> List[Position]:
        with self._position_lock:
            return [p for p in self._positions.values() if p.is_long()]
    
    def get_short_positions(self) -> List[Position]:
        with self._position_lock:
            return [p for p in self._positions.values() if p.is_short()]
    
    def get_total_pnl(self) -> Dict[str, Decimal]:
        with self._position_lock:
            total_realized = sum(p.realized_pnl for p in self._positions.values())
            total_unrealized = sum(p.unrealized_pnl for p in self._positions.values())
            
            return {
                "realized_pnl": total_realized,
                "unrealized_pnl": total_unrealized,
                "total_pnl": total_realized + total_unrealized,
            }
    
    def get_account_values(self) -> Dict[str, Decimal]:
        return {
            "buying_power": self._buying_power,
            "day_trading_bp": self._day_trading_bp,
            "overnight_bp": self._overnight_bp,
            "cash": self._cash,
            "total_pnl": self._total_pnl,
        }
    
    async def get_buying_power(self) -> Dict[str, Decimal]:
        try:
            response = await self.connection.send_command(
                Commands.GET_BP,
                wait_response=True,
                response_type="BUYING_POWER"
            )
            
            if response and response.get("type") == "BUYING_POWER":
                return {
                    "buying_power": response.get("buying_power", Decimal("0")),
                    "day_trading_bp": response.get("day_trading_bp", Decimal("0")),
                    "overnight_bp": response.get("overnight_bp", Decimal("0")),
                    "cash": response.get("cash", Decimal("0")),
                }
            
            return self.get_account_values()
            
        except Exception as e:
            logger.error(f"Failed to get buying power: {e}")
            return self.get_account_values()
    
    def add_fill(self, symbol: str, fill_quantity: int, fill_price: Decimal):
        symbol = symbol.upper()
        
        with self._position_lock:
            position = self._positions.get(symbol)
            
            if not position:
                position = Position(
                    symbol=symbol,
                    quantity=0,
                    avg_cost=Decimal("0"),
                    current_price=fill_price
                )
                self._positions[symbol] = position
                was_new = True
            else:
                was_new = False
            
            was_flat = position.is_flat()
            position.add_fill(fill_quantity, fill_price)
            
            if was_new or was_flat:
                self._trigger_callback("position_opened", position)
            elif position.is_flat():
                self._trigger_callback("position_closed", position)
            else:
                self._trigger_callback("position_updated", position)
            
            self._trigger_callback("pnl_updated", self.get_total_pnl())
            
            if not position.is_flat() and symbol not in self._position_quotes:
                asyncio.create_task(self._subscribe_position_quotes(symbol))
    
    async def _subscribe_position_quotes(self, symbol: str):
        try:
            from .market_data import MarketDataLevel
            self._position_quotes[symbol] = True
            logger.info(f"Subscribed to quotes for position: {symbol}")
        except Exception as e:
            logger.error(f"Failed to subscribe to quotes for {symbol}: {e}")
    
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for position events."""
        if event in self._position_callbacks:
            self._position_callbacks[event].append(callback)
            logger.debug(f"Registered callback for event: {event}")
    
    def unregister_callback(self, event: str, callback: Callable):
        """Unregister a callback for position events."""
        if event in self._position_callbacks and callback in self._position_callbacks[event]:
            self._position_callbacks[event].remove(callback)
            logger.debug(f"Unregistered callback for event: {event}")
    
    async def _handle_position_message(self, message: Dict[str, Any]):
        """Handle position update messages."""
        symbol = message.get("symbol")
        if not symbol:
            return
        
        symbol = symbol.upper()
        
        with self._position_lock:
            position = self._positions.get(symbol)
            
            if not position:
                position = Position(
                    symbol=symbol,
                    quantity=message.get("quantity", 0),
                    avg_cost=message.get("avg_cost", Decimal("0")),
                    current_price=message.get("current_price", Decimal("0"))
                )
                self._positions[symbol] = position
                self._trigger_callback("position_opened", position)
            else:
                position.quantity = message.get("quantity", position.quantity)
                position.avg_cost = message.get("avg_cost", position.avg_cost)
                position.current_price = message.get("current_price", position.current_price)
                position.update_pnl()
                self._trigger_callback("position_updated", position)
            
            if "pnl" in message:
                position.unrealized_pnl = message["pnl"]
            if "pnl_percent" in message:
                position.pnl_percent = message["pnl_percent"]
            
            if position.is_flat():
                self._trigger_callback("position_closed", position)
                if symbol in self._position_quotes:
                    del self._position_quotes[symbol]
            
            self._trigger_callback("pnl_updated", self.get_total_pnl())
    
    async def _handle_buying_power_message(self, message: Dict[str, Any]):
        self._buying_power = message.get("buying_power", self._buying_power)
        self._day_trading_bp = message.get("day_trading_bp", self._day_trading_bp)
        self._overnight_bp = message.get("overnight_bp", self._overnight_bp)
        self._cash = message.get("cash", self._cash)
        
        logger.info(f"Account values updated - BP: {self._buying_power}, "
                   f"DT BP: {self._day_trading_bp}, Cash: {self._cash}")
    
    async def _handle_quote_update(self, message: Dict[str, Any]):
        symbol = message.get("symbol")
        if not symbol or symbol not in self._position_quotes:
            return
        
        last_price = message.get("last")
        if last_price is None:
            return
        
        with self._position_lock:
            position = self._positions.get(symbol)
            if position and not position.is_flat():
                position.update_price(last_price)
                self._trigger_callback("position_updated", position)
                self._trigger_callback("pnl_updated", self.get_total_pnl())
    
    def _trigger_callback(self, event: str, data: Any):
        callbacks = self._position_callbacks.get(event, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in callback for {event}: {e}")
    
    def clear_positions(self):
        with self._position_lock:
            self._positions.clear()
            self._position_quotes.clear()
            logger.info("Cleared all positions from memory")
    
    def calculate_portfolio_metrics(self) -> Dict[str, Any]:
        with self._position_lock:
            positions = list(self._positions.values())
            open_positions = [p for p in positions if not p.is_flat()]
            
            if not open_positions:
                return {
                    "total_positions": 0,
                    "long_positions": 0,
                    "short_positions": 0,
                    "total_market_value": Decimal("0"),
                    "total_cost_basis": Decimal("0"),
                    "total_unrealized_pnl": Decimal("0"),
                    "total_realized_pnl": Decimal("0"),
                    "total_pnl": Decimal("0"),
                    "avg_pnl_percent": Decimal("0"),
                }
            
            total_market_value = sum(p.market_value for p in open_positions)
            total_cost_basis = sum(p.cost_basis for p in open_positions)
            total_unrealized = sum(p.unrealized_pnl for p in positions)
            total_realized = sum(p.realized_pnl for p in positions)
            
            avg_pnl_percent = Decimal("0")
            if total_cost_basis > 0:
                avg_pnl_percent = (total_unrealized / total_cost_basis) * 100
            
            return {
                "total_positions": len(open_positions),
                "long_positions": len([p for p in open_positions if p.is_long()]),
                "short_positions": len([p for p in open_positions if p.is_short()]),
                "total_market_value": total_market_value,
                "total_cost_basis": total_cost_basis,
                "total_unrealized_pnl": total_unrealized,
                "total_realized_pnl": total_realized,
                "total_pnl": total_unrealized + total_realized,
                "avg_pnl_percent": avg_pnl_percent,
                "winning_positions": len([p for p in open_positions if p.unrealized_pnl > 0]),
                "losing_positions": len([p for p in open_positions if p.unrealized_pnl < 0]),
            }