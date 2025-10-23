# Known Issues

This document tracks known limitations and issues with the DAS Trader CMD API integration.

## DAS Trader Crashes on Multiple SLPRICEINQUIRE Commands

**Severity**: CRITICAL
**Status**: UNFIXABLE (DAS API limitation)
**Discovered**: 2025-10-21
**Affected Methods**: `SmartLocateManager.compare_routes()` (now deprecated)

### Issue Description

DAS Trader disconnects and crashes when multiple `SLPRICEINQUIRE` commands are sent in sequence, regardless of the delay between commands. The first command succeeds, but the second command causes a "Connection reset by peer" error and DAS Trader terminates.

### Evidence

Test file `test_two_locates.py` demonstrates the crash:

```
COMMAND #1: SLPRICEINQUIRE GSIT 100 ALLROUTE
✅ SUCCESS - Rate: $0.000625/share

[Waiting 5 seconds...]

COMMAND #2: SLPRICEINQUIRE GSIT 100 ARCA
❌ TIMEOUT → Connection reset by peer → DAS CRASHED
```

**Error Message**:
```
Connection lost: [Errno 54] Connection reset by peer
TimeoutError: Timeout waiting for response to command: SLPRICEINQUIRE GSIT 100 ARCA
```

### Test Files

The following test files were created to isolate and confirm the issue:

- `test_single_locate.py` - ✅ Single command works fine
- `test_two_locates.py` - ❌ Second command crashes DAS
- `test_locate_step_by_step.py` - ❌ Crashes on second command

### Root Cause

This is a limitation of the DAS Trader CMD API. The API cannot handle multiple `SLPRICEINQUIRE` commands in the same session, regardless of:
- Delay between commands (tested with 5+ second delays)
- Different routes (ALLROUTE, ARCA, NASDAQ, etc.)
- Different symbols

### Impact

- **Route comparison**: Cannot compare locate prices across multiple routes
- **Price shopping**: Cannot find the cheapest route for locates
- **Smart routing**: Must use a single route for all locate inquiries

### Workaround

**Use only `ALLROUTE` for locate price inquiries:**

```python
# ✅ SAFE - Single inquiry with ALLROUTE
locate_info = await client.inquire_locate_price(
    symbol="GSIT",
    shares=100,
    route="ALLROUTE"
)
```

**Do NOT attempt multiple inquiries:**

```python
# ❌ DANGEROUS - Will crash DAS on second command
locate1 = await client.inquire_locate_price("GSIT", 100, "ALLROUTE")
locate2 = await client.inquire_locate_price("GSIT", 100, "ARCA")  # CRASH!
```

### Deprecated Methods

Due to this issue, the following methods have been deprecated:

#### `SmartLocateManager.compare_routes()`

This method attempted to compare locate prices across multiple routes but would crash DAS on the second query. The method now returns an error dictionary and logs a warning:

```python
{
    "success": False,
    "error": "compare_routes() is deprecated - causes DAS to crash",
    "message": "Multiple SLPRICEINQUIRE commands cause DAS to disconnect. "
               "Use client.inquire_locate_price(symbol, shares, 'ALLROUTE') instead.",
    "workaround": "Use ALLROUTE only for locate pricing"
}
```

### Recommended Usage

Use the `SmartLocateManager.analyze_locate()` method which safely uses a single `SLPRICEINQUIRE` command with `ALLROUTE`:

```python
# ✅ Recommended approach
analysis = await client.locate_manager.analyze_locate(
    symbol="GSIT",
    shares=100
)

if analysis["success"]:
    print(f"Locate rate: ${analysis['locate_rate']:.6f}/share")
    print(f"Total cost: ${analysis['locate_total_cost']:.2f}")
    print(f"Recommendation: {analysis['recommendation']}")
```

### Future Considerations

- Monitor DAS API updates for possible fixes
- Consider alternative APIs if route comparison becomes critical
- Document any other commands that may have similar limitations

### References

- See `locate_manager.py:354-397` for deprecated `compare_routes()` implementation
- Test files in repository root demonstrate the crash behavior
- Git history preserves original implementation before deprecation
