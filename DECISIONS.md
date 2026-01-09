# Architecture Decisions

## ADR-001: Alerts-Only Architecture
**Status**: Accepted  
**Date**: 2025-01  
**Context**: Initial system design for prediction market monitoring.  
**Decision**: Build alerts-only system with no trading execution until Phase D.  
**Consequences**: 
- Simpler initial implementation
- Lower risk during development
- Clear separation of concerns
- Easy to add execution later

## ADR-002: Multi-Upstream Support
**Status**: Accepted  
**Date**: 2025-01  
**Context**: Need to support multiple data sources (dev, Polymarket, price feeds).  
**Decision**: Implement pluggable upstream architecture with mode selection.  
**Consequences**:
- Single codebase supports multiple sources
- Easy to add new sources
- Requires careful error handling per source
- Configuration complexity increases

## ADR-003: Polymarket CLOB /price Endpoint
**Status**: Accepted  
**Date**: 2025-01  
**Context**: Initial implementation used `/prices-history` which could return empty lists.  
**Decision**: Switch to `/price` endpoint with `side=SELL` for current price only.  
**Consequences**:
- More reliable (always returns current price)
- Simpler response parsing (dict vs list)
- Faster response times
- No historical data (not needed for alerts)

## ADR-004: In-Memory State Only
**Status**: Accepted  
**Date**: 2025-01  
**Context**: Need to track previous probabilities for delta calculation.  
**Decision**: Use in-memory cache, no database persistence.  
**Consequences**:
- Simple implementation
- Fast lookups
- State lost on restart
- Not suitable for long-term analytics
- Acceptable for alerts-only use case

## ADR-005: Pydantic for All Models
**Status**: Accepted  
**Date**: 2025-01  
**Context**: Need type safety and validation throughout.  
**Decision**: Use Pydantic for configuration, events, alerts, and webhooks.  
**Consequences**:
- Strong type safety
- Automatic validation
- Clear data contracts
- Better IDE support
- Fail fast on invalid data

## ADR-006: Automatic Log Redaction
**Status**: Accepted  
**Date**: 2025-01  
**Context**: Risk of logging sensitive data (tokens, webhooks, API keys).  
**Decision**: Implement automatic redaction filter in logging setup.  
**Consequences**:
- Safer logging by default
- No manual redaction needed
- Slight performance overhead
- May over-redact in some cases

## ADR-007: HTTP Client Abstraction
**Status**: Accepted  
**Date**: 2025-01  
**Context**: Multiple HTTP calls with different retry/timeout needs.  
**Decision**: Single `HttpClient` class with automatic retries and error handling.  
**Consequences**:
- Consistent error handling
- Centralized retry logic
- Easier to test
- Single point of configuration

## ADR-008: Edge-Triggered Alerts
**Status**: Accepted  
**Date**: 2025-01  
**Context**: Avoid alert spam when probability stays above threshold.  
**Decision**: Only fire alerts on false→true transitions, not while condition remains true.  
**Consequences**:
- Reduces alert noise
- Requires state tracking
- May miss alerts if monitor restarts
- More predictable behavior

## ADR-009: Webhook Schema Versioning
**Status**: Accepted  
**Date**: 2025-01  
**Context**: Need forward compatibility for webhook consumers.  
**Decision**: Include `schema_version` field, use Pydantic `extra="ignore"` for parsing.  
**Consequences**:
- Forward compatible
- Can add fields without breaking consumers
- Requires version checking
- Clear evolution path

## ADR-010: Coinbase for Price Data
**Status**: Accepted  
**Date**: 2025-01  
**Context**: Need reliable crypto price source for price-based alerts.  
**Decision**: Use Coinbase public candles API (no auth required).  
**Consequences**:
- Free, no API key needed
- Reliable data source
- Limited to Coinbase-listed pairs
- Rate limits apply
- Single point of failure for price mode
