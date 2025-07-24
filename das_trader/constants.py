"""Constants and enumerations for DAS Trader API."""

from enum import Enum, auto


class OrderType(Enum):
    # Order types from DAS manual
    MARKET = "MKT"
    LIMIT = "LIMIT"
    STOP = "STOPMKT"
    STOP_LIMIT = "STOPLMT"
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
    TIME_SALES = "T&S"


class ChartType(Enum):
    """Chart data types."""
    DAY = "DAY"
    MINUTE = "MINUTE"
    TICK = "TICK"


class Commands:
    """DAS API command constants."""
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    
    CHECK_CONNECTION = "CHECKCONNECTION"
    ECHO = "ECHO"
    ECHO_ON = "ECHO ON"
    ECHO_OFF = "ECHO OFF"
    CLIENT = "CLIENT"
    QUIT = "QUIT"
    
    NEW_ORDER = "NEWORDER"
    CANCEL_ORDER = "CANCEL"
    CANCEL_ALL = "CANCELALL"
    REPLACE_ORDER = "REPLACE"
    
    POS_REFRESH = "POSREFRESH"
    
    GET_BP = "GET BP"
    GET_SHORT_INFO = "GET SHORTINFO"
    
    SUBSCRIBE = "SUBSCRIBE"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    GET_QUOTE = "GETQUOTE"
    GET_CHART = "GETCHART"
    
    SCRIPT = "SCRIPT"
    GLOBAL_SCRIPT = "SCRIPT GLOBALSCRIPT"
    
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
    BUYING_POWER = "%BP"
    SHORT_INFO = "%SHORTINFO"
    LOCATE_INFO = "%LOCATEINFO"
    LOCATE_RETURN = "%SLRET"
    LOCATE_ORDER = "%SLOrder"
    LOCATE_AVAIL = "$SLAvailQueryRet"


DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9910
DEFAULT_TIMEOUT = 30.0
DEFAULT_HEARTBEAT_INTERVAL = 30.0
DEFAULT_RECONNECT_DELAY = 5.0
MAX_RECONNECT_ATTEMPTS = 10
BUFFER_SIZE = 4096
MESSAGE_DELIMITER = "\r\n"