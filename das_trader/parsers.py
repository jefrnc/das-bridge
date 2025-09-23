"""
DAS CMD API Response Parsers
Parsea las respuestas del CMD API de DAS Trader Pro
Incluye soporte especial para small caps de Zimtra
"""

import re
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, time
from dataclasses import dataclass
from enum import Enum


class MessageType(Enum):
    """Tipos de mensajes del CMD API"""
    ORDER = "ORDER"
    TRADE = "TRADE"
    QUOTE = "QUOTE"
    SHORTINFO = "SHORTINFO"
    POSITION = "POS"
    BUYING_POWER = "BP"
    ACCOUNT_INFO = "ACCOUNT"
    ROUTE_STATUS = "RouteStatus"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


@dataclass
class ParsedOrder:
    """Orden parseada del CMD API"""
    order_id: str
    sequence: int
    symbol: str
    side: str  # B, S, SS
    order_type: str  # L, M, etc
    quantity: int
    filled: int
    remaining: int
    price: float
    route: str
    status: str
    time: str
    account: Optional[str] = None
    user: Optional[str] = None
    source: Optional[str] = None


@dataclass
class ParsedTrade:
    """Trade parseado del CMD API"""
    trade_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    route: str
    time: str
    execution_id: Optional[str] = None
    pnl: float = 0.0
    commission: float = 0.0


@dataclass
class ParsedQuote:
    """Quote parseada del CMD API"""
    symbol: str
    bid: float
    ask: float
    last: float
    bid_size: int
    ask_size: int
    volume: int
    timestamp: Optional[str] = None


@dataclass
class ParsedShortInfo:
    """Información de short parseada"""
    symbol: str
    shortable: bool
    shares_available: int
    uptick_rule: bool = False
    ssr_triggered: bool = False


@dataclass
class ParsedPosition:
    """Posición parseada"""
    symbol: str
    position_type: str  # L (Long), S (Short)
    quantity: int
    avg_cost: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


class DASResponseParser:
    """Parser principal para respuestas del CMD API de DAS"""
    
    # Patterns para identificar tipos de mensajes
    PATTERNS = {
        'ORDER': re.compile(r'^%ORDER\s+'),
        'TRADE': re.compile(r'^%TRADE\s+'),
        'QUOTE': re.compile(r'^\$QUOTE\s+'),
        'SHORTINFO': re.compile(r'^\$SHORTINFO\s+'),
        'POSITION': re.compile(r'^%POS\s+'),
        'BUYING_POWER': re.compile(r'^\$BP\s+'),
        'ROUTE_STATUS': re.compile(r'^\$RouteStatus\s+'),
    }
    
    @classmethod
    def identify_message_type(cls, line: str) -> MessageType:
        """Identificar el tipo de mensaje"""
        line = line.strip()
        
        for msg_type, pattern in cls.PATTERNS.items():
            if pattern.match(line):
                return MessageType[msg_type]
        
        if line.startswith('#'):
            # Comentarios o headers
            return MessageType.UNKNOWN
        elif 'ERROR' in line or 'Invalid' in line or 'Failed' in line:
            return MessageType.ERROR
        
        return MessageType.UNKNOWN
    
    @classmethod
    def parse_line(cls, line: str) -> Optional[Union[ParsedOrder, ParsedTrade, ParsedQuote, ParsedShortInfo]]:
        """Parsear una línea individual"""
        msg_type = cls.identify_message_type(line)
        
        if msg_type == MessageType.ORDER:
            return cls.parse_order_line(line)
        elif msg_type == MessageType.TRADE:
            return cls.parse_trade_line(line)
        elif msg_type == MessageType.QUOTE:
            return cls.parse_quote_line(line)
        elif msg_type == MessageType.SHORTINFO:
            return cls.parse_shortinfo_line(line)
        elif msg_type == MessageType.POSITION:
            return cls.parse_position_line(line)
        
        return None
    
    @classmethod
    def parse_order_line(cls, line: str) -> Optional[ParsedOrder]:
        """
        Parsear línea de orden
        Formato: %ORDER id seq symbol side type qty filled remaining price route status time flags account user source
        """
        try:
            parts = line.strip().split()
            if len(parts) < 13:
                return None
            
            return ParsedOrder(
                order_id=parts[1],
                sequence=int(parts[2]),
                symbol=parts[3],
                side=parts[4],
                order_type=parts[5],
                quantity=int(parts[6]),
                filled=int(parts[7]),
                remaining=int(parts[8]),
                price=float(parts[9]),
                route=parts[10],
                status=parts[11],
                time=parts[12],
                account=parts[14] if len(parts) > 14 else None,
                user=parts[15] if len(parts) > 15 else None,
                source=parts[16] if len(parts) > 16 else None
            )
        except (IndexError, ValueError) as e:
            return None
    
    @classmethod
    def parse_trade_line(cls, line: str) -> Optional[ParsedTrade]:
        """
        Parsear línea de trade
        Formato: %TRADE id symbol side qty price route time tradeid flags pnl commission
        """
        try:
            parts = line.strip().split()
            if len(parts) < 8:
                return None
            
            return ParsedTrade(
                trade_id=parts[1],
                symbol=parts[2],
                side=parts[3],
                quantity=int(parts[4]),
                price=float(parts[5]),
                route=parts[6],
                time=parts[7],
                execution_id=parts[8] if len(parts) > 8 else None,
                pnl=float(parts[10]) if len(parts) > 10 and parts[10] != '-' else 0.0,
                commission=float(parts[11]) if len(parts) > 11 and parts[11] != '-' else 0.0
            )
        except (IndexError, ValueError) as e:
            return None
    
    @classmethod
    def parse_quote_line(cls, line: str) -> Optional[ParsedQuote]:
        """
        Parsear línea de quote
        Formato: $QUOTE symbol bid ask last bidsize asksize volume time
        """
        try:
            parts = line.strip().split()
            if len(parts) < 8:
                return None
            
            return ParsedQuote(
                symbol=parts[1],
                bid=float(parts[2]),
                ask=float(parts[3]),
                last=float(parts[4]),
                bid_size=int(parts[5]),
                ask_size=int(parts[6]),
                volume=int(parts[7]),
                timestamp=parts[8] if len(parts) > 8 else None
            )
        except (IndexError, ValueError) as e:
            return None
    
    @classmethod
    def parse_shortinfo_line(cls, line: str) -> Optional[ParsedShortInfo]:
        """
        Parsear información de short
        Formato: $SHORTINFO symbol shortable shares_available uptick_rule ssr ...
        """
        try:
            parts = line.strip().split()
            if len(parts) < 4:
                return None
            
            return ParsedShortInfo(
                symbol=parts[1],
                shortable=(parts[2] == 'Y'),
                shares_available=int(parts[3]) if parts[3].isdigit() else 0,
                uptick_rule=(parts[4] == 'Y') if len(parts) > 4 else False,
                ssr_triggered=(parts[5] == 'Y') if len(parts) > 5 else False
            )
        except (IndexError, ValueError) as e:
            return None
    
    @classmethod
    def parse_position_line(cls, line: str) -> Optional[ParsedPosition]:
        """
        Parsear línea de posición
        Formato: %POS symbol type qty avgcost initqty initprice realized createtime unrealized
        """
        try:
            parts = line.strip().split()
            if len(parts) < 5:
                return None
            
            return ParsedPosition(
                symbol=parts[1],
                position_type=parts[2],  # L or S
                quantity=int(parts[3]),
                avg_cost=float(parts[4]),
                unrealized_pnl=float(parts[9]) if len(parts) > 9 else 0.0,
                realized_pnl=float(parts[7]) if len(parts) > 7 else 0.0
            )
        except (IndexError, ValueError) as e:
            return None
    
    @classmethod
    def parse_response(cls, response: str) -> Dict[str, List[Any]]:
        """
        Parsear respuesta completa del CMD API
        Retorna un diccionario categorizado por tipo de mensaje
        """
        result = {
            'orders': [],
            'trades': [],
            'quotes': [],
            'positions': [],
            'short_info': [],
            'errors': [],
            'unknown': []
        }
        
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parsed = cls.parse_line(line)
            
            if isinstance(parsed, ParsedOrder):
                result['orders'].append(parsed)
            elif isinstance(parsed, ParsedTrade):
                result['trades'].append(parsed)
            elif isinstance(parsed, ParsedQuote):
                result['quotes'].append(parsed)
            elif isinstance(parsed, ParsedShortInfo):
                result['short_info'].append(parsed)
            elif isinstance(parsed, ParsedPosition):
                result['positions'].append(parsed)
            else:
                # Línea no parseada
                msg_type = cls.identify_message_type(line)
                if msg_type == MessageType.ERROR:
                    result['errors'].append(line)
                elif msg_type != MessageType.UNKNOWN:
                    result['unknown'].append(line)
        
        return result


class SmallCapsParser(DASResponseParser):
    """
    Parser especializado para small caps de Zimtra
    Extiende DASResponseParser con funcionalidad específica
    """
    
    # Small caps típicos de Zimtra
    SMALL_CAPS_SYMBOLS = ['BBLG', 'CIGL', 'HWH', 'BTBD', 'IPDN', 'BTBT', 'BTCS']
    
    @classmethod
    def is_small_cap(cls, symbol: str) -> bool:
        """Verificar si un símbolo es small cap"""
        return symbol.upper() in cls.SMALL_CAPS_SYMBOLS
    
    @classmethod
    def filter_small_caps(cls, parsed_data: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
        """Filtrar solo datos de small caps"""
        filtered = {
            'orders': [],
            'trades': [],
            'quotes': [],
            'positions': [],
            'short_info': []
        }
        
        # Filtrar órdenes
        for order in parsed_data.get('orders', []):
            if cls.is_small_cap(order.symbol):
                filtered['orders'].append(order)
        
        # Filtrar trades
        for trade in parsed_data.get('trades', []):
            if cls.is_small_cap(trade.symbol):
                filtered['trades'].append(trade)
        
        # Filtrar quotes
        for quote in parsed_data.get('quotes', []):
            if cls.is_small_cap(quote.symbol):
                filtered['quotes'].append(quote)
        
        # Filtrar posiciones
        for position in parsed_data.get('positions', []):
            if cls.is_small_cap(position.symbol):
                filtered['positions'].append(position)
        
        # Filtrar short info
        for info in parsed_data.get('short_info', []):
            if cls.is_small_cap(info.symbol):
                filtered['short_info'].append(info)
        
        return filtered
    
    @classmethod
    def get_symbol_summary(cls, parsed_data: Dict[str, List[Any]], symbol: str) -> Dict:
        """Obtener resumen de un símbolo específico"""
        symbol = symbol.upper()
        
        summary = {
            'symbol': symbol,
            'total_orders': 0,
            'executed_orders': 0,
            'canceled_orders': 0,
            'total_volume': 0,
            'avg_price': 0.0,
            'price_range': {'min': float('inf'), 'max': 0.0},
            'trades': [],
            'positions': []
        }
        
        # Analizar órdenes
        orders = [o for o in parsed_data.get('orders', []) if o.symbol == symbol]
        summary['total_orders'] = len(orders)
        
        prices = []
        for order in orders:
            if order.status == 'Executed':
                summary['executed_orders'] += 1
                summary['total_volume'] += order.quantity
                prices.append(order.price)
            elif order.status == 'Canceled':
                summary['canceled_orders'] += 1
            
            # Actualizar rango de precios
            if order.price > 0:
                summary['price_range']['min'] = min(summary['price_range']['min'], order.price)
                summary['price_range']['max'] = max(summary['price_range']['max'], order.price)
        
        # Calcular precio promedio
        if prices:
            summary['avg_price'] = sum(prices) / len(prices)
        
        # Agregar trades
        summary['trades'] = [t for t in parsed_data.get('trades', []) if t.symbol == symbol]
        
        # Agregar posiciones
        summary['positions'] = [p for p in parsed_data.get('positions', []) if p.symbol == symbol]
        
        return summary