"""Enhanced exception handling for DAS Trader API based on short-fade-das patterns."""

from typing import Optional, Dict, Any, List
from decimal import Decimal


class DASBaseException(Exception):
    """Base exception for all DAS-related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        retry_after: Optional[float] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.retry_after = retry_after

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
            "retry_after": self.retry_after
        }


class DASConnectionError(DASBaseException):
    """Connection-related errors."""

    def __init__(
        self,
        message: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        retry_after: Optional[float] = None
    ):
        context = {}
        if host:
            context["host"] = host
        if port:
            context["port"] = port

        super().__init__(message, "CONNECTION_ERROR", context, retry_after)


class DASAuthenticationError(DASBaseException):
    """Authentication-related errors."""

    def __init__(
        self,
        message: str,
        username: Optional[str] = None,
        account: Optional[str] = None
    ):
        context = {}
        if username:
            context["username"] = username
        if account:
            context["account"] = account

        super().__init__(message, "AUTH_ERROR", context)


class DASTimeoutError(DASBaseException):
    """Timeout-related errors."""

    def __init__(
        self,
        message: str,
        timeout_duration: Optional[float] = None,
        operation: Optional[str] = None
    ):
        context = {}
        if timeout_duration:
            context["timeout_duration"] = timeout_duration
        if operation:
            context["operation"] = operation

        super().__init__(message, "TIMEOUT_ERROR", context, retry_after=5.0)


class DASOrderError(DASBaseException):
    """Order-related errors."""

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        quantity: Optional[int] = None,
        price: Optional[Decimal] = None,
        reject_reason: Optional[str] = None
    ):
        context = {}
        if order_id:
            context["order_id"] = order_id
        if symbol:
            context["symbol"] = symbol
        if quantity:
            context["quantity"] = quantity
        if price:
            context["price"] = str(price)
        if reject_reason:
            context["reject_reason"] = reject_reason

        super().__init__(message, "ORDER_ERROR", context)


class DASPositionError(DASBaseException):
    """Position-related errors."""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        current_position: Optional[int] = None,
        available_shares: Optional[int] = None
    ):
        context = {}
        if symbol:
            context["symbol"] = symbol
        if current_position is not None:
            context["current_position"] = current_position
        if available_shares is not None:
            context["available_shares"] = available_shares

        super().__init__(message, "POSITION_ERROR", context)


class DASMarketDataError(DASBaseException):
    """Market data related errors."""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        data_type: Optional[str] = None
    ):
        context = {}
        if symbol:
            context["symbol"] = symbol
        if data_type:
            context["data_type"] = data_type

        super().__init__(message, "MARKET_DATA_ERROR", context, retry_after=2.0)


class DASInvalidSymbolError(DASBaseException):
    """Invalid symbol errors."""

    def __init__(self, message: str, symbol: Optional[str] = None):
        context = {}
        if symbol:
            context["symbol"] = symbol

        super().__init__(message, "INVALID_SYMBOL", context)


class DASRateLimitError(DASBaseException):
    """Rate limiting errors."""

    def __init__(
        self,
        message: str,
        rate_limit: Optional[int] = None,
        reset_time: Optional[float] = None
    ):
        context = {}
        if rate_limit:
            context["rate_limit"] = rate_limit
        if reset_time:
            context["reset_time"] = reset_time

        retry_after = reset_time if reset_time else 60.0
        super().__init__(message, "RATE_LIMIT", context, retry_after)


class DASInsufficientFundsError(DASBaseException):
    """Insufficient funds errors."""

    def __init__(
        self,
        message: str,
        required_amount: Optional[Decimal] = None,
        available_amount: Optional[Decimal] = None,
        symbol: Optional[str] = None
    ):
        context = {}
        if required_amount:
            context["required_amount"] = str(required_amount)
        if available_amount:
            context["available_amount"] = str(available_amount)
        if symbol:
            context["symbol"] = symbol

        super().__init__(message, "INSUFFICIENT_FUNDS", context)


class DASLocateError(DASBaseException):
    """Short locate related errors."""

    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        quantity: Optional[int] = None,
        rate: Optional[Decimal] = None
    ):
        context = {}
        if symbol:
            context["symbol"] = symbol
        if quantity:
            context["quantity"] = quantity
        if rate:
            context["rate"] = str(rate)

        super().__init__(message, "LOCATE_ERROR", context, retry_after=10.0)


class DASServerError(DASBaseException):
    """DAS server-side errors."""

    def __init__(
        self,
        message: str,
        server_code: Optional[str] = None,
        server_message: Optional[str] = None
    ):
        context = {}
        if server_code:
            context["server_code"] = server_code
        if server_message:
            context["server_message"] = server_message

        super().__init__(message, "SERVER_ERROR", context, retry_after=30.0)


class DASValidationError(DASBaseException):
    """Input validation errors."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        expected: Optional[str] = None
    ):
        context = {}
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = str(value)
        if expected:
            context["expected"] = expected

        super().__init__(message, "VALIDATION_ERROR", context)


class DASConfigurationError(DASBaseException):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[str] = None
    ):
        context = {}
        if config_key:
            context["config_key"] = config_key
        if config_value:
            context["config_value"] = config_value

        super().__init__(message, "CONFIG_ERROR", context)


# Convenience function to categorize DAS error responses
def categorize_das_error(error_message: str) -> DASBaseException:
    """Categorize a DAS error message into appropriate exception type."""
    error_lower = error_message.lower()

    # Order rejections
    if any(phrase in error_lower for phrase in [
        "insufficient buying power", "insufficient funds", "not enough buying power"
    ]):
        return DASInsufficientFundsError(error_message)

    if any(phrase in error_lower for phrase in [
        "invalid symbol", "symbol not found", "unknown symbol"
    ]):
        return DASInvalidSymbolError(error_message)

    if any(phrase in error_lower for phrase in [
        "order rejected", "reject", "cannot place order"
    ]):
        return DASOrderError(error_message)

    if any(phrase in error_lower for phrase in [
        "locate", "short", "not shortable"
    ]):
        return DASLocateError(error_message)

    if any(phrase in error_lower for phrase in [
        "timeout", "timed out", "request timeout"
    ]):
        return DASTimeoutError(error_message)

    if any(phrase in error_lower for phrase in [
        "connection", "disconnect", "network", "socket"
    ]):
        return DASConnectionError(error_message)

    if any(phrase in error_lower for phrase in [
        "authentication", "login", "invalid credentials", "unauthorized"
    ]):
        return DASAuthenticationError(error_message)

    if any(phrase in error_lower for phrase in [
        "rate limit", "too many requests", "throttled"
    ]):
        return DASRateLimitError(error_message)

    if any(phrase in error_lower for phrase in [
        "server error", "internal error", "service unavailable"
    ]):
        return DASServerError(error_message)

    # Default to base exception
    return DASBaseException(error_message, "UNKNOWN_ERROR")


# Exception hierarchy for easier catching
class DASRecoverableError(DASBaseException):
    """Base class for errors that can be retried."""
    pass


class DASNonRecoverableError(DASBaseException):
    """Base class for errors that should not be retried."""
    pass


# Update existing exceptions to inherit from appropriate base
DASTimeoutError.__bases__ = (DASRecoverableError,)
DASConnectionError.__bases__ = (DASRecoverableError,)
DASRateLimitError.__bases__ = (DASRecoverableError,)
DASServerError.__bases__ = (DASRecoverableError,)
DASMarketDataError.__bases__ = (DASRecoverableError,)

DASAuthenticationError.__bases__ = (DASNonRecoverableError,)
DASValidationError.__bases__ = (DASNonRecoverableError,)
DASConfigurationError.__bases__ = (DASNonRecoverableError,)
DASInvalidSymbolError.__bases__ = (DASNonRecoverableError,)