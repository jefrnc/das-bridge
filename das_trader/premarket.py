"""
Premarket Trading Support for DAS Trader
Provides specialized functionality for premarket/extended hours trading
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, time
from decimal import Decimal

from .client import DASTraderClient
from .constants import OrderSide, OrderType, TimeInForce
from .exceptions import DASAPIError

logger = logging.getLogger(__name__)


class PremarketSession:
    """Manager for premarket/extended hours trading sessions."""
    
    # Premarket hours (ET)
    PREMARKET_START = time(4, 0)   # 4:00 AM ET
    PREMARKET_END = time(9, 30)    # 9:30 AM ET
    
    # After hours (ET)
    AFTERHOURS_START = time(16, 0)  # 4:00 PM ET
    AFTERHOURS_END = time(20, 0)    # 8:00 PM ET
    
    def __init__(self, client: DASTraderClient):
        """Initialize premarket session manager.
        
        Args:
            client: DAS Trader client instance
        """
        self.client = client
        self._session_active = False
        
    def is_premarket_time(self) -> bool:
        """Check if current time is within premarket hours.
        
        Returns:
            True if in premarket hours
        """
        now = datetime.now().time()
        return self.PREMARKET_START <= now <= self.PREMARKET_END
    
    def is_afterhours_time(self) -> bool:
        """Check if current time is within after-hours.
        
        Returns:
            True if in after-hours
        """
        now = datetime.now().time()
        return self.AFTERHOURS_START <= now <= self.AFTERHOURS_END
    
    def is_extended_hours(self) -> bool:
        """Check if in any extended hours session.
        
        Returns:
            True if in premarket or after-hours
        """
        return self.is_premarket_time() or self.is_afterhours_time()
    
    async def send_premarket_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        **kwargs
    ) -> str:
        """Send an order configured for premarket trading.
        
        Automatically configures order for extended hours execution.
        
        Args:
            symbol: Stock symbol
            side: Buy or sell
            quantity: Number of shares
            order_type: Type of order
            price: Limit price (if applicable)
            stop_price: Stop price (if applicable)
            **kwargs: Additional order parameters
            
        Returns:
            Order ID
        """
        # Force GTC for premarket orders (DAY orders don't work in premarket)
        kwargs['time_in_force'] = TimeInForce.GTC
        
        # Extended hours flag (if DAS supports it)
        kwargs['extended_hours'] = True
        
        # For premarket, prefer limit orders over market
        if order_type == OrderType.MARKET and self.is_premarket_time():
            logger.warning("Market orders not recommended in premarket, consider using limit")
        
        return await self.client.send_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            **kwargs
        )
    
    async def get_premarket_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get premarket quote for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quote data with premarket prices
        """
        quote = await self.client.get_quote(symbol)
        
        if quote and self.is_extended_hours():
            # Add extended hours indicators
            quote_dict = quote.to_dict() if hasattr(quote, 'to_dict') else dict(quote)
            quote_dict['is_extended_hours'] = True
            quote_dict['session'] = 'premarket' if self.is_premarket_time() else 'afterhours'
            return quote_dict
            
        return quote


class PremarketScanner:
    """Scanner specifically for premarket movers and gaps."""
    
    def __init__(self, client: DASTraderClient):
        """Initialize premarket scanner.
        
        Args:
            client: DAS Trader client instance
        """
        self.client = client
        self._cache = {}
        
    async def get_premarket_movers(self, min_volume: int = 10000) -> List[Dict[str, Any]]:
        """Get premarket movers based on volume and price change.
        
        Args:
            min_volume: Minimum premarket volume
            
        Returns:
            List of premarket movers
        """
        # This would need to be implemented based on DAS API capabilities
        # For now, return empty list as placeholder
        logger.warning("Premarket movers scanning not yet implemented for DAS")
        return []
    
    async def scan_gaps(
        self,
        symbols: List[str],
        min_gap: float = 5.0,
        max_gap: float = 50.0
    ) -> List[Dict[str, Any]]:
        """Scan for gap stocks in premarket.
        
        Args:
            symbols: List of symbols to scan
            min_gap: Minimum gap percentage
            max_gap: Maximum gap percentage
            
        Returns:
            List of gap candidates
        """
        gaps = []
        
        for symbol in symbols:
            try:
                # Get current quote
                quote = await self.client.get_quote(symbol)
                if not quote:
                    continue
                
                # Would need previous close data
                # This is a placeholder - actual implementation would need
                # historical data access
                
                gaps.append({
                    'symbol': symbol,
                    'current_price': quote.last,
                    'volume': quote.volume
                })
                
            except Exception as e:
                logger.debug(f"Error scanning {symbol}: {e}")
                
        return gaps


class PremarketIndicators:
    """Technical indicators optimized for premarket trading."""
    
    @staticmethod
    def calculate_premarket_vwap(trades: List[Dict[str, Any]]) -> float:
        """Calculate VWAP for premarket session.
        
        Args:
            trades: List of trades with price and volume
            
        Returns:
            VWAP value
        """
        if not trades:
            return 0.0
        
        total_volume = sum(t.get('volume', 0) for t in trades)
        if total_volume == 0:
            return 0.0
        
        vwap = sum(t.get('price', 0) * t.get('volume', 0) for t in trades) / total_volume
        return vwap
    
    @staticmethod
    def calculate_relative_volume(
        current_volume: int,
        avg_volume: int,
        time_elapsed: float
    ) -> float:
        """Calculate relative volume for premarket.
        
        Args:
            current_volume: Current premarket volume
            avg_volume: Average daily volume
            time_elapsed: Hours elapsed in premarket
            
        Returns:
            Relative volume ratio
        """
        if avg_volume == 0 or time_elapsed == 0:
            return 0.0
        
        # Assume 6.5 hour regular trading day
        expected_volume = (avg_volume / 6.5) * time_elapsed
        
        if expected_volume == 0:
            return 0.0
            
        return current_volume / expected_volume
    
    @staticmethod
    def identify_opening_range(
        bars: List[Dict[str, Any]],
        minutes: int = 30
    ) -> Dict[str, float]:
        """Identify opening range for breakout trading.
        
        Args:
            bars: List of price bars
            minutes: Minutes to consider for opening range
            
        Returns:
            Dict with high, low, and midpoint
        """
        if not bars:
            return {'high': 0, 'low': 0, 'midpoint': 0}
        
        # Get bars for specified minutes
        opening_bars = bars[:minutes]
        
        high = max(b.get('high', 0) for b in opening_bars)
        low = min(b.get('low', float('inf')) for b in opening_bars)
        midpoint = (high + low) / 2
        
        return {
            'high': high,
            'low': low,
            'midpoint': midpoint,
            'range': high - low
        }