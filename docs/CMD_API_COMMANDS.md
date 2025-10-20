# DAS Trader CMD API - Comandos Válidos

Última actualización: 2025-10-20

## Comandos Probados y Funcionando

### Información General
| Comando | Descripción | Ejemplo de Respuesta |
|---------|-------------|---------------------|
| `HELP` | Muestra ayuda disponible | Lista de comandos disponibles |

### Información de Cuenta
| Comando | Descripción | Formato de Respuesta |
|---------|-------------|---------------------|
| `GET BP` | Obtener buying power | `BP [buying_power] [overnight_bp]` |
| `GET ACCOUNTINFO` | Información completa de cuenta | Múltiples líneas con info de cuenta |
| `GET POSITIONS` | Posiciones abiertas | `%POS [symbol] [type] [qty] [avgcost] ...` |
| `GET ORDERS` | Órdenes activas | `%ORDER [id] [seq] [symbol] [side] ...` |
| `GET TRADES` | Trades del día | `%TRADE [id] [symbol] [side] [qty] ...` |

### Market Data
| Comando | Descripción | Formato de Respuesta |
|---------|-------------|---------------------|
| `SB [symbol] Lv1` | Subscribe a Level 1 | Datos de mercado en tiempo real |
| `SB [symbol] tms` | Subscribe a Time and Sales | `$T&S [symbol] [price] [volume] ...` |
| `SB [symbol] Lv2` | Subscribe a Level 2 | `$Lv2 [symbol] [condition] [MMID] [price] [size]` |
| `SB [symbol] Minchart` | Subscribe a Minute Chart (OHLCV) | `$Chart [symbol] ...` |
| `SB [symbol] Daychart` | Subscribe a Day Chart (OHLCV) | `$Chart [symbol] ...` |
| `SB [symbol] Tickchart` | Subscribe a Tick Chart | `$Chart [symbol] ...` |
| `UNSB [symbol] Lv1` | Unsubscribe de Level 1 | Confirmación |
| `UNSB [symbol] tms` | Unsubscribe de Time and Sales | Confirmación |
| `UNSB [symbol] Lv2` | Unsubscribe de Level 2 | Confirmación |
| `UNSB [symbol] Minchart` | Unsubscribe de Minute Chart | Confirmación |
| `UNSB [symbol] Daychart` | Unsubscribe de Day Chart | Confirmación |
| `UNSB [symbol] Tickchart` | Unsubscribe de Tick Chart | Confirmación |
| `GET SHORTINFO [symbol]` | Info de short para símbolo | `$SHORTINFO [symbol] [Y/N] [shares] ...` |

### Trading (Órdenes)
| Comando | Descripción | Formato |
|---------|-------------|---------|
| `Neworder` | Enviar nueva orden | Ver documentación de órdenes |

## Comandos que NO Funcionan

Los siguientes comandos devuelven "INVALD COMMAND!" o error similar:

- `GETCHART [symbol]` - No existe, usar `SB [symbol] Minchart/Daychart/Tickchart` en su lugar
- `GET QUOTE [symbol]` - No existe, usar subscribe Level 1 en su lugar
- `GET ORDER [symbol]` - Usar `GET ORDERS` sin símbolo
- `GET TRADE [symbol]` - Usar `GET TRADES` sin símbolo
- `GET LV1 [symbol]` - Usar `SB [symbol] Lv1`
- `ISSHORTABLE [symbol]` - Usar `GET SHORTINFO [symbol]`
- `PING` - No implementado
- `GET POS` - Usar `GET POSITIONS`
- `GET ACCOUNT` - Usar `GET ACCOUNTINFO`

## Notas Importantes

1. **Autenticación**: El login debe ser: `LOGIN [username] [password] [account]`

2. **Permisos**: El mensaje "No Permission for API FEED" indica falta de permisos para market data. Contactar soporte de DAS.

3. **Small Caps**: Para símbolos como BBLG, CIGL, HWH, usar los mismos comandos pero los datos pueden ser limitados.

4. **Time and Sales**: El comando correcto es `SB [symbol] tms` (minúsculas), **NO** `T&S`. Las respuestas del servidor usan el prefijo `$T&S`.
   - ✓ Correcto: `SB AAPL tms`
   - ✗ Incorrecto: `SB AAPL T&S`

5. **Formato de respuestas**:
   - Las órdenes empiezan con `%ORDER`
   - Los trades empiezan con `%TRADE`
   - Las posiciones empiezan con `%POS`
   - Info de short empieza con `$SHORTINFO`
   - Time and Sales empieza con `$T&S`

## Ejemplo de Uso

```python
import socket

# Conectar
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('10.211.55.3', 9910))

# Login
sock.send(b"LOGIN ZIMDASE9C64 password ZIMDASE9C64\r\n")

# Obtener buying power
sock.send(b"GET BP\r\n")

# Obtener órdenes
sock.send(b"GET ORDERS\r\n")

# Subscribe a market data
sock.send(b"SB CIGL Lv1\r\n")
```

## Parsers Disponibles

Los parsers en `das_trader.parsers` pueden procesar automáticamente las respuestas:

- `DASResponseParser.parse_response()` - Parser principal
- `SmallCapsParser` - Parser especializado para small caps
- Tipos de datos: `ParsedOrder`, `ParsedTrade`, `ParsedPosition`, `ParsedShortInfo`