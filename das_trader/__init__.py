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
from .strategies import TradingStrategies, StrategyResult
from .risk import RiskCalculator, PositionSizeResult
from .locate_manager import SmartLocateManager
from .exceptions import (
    DASConnectionError,
    DASAuthenticationError,
    DASOrderError,
    DASAPIError
)

__version__ = "1.2.0"
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
    "TradingStrategies",
    "StrategyResult",
    "RiskCalculator",
    "PositionSizeResult",
    "SmartLocateManager",
    "DASConnectionError",
    "DASAuthenticationError",
    "DASOrderError",
    "DASAPIError",
]