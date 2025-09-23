"""Enhanced DAS Logger based on short-fade-das logging patterns."""

import json
import logging
import os
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, Union
from logging.handlers import RotatingFileHandler


class DASLogLevel(Enum):
    """DAS-specific log levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"
    COMMAND = "COMMAND"
    RESPONSE = "RESPONSE"
    CONNECTION = "CONNECTION"
    ORDER = "ORDER"
    POSITION = "POSITION"
    MARKET_DATA = "MARKET_DATA"


class DASLogEntry:
    """Structured log entry for DAS interactions."""

    def __init__(
        self,
        level: DASLogLevel,
        action: str,
        symbol: Optional[str] = None,
        command: Optional[str] = None,
        response: Optional[str] = None,
        error: Optional[str] = None,
        duration: Optional[float] = None,
        order_id: Optional[str] = None,
        price: Optional[float] = None,
        quantity: Optional[int] = None,
        account_id: Optional[str] = None,
        session_id: Optional[str] = None,
        raw_data: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.timestamp = datetime.now()
        self.level = level
        self.action = action
        self.symbol = symbol
        self.command = command
        self.response = response
        self.error = error
        self.duration = duration
        self.order_id = order_id
        self.price = price
        self.quantity = quantity
        self.account_id = account_id
        self.session_id = session_id
        self.raw_data = raw_data
        self.context = context or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary."""
        data = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "action": self.action,
        }

        # Only include non-None fields
        optional_fields = [
            "symbol", "command", "response", "error", "order_id",
            "price", "quantity", "account_id", "session_id", "raw_data"
        ]

        for field in optional_fields:
            value = getattr(self, field)
            if value is not None:
                data[field] = value

        if self.duration is not None:
            data["duration"] = f"{self.duration:.3f}s"

        if self.context:
            data["context"] = self.context

        return data

    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict(), indent=None, separators=(',', ':'))


class EnhancedDASLogger:
    """Enhanced DAS Logger with structured logging and rotation."""

    def __init__(
        self,
        account_id: str,
        log_dir: str = "logs",
        max_log_size: int = 50 * 1024 * 1024,  # 50MB
        backup_count: int = 5,
        session_id: Optional[str] = None
    ):
        self.account_id = account_id
        self.session_id = session_id or self._generate_session_id()
        self.log_dir = Path(log_dir)
        self.max_log_size = max_log_size
        self.backup_count = backup_count

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup loggers
        self._setup_loggers()

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return f"das_{int(time.time())}"

    def _setup_loggers(self):
        """Setup different loggers for different types of data."""
        # Main DAS logger with rotation
        self.das_logger = logging.getLogger(f"das.{self.account_id}")
        self.das_logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        self.das_logger.handlers.clear()

        # JSON log file with rotation
        json_log_file = self.log_dir / f"das_{self.account_id}.jsonl"
        json_handler = RotatingFileHandler(
            json_log_file,
            maxBytes=self.max_log_size,
            backupCount=self.backup_count
        )
        json_handler.setLevel(logging.DEBUG)

        # Human-readable log file
        text_log_file = self.log_dir / f"das_{self.account_id}.log"
        text_handler = RotatingFileHandler(
            text_log_file,
            maxBytes=self.max_log_size,
            backupCount=self.backup_count
        )
        text_handler.setLevel(logging.INFO)

        # Formatters
        json_formatter = logging.Formatter('%(message)s')
        text_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )

        json_handler.setFormatter(json_formatter)
        text_handler.setFormatter(text_formatter)

        self.das_logger.addHandler(json_handler)
        self.das_logger.addHandler(text_handler)

        # Console handler for important messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(text_formatter)
        self.das_logger.addHandler(console_handler)

    def log_entry(self, entry: DASLogEntry):
        """Log a structured DAS entry."""
        # JSON log (structured)
        json_data = entry.to_json()
        self.das_logger.debug(json_data)

        # Human-readable log
        msg = self._format_human_readable(entry)

        if entry.level == DASLogLevel.ERROR:
            self.das_logger.error(msg)
        elif entry.level == DASLogLevel.WARNING:
            self.das_logger.warning(msg)
        else:
            self.das_logger.info(msg)

    def _format_human_readable(self, entry: DASLogEntry) -> str:
        """Format log entry for human reading."""
        parts = [f"[{entry.level.value}]", entry.action]

        if entry.symbol:
            parts.append(f"({entry.symbol})")

        if entry.command:
            # Hide passwords in LOGIN commands like short-fade-das
            cmd = entry.command
            if cmd.upper().startswith("LOGIN"):
                cmd_parts = cmd.split()
                if len(cmd_parts) >= 3:
                    cmd_parts[2] = "***"  # Hide password
                    cmd = " ".join(cmd_parts)
            parts.append(f"CMD: {cmd}")

        if entry.order_id:
            parts.append(f"Order: {entry.order_id}")

        if entry.price and entry.quantity:
            parts.append(f"{entry.quantity}@${entry.price}")

        if entry.duration:
            parts.append(f"({entry.duration:.3f}s)")

        if entry.error:
            parts.append(f"ERROR: {entry.error}")

        return " ".join(parts)

    def log_connection(
        self,
        host: str,
        port: int,
        success: bool,
        error: Optional[Exception] = None,
        duration: Optional[float] = None
    ):
        """Log connection attempt."""
        entry = DASLogEntry(
            level=DASLogLevel.CONNECTION,
            action="CONNECTION_ATTEMPT",
            error=str(error) if error else None,
            duration=duration,
            context={
                "host": host,
                "port": port,
                "success": success
            }
        )
        self.log_entry(entry)

    def log_command(
        self,
        action: str,
        command: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log DAS command."""
        entry = DASLogEntry(
            level=DASLogLevel.COMMAND,
            action=action,
            command=command,
            session_id=self.session_id,
            account_id=self.account_id,
            context=context
        )
        self.log_entry(entry)

    def log_response(
        self,
        action: str,
        response: str,
        duration: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log DAS response."""
        entry = DASLogEntry(
            level=DASLogLevel.RESPONSE,
            action=action,
            response=response[:500] if response else None,  # Truncate long responses
            duration=duration,
            session_id=self.session_id,
            account_id=self.account_id,
            context=context
        )
        self.log_entry(entry)

    def log_order(
        self,
        action: str,
        symbol: str,
        order_id: Optional[str] = None,
        price: Optional[float] = None,
        quantity: Optional[int] = None,
        error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log order-related actions."""
        entry = DASLogEntry(
            level=DASLogLevel.ORDER,
            action=action,
            symbol=symbol,
            order_id=order_id,
            price=price,
            quantity=quantity,
            error=error,
            session_id=self.session_id,
            account_id=self.account_id,
            context=context
        )
        self.log_entry(entry)

    def log_position(
        self,
        action: str,
        symbol: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log position-related actions."""
        entry = DASLogEntry(
            level=DASLogLevel.POSITION,
            action=action,
            symbol=symbol,
            quantity=quantity,
            price=price,
            error=error,
            session_id=self.session_id,
            account_id=self.account_id,
            context=context
        )
        self.log_entry(entry)

    def log_market_data(
        self,
        action: str,
        symbol: str,
        price: Optional[float] = None,
        error: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log market data actions."""
        entry = DASLogEntry(
            level=DASLogLevel.MARKET_DATA,
            action=action,
            symbol=symbol,
            price=price,
            error=error,
            session_id=self.session_id,
            account_id=self.account_id,
            context=context
        )
        self.log_entry(entry)

    def log_error(
        self,
        action: str,
        error: Union[str, Exception],
        context: Optional[Dict[str, Any]] = None
    ):
        """Log error."""
        entry = DASLogEntry(
            level=DASLogLevel.ERROR,
            action=action,
            error=str(error),
            session_id=self.session_id,
            account_id=self.account_id,
            context=context
        )
        self.log_entry(entry)

    def log_debug(
        self,
        action: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log debug information."""
        entry = DASLogEntry(
            level=DASLogLevel.DEBUG,
            action=action,
            raw_data=message,
            session_id=self.session_id,
            account_id=self.account_id,
            context=context
        )
        self.log_entry(entry)

    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        json_log_file = self.log_dir / f"das_{self.account_id}.jsonl"
        text_log_file = self.log_dir / f"das_{self.account_id}.log"

        stats = {
            "session_id": self.session_id,
            "account_id": self.account_id,
            "log_dir": str(self.log_dir),
            "json_log_size": json_log_file.stat().st_size if json_log_file.exists() else 0,
            "text_log_size": text_log_file.stat().st_size if text_log_file.exists() else 0,
        }

        return stats