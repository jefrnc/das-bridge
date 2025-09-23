"""Configuration management for DAS Trader API inspired by short-fade-das patterns."""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class DASConnectionConfig:
    """DAS connection configuration."""
    host: str = "localhost"
    port: int = 9910
    timeout: float = 30.0
    heartbeat_interval: float = 30.0
    auto_reconnect: bool = True
    use_ssl: bool = False

    # Resilience settings
    max_reconnect_attempts: int = 10
    health_check_interval: float = 60.0
    command_timeout: float = 10.0


@dataclass
class DASCredentials:
    """DAS authentication credentials."""
    username: str = ""
    password: str = ""
    account: str = ""

    def is_complete(self) -> bool:
        """Check if all required credentials are provided."""
        return bool(self.username and self.password and self.account)

    def mask_password(self) -> Dict[str, str]:
        """Return credentials with masked password for logging."""
        return {
            "username": self.username,
            "password": "***" if self.password else "",
            "account": self.account
        }


@dataclass
class DASLoggingConfig:
    """DAS logging configuration."""
    enabled: bool = True
    log_dir: str = "logs"
    max_log_size: int = 50 * 1024 * 1024  # 50MB
    backup_count: int = 5
    log_level: str = "INFO"
    structured_logging: bool = True
    console_output: bool = True


@dataclass
class DASTradingConfig:
    """DAS trading configuration."""
    max_position_size: Decimal = Decimal("1000")
    max_order_size: Decimal = Decimal("100")
    default_time_in_force: str = "DAY"
    default_exchange: str = "AUTO"
    enable_notifications: bool = False
    risk_checks: bool = True


@dataclass
class DASNotificationConfig:
    """DAS notification configuration."""
    enabled: bool = False
    telegram_token: str = ""
    telegram_chat_id: str = ""
    email_enabled: bool = False
    email_smtp_server: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_recipients: list = field(default_factory=list)


class DASConfigManager:
    """Configuration manager for DAS Trader API."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "das_config.json"
        self._config_cache: Optional[Dict[str, Any]] = None

        # Configuration objects
        self.connection = DASConnectionConfig()
        self.credentials = DASCredentials()
        self.logging = DASLoggingConfig()
        self.trading = DASTradingConfig()
        self.notifications = DASNotificationConfig()

    def load_config(self, config_file: Optional[str] = None) -> bool:
        """Load configuration from file and environment variables."""
        if config_file:
            self.config_file = config_file

        try:
            # Load from file first
            if Path(self.config_file).exists():
                self._load_from_file()
                logger.info(f"✅ Loaded config from {self.config_file}")
            else:
                logger.warning(f"⚠️ Config file {self.config_file} not found, using defaults")

            # Override with environment variables
            self._load_from_environment()

            # Validate configuration
            validation_errors = self._validate_config()
            if validation_errors:
                logger.error(f"❌ Config validation errors: {validation_errors}")
                return False

            logger.info("✅ Configuration loaded and validated successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            return False

    def _load_from_file(self):
        """Load configuration from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)

            # Update configuration objects
            if "connection" in config_data:
                self._update_dataclass(self.connection, config_data["connection"])

            if "credentials" in config_data:
                self._update_dataclass(self.credentials, config_data["credentials"])

            if "logging" in config_data:
                self._update_dataclass(self.logging, config_data["logging"])

            if "trading" in config_data:
                # Handle Decimal fields in trading config
                trading_data = config_data["trading"].copy()
                for field_name in ["max_position_size", "max_order_size"]:
                    if field_name in trading_data:
                        trading_data[field_name] = Decimal(str(trading_data[field_name]))
                self._update_dataclass(self.trading, trading_data)

            if "notifications" in config_data:
                self._update_dataclass(self.notifications, config_data["notifications"])

        except Exception as e:
            logger.error(f"Failed to load config from file: {e}")
            raise

    def _load_from_environment(self):
        """Load configuration from environment variables."""
        # Connection settings
        if os.getenv("DAS_HOST"):
            self.connection.host = os.getenv("DAS_HOST")
        if os.getenv("DAS_PORT"):
            self.connection.port = int(os.getenv("DAS_PORT"))
        if os.getenv("DAS_TIMEOUT"):
            self.connection.timeout = float(os.getenv("DAS_TIMEOUT"))
        if os.getenv("DAS_AUTO_RECONNECT"):
            self.connection.auto_reconnect = os.getenv("DAS_AUTO_RECONNECT").lower() == "true"

        # Credentials (most important - usually from env vars)
        if os.getenv("DAS_USERNAME"):
            self.credentials.username = os.getenv("DAS_USERNAME")
        if os.getenv("DAS_PASSWORD"):
            self.credentials.password = os.getenv("DAS_PASSWORD")
        if os.getenv("DAS_ACCOUNT"):
            self.credentials.account = os.getenv("DAS_ACCOUNT")

        # Logging settings
        if os.getenv("DAS_LOG_DIR"):
            self.logging.log_dir = os.getenv("DAS_LOG_DIR")
        if os.getenv("DAS_LOG_LEVEL"):
            self.logging.log_level = os.getenv("DAS_LOG_LEVEL")

        # Trading settings
        if os.getenv("DAS_MAX_POSITION_SIZE"):
            self.trading.max_position_size = Decimal(os.getenv("DAS_MAX_POSITION_SIZE"))
        if os.getenv("DAS_MAX_ORDER_SIZE"):
            self.trading.max_order_size = Decimal(os.getenv("DAS_MAX_ORDER_SIZE"))

        # Notification settings
        if os.getenv("DAS_NOTIFICATIONS_ENABLED"):
            self.notifications.enabled = os.getenv("DAS_NOTIFICATIONS_ENABLED").lower() == "true"
        if os.getenv("TELEGRAM_TOKEN"):
            self.notifications.telegram_token = os.getenv("TELEGRAM_TOKEN")
        if os.getenv("TELEGRAM_CHAT_ID"):
            self.notifications.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    def _update_dataclass(self, obj, data: Dict[str, Any]):
        """Update dataclass object with dictionary data."""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

    def _validate_config(self) -> list:
        """Validate configuration and return list of errors."""
        errors = []

        # Validate connection
        if self.connection.port < 1 or self.connection.port > 65535:
            errors.append("Invalid port number")

        if self.connection.timeout <= 0:
            errors.append("Timeout must be positive")

        # Validate credentials
        if not self.credentials.is_complete():
            errors.append("Incomplete credentials (username, password, account required)")

        # Validate trading limits
        if self.trading.max_position_size <= 0:
            errors.append("Max position size must be positive")

        if self.trading.max_order_size <= 0:
            errors.append("Max order size must be positive")

        # Validate logging
        if not self.logging.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            errors.append("Invalid log level")

        return errors

    def save_config(self, config_file: Optional[str] = None) -> bool:
        """Save current configuration to file."""
        if config_file:
            self.config_file = config_file

        try:
            config_data = {
                "connection": self._dataclass_to_dict(self.connection),
                "credentials": self._dataclass_to_dict(self.credentials),
                "logging": self._dataclass_to_dict(self.logging),
                "trading": self._dataclass_to_dict(self.trading),
                "notifications": self._dataclass_to_dict(self.notifications)
            }

            # Convert Decimal to string for JSON serialization
            if "max_position_size" in config_data["trading"]:
                config_data["trading"]["max_position_size"] = str(config_data["trading"]["max_position_size"])
            if "max_order_size" in config_data["trading"]:
                config_data["trading"]["max_order_size"] = str(config_data["trading"]["max_order_size"])

            # Create directory if it doesn't exist
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)

            logger.info(f"✅ Configuration saved to {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to save configuration: {e}")
            return False

    def _dataclass_to_dict(self, obj) -> Dict[str, Any]:
        """Convert dataclass to dictionary."""
        result = {}
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            if isinstance(value, Decimal):
                result[field_name] = str(value)
            else:
                result[field_name] = value
        return result

    def create_sample_config(self, config_file: Optional[str] = None) -> bool:
        """Create a sample configuration file."""
        if config_file:
            self.config_file = config_file

        try:
            sample_config = {
                "connection": {
                    "host": "localhost",
                    "port": 9910,
                    "timeout": 30.0,
                    "heartbeat_interval": 30.0,
                    "auto_reconnect": True,
                    "use_ssl": False,
                    "max_reconnect_attempts": 10,
                    "health_check_interval": 60.0,
                    "command_timeout": 10.0
                },
                "credentials": {
                    "username": "your_username",
                    "password": "your_password",
                    "account": "your_account"
                },
                "logging": {
                    "enabled": True,
                    "log_dir": "logs",
                    "max_log_size": 52428800,
                    "backup_count": 5,
                    "log_level": "INFO",
                    "structured_logging": True,
                    "console_output": True
                },
                "trading": {
                    "max_position_size": "1000.00",
                    "max_order_size": "100.00",
                    "default_time_in_force": "DAY",
                    "default_exchange": "AUTO",
                    "enable_notifications": False,
                    "risk_checks": True
                },
                "notifications": {
                    "enabled": False,
                    "telegram_token": "your_telegram_bot_token",
                    "telegram_chat_id": "your_telegram_chat_id",
                    "email_enabled": False,
                    "email_smtp_server": "smtp.gmail.com",
                    "email_smtp_port": 587,
                    "email_username": "your_email@gmail.com",
                    "email_password": "your_email_password",
                    "email_recipients": ["recipient@example.com"]
                }
            }

            # Create directory if it doesn't exist
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w') as f:
                json.dump(sample_config, f, indent=2)

            logger.info(f"✅ Sample configuration created at {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create sample configuration: {e}")
            return False

    def get_client_config(self) -> Dict[str, Any]:
        """Get configuration for DAS client initialization."""
        return {
            "host": self.connection.host,
            "port": self.connection.port,
            "timeout": self.connection.timeout,
            "heartbeat_interval": self.connection.heartbeat_interval,
            "auto_reconnect": self.connection.auto_reconnect,
            "log_level": self.logging.log_level,
            "notification_config": self._get_notification_config() if self.notifications.enabled else None
        }

    def _get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration dictionary."""
        config = {}

        if self.notifications.telegram_token and self.notifications.telegram_chat_id:
            config["telegram"] = {
                "token": self.notifications.telegram_token,
                "chat_id": self.notifications.telegram_chat_id
            }

        if self.notifications.email_enabled:
            config["email"] = {
                "smtp_server": self.notifications.email_smtp_server,
                "smtp_port": self.notifications.email_smtp_port,
                "username": self.notifications.email_username,
                "password": self.notifications.email_password,
                "recipients": self.notifications.email_recipients
            }

        return config

    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary for display."""
        return {
            "connection": f"{self.connection.host}:{self.connection.port}",
            "account": self.credentials.account,
            "auto_reconnect": self.connection.auto_reconnect,
            "logging_enabled": self.logging.enabled,
            "log_level": self.logging.log_level,
            "notifications_enabled": self.notifications.enabled,
            "max_position_size": str(self.trading.max_position_size),
            "max_order_size": str(self.trading.max_order_size),
            "config_file": self.config_file
        }

    def print_summary(self):
        """Print configuration summary."""
        summary = self.get_summary()
        print("\n📋 DAS Configuration Summary")
        print("=" * 40)
        for key, value in summary.items():
            key_formatted = key.replace("_", " ").title()
            print(f"{key_formatted:20}: {value}")
        print()


# Global config manager instance
das_config = DASConfigManager()


def load_das_config(config_file: Optional[str] = None) -> DASConfigManager:
    """Load DAS configuration (convenience function)."""
    global das_config

    if config_file or not das_config._config_cache:
        das_config.load_config(config_file)

    return das_config