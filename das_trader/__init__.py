"""DAS Trader CMD API Python Client

A comprehensive Python client for interacting with DAS Trader Pro's CMD API.
Supports trading operations, market data streaming, and account management.
"""

from .client import DASTraderClient
from .connection import ConnectionManager
from .orders import OrderManager, OrderType, OrderSide, OrderStatus
from .positions import PositionManager
from .market_data import MarketDataManager
from .notifications import NotificationManager
from .exceptions import (
    DASConnectionError,
    DASAuthenticationError,
    DASOrderError,
    DASAPIError
)

__version__ = "0.1.0"
__author__ = "DAS Bridge Development Team"

__all__ = [
    "DASTraderClient",
    "ConnectionManager",
    "OrderManager",
    "OrderType",
    "OrderSide",
    "OrderStatus",
    "PositionManager",
    "MarketDataManager",
    "NotificationManager",
    "DASConnectionError",
    "DASAuthenticationError",
    "DASOrderError",
    "DASAPIError",
]