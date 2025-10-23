# Trading Sessions and Order Type Limitations

This document explains the different trading sessions and order type limitations in DAS Trader.

## Trading Sessions

DAS Trader supports trading during three main sessions:

### 1. Premarket (Extended Hours)
- **Time:** 4:00 AM - 9:30 AM ET
- **Status:** Extended hours session
- **Liquidity:** Lower than RTH
- **Spreads:** Typically wider

### 2. Regular Trading Hours (RTH)
- **Time:** 9:30 AM - 4:00 PM ET
- **Status:** Main trading session
- **Liquidity:** Highest
- **Spreads:** Tightest

### 3. After-Hours (Extended Hours)
- **Time:** 4:00 PM - 8:00 PM ET
- **Status:** Extended hours session
- **Liquidity:** Lower than RTH
- **Spreads:** Typically wider

## Order Type Restrictions by Session

### Regular Trading Hours (RTH)
✅ **All order types allowed:**
- Market Orders
- Limit Orders
- Stop Market Orders
- Stop Limit Orders
- Trailing Stop Orders
- Peg Orders (Mid, Agg, Primary, etc.)
- Hidden/Reserve Orders

### Extended Hours (Premarket & After-Hours)
⚠️ **RESTRICTED - LIMIT ORDERS ONLY:**
- ✅ Limit Orders **ALLOWED**
- ❌ Market Orders **NOT ALLOWED**
- ❌ Stop Orders **NOT ALLOWED**
- ❌ Stop Limit Orders **NOT ALLOWED**
- ❌ Trailing Stops **NOT ALLOWED**
- ❌ Peg Orders **NOT ALLOWED**

## das-bridge Strategy Behavior

The built-in trading strategies in das-bridge automatically validate sessions and handle restrictions:

### Default Behavior (RTH Only)

By default, strategies will **REJECT** execution during extended hours:

```python
# This will fail in premarket/after-hours
result = await client.strategies.buy_with_risk_stop(
    symbol="AAPL",
    entry_price=150.0,
    stop_price=149.0,
    risk_amount=200.0
)
# Returns: StrategyResult(success=False, message="Cannot execute strategy in premarket...")
```

### Extended Hours Mode

To trade during extended hours, use `allow_extended_hours=True`:

```python
# This will work in premarket/after-hours
result = await client.strategies.buy_with_risk_stop(
    symbol="AAPL",
    entry_price=150.0,
    stop_price=149.0,  # Used ONLY for position sizing
    risk_amount=200.0,
    entry_type="limit",
    allow_extended_hours=True
)
# Entry: ✅ LIMIT order placed
# Stop:  ❌ NOT placed (extended hours restriction)
```

### Extended Hours Behavior Details

When `allow_extended_hours=True`:

1. **Entry Orders:**
   - Only LIMIT orders are placed
   - Market orders are converted to LIMIT
   - Price based on `entry_type` (mid/bid/ask/limit)

2. **Stop Orders:**
   - **NOT PLACED** during extended hours
   - `stop_price` is used for position sizing only
   - User receives warning with suggested stop price
   - User must manually place stop or wait for RTH

3. **Target Orders:**
   - ✅ PLACED if specified (limit orders allowed)
   - Work normally in extended hours

## Examples

### RTH Trading (Full Strategy)
```python
# During 9:30 AM - 4:00 PM ET
result = await client.strategies.buy_with_risk_stop(
    symbol="AAPL",
    entry_price=150.0,
    stop_price=149.0,
    risk_amount=200.0,
    target_price=152.0
)

if result.success:
    print(f"Entry: {result.entry_order_id}")
    print(f"Stop: {result.stop_order_id}")     # ✅ Placed
    print(f"Target: {result.target_order_id}") # ✅ Placed
```

### Premarket Trading (Entry Only)
```python
# During 4:00 AM - 9:30 AM ET
result = await client.strategies.buy_with_risk_stop(
    symbol="AAPL",
    entry_price=150.0,
    stop_price=149.0,  # For position sizing only
    risk_amount=200.0,
    entry_type="limit",
    allow_extended_hours=True
)

if result.success:
    print(f"Entry: {result.entry_order_id}")
    print(f"Stop: {result.stop_order_id}")     # ❌ None
    print(f"Session: {result.details['session']}")  # "premarket"
    print(f"Suggested Stop: ${result.details['suggested_stop']}")
    print(result.message)
    # "Long position opened: 200 shares of AAPL WARNING: Stop order NOT placed..."
```

## Checking Current Session

You can programmatically check the current session:

```python
from das_trader.strategies import get_current_session, is_extended_hours

# Get current session
session = get_current_session()
# Returns: "premarket", "rth", "afterhours", or "closed"

# Check if in extended hours
if is_extended_hours():
    print("Currently in extended hours (premarket or after-hours)")
else:
    print("Currently in RTH or market is closed")
```

## Validate Order Types

You can validate if an order type is allowed in current session:

```python
from das_trader.strategies import validate_order_type_for_session
from das_trader.constants import OrderType

# Check if stop order allowed now
is_valid, message = validate_order_type_for_session(OrderType.STOP_MARKET)

if not is_valid:
    print(f"Cannot place stop order: {message}")
```

## Best Practices

### For Extended Hours Trading

1. **Always use LIMIT orders** - Market orders will be rejected
2. **Manual stop management** - Place stops when RTH opens or use mental stops
3. **Consider liquidity** - Extended hours have lower volume
4. **Watch spreads** - Bid-ask spreads are typically wider
5. **Use GTC orders** - DAY orders may not work in extended hours

### Risk Management in Extended Hours

```python
# Calculate position size (same as RTH)
shares = client.risk.calculate_shares_for_risk(
    entry_price=150.0,
    stop_price=149.0,
    risk_dollars=200.0
)

# Place entry in premarket
result = await client.strategies.buy_with_risk_stop(
    symbol="AAPL",
    entry_price=150.0,
    stop_price=149.0,
    risk_amount=200.0,
    entry_type="limit",
    allow_extended_hours=True
)

if result.success:
    suggested_stop = result.details['suggested_stop']

    # Option 1: Use mental stop
    print(f"Mental stop: ${suggested_stop}")

    # Option 2: Set alert to place stop at 9:30 AM
    print(f"Place stop order at 9:30 AM: ${suggested_stop}")

    # Option 3: Place stop immediately when RTH opens
    # (implement scheduled task to place stop at 9:30 AM)
```

## Session Transition Handling

### Premarket → RTH (9:30 AM)
- Premarket limit orders remain active
- Now you can place stop orders
- Consider placing protective stops immediately

### RTH → After-Hours (4:00 PM)
- Active stop orders may still execute briefly
- Consider canceling stops or closing positions
- After-hours: only limit orders allowed

## Common Errors

### Error: "Stop orders are not allowed in premarket"
```python
# ❌ Wrong - trying to use stop in premarket without flag
result = await client.strategies.buy_with_risk_stop(...)

# ✅ Correct - use allow_extended_hours=True
result = await client.strategies.buy_with_risk_stop(
    ...,
    allow_extended_hours=True
)
```

### Error: "Extended hours requires entry_type to be 'limit'"
```python
# ❌ Wrong - market not allowed in extended hours
entry_type="market"

# ✅ Correct - use limit, bid, ask, or mid
entry_type="limit"
```

## Summary Table

| Feature | RTH | Premarket | After-Hours |
|---------|-----|-----------|-------------|
| Time | 9:30 AM - 4:00 PM | 4:00 AM - 9:30 AM | 4:00 PM - 8:00 PM |
| Limit Orders | ✅ | ✅ | ✅ |
| Market Orders | ✅ | ❌ | ❌ |
| Stop Orders | ✅ | ❌ | ❌ |
| Trailing Stops | ✅ | ❌ | ❌ |
| das-bridge Strategies (default) | ✅ | ❌ (rejected) | ❌ (rejected) |
| das-bridge Strategies (with flag) | ✅ | ✅ (entry only) | ✅ (entry only) |
| Auto Stop Placement | ✅ | ❌ | ❌ |
| Target Placement | ✅ | ✅ | ✅ |

## Additional Resources

- [DAS Trader Documentation](https://dastrader.com)
- [Premarket Trading Guide](premarket.py)
- [Risk Management Examples](../examples/risk_based_trading.py)
