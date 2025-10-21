# Changelog

All notable changes to das-bridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-10-21

### Added
- **SmartLocateManager**: Intelligent locate management with volume and cost controls
  - Volume control: Limits shares to max % of daily volume (default 1%)
  - Cost control: Rejects locates above configurable thresholds
  - ETB (Easy to Borrow) detection for free locates
  - Safety checks for pricing data integrity
  - Block sizing with 100-share blocks
  - Methods:
    - `analyze_locate()`: Comprehensive locate analysis with cost evaluation
    - `ensure_locate()`: Check availability and optionally auto-purchase
    - `inquire_locate_price()`: Get locate pricing from DAS Trader

### Fixed
- Fixed incorrect parameter in `SmartLocateManager.ensure_locate()` method
  - Changed invalid `price` parameter to correct `route` parameter in `locate_stock()` call
  - Resolves `TypeError` when attempting to purchase locates

### Deprecated
- **SmartLocateManager.compare_routes()**: Method causes DAS Trader to crash
  - Issue: Multiple SLPRICEINQUIRE commands cause DAS to disconnect
  - Workaround: Use single `inquire_locate_price()` with `route="ALLROUTE"`
  - See `KNOWN_ISSUES.md` for details

### Known Issues
- `SLNEWORDER` and `SLAvailQuery` commands timeout during locate purchase
  - This appears to be a DAS API/broker configuration limitation
  - Analysis and price inquiry work correctly
  - Purchase submission may not be confirmed via API

## [0.1.0] - 2025-01-15

### Added
- Initial release
- Complete DAS Trader CMD API client
- Real-time order management
- Position tracking with P&L
- Market data streaming (Level 1, Level 2, Time & Sales)
- Risk management tools and strategies
- Extended hours trading support
- Production-grade logging and error handling
- Configuration management
- Connection resilience with auto-reconnect

[1.2.0]: https://github.com/jefrnc/das-bridge/compare/v1.0.0...v1.2.0
[0.1.0]: https://github.com/jefrnc/das-bridge/releases/tag/v0.1.0
