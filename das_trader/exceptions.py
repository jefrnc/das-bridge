"""Custom exceptions for DAS Trader API client."""


class DASAPIError(Exception):
    """Base exception for all DAS API related errors."""
    pass


class DASConnectionError(DASAPIError):
    """Raised when connection to DAS API fails."""
    pass


class DASAuthenticationError(DASAPIError):
    """Raised when authentication with DAS API fails."""
    pass


class DASOrderError(DASAPIError):
    """Raised when order operations fail."""
    pass


class DASMarketDataError(DASAPIError):
    """Raised when market data operations fail."""
    pass


class DASPositionError(DASAPIError):
    """Raised when position operations fail."""
    pass


class DASTimeoutError(DASAPIError):
    """Raised when API operations timeout."""
    pass


class DASInvalidSymbolError(DASAPIError):
    """Raised when an invalid symbol is provided."""
    pass


class DASInsufficientFundsError(DASAPIError):
    """Raised when there are insufficient funds for an operation."""
    pass