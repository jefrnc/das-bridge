"""Example configuration file for DAS Trader API client."""

from das_trader.constants import TimeInForce, Exchange

# Connection Settings
DAS_HOST = "localhost"
DAS_PORT = 9910
DAS_TIMEOUT = 30.0
DAS_HEARTBEAT_INTERVAL = 30.0
DAS_AUTO_RECONNECT = True
DAS_USE_SSL = False

# Authentication (DO NOT COMMIT THESE VALUES)
# Use environment variables or a separate config file
DAS_USERNAME = "TU_USUARIO_DAS"
DAS_PASSWORD = "TU_PASSWORD_DAS"
DAS_ACCOUNT = "TU_CUENTA_DAS"

# Trading Settings
DEFAULT_ORDER_TIMEOUT = 60.0
DEFAULT_TIME_IN_FORCE = TimeInForce.DAY
DEFAULT_EXCHANGE = Exchange.AUTO
ENABLE_ORDER_CONFIRMATIONS = True

# Risk Management
MAX_POSITION_SIZE = 1000
MAX_ORDER_VALUE = 50000.0
STOP_LOSS_PERCENT = 0.02  # 2%
TAKE_PROFIT_PERCENT = 0.04  # 4%

# Market Data Settings
ENABLE_LEVEL1_QUOTES = True
ENABLE_LEVEL2_QUOTES = False
ENABLE_TIME_SALES = False
MAX_QUOTE_HISTORY = 1000
MAX_CHART_BARS = 500

# Logging Settings
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_TO_FILE = True
LOG_FILE_PATH = "das_trader.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# Performance Settings
MESSAGE_QUEUE_SIZE = 10000
THREAD_POOL_SIZE = 4
ENABLE_UVLOOP = True  # Use uvloop on Unix systems

# Monitoring Settings
ENABLE_METRICS = False
METRICS_PORT = 8000
HEALTH_CHECK_INTERVAL = 60.0

# Feature Flags
ENABLE_SHORT_SELLING = True
ENABLE_LOCATE_TRACKING = True
ENABLE_SCRIPT_EXECUTION = False
ENABLE_HISTORICAL_DATA = True

# Data Storage (if enabled)
DATABASE_URL = "sqlite:///das_trader.db"
ENABLE_ORDER_HISTORY = True
ENABLE_POSITION_HISTORY = True
ENABLE_TRADE_HISTORY = True

# Notification Settings
ENABLE_NOTIFICATIONS = False
NOTIFICATION_TYPE = "email"  # "email", "discord", "telegram", "pushover", "webhook", "desktop"

# Email Notifications
EMAIL_SMTP_HOST = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587
EMAIL_USERNAME = "tu_email@gmail.com"
EMAIL_PASSWORD = "tu_app_password"
EMAIL_TO_ADDRESSES = ["tu_email_trading@gmail.com"]
EMAIL_USE_TLS = True

# Discord Notifications
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/TU_WEBHOOK_ID/TU_TOKEN"

# Telegram Notifications
TELEGRAM_BOT_TOKEN = "TU_BOT_TOKEN"
TELEGRAM_CHAT_ID = "TU_CHAT_ID"

# Pushover Notifications (mobile push)
PUSHOVER_USER_KEY = "TU_USER_KEY"
PUSHOVER_APP_TOKEN = "TU_APP_TOKEN"

# Slack Notifications
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/TU/SLACK/WEBHOOK"

# Generic Webhook
CUSTOM_WEBHOOK_URL = "https://tu-servidor.com/webhook"
WEBHOOK_HEADERS = {"Authorization": "Bearer TU_TOKEN"}

# Desktop Notifications (Windows/macOS/Linux)
ENABLE_DESKTOP_NOTIFICATIONS = True
DESKTOP_NOTIFICATION_SOUND = True

# Paper Trading Mode
PAPER_TRADING_MODE = False
PAPER_TRADING_INITIAL_BALANCE = 100000.0

# Symbols Configuration
WATCHLIST_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "META", "NVDA", "NFLX", "CRM", "ZOOM"
]

EXCLUDED_SYMBOLS = [
    # Add any symbols you want to exclude from trading
]

# Trading Schedule
MARKET_OPEN_TIME = "09:30"  # EST
MARKET_CLOSE_TIME = "16:00"  # EST
ENABLE_PREMARKET_TRADING = False
ENABLE_AFTERHOURS_TRADING = False

# Algorithm Settings (for trading bots)
MOMENTUM_LOOKBACK_PERIODS = 10
MOMENTUM_THRESHOLD = 0.001  # 0.1%
VOLATILITY_THRESHOLD = 0.02  # 2%
MIN_VOLUME_THRESHOLD = 100000

# Position Sizing
POSITION_SIZING_METHOD = "fixed"  # "fixed", "percent_equity", "volatility_adjusted"
FIXED_POSITION_SIZE = 100
PERCENT_EQUITY_RISK = 0.01  # 1% of equity per trade
VOLATILITY_LOOKBACK = 20

# Commission and Fees
COMMISSION_PER_SHARE = 0.005
MINIMUM_COMMISSION = 1.00
SEC_FEE_RATE = 0.0000221  # Current SEC fee rate
TAF_FEE_RATE = 0.000145   # Current TAF fee rate