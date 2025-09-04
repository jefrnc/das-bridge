"""Market scanner for top gainers, losers, and most active stocks."""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

from .connection import ConnectionManager
from .constants import Commands, MessagePrefix
from .exceptions import DASAPIError

logger = logging.getLogger(__name__)


class ScannerType(Enum):
    """Types of market scanners available."""
    GAINERS = "Gainers"           # Top percentage gainers
    LOSERS = "Losers"             # Top percentage losers
    MOST_ACTIVE = "MostActive"    # Most active by volume
    HIGH_VOLUME = "HighVolume"    # High volume stocks
    NEW_HIGH = "NewHigh"          # New 52-week highs
    NEW_LOW = "NewLow"            # New 52-week lows
    GAP_UP = "GapUp"              # Gapped up from previous close
    GAP_DOWN = "GapDown"          # Gapped down from previous close
    

class MarketScanner:
    """Handles market scanning and top lists from DAS API."""
    
    def __init__(self, connection: ConnectionManager):
        self.connection = connection
        self._scanners: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        
    async def get_top_gainers(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get top percentage gainers.
        
        Args:
            limit: Number of stocks to return (default 20)
            
        Returns:
            List of dictionaries with stock data
        """
        return await self._get_top_list(ScannerType.GAINERS, limit)
    
    async def get_top_losers(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get top percentage losers.
        
        Args:
            limit: Number of stocks to return (default 20)
            
        Returns:
            List of dictionaries with stock data
        """
        return await self._get_top_list(ScannerType.LOSERS, limit)
    
    async def get_most_active(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get most active stocks by volume.
        
        Args:
            limit: Number of stocks to return (default 20)
            
        Returns:
            List of dictionaries with stock data
        """
        return await self._get_top_list(ScannerType.MOST_ACTIVE, limit)
    
    async def _get_top_list(
        self, 
        scanner_type: ScannerType, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get top list for specified scanner type.
        
        Args:
            scanner_type: Type of scanner to use
            limit: Number of results to return
            
        Returns:
            List of stock data dictionaries
        """
        command = f"{Commands.SUBSCRIBE_TOPLIST} {scanner_type.value} {limit}"
        
        logger.info(f"Requesting top list: {scanner_type.value}")
        
        # Send command
        await self.connection.send_command(command)
        
        # Collect responses
        stocks = []
        await asyncio.sleep(1)  # Allow time for response
        
        # Process messages from connection
        while True:
            message = await self.connection.get_message(timeout=0.5)
            if not message:
                break
                
            if message.startswith(MessagePrefix.TOPLIST):
                stock_data = self._parse_toplist_entry(message)
                if stock_data:
                    stocks.append(stock_data)
        
        # Sort by percentage change
        stocks.sort(key=lambda x: abs(x.get('percent_change', 0)), reverse=True)
        
        return stocks[:limit]
    
    def _parse_toplist_entry(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Parse a top list entry message.
        
        Format: $TopList Symbol Last Change %Change Volume
        Example: $TopList AAPL 150.25 +2.50 +1.69% 45234567
        
        Args:
            message: Raw message from API
            
        Returns:
            Parsed stock data or None
        """
        try:
            parts = message.split()
            
            if len(parts) < 6:
                return None
                
            # Extract percentage change
            percent_str = parts[4].replace('%', '').replace('+', '')
            
            return {
                'symbol': parts[1],
                'last': float(parts[2]),
                'change': float(parts[3].replace('+', '')),
                'percent_change': float(percent_str),
                'volume': int(parts[5]),
                'timestamp': datetime.now()
            }
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse top list entry: {message} - {e}")
            return None
    
    async def subscribe_scanner(
        self,
        scanner_type: ScannerType,
        callback: Optional[Callable] = None,
        update_interval: int = 60
    ):
        """
        Subscribe to continuous scanner updates.
        
        Args:
            scanner_type: Type of scanner to subscribe to
            callback: Function to call with updates
            update_interval: Seconds between updates (default 60)
        """
        scanner_id = f"{scanner_type.value}_{datetime.now().timestamp()}"
        
        self._scanners[scanner_id] = {
            'type': scanner_type,
            'callback': callback,
            'interval': update_interval,
            'active': True
        }
        
        # Start update task
        asyncio.create_task(self._scanner_update_loop(scanner_id))
        
        return scanner_id
    
    async def unsubscribe_scanner(self, scanner_id: str):
        """
        Unsubscribe from scanner updates.
        
        Args:
            scanner_id: ID returned from subscribe_scanner
        """
        if scanner_id in self._scanners:
            self._scanners[scanner_id]['active'] = False
            del self._scanners[scanner_id]
    
    async def _scanner_update_loop(self, scanner_id: str):
        """
        Background task to fetch scanner updates.
        
        Args:
            scanner_id: Scanner subscription ID
        """
        scanner_info = self._scanners.get(scanner_id)
        
        while scanner_info and scanner_info['active']:
            try:
                # Get latest data
                stocks = await self._get_top_list(scanner_info['type'])
                
                # Call callback if provided
                if scanner_info['callback']:
                    await scanner_info['callback'](stocks)
                
                # Wait for next update
                await asyncio.sleep(scanner_info['interval'])
                
            except Exception as e:
                logger.error(f"Error in scanner update loop: {e}")
                await asyncio.sleep(10)  # Brief pause on error
    
    async def get_custom_scan(
        self,
        criteria: Dict[str, Any],
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get custom scan based on multiple criteria.
        
        Args:
            criteria: Dictionary of scan criteria
                - min_price: Minimum stock price
                - max_price: Maximum stock price
                - min_volume: Minimum volume
                - min_change_pct: Minimum % change
                - exchanges: List of exchanges to include
            limit: Maximum results to return
            
        Returns:
            List of stocks matching criteria
        """
        # For now, get all top movers and filter
        # In future, this could use more advanced DAS scanning features
        
        all_stocks = []
        
        # Combine different scanners
        gainers = await self.get_top_gainers(limit=50)
        losers = await self.get_top_losers(limit=50)
        active = await self.get_most_active(limit=50)
        
        all_stocks.extend(gainers)
        all_stocks.extend(losers)
        all_stocks.extend(active)
        
        # Remove duplicates
        seen = set()
        unique_stocks = []
        for stock in all_stocks:
            if stock['symbol'] not in seen:
                seen.add(stock['symbol'])
                unique_stocks.append(stock)
        
        # Apply filters
        filtered = unique_stocks
        
        if 'min_price' in criteria:
            filtered = [s for s in filtered if s['last'] >= criteria['min_price']]
            
        if 'max_price' in criteria:
            filtered = [s for s in filtered if s['last'] <= criteria['max_price']]
            
        if 'min_volume' in criteria:
            filtered = [s for s in filtered if s['volume'] >= criteria['min_volume']]
            
        if 'min_change_pct' in criteria:
            filtered = [s for s in filtered 
                       if abs(s['percent_change']) >= criteria['min_change_pct']]
        
        # Sort by percentage change
        filtered.sort(key=lambda x: abs(x.get('percent_change', 0)), reverse=True)
        
        return filtered[:limit]


class SymbolInfo:
    """Get detailed symbol information including SSR, halt status, etc."""
    
    def __init__(self, connection: ConnectionManager):
        self.connection = connection
    
    async def get_symbol_status(self, symbol: str) -> Dict[str, Any]:
        """
        Get symbol status including SSR and halt information.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with symbol status
        """
        command = f"{Commands.GET_SYM_STATUS} {symbol}"
        await self.connection.send_command(command)
        
        # Wait for response
        await asyncio.sleep(0.5)
        
        status = {
            'symbol': symbol,
            'ssr': False,
            'halted': False,
            'trading_action': None,
            'action_time': None
        }
        
        while True:
            message = await self.connection.get_message(timeout=0.5)
            if not message:
                break
                
            if MessagePrefix.SYM_STATUS in message:
                # Parse: $SymStatus BTBD SSR:Y TA:T TAT:08:25:00
                if 'SSR:Y' in message:
                    status['ssr'] = True
                    
                if 'TA:' in message:
                    ta_index = message.index('TA:') + 3
                    ta_value = message[ta_index:ta_index+1]
                    
                    status['trading_action'] = ta_value
                    status['halted'] = (ta_value == 'H')
                    
                if 'TAT:' in message:
                    tat_index = message.index('TAT:') + 4
                    time_str = message[tat_index:tat_index+8]
                    status['action_time'] = time_str
        
        return status
    
    async def get_limit_prices(self, symbol: str) -> Dict[str, Optional[float]]:
        """
        Get limit down and limit up prices for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with limit_down and limit_up prices
        """
        command = f"{Commands.GET_LDLU} {symbol}"
        await self.connection.send_command(command)
        
        await asyncio.sleep(0.5)
        
        limits = {
            'symbol': symbol,
            'limit_down': None,
            'limit_up': None
        }
        
        while True:
            message = await self.connection.get_message(timeout=0.5)
            if not message:
                break
                
            if MessagePrefix.LDLU in message:
                # Parse: $LDLU SPY 400.50 450.75
                parts = message.split()
                if len(parts) >= 4:
                    try:
                        limits['limit_down'] = float(parts[2])
                        limits['limit_up'] = float(parts[3])
                    except ValueError:
                        pass
        
        return limits
    
    async def get_short_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get shortable information for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with shortable information
        """
        command = f"{Commands.GET_SHORT_INFO} {symbol}"
        await self.connection.send_command(command)
        
        await asyncio.sleep(0.5)
        
        info = {
            'symbol': symbol,
            'shortable': False,
            'short_size': 0,
            'marginable': False,
            'long_margin': 0,
            'short_margin': 0,
            'prohibited': False,
            'regsho': False
        }
        
        while True:
            message = await self.connection.get_message(timeout=0.5)
            if not message:
                break
                
            if MessagePrefix.SHORT_INFO in message:
                # Parse: $SHORTINFO AAPL Y 1000000000 Y 0 0 N N
                parts = message.split()
                if len(parts) >= 7:
                    info['shortable'] = (parts[2] == 'Y')
                    info['short_size'] = int(parts[3]) if parts[3].isdigit() else 0
                    info['marginable'] = (parts[4] == 'Y')
                    info['long_margin'] = float(parts[5]) if parts[5].replace('.','').isdigit() else 0
                    info['short_margin'] = float(parts[6]) if parts[6].replace('.','').isdigit() else 0
                    
                    if len(parts) > 7:
                        info['prohibited'] = (parts[7] == 'Y')
                    if len(parts) > 8:
                        info['regsho'] = (parts[8] == 'Y')
        
        return info