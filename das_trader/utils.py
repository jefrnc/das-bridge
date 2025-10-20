"""Utility functions for DAS Trader API client."""

import asyncio
import hashlib
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from functools import wraps

logger = logging.getLogger(__name__)


def parse_decimal(value: Union[str, float, int, None]) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def format_price(price: Union[float, Decimal]) -> str:
    # DAS expects 4 decimal places
    return f"{float(price):.4f}"


def format_quantity(quantity: Union[int, float]) -> str:
    return str(int(quantity))


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse various timestamp formats from DAS API."""
    formats = [
        "%Y%m%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y%m%d%H%M%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    
    return None


def generate_order_id() -> str:
    # Simple order ID generation
    # TODO: Maybe use UUID instead?
    timestamp = str(time.time()).encode()
    return hashlib.md5(timestamp).hexdigest()[:16]


def parse_message(message: str) -> Dict[str, Any]:
    """Parse a message from DAS API into structured data."""
    message = message.strip()
    # print(f"DEBUG: Parsing message: {message[:50]}...")  # debug

    # Determine message type by prefix
    if message.startswith("%"):
        return parse_control_message(message)
    elif message.startswith("$"):
        return parse_data_message(message)
    elif message.startswith("#"):
        return parse_sync_message(message)
    elif message.startswith("ERROR"):
        return {"type": "ERROR", "message": message[6:].strip()}
    elif message.startswith("WARNING"):
        return {"type": "WARNING", "message": message[8:].strip()}
    elif message.startswith("INFO"):
        return {"type": "INFO", "message": message[5:].strip()}
    else:
        return {"type": "UNKNOWN", "raw": message}


def parse_control_message(message: str) -> Dict[str, Any]:
    """Parse control messages (starting with %)."""
    parts = message.split()
    if not parts:
        return {"type": "UNKNOWN", "raw": message}
    
    msg_type = parts[0]
    
    if msg_type == "%ORDER":
        return parse_order_message(parts[1:])
    elif msg_type == "%OrderAct":
        return parse_order_action_message(parts[1:])
    elif msg_type == "%POS":
        return parse_position_message(parts[1:])
    elif msg_type == "%BP":
        return parse_buying_power_message(parts[1:])
    elif msg_type == "%SHORTINFO":
        return parse_short_info_message(parts[1:])
    elif msg_type == "%LOCATEINFO":
        return parse_locate_info_message(parts[1:])
    elif msg_type == "%SLRET":
        return parse_locate_return_message(parts[1:])
    elif msg_type == "%SLOrder":
        return parse_locate_order_message(parts[1:])
    elif msg_type == "%IORDER":
        return parse_watch_order_message(parts[1:])
    elif msg_type == "%IPOS":
        return parse_watch_position_message(parts[1:])
    elif msg_type == "%ITRADE":
        return parse_watch_trade_message(parts[1:])
    else:
        return {"type": msg_type, "data": parts[1:]}


def parse_data_message(message: str) -> Dict[str, Any]:
    """Parse data messages (starting with $)."""
    parts = message.split()
    if not parts:
        return {"type": "UNKNOWN", "raw": message}

    msg_type = parts[0]

    if msg_type == "$Quote":
        return parse_quote_message(parts[1:])
    elif msg_type == "$Lv2":
        return parse_level2_message(parts[1:])
    elif msg_type == "$T&S":
        return parse_time_sales_message(parts[1:])
    elif msg_type == "$Chart" or msg_type == "$Bar":
        return parse_chart_message(parts[1:])
    elif msg_type == "$LDLU":
        return parse_limit_down_up_message(parts[1:])
    elif msg_type == "$SLAvailQueryRet":
        return parse_locate_avail_message(parts[1:])
    else:
        return {"type": msg_type, "data": parts[1:]}


def parse_sync_message(message: str) -> Dict[str, Any]:
    """Parse synchronization/control messages (starting with #)."""
    message = message.strip()

    # Handle various sync messages from DAS
    if message.startswith("#Welcome"):
        return {"type": "WELCOME", "message": message[1:]}
    elif message.startswith("#LOGIN SUCCESSED"):
        return {"type": "LOGIN", "success": True, "message": "Login successful"}
    elif message.startswith("#LOGIN FAILED"):
        return {"type": "LOGIN", "success": False, "message": "Login failed"}
    elif message == "#POS" or message.startswith("#POS "):
        return {"type": "POS_START", "raw": message}
    elif message == "#POSEND":
        return {"type": "POS_END"}
    elif message == "#Order" or message.startswith("#Order "):
        return {"type": "ORDER_START", "raw": message}
    elif message == "#OrderEnd":
        return {"type": "ORDER_END"}
    elif message == "#Trade" or message.startswith("#Trade "):
        return {"type": "TRADE_START", "raw": message}
    elif message == "#TradeEnd":
        return {"type": "TRADE_END"}
    elif message == "#SLOrder" or message.startswith("#SLOrder "):
        return {"type": "SLORDER_START", "raw": message}
    elif message == "#SLOrderEnd" or message == "#LOrderEnd":
        return {"type": "SLORDER_END"}
    elif message.startswith("#OrderServer:"):
        # Connection status messages
        parts = message[1:].split(":")
        return {
            "type": "CONNECTION_STATUS",
            "server": "order",
            "event": parts[1] if len(parts) > 1 else "",
            "status": parts[2] if len(parts) > 2 else "",
            "message": message
        }
    elif message.startswith("#QuoteServer:"):
        # Connection status messages
        parts = message[1:].split(":")
        return {
            "type": "CONNECTION_STATUS",
            "server": "quote",
            "event": parts[1] if len(parts) > 1 else "",
            "status": parts[2] if len(parts) > 2 else "",
            "message": message
        }
    else:
        # Generic sync message
        return {"type": "SYNC", "message": message[1:]}


def parse_order_message(parts: List[str]) -> Dict[str, Any]:
    # Parse order updates from DAS
    # Format: %ORDER id token symbol side type qty lvqty cxlqty price route status time origoid account trader source
    # Example: %ORDER 71003 189 GSIT B L 10 0 10 15.37 EDUPRO Canceled 11:57:03 0 YOUR_ACCOUNT YOUR_ACCOUNT Hotkey
    try:
        return {
            "type": "ORDER",
            "order_id": parts[0] if len(parts) > 0 else None,
            "token": parts[1] if len(parts) > 1 else None,
            "symbol": parts[2] if len(parts) > 2 else None,
            "side": parts[3] if len(parts) > 3 else None,  # B, S, SS, BC, SC, etc.
            "order_type": parts[4] if len(parts) > 4 else None,  # L=Limit, M=Market, etc.
            "quantity": int(parts[5]) if len(parts) > 5 else 0,
            "leaves_qty": int(parts[6]) if len(parts) > 6 else 0,  # Remaining unfilled quantity
            "cancelled_qty": int(parts[7]) if len(parts) > 7 else 0,
            "price": parse_decimal(parts[8]) if len(parts) > 8 else None,
            "route": parts[9] if len(parts) > 9 else None,
            "status": parts[10] if len(parts) > 10 else None,
            "time": parts[11] if len(parts) > 11 else None,
            "orig_order_id": parts[12] if len(parts) > 12 else None,
            "account": parts[13] if len(parts) > 13 else None,
            "trader": parts[14] if len(parts) > 14 else None,
            "source": parts[15] if len(parts) > 15 else None,
        }
    except Exception as e:
        logger.error(f"Error parsing order message: {e}, parts: {parts}")
        return {"type": "ORDER", "error": str(e), "raw": parts}


def parse_order_action_message(parts: List[str]) -> Dict[str, Any]:
    try:
        return {
            "type": "ORDER_ACTION",
            "order_id": parts[0] if len(parts) > 0 else None,
            "action": parts[1] if len(parts) > 1 else None,
            "status": parts[2] if len(parts) > 2 else None,
            "details": " ".join(parts[3:]) if len(parts) > 3 else None,
        }
    except Exception as e:
        logger.error(f"Error parsing order action message: {e}")
        return {"type": "ORDER_ACTION", "error": str(e), "raw": parts}


def parse_position_message(parts: List[str]) -> Dict[str, Any]:
    try:
        qty = int(parts[1]) if len(parts) > 1 else 0
        avg_cost = parse_decimal(parts[2]) if len(parts) > 2 else Decimal("0")
        current_price = parse_decimal(parts[3]) if len(parts) > 3 else Decimal("0")
        
        return {
            "type": "POSITION",
            "symbol": parts[0] if len(parts) > 0 else None,
            "quantity": qty,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "pnl": parse_decimal(parts[4]) if len(parts) > 4 else None,
            "pnl_percent": parse_decimal(parts[5]) if len(parts) > 5 else None,
            "market_value": qty * current_price if qty and current_price else Decimal("0"),
        }
    except Exception as e:
        logger.error(f"Error parsing position message: {e}")
        return {"type": "POSITION", "error": str(e), "raw": parts}


def parse_quote_message(parts: List[str]) -> Dict[str, Any]:
    # Parse Level 1 quotes
    # Format: $Quote Symbol Bid Ask Last Volume ...
    try:
        return {
            "type": "QUOTE",
            "symbol": parts[0] if len(parts) > 0 else None,
            "bid": parse_decimal(parts[1]) if len(parts) > 1 else None,
            "ask": parse_decimal(parts[2]) if len(parts) > 2 else None,
            "last": parse_decimal(parts[3]) if len(parts) > 3 else None,
            "volume": int(parts[4]) if len(parts) > 4 else 0,
            "bid_size": int(parts[5]) if len(parts) > 5 else 0,
            "ask_size": int(parts[6]) if len(parts) > 6 else 0,
            "timestamp": parse_timestamp(" ".join(parts[7:9])) if len(parts) > 8 else None,
        }
    except Exception as e:
        logger.error(f"Error parsing quote message: {e}")
        return {"type": "QUOTE", "error": str(e), "raw": parts}


def parse_level2_message(parts: List[str]) -> Dict[str, Any]:
    """Parse a Level 2 market depth message."""
    # Format: $Lv2 Symbol Side Price Size MMID ...
    try:
        return {
            "type": "LEVEL2",
            "symbol": parts[0] if len(parts) > 0 else None,
            "side": parts[1] if len(parts) > 1 else None,
            "price": parse_decimal(parts[2]) if len(parts) > 2 else None,
            "size": int(parts[3]) if len(parts) > 3 else 0,
            "mmid": parts[4] if len(parts) > 4 else None,
            "timestamp": parse_timestamp(" ".join(parts[5:7])) if len(parts) > 6 else None,
        }
    except Exception as e:
        logger.error(f"Error parsing level2 message: {e}")
        return {"type": "LEVEL2", "error": str(e), "raw": parts}


def parse_time_sales_message(parts: List[str]) -> Dict[str, Any]:
    """Parse a time and sales message."""
    # Format: $T&S Symbol Price Size Time ...
    try:
        return {
            "type": "TIME_SALES",
            "symbol": parts[0] if len(parts) > 0 else None,
            "price": parse_decimal(parts[1]) if len(parts) > 1 else None,
            "size": int(parts[2]) if len(parts) > 2 else 0,
            "timestamp": parse_timestamp(parts[3]) if len(parts) > 3 else None,
            "condition": parts[4] if len(parts) > 4 else None,
        }
    except Exception as e:
        logger.error(f"Error parsing time sales message: {e}")
        return {"type": "TIME_SALES", "error": str(e), "raw": parts}


def parse_chart_message(parts: List[str]) -> Dict[str, Any]:
    """Parse a chart data message."""
    # Format: $Chart Symbol Type Open High Low Close Volume Time
    try:
        return {
            "type": "CHART",
            "symbol": parts[0] if len(parts) > 0 else None,
            "chart_type": parts[1] if len(parts) > 1 else None,
            "open": parse_decimal(parts[2]) if len(parts) > 2 else None,
            "high": parse_decimal(parts[3]) if len(parts) > 3 else None,
            "low": parse_decimal(parts[4]) if len(parts) > 4 else None,
            "close": parse_decimal(parts[5]) if len(parts) > 5 else None,
            "volume": int(parts[6]) if len(parts) > 6 else 0,
            "timestamp": parse_timestamp(parts[7]) if len(parts) > 7 else None,
        }
    except Exception as e:
        logger.error(f"Error parsing chart message: {e}")
        return {"type": "CHART", "error": str(e), "raw": parts}


def parse_buying_power_message(parts: List[str]) -> Dict[str, Any]:
    """Parse a buying power message with multi-line support."""
    # Format: %BP BuyingPower DayTradingBP ... OR multi-line BP response
    try:
        return {
            "type": "BUYING_POWER",
            "buying_power": parse_decimal(parts[0]) if len(parts) > 0 else None,
            "day_trading_bp": parse_decimal(parts[1]) if len(parts) > 1 else None,
            "overnight_bp": parse_decimal(parts[2]) if len(parts) > 2 else None,
            "cash": parse_decimal(parts[3]) if len(parts) > 3 else None,
        }
    except Exception as e:
        logger.error(f"Error parsing buying power message: {e}")
        return {"type": "BUYING_POWER", "error": str(e), "raw": parts}


def parse_buying_power_response(response: str) -> Dict[str, Any]:
    """Parse buying power response with multiple format support like short-fade-das."""
    try:
        # Single line format: "BP 12345.67"
        if response.startswith("BP "):
            bp_str = response.strip().replace("BP ", "")
            return {
                "type": "BUYING_POWER",
                "buying_power": parse_decimal(bp_str),
                "success": True
            }

        # Multi-line format: search for BP in each line
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("BP "):
                bp_str = line.replace("BP ", "")
                return {
                    "type": "BUYING_POWER",
                    "buying_power": parse_decimal(bp_str),
                    "success": True
                }

        # No BP found
        return {
            "type": "BUYING_POWER",
            "buying_power": None,
            "success": False,
            "error": "No BP data found in response"
        }

    except Exception as e:
        logger.error(f"Error parsing buying power response: {e}")
        return {
            "type": "BUYING_POWER",
            "buying_power": None,
            "success": False,
            "error": str(e)
        }


def parse_short_info_message(parts: List[str]) -> Dict[str, Any]:
    """Parse a short info message."""
    # Format: %SHORTINFO Symbol Shortable Rate ...
    try:
        return {
            "type": "SHORT_INFO",
            "symbol": parts[0] if len(parts) > 0 else None,
            "shortable": parts[1].upper() == "YES" if len(parts) > 1 else False,
            "rate": parse_decimal(parts[2]) if len(parts) > 2 else None,
            "available_shares": int(parts[3]) if len(parts) > 3 else 0,
        }
    except Exception as e:
        logger.error(f"Error parsing short info message: {e}")
        return {"type": "SHORT_INFO", "error": str(e), "raw": parts}


def parse_locate_info_message(parts: List[str]) -> Dict[str, Any]:
    """Parse a locate info message."""
    # Format: %LOCATEINFO Symbol Located Qty Rate ...
    try:
        return {
            "type": "LOCATE_INFO",
            "symbol": parts[0] if len(parts) > 0 else None,
            "located": parts[1].upper() == "YES" if len(parts) > 1 else False,
            "quantity": int(parts[2]) if len(parts) > 2 else 0,
            "rate": parse_decimal(parts[3]) if len(parts) > 3 else None,
            "locate_id": parts[4] if len(parts) > 4 else None,
        }
    except Exception as e:
        logger.error(f"Error parsing locate info message: {e}")
        return {"type": "LOCATE_INFO", "error": str(e), "raw": parts}


def retry_on_error(max_attempts: int = 3, delay: float = 1.0):
    """Decorator to retry async functions on error."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (attempt + 1))
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
            raise last_exception
        return wrapper
    return decorator


def validate_symbol(symbol: str) -> bool:
    """Validate if a symbol is in correct format."""
    if not symbol or not isinstance(symbol, str):
        return False
    
    # Basic validation - alphanumeric, 1-5 characters
    symbol = symbol.strip().upper()
    if len(symbol) < 1 or len(symbol) > 5:
        return False
    
    return symbol.isalnum()


def parse_locate_return_message(parts: List[str]) -> Dict[str, Any]:
    try:
        return {
            "type": "LOCATE_RETURN",
            "symbol": parts[0] if len(parts) > 0 else None,
            "quantity": int(parts[1]) if len(parts) > 1 else 0,
            "rate": parse_decimal(parts[2]) if len(parts) > 2 else None,
            "available": parts[3].upper() == "YES" if len(parts) > 3 else False,
            "route": parts[4] if len(parts) > 4 else None,
        }
    except Exception as e:
        logger.error(f"Error parsing locate return message: {e}")
        return {"type": "LOCATE_RETURN", "error": str(e), "raw": parts}


def parse_locate_order_message(parts: List[str]) -> Dict[str, Any]:
    """Parse a locate order message."""
    # Format: %SLOrder OrderID Symbol Status Details
    try:
        return {
            "type": "LOCATE_ORDER",
            "locate_id": parts[0] if len(parts) > 0 else None,
            "symbol": parts[1] if len(parts) > 1 else None,
            "status": parts[2] if len(parts) > 2 else None,
            "details": " ".join(parts[3:]) if len(parts) > 3 else None,
            "located": parts[2].upper() == "ACCEPTED" if len(parts) > 2 else False,
        }
    except Exception as e:
        logger.error(f"Error parsing locate order message: {e}")
        return {"type": "LOCATE_ORDER", "error": str(e), "raw": parts}


def parse_locate_avail_message(parts: List[str]) -> Dict[str, Any]:
    """Parse a locate availability message."""
    # Format: $SLAvailQueryRet Account Symbol AvailableShares Rate
    try:
        return {
            "type": "LOCATE_AVAIL",
            "account": parts[0] if len(parts) > 0 else None,
            "symbol": parts[1] if len(parts) > 1 else None,
            "available_shares": int(parts[2]) if len(parts) > 2 else 0,
            "rate": parse_decimal(parts[3]) if len(parts) > 3 else None,
        }
    except Exception as e:
        logger.error(f"Error parsing locate avail message: {e}")
        return {"type": "LOCATE_AVAIL", "error": str(e), "raw": parts}


def parse_limit_down_up_message(parts: List[str]) -> Dict[str, Any]:
    """Parse a limit down/up message."""
    # Format: $LDLU Symbol LimitDown LimitUp
    try:
        return {
            "type": "LIMIT_DOWN_UP",
            "symbol": parts[0] if len(parts) > 0 else None,
            "limit_down": parse_decimal(parts[1]) if len(parts) > 1 else None,
            "limit_up": parse_decimal(parts[2]) if len(parts) > 2 else None,
        }
    except Exception as e:
        logger.error(f"Error parsing limit down/up message: {e}")
        return {"type": "LIMIT_DOWN_UP", "error": str(e), "raw": parts}


def parse_watch_order_message(parts: List[str]) -> Dict[str, Any]:
    """Parse a watch mode order message."""
    # Same format as regular order but different type
    result = parse_order_message(parts)
    result["type"] = "WATCH_ORDER"
    return result


def parse_watch_position_message(parts: List[str]) -> Dict[str, Any]:
    """Parse a watch mode position message."""
    # Same format as regular position but different type
    result = parse_position_message(parts)
    result["type"] = "WATCH_POSITION"
    return result


def parse_watch_trade_message(parts: List[str]) -> Dict[str, Any]:
    """Parse a watch mode trade message."""
    # Format: %ITRADE id symbol B/S qty price route time orderid
    try:
        return {
            "type": "WATCH_TRADE",
            "trade_id": parts[0] if len(parts) > 0 else None,
            "symbol": parts[1] if len(parts) > 1 else None,
            "side": parts[2] if len(parts) > 2 else None,
            "quantity": int(parts[3]) if len(parts) > 3 else 0,
            "price": parse_decimal(parts[4]) if len(parts) > 4 else None,
            "route": parts[5] if len(parts) > 5 else None,
            "timestamp": parse_timestamp(parts[6]) if len(parts) > 6 else None,
            "order_id": parts[7] if len(parts) > 7 else None,
        }
    except Exception as e:
        logger.error(f"Error parsing watch trade message: {e}")
        return {"type": "WATCH_TRADE", "error": str(e), "raw": parts}


def calculate_pnl(quantity: int, avg_cost: Decimal, current_price: Decimal) -> Dict[str, Decimal]:
    """Calculate P&L for a position."""
    if quantity == 0:
        return {"realized_pnl": Decimal("0"), "unrealized_pnl": Decimal("0"), "pnl_percent": Decimal("0")}
    
    position_cost = quantity * avg_cost
    current_value = quantity * current_price
    unrealized_pnl = current_value - position_cost
    pnl_percent = (unrealized_pnl / position_cost * 100) if position_cost != 0 else Decimal("0")
    
    return {
        "unrealized_pnl": unrealized_pnl,
        "pnl_percent": pnl_percent,
        "position_cost": position_cost,
        "current_value": current_value,
    }