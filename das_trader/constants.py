"""Constants and enumerations for DAS Trader API."""

from enum import Enum, auto


class OrderType(Enum):
    # Order types from DAS manual and API messages
    # DAS API uses single-letter codes in responses (L, M, S, etc.)
    LIMIT = "L"  # Limit order
    MARKET = "M"  # Market order
    STOP_MARKET = "S"  # Stop market
    STOP_LIMIT = "T"  # Stop limit
    # Full names for order placement (still supported)
    LIMIT_FULL = "LIMIT"
    MARKET_FULL = "MKT"
    STOP_FULL = "STOPMKT"
    STOP_LIMIT_FULL = "STOPLMT"
    STOP_TRAILING = "STOPTRAILING"
    STOP_RANGE = "STOPRANGE"
    STOP_RANGE_MARKET = "STOPRANGEMKT"
    PEG_MID = "PEG MID"
    PEG_AGG = "PEG AGG"
    PEG_PRIM = "PEG PRIM"
    PEG_LAST = "PEG LAST"
    HIDDEN = "HIDDEN"
    RESERVE = "RESERVE"


class OrderSide(Enum):
    BUY = "B"
    SELL = "S"
    SHORT = "SS"
    COVER = "S"
    BUY_TO_OPEN = "BO"
    BUY_TO_CLOSE = "BC"
    SELL_TO_OPEN = "SO"
    SELL_TO_CLOSE = "SC"


class OrderStatus(Enum):
    """Order status states."""
    # NOTE: These statuses come directly from DAS API
    PENDING = "PENDING"
    NEW = "NEW"
    HOLD = "Hold"
    SENDING = "Sending"
    ACCEPTED = "Accepted"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "Executed"
    CANCELLED = "Canceled"
    REJECTED = "Rejected"
    EXPIRED = "EXPIRED"
    REPLACED = "REPLACED"
    TRIGGERED = "Triggered"
    CLOSED = "Closed"


class TimeInForce(Enum):
    DAY = "DAY"
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    GTD = "GTD"  # Good Till Date - TODO: needs date parameter
    MOO = "MOO"  # Market on Open
    MOC = "MOC"  # Market on Close


class Exchange(Enum):
    """Exchange routing options."""
    AUTO = "AUTO"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    ARCA = "ARCA"
    BATS = "BATS"
    IEX = "IEX"
    EDGX = "EDGX"
    DARK = "DARK"


class MarketDataLevel(Enum):
    """Market data subscription levels."""
    LEVEL1 = "Lv1"
    LEVEL2 = "Lv2"
    TIME_SALES = "tms"


class ChartType(Enum):
    """Chart data types."""
    DAY = "Daychart"
    MINUTE = "Minchart"
    TICK = "Tickchart"


class Commands:
    """DAS API command constants."""
    # Authentication
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"

    # System commands
    ECHO = "ECHO"
    ECHO_ON = "ECHO ON"
    ECHO_OFF = "ECHO OFF"
    CLIENT = "CLIENT"
    QUIT = "QUIT"

    # Order management
    NEW_ORDER = "NEWORDER"
    CANCEL_ORDER = "CANCEL"
    CANCEL_ALL = "CANCELALL"
    REPLACE_ORDER = "REPLACE"

    # Position management
    POS_REFRESH = "POSREFRESH"

    # Account info commands
    GET_BP = "GET BP"
    GET_SHORT_INFO = "GET SHORTINFO"
    GET_ACCOUNT_INFO = "GET AccountInfo"
    GET_POSITIONS = "GET POSITIONS"
    GET_ORDERS = "GET ORDERS"
    GET_PENDING_ORDERS = "GET PENDINGORDERS"
    GET_EXECUTED_ORDERS = "GET EXECUTEDORDERS"
    GET_TRADES = "GET TRADES"
    GET_SYM_STATUS = "GET SymStatus"
    GET_LDLU = "GET LDLU"
    GET_ROUTE_STATUS = "GET RouteStatus"
    GET_LOCATES = "GET LOCATES"
    GET_INT_MSGS = "GET INTMSGS"

    # Market data - IMPORTANT: Use subscription model (SB/UNSB), NOT request-response
    SUBSCRIBE = "SB"
    UNSUBSCRIBE = "UNSB"
    SUBSCRIBE_TOPLIST = "SB TopList"  # Para gainers, losers, most active

    # Scripts
    SCRIPT = "SCRIPT"
    GLOBAL_SCRIPT = "SCRIPT GLOBALSCRIPT"

    # Locate management
    LOCATE_STOCK = "SLNEWORDER"
    LOCATE_INQUIRE = "SLPRICEINQUIRE"
    LOCATE_CANCEL = "SLCANCELORDER"
    LOCATE_ACCEPT = "SLOFFEROPERATION"
    LOCATE_QUERY = "SLAvailQuery"
    GET_LOCATE_INFO = "GETLOCATEINFO"


class MessagePrefix:
    """Message prefixes for parsing responses."""
    ORDER = "%ORDER"
    ORDER_ACTION = "%OrderAct"
    POSITION = "%POS"
    QUOTE = "$Quote"
    LEVEL2 = "$Lv2"
    TIME_SALES = "$T&S"
    CHART = "$Chart"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    BUYING_POWER = "BP"
    SHORT_INFO = "$SHORTINFO"
    ACCOUNT_INFO = "$AccountInfo"
    TRADE = "%TRADE"
    SYM_STATUS = "$SymStatus"
    LDLU = "$LDLU"
    ROUTE_STATUS = "$RouteStatus"
    INT_MSG = "$INTMSG"
    LOCATE_INFO = "%LOCATEINFO"
    LOCATE_RETURN = "%SLRET"
    LOCATE_ORDER = "%SLOrder"
    LOCATE_AVAIL = "$SLAvailQueryRet"
    TOPLIST = "$TopList"


DEFAULT_HOST = "192.168.4.242"  # DAS en Parallels/Windows
DEFAULT_PORT = 9910
DEFAULT_TIMEOUT = 30.0
DEFAULT_HEARTBEAT_INTERVAL = 30.0
DEFAULT_RECONNECT_DELAY = 5.0
MAX_RECONNECT_ATTEMPTS = 10
BUFFER_SIZE = 4096
MESSAGE_DELIMITER = "\r\n"