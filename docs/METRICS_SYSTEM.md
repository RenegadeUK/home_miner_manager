# HMM Unified Metrics System

## Problem Statement
Currently, every component (Dashboard, Analytics, Sam AI) recalculates the same metrics from raw telemetry data:
- Energy costs computed 3+ times
- Slow queries (60k+ telemetry records)
- Inconsistent results across pages
- Timeouts with Ollama due to large result sets

## Solution: Pre-Computed Metrics Store

### Database Schema

```python
class Metric(Base):
    """Pre-computed metrics for fast querying"""
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True)
    metric_type = Column(String(50), nullable=False, index=True)
    # Examples: energy_cost, hashrate, pool_health, reject_rate
    
    entity_type = Column(String(20), nullable=True, index=True)  
    # "miner", "pool", "system", None
    
    entity_id = Column(Integer, nullable=True, index=True)
    # Miner ID, Pool ID, or NULL for system-wide
    
    period = Column(String(20), nullable=False, index=True)
    # "hourly", "daily", "weekly", "monthly"
    
    timestamp = Column(DateTime, nullable=False, index=True)
    # Start of the period this metric covers
    
    value_json = Column(JSON, nullable=False)
    # Flexible JSON storage for metric-specific data
    
    computed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # When this metric was calculated
    
    __table_args__ = (
        Index('idx_metric_lookup', 'metric_type', 'entity_type', 'entity_id', 'period', 'timestamp'),
    )
```

### Metric Types

#### Energy Metrics
```json
{
  "metric_type": "energy_cost",
  "entity_type": "miner",
  "entity_id": 1,
  "period": "daily",
  "timestamp": "2026-01-23T00:00:00Z",
  "value_json": {
    "kwh": 2.19,
    "cost_gbp": 0.41,
    "avg_price_pence": 18.72,
    "records": 2880
  }
}
```

#### Performance Metrics
```json
{
  "metric_type": "hashrate",
  "entity_type": "miner",
  "entity_id": 1,
  "period": "hourly",
  "timestamp": "2026-01-24T12:00:00Z",
  "value_json": {
    "avg": 540.5,
    "min": 530.2,
    "max": 550.8,
    "unit": "GH/s",
    "stability": 96.2
  }
}
```

#### Pool Metrics
```json
{
  "metric_type": "pool_health",
  "entity_type": "pool",
  "entity_id": 5,
  "period": "hourly",
  "timestamp": "2026-01-24T12:00:00Z",
  "value_json": {
    "health_score": 85,
    "response_time_ms": 45,
    "reject_rate": 1.2,
    "reachable": true
  }
}
```

#### System-Wide Metrics
```json
{
  "metric_type": "energy_cost",
  "entity_type": "system",
  "entity_id": null,
  "period": "daily",
  "timestamp": "2026-01-23T00:00:00Z",
  "value_json": {
    "total_kwh": 21.92,
    "total_cost_gbp": 4.09,
    "miner_count": 10,
    "avg_cost_per_miner": 0.41
  }
}
```

## Implementation Plan

### Phase 1: Core Infrastructure
1. ✅ Create Metric model in database.py
2. ✅ Create MetricsEngine class in core/metrics.py
3. ✅ Add scheduler job to compute metrics hourly

### Phase 2: Metric Calculators
Implement calculators for:
- Energy costs (hourly, daily)
- Hashrate stats (hourly, daily)
- Temperature stats (hourly, daily)
- Pool health (hourly)
- Reject rates (hourly, daily)
- Uptime (daily)

### Phase 3: Query Layer
- Create API endpoints: `GET /api/metrics?type=energy_cost&period=daily&days=7`
- Add helper functions for common queries
- Update Sam's tools to use metrics

### Phase 4: Migration
- Update Dashboard to use metrics
- Update Analytics page to use metrics
- Update Sam AI tools to use metrics
- Keep raw telemetry queries as fallback

## Benefits

1. **Performance**: Query 30 rows instead of 60,000
2. **Consistency**: Same numbers everywhere
3. **Scalability**: Works with Ollama's 4k context
4. **Maintainability**: Add new metrics without touching UI
5. **Historical**: Keep metrics longer than raw telemetry

## Scheduler Jobs

### Hourly (XX:05)
- Compute hourly metrics for previous hour
- Energy, hashrate, temperature, pool health

### Daily (00:30)
- Compute daily metrics for previous day
- Rollup from hourly data
- Cleanup old metrics (>1 year)

### On-Demand
- Backfill historical metrics
- Recompute corrupted data

## Query Examples

### Sam AI Tool
```python
# Old way: 86 seconds, 60k records
telemetry = await db.execute(select(Telemetry).where(...))
# Process all records...

# New way: <1 second, 30 records
metrics = await db.execute(
    select(Metric)
    .where(Metric.metric_type == "energy_cost")
    .where(Metric.entity_type == "system")
    .where(Metric.period == "daily")
    .where(Metric.timestamp >= since)
    .order_by(Metric.timestamp)
)
```

### Dashboard
```python
# Get today's energy cost
today_cost = await get_metric(
    metric_type="energy_cost",
    entity_type="system",
    period="daily",
    timestamp=date.today()
)
```

## Backward Compatibility

- Keep raw telemetry queries as fallback
- If metric not computed yet, calculate on-demand
- Gradually migrate code over time
- No breaking changes

## Future Enhancements

- Real-time metrics (via Redis)
- Metric alerts (threshold monitoring)
- Trend detection (ML on metric history)
- Export metrics (Prometheus, InfluxDB)
