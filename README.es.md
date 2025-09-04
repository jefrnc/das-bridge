# DAS Trader Python API Client

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

[English](README.md) | [Español](README.es.md)

</div>

Cliente Python completo para la API CMD de DAS Trader Pro que permite trading automatizado, gestión de órdenes en tiempo real, seguimiento de posiciones y streaming de market data.

## 🚀 Características Principales

- **Trading Completo**: Envío, modificación y cancelación de órdenes (Market, Limit, Stop, Peg, etc.)
- **Market Data en Tiempo Real**: Streaming de Level 1, Level 2 y Time & Sales
- **Gestión de Posiciones**: Seguimiento automático de posiciones y P&L en tiempo real
- **Datos Históricos**: Acceso a gráficos diarios y por minutos
- **Reconexión Automática**: Manejo robusto de conexiones con reconexión automática
- **Notificaciones Multi-plataforma**: 7 tipos diferentes de notificaciones
- **Asyncio Nativo**: Alto rendimiento con operaciones concurrentes
- **Type Safety**: Completamente tipado para mejor soporte de IDE
- **Logging Detallado**: Sistema de logging comprehensivo para debugging

## 📋 Requisitos

- Python 3.8+
- DAS Trader Pro con CMD API habilitado
- Cuenta válida de DAS Trader

## ⚡ Instalación Rápida

```bash
git clone https://github.com/jefrnc/das-bridge.git
cd das-bridge
pip install -e .
```

### Dependencias Opcionales

```bash
# Para notificaciones
pip install aiohttp

# Para análisis de datos
pip install numpy pandas matplotlib

# Para notificaciones de escritorio en Windows
pip install win10toast  # Solo Windows

# Para gestión de configuración
pip install python-dotenv
```

## 🔧 Configuración

### 1. Variables de Entorno
```bash
cp .env.example .env
# Edita .env con tus credenciales
```

### 2. Configuración Básica
```python
# .env
DAS_HOST=localhost
DAS_PORT=9910
DAS_USERNAME=tu_usuario_das
DAS_PASSWORD=tu_password_das
DAS_ACCOUNT=tu_cuenta_das
```

## 🎯 Uso Básico

```python
import asyncio
from das_trader import DASTraderClient, OrderSide, OrderType, MarketDataLevel

async def main():
    # Crear cliente
    client = DASTraderClient(host="localhost", port=9910)
    
    try:
        # Conectar a DAS Trader
        await client.connect("tu_usuario", "tu_password", "tu_cuenta")
        
        # Obtener buying power
        bp = await client.get_buying_power()
        print(f"Buying Power: ${bp['buying_power']:,.2f}")
        
        # Suscribirse a market data
        await client.subscribe_quote("AAPL", MarketDataLevel.LEVEL1)
        
        # Obtener cotización
        quote = await client.get_quote("AAPL")
        print(f"AAPL: Bid ${quote.bid} | Ask ${quote.ask} | Last ${quote.last}")
        
        # Enviar orden
        order_id = await client.send_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=150.00
        )
        print(f"Orden enviada: {order_id}")
        
        # Verificar posiciones
        positions = client.get_positions()
        for pos in positions:
            if not pos.is_flat():
                print(f"{pos.symbol}: {pos.quantity} shares, "
                      f"P&L: ${pos.unrealized_pnl:.2f}")
        
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📊 Tipos de Órdenes Soportadas

```python
# Market Order
await client.send_order("AAPL", OrderSide.BUY, 100, OrderType.MARKET)

# Limit Order
await client.send_order("AAPL", OrderSide.BUY, 100, OrderType.LIMIT, price=150.00)

# Stop Loss
await client.send_order("AAPL", OrderSide.SELL, 100, OrderType.STOP, stop_price=145.00)

# Stop Limit
await client.send_order("AAPL", OrderSide.SELL, 100, OrderType.STOP_LIMIT, 
                       price=148.00, stop_price=145.00)

# Trailing Stop
await client.send_order("AAPL", OrderSide.SELL, 100, OrderType.TRAILING_STOP,
                       trail_amount=2.00)
```

## 📱 Sistema de Notificaciones

Soporta 7 tipos diferentes de notificaciones:

### 📧 Email
```python
NOTIFICATION_TYPE=email
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_USERNAME=tu_email@gmail.com
EMAIL_PASSWORD=tu_app_password
```

### 🎮 Discord
```python
NOTIFICATION_TYPE=discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/TU_ID/TU_TOKEN
```

### 📱 Telegram
```python
NOTIFICATION_TYPE=telegram
TELEGRAM_BOT_TOKEN=tu_bot_token
TELEGRAM_CHAT_ID=tu_chat_id
```

### 📲 Pushover (Notificaciones Móviles)
```python
NOTIFICATION_TYPE=pushover
PUSHOVER_USER_KEY=tu_user_key
PUSHOVER_APP_TOKEN=tu_app_token
```

### 💼 Slack
```python
NOTIFICATION_TYPE=slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/TU/WEBHOOK
```

### 🖥️ Desktop (Windows/macOS/Linux)
```python
NOTIFICATION_TYPE=desktop
ENABLE_DESKTOP_NOTIFICATIONS=true
```

### 🌐 Webhook Personalizado
```python
NOTIFICATION_TYPE=webhook
CUSTOM_WEBHOOK_URL=https://tu-servidor.com/webhook
WEBHOOK_AUTH_TOKEN=tu_token
```

## 📈 Callbacks y Eventos

```python
# Callbacks para órdenes
def on_order_filled(order):
    print(f"Orden completada: {order.symbol}")

def on_order_rejected(order):
    print(f"Orden rechazada: {order.symbol}")

client.orders.register_callback("order_filled", on_order_filled)
client.orders.register_callback("order_rejected", on_order_rejected)

# Callbacks para posiciones
def on_position_update(position):
    print(f"Posición actualizada: {position.symbol} P&L: ${position.unrealized_pnl:.2f}")

client.positions.register_callback("position_updated", on_position_update)

# Callbacks para market data
def on_quote_update(quote):
    print(f"{quote.symbol}: ${quote.last}")

client.market_data.register_callback("quote_update", on_quote_update)
```

## 🤖 Ejemplos Avanzados

### Trading Bot Básico
```python
# Ver examples/trading_bot.py
python examples/trading_bot.py
```

### Monitor de Portfolio
```python
# Ver examples/portfolio_monitor.py
python examples/portfolio_monitor.py
```

### Streaming de Market Data
```python
# Ver examples/market_data_streaming.py
python examples/market_data_streaming.py
```

### Sistema de Notificaciones
```python
# Ver examples/notifications_example.py
python examples/notifications_example.py
```

## 🛡️ Gestión de Riesgos

```python
# Configuración en config.example.py
MAX_POSITION_SIZE = 1000
MAX_ORDER_VALUE = 50000.0
STOP_LOSS_PERCENT = 0.02  # 2%
TAKE_PROFIT_PERCENT = 0.04  # 4%

# Paper Trading Mode
PAPER_TRADING_MODE = True
PAPER_TRADING_INITIAL_BALANCE = 100000.0
```

## 📚 Documentación de la API

### Clases Principales

- **`DASTraderClient`**: Cliente principal para interactuar con DAS Trader
- **`OrderManager`**: Gestión de órdenes y tracking de estado
- **`PositionManager`**: Seguimiento de posiciones y P&L
- **`MarketDataManager`**: Streaming y cache de market data
- **`ConnectionManager`**: Manejo de conexiones TCP y reconexión
- **`NotificationManager`**: Sistema de notificaciones multi-plataforma

### Enums Principales

- **`OrderType`**: MARKET, LIMIT, STOP, STOP_LIMIT, PEG, TRAILING_STOP
- **`OrderSide`**: BUY, SELL, SHORT, COVER
- **`OrderStatus`**: PENDING, NEW, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED
- **`TimeInForce`**: DAY, GTC, IOC, FOK, MOO, MOC
- **`MarketDataLevel`**: LEVEL1, LEVEL2, TIME_SALES

## 🧪 Testing

```bash
# Ejecutar tests
pytest tests/ -v

# Con coverage
pytest tests/ --cov=das_trader --cov-report=html
```

## 🔐 Seguridad

- **Nunca** commities credenciales en el código
- Usa variables de entorno para configuración sensible
- El archivo `.env` está en `.gitignore`
- Considera usar paper trading mode para pruebas

## 📝 Logging

```python
import logging
logging.basicConfig(level=logging.INFO)

# El cliente incluye logging detallado:
# - Conexiones y autenticación
# - Órdenes enviadas y recibidas
# - Market data streaming
# - Errores y reconexiones
```

## 🤝 Contribuciones

Las contribuciones son bienvenidas! Por favor:

1. Fork el repositorio
2. Crea una branch para tu feature (`git checkout -b feature/nueva-caracteristica`)
3. Commit tus cambios (`git commit -am 'Agrega nueva característica'`)
4. Push a la branch (`git push origin feature/nueva-caracteristica`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## ⚠️ Disclaimer

Este software es para propósitos educativos y de desarrollo. El trading automatizado conlleva riesgos financieros significativos. Úsalo bajo tu propia responsabilidad y considera siempre:

- Pruebas exhaustivas en paper trading mode
- Gestión adecuada de riesgos
- Monitoreo constante de posiciones
- Cumplimiento de regulaciones locales

## 🔗 Proyectos Relacionados

- **[das-api-examples](https://github.com/jefrnc/das-api-examples)**: Ejemplos prácticos y pruebas para el CMD API de DAS Trader Pro
  - Pruebas de conexión TCP directa
  - Verificación de características del API
  - Guías de configuración y troubleshooting

## 📚 Enlaces Útiles

- [Documentación DAS Trader Pro](https://dastrader.com)
- [CMD API Manual](CMD%20API%20Manual.pdf)
- [Ejemplos de Uso](examples/)
- [Tests](tests/)

## 📞 Soporte

Para reportar bugs o solicitar features:
- Abre un [Issue](https://github.com/jefrnc/das-bridge/issues)
- Revisa la [documentación](examples/)
- Consulta los [ejemplos](examples/)

---

**Desarrollado con ❤️ para la comunidad de trading algorítmico**