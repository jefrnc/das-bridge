# DAS Trader CMD API - Comandos Válidos

Última actualización: 2025-09-05

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
| `UNSB [symbol] Lv1` | Unsubscribe de Level 1 | Confirmación |
| `GET SHORTINFO [symbol]` | Info de short para símbolo | `$SHORTINFO [symbol] [Y/N] [shares] ...` |

### Trading (Órdenes)
| Comando | Descripción | Formato |
|---------|-------------|---------|
| `Neworder` | Enviar nueva orden | Ver documentación de órdenes |

## Comandos que NO Funcionan

Los siguientes comandos devuelven "INVALD COMMAND!" o error similar:

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

4. **Formato de respuestas**: 
   - Las órdenes empiezan con `%ORDER`
   - Los trades empiezan con `%TRADE`
   - Las posiciones empiezan con `%POS`
   - Info de short empieza con `$SHORTINFO`

## Ejemplo de Uso

```python
import socket

# Conectar
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('10.211.55.3', 9910))

# Login
sock.send(b"LOGIN YOUR_ACCOUNT password YOUR_ACCOUNT\r\n")

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