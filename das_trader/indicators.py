"""
Technical Indicators for DAS Trader
Common indicators used in trading strategies
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators from price data."""
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average.
        
        Args:
            prices: List of prices (oldest to newest)
            period: EMA period
            
        Returns:
            Current EMA value or None if not enough data
        """
        if len(prices) < period:
            return None
        
        # Use numpy for efficient calculation
        prices_array = np.array(prices)
        
        # Calculate EMA
        multiplier = 2 / (period + 1)
        ema = prices_array[0]  # Start with first price
        
        for price in prices_array[1:]:
            ema = (price - ema) * multiplier + ema
        
        return float(ema)
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average.
        
        Args:
            prices: List of prices
            period: SMA period
            
        Returns:
            Current SMA value or None if not enough data
        """
        if len(prices) < period:
            return None
        
        return sum(prices[-period:]) / period
    
    @staticmethod
    def calculate_vwap(trades: List[Dict[str, float]]) -> Optional[float]:
        """Calculate Volume Weighted Average Price.
        
        Args:
            trades: List of trades with 'price' and 'volume' keys
            
        Returns:
            VWAP value or None if no trades
        """
        if not trades:
            return None
        
        total_volume = sum(t.get('volume', 0) for t in trades)
        
        if total_volume == 0:
            return None
        
        vwap = sum(t.get('price', 0) * t.get('volume', 0) for t in trades) / total_volume
        
        return vwap
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index.
        
        Args:
            prices: List of prices
            period: RSI period (default 14)
            
        Returns:
            RSI value (0-100) or None if not enough data
        """
        if len(prices) < period + 1:
            return None
        
        # Calculate price changes
        deltas = np.diff(prices)
        
        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calculate average gain and loss
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0  # No losses = RSI 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Optional[Dict[str, float]]:
        """Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            prices: List of prices
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line EMA period (default 9)
            
        Returns:
            Dict with 'macd', 'signal', and 'histogram' or None
        """
        if len(prices) < slow_period:
            return None
        
        # Calculate EMAs
        fast_ema = TechnicalIndicators.calculate_ema(prices, fast_period)
        slow_ema = TechnicalIndicators.calculate_ema(prices, slow_period)
        
        if fast_ema is None or slow_ema is None:
            return None
        
        macd_line = fast_ema - slow_ema
        
        # For signal line, we need MACD history
        # Simplified: just return current MACD
        return {
            'macd': macd_line,
            'signal': macd_line,  # Simplified
            'histogram': 0
        }
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Optional[Dict[str, float]]:
        """Calculate Bollinger Bands.
        
        Args:
            prices: List of prices
            period: SMA period (default 20)
            std_dev: Standard deviation multiplier (default 2.0)
            
        Returns:
            Dict with 'upper', 'middle', 'lower' bands or None
        """
        if len(prices) < period:
            return None
        
        # Calculate SMA (middle band)
        middle = TechnicalIndicators.calculate_sma(prices, period)
        
        if middle is None:
            return None
        
        # Calculate standard deviation
        recent_prices = prices[-period:]
        std = np.std(recent_prices)
        
        return {
            'upper': middle + (std * std_dev),
            'middle': middle,
            'lower': middle - (std * std_dev)
        }
    
    @staticmethod
    def calculate_atr(
        bars: List[Dict[str, float]],
        period: int = 14
    ) -> Optional[float]:
        """Calculate Average True Range.
        
        Args:
            bars: List of bars with 'high', 'low', 'close' keys
            period: ATR period (default 14)
            
        Returns:
            ATR value or None if not enough data
        """
        if len(bars) < period + 1:
            return None
        
        true_ranges = []
        
        for i in range(1, len(bars)):
            high = bars[i].get('high', 0)
            low = bars[i].get('low', 0)
            prev_close = bars[i-1].get('close', 0)
            
            # True range is max of:
            # 1. Current high - current low
            # 2. Abs(current high - previous close)
            # 3. Abs(current low - previous close)
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        # Calculate ATR as EMA of true ranges
        if len(true_ranges) >= period:
            return sum(true_ranges[-period:]) / period
        
        return None
    
    @staticmethod
    def calculate_support_resistance(
        bars: List[Dict[str, float]],
        lookback: int = 20
    ) -> Dict[str, List[float]]:
        """Calculate support and resistance levels.
        
        Args:
            bars: List of bars with OHLC data
            lookback: Number of bars to look back
            
        Returns:
            Dict with 'support' and 'resistance' levels
        """
        if len(bars) < lookback:
            return {'support': [], 'resistance': []}
        
        recent_bars = bars[-lookback:]
        
        highs = [b.get('high', 0) for b in recent_bars]
        lows = [b.get('low', 0) for b in recent_bars]
        
        # Simple approach: use recent highs as resistance, lows as support
        # Group similar prices together
        resistance_levels = []
        support_levels = []
        
        # Find local maxima for resistance
        for i in range(1, len(highs) - 1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                resistance_levels.append(highs[i])
        
        # Find local minima for support
        for i in range(1, len(lows) - 1):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                support_levels.append(lows[i])
        
        return {
            'support': sorted(set(support_levels))[:3],  # Top 3 support levels
            'resistance': sorted(set(resistance_levels), reverse=True)[:3]  # Top 3 resistance levels
        }
    
    @staticmethod
    def calculate_pivot_points(
        high: float,
        low: float,
        close: float
    ) -> Dict[str, float]:
        """Calculate pivot points for intraday trading.
        
        Args:
            high: Previous day's high
            low: Previous day's low
            close: Previous day's close
            
        Returns:
            Dict with pivot levels
        """
        # Standard pivot point
        pivot = (high + low + close) / 3
        
        # Support and resistance levels
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)
        
        return {
            'pivot': pivot,
            'r1': r1,
            'r2': r2,
            'r3': r3,
            's1': s1,
            's2': s2,
            's3': s3
        }
    
    @staticmethod
    def identify_candlestick_pattern(
        bars: List[Dict[str, float]]
    ) -> Optional[str]:
        """Identify common candlestick patterns.
        
        Args:
            bars: List of recent bars (need at least 3)
            
        Returns:
            Pattern name or None
        """
        if len(bars) < 3:
            return None
        
        # Get last 3 bars
        bar1, bar2, bar3 = bars[-3:]
        
        # Calculate body sizes
        body1 = abs(bar1['close'] - bar1['open'])
        body2 = abs(bar2['close'] - bar2['open'])
        body3 = abs(bar3['close'] - bar3['open'])
        
        # Bullish patterns
        if bar1['close'] < bar1['open'] and bar2['close'] > bar2['open']:
            if bar2['close'] > bar1['open'] and bar2['open'] < bar1['close']:
                return "Bullish Engulfing"
        
        # Hammer
        if body3 < (bar3['high'] - bar3['low']) * 0.3:
            if bar3['close'] > bar3['open'] and (bar3['low'] - min(bar3['open'], bar3['close'])) > body3 * 2:
                return "Hammer"
        
        # Doji
        if body3 < (bar3['high'] - bar3['low']) * 0.1:
            return "Doji"
        
        # Morning Star (simplified)
        if bar1['close'] < bar1['open'] and bar3['close'] > bar3['open']:
            if body2 < body1 * 0.3 and body2 < body3 * 0.3:
                return "Morning Star"
        
        return None


class PremarketIndicators:
    """Indicators specifically for premarket trading."""
    
    @staticmethod
    def calculate_gap_percentage(
        prev_close: float,
        current_price: float
    ) -> float:
        """Calculate gap percentage.
        
        Args:
            prev_close: Previous day's closing price
            current_price: Current premarket price
            
        Returns:
            Gap percentage
        """
        if prev_close == 0:
            return 0.0
        
        return ((current_price - prev_close) / prev_close) * 100
    
    @staticmethod
    def calculate_premarket_range(
        bars: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """Calculate premarket high/low range.
        
        Args:
            bars: Premarket bars
            
        Returns:
            Dict with high, low, range, and midpoint
        """
        if not bars:
            return {'high': 0, 'low': 0, 'range': 0, 'midpoint': 0}
        
        high = max(b.get('high', 0) for b in bars)
        low = min(b.get('low', float('inf')) for b in bars)
        
        return {
            'high': high,
            'low': low,
            'range': high - low,
            'midpoint': (high + low) / 2
        }
    
    @staticmethod
    def calculate_spike_from_close(
        prev_close: float,
        premarket_low: float
    ) -> float:
        """Calculate spike percentage from previous close.
        
        Args:
            prev_close: Previous day's close
            premarket_low: Premarket session low
            
        Returns:
            Spike percentage (negative if below close)
        """
        if prev_close == 0:
            return 0.0
        
        return ((premarket_low - prev_close) / prev_close) * 100