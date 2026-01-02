# CKPool Analytics Enhancement Plan

## Overview
Create detailed analytics page for CKPool solo mining with effort tracking, block history visualization, and performance insights.

## Current State Analysis

### What We Have
- ✅ Block tracking in `CKPoolBlock` table (hash, height, timestamp, accepted status)
- ✅ Dashboard widgets showing current workers, effort, blocks, rewards
- ✅ Network difficulty tracking in `Pool` table
- ✅ Block deduplication by hash/height/timestamp
- ✅ 24h/7d/28d block counts

### What We Don't Have
- ❌ Effort percentage at time of block discovery
- ❌ Historical effort data for trend analysis
- ❌ Detailed block-by-block view
- ❌ Luck/effort distribution charts
- ❌ Time-to-block tracking
- ❌ CKPool-specific detail page

## Requirements - CONFIRMED

### User Story
> "When I click on any CKPool tile on the dashboard, I want to see a detailed analytics page showing:
> - A scatter plot graph with dates on X-axis and effort % on Y-axis, with each dot representing a found block
> - Summary statistics: total blocks, average effort, best/worst effort, median, average time between blocks, total rewards, recent blocks (24h/7d/30d)
> - A table below showing: Date/Time, Block Height, Effort %, Time to Block, Block Hash"

### Data Requirements - CONFIRMED
1. **Effort at Block Discovery**: Calculate using existing formula: `(total_hashes / (network_difficulty * 2^32)) * 100`
2. **Time Between Blocks**: Track seconds elapsed between consecutive accepted blocks
3. **Network Difficulty**: Already captured, verify it's updated before block recording
4. **Historical Blocks**: Set effort to 100% for existing blocks without calculated effort

### UI Requirements - CONFIRMED
1. **Chart Type**: Scatter plot (individual dots, not connected)
2. **Time Range**: Rolling 12 months of data (no filtering controls for MVP)
3. **Terminology**: Use "Effort %" consistently (not "luck")
4. **Stats Cards**: Display all 8 metrics (total blocks, avg effort, best/worst, median, avg time, rewards, 24h/7d/30d counts)
5. **Table Columns**: Date/Time, Block Height, Effort %, Time to Block, Block Hash
6. **Chart Styling**: Scatter plot dots use same color. Background bands: 0-100% green, 100-200% orange, 200+% red using Chart.js annotation plugin
7. **Table Sorting**: Date order, newest first. No column sorting controls needed for MVP
8. **Navigation**: Clicking any CKPool tile (workers/effort/blocks/rewards) for a coin navigates to that coin's analytics page. Analytics sidebar section also contains entries for each configured coin
9. **Empty State**: Show page even with no blocks. Stats cards display zeros/N/A. Chart shows message "No blocks found in the last 12 months". Table shows empty state message
10. **Breadcrumbs**: Dashboard → CKPool {Coin} Analytics

---

## Implementation Plan

## PHASE 1: Database Schema Enhancement (2 hours)
**Goal**: Create lean analytics table with 12-month retention

### Task 1.1: Create CKPoolBlockMetrics model
- **File**: `app/core/database.py`
- **Changes**:
  ```python
  class CKPoolBlockMetrics(Base):
      """Lean CKPool block metrics for 12-month analytics (auto-pruned)"""
      __tablename__ = "ckpool_block_metrics"
      
      id: Mapped[int] = mapped_column(primary_key=True)
      pool_id: Mapped[int] = mapped_column(Integer, index=True)
      coin: Mapped[str] = mapped_column(String(10), index=True)  # BTC, BCH, DGB
      timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
      block_height: Mapped[int] = mapped_column(Integer)
      block_hash: Mapped[str] = mapped_column(String(100), index=True)
      effort_percent: Mapped[float] = mapped_column(Float, default=100.0)
      time_to_block_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
      confirmed_reward_coins: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
  ```
- **Reason**: Separate analytics table avoids bloating CKPoolBlock with log_entry field. 12-month retention policy. Much better query performance.

### Task 1.2: Create database migration
- **File**: `app/core/migrations.py`
- **Changes**:
  ```python
  CREATE TABLE ckpool_block_metrics (
      id INTEGER PRIMARY KEY,
      pool_id INTEGER NOT NULL,
      coin VARCHAR(10) NOT NULL,
      timestamp DATETIME NOT NULL,
      block_height INTEGER NOT NULL,
      block_hash VARCHAR(100) NOT NULL,
      effort_percent FLOAT DEFAULT 100.0,
      time_to_block_seconds INTEGER,
      confirmed_reward_coins FLOAT
  );
  CREATE INDEX idx_ckpool_metrics_pool ON ckpool_block_metrics(pool_id);
  CREATE INDEX idx_ckpool_metrics_coin ON ckpool_block_metrics(coin);
  CREATE INDEX idx_ckpool_metrics_timestamp ON ckpool_block_metrics(timestamp);
  CREATE INDEX idx_ckpool_metrics_hash ON ckpool_block_metrics(block_hash);
  ```
- **Reason**: New table with proper indexing for fast analytics queries

### Task 1.3: Backfill existing accepted blocks
- **File**: `app/core/migrations.py` or one-time script
- **Logic**:
  ```python
  # Copy all accepted blocks from ckpool_blocks to ckpool_block_metrics
  # Set effort_percent = 100.0 for historical blocks
  # Extract coin from pool.url or pool.name
  ```
- **Reason**: Populate analytics table with historical data
- **⚠️ MUST TEST ON DEV DATABASE FIRST** - See Phase 5 Task 5.1 before running in production

### Task 1.4: Add CKPoolBlock pruning scheduler
- **File**: `app/core/scheduler.py`
- **Changes**:
  - Prune CKPoolBlock entries where `block_accepted = False` AND `timestamp < 30 days ago`
  - Keep all accepted blocks forever (block_accepted = True)
  - Prune CKPoolBlockMetrics where `timestamp < 12 months ago`
- **Reason**: Clean up submissions but preserve accepted blocks. Auto-prune analytics after 12 months.
- **⚠️ MUST TEST ON DEV FIRST** - See Phase 5 Task 5.3 to verify correct data deleted
- Estimate: 2 hours

---

## PHASE 2: Backend - Effort Calculation & Storage (3 hours)
**Goal**: Calculate and store effort percentage when blocks are discovered

### Task 2.1: Enhance fetch_and_cache_blocks() to write to metrics table
- **File**: `app/core/ckpool.py`
- **Function**: `fetch_and_cache_blocks()`
- **⚠️ HIGH RISK AREA - This is core block tracking functionality**
- **Logic**:
  1. When parsing "BLOCK ACCEPTED" entry:
     - Continue storing in CKPoolBlock as-is (PRIMARY - do not change existing logic)
     - ALSO create CKPoolBlockMetrics entry with calculated effort (SECONDARY - wrapped in try/catch)
     - Get pool stats via `get_pool_stats()` to fetch current hashrate
     - Use `pool.network_difficulty` (already cached)
     - Calculate time since last accepted block (from CKPoolBlockMetrics, not CKPoolBlock)
     - Calculate effort: `(hashrate_gh * 1e9 * time_seconds) / (network_diff * 2^32) * 100`
     - Extract coin from pool (BTC/BCH/DGB)
  2. Store in CKPoolBlockMetrics with calculated effort
  3. Handle edge cases:
     - First block ever (no previous block) - time_to_block = null
     - Missing network difficulty - use cached value or skip effort calc
     - API unavailable for hashrate - use last known or skip
     - **CRITICAL**: If metrics write fails, log error but DO NOT break main block write
- **⚠️ MUST TEST THOROUGHLY** - See Phase 5 Task 5.2 before production deployment

### Task 2.2: Add helper function for effort calculation
- **File**: `app/core/ckpool.py`
- **Function**: `calculate_mining_effort(hashrate_gh, time_seconds, network_difficulty) -> float`
- **Returns**: Effort percentage (0-infinity, where 100% = expected difficulty)
- **Reason**: Reusable calculation logic for consistency

### Task 2.3: Historical data handling
- **Status**: NOT REQUIRED - SKIPPED
- **Reason**: User confirmed historical blocks should default to 100% effort (already handled by DEFAULT 100.0 in migration)

---

## PHASE 3: API Endpoint Creation (3 hours)
**Goal**: Build REST API to serve analytics data

### Task 3.1: Create analytics endpoint
- **File**: `app/api/analytics.py` (or create `app/api/ckpool.py`)
- **Route**: `/api/ckpool/analytics`
- **Method**: GET
- **Query Params**: 
  - `coin` (required): BTC, BCH, or DGB
- **Response**:
  ```json
  {
    "blocks": [
      {
        "timestamp": "2025-01-01T12:00:00Z",
        "block_height": 1234567,
        "block_hash": "000000...",
        "effort_percent": 95.3,
        "time_to_block_seconds": 3600
      }
    ],
    "stats": {
      "total_blocks": 15,
      "average_effort": 102.3,
      "median_effort": 98.5,
      "best_effort": 45.2,
      "worst_effort": 234.5,
      "average_time_to_block_hours": 18.5,
      "total_rewards": 9000000.0,
      "blocks_24h": 2,
      "blocks_7d": 8,
      "blocks_30d": 15
    }
  }
  ```
- **Data Source**: Query `CKPoolBlockMetrics` table (NOT CKPoolBlock)
- **Time Range**: Last 12 months of blocks (365 days from current date)
- **Calculations**:
  - Best/worst effort: MIN/MAX of effort_percent
  - Median: Use SQLAlchemy percentile or Python statistics.median()
  - Average time: Average of time_to_block_seconds converted to hours
- **Filtering**: Only blocks from specified coin
- **Ordering**: Sort blocks by timestamp DESC (newest first)

### Task 3.2: Add caching
- **File**: Same as Task 3.1
- **Cache Strategy**:
  - Cache key: `ckpool_analytics_{coin}_12m`
  - TTL: 5 minutes (data changes when new block found)
  - Reason: Expensive queries with joins and calculations

---

## PHASE 4: UI Implementation (6 hours)

### Task 4.1: Create `/ui/templates/analytics/ckpool.html`
- Scatter plot with Chart.js (type: 'scatter')
  - Dots: same color for all points
  - Background bands using annotation plugin: 0-100% green, 100-200% orange, 200+% red
- 8 stat cards: Total Blocks, Average Effort %, Best Effort, Worst Effort, Median Effort, Avg Time Between Blocks, Total Rewards, Recent Blocks (24h/7d/30d)
  - Display zeros/N/A when no blocks found
- Table with 5 columns: Date/Time, Block Height, Effort %, Time to Block, Block Hash
  - Sorted by date descending (newest first), no column sorting
  - Empty state message: "No blocks found in the last 12 months"
- Chart empty state: "No blocks found in the last 12 months"
- No time range selector or pagination for MVP
- Breadcrumb: Dashboard → CKPool {Coin} Analytics

### Task 4.2: Update `/ui/templates/dashboard.html`
- Make CKPool tiles (workers/effort/blocks/rewards) clickable for each coin
- Links navigate to `/analytics/ckpool?coin={BTC|BCH|DGB}`
- **⚠️ TEST CAREFULLY** - Don't break existing tile rendering (See Phase 5 Task 5.4)

### Task 4.3: Update sidebar navigation
- Add Analytics section with entries for each configured CKPool coin
- Links to `/analytics/ckpool?coin={coin}`

### Task 4.4: Update `/ui/routes.py`
- Add route: `/analytics/ckpool` with coin query parameter
- Render template with coin passed to context

### Task 4.5: Styling and polish
- Ensure dark/light theme compatibility
- Mobile responsive design
- Loading states and error handling

---

## PHASE 5: Testing & Refinement (4 hours)
**Goal**: Validate accuracy and user experience with focus on HIGH RISK areas

### Task 5.1: 🔴 CRITICAL - Test database migration and backfill
- **Test on DEV ONLY**:
  - Copy production data.db to local dev environment
  - Run migration to create ckpool_block_metrics table
  - Run backfill script
  - Verify all accepted blocks copied correctly
  - Verify coin extraction worked (BTC/BCH/DGB)
  - Verify duplicate blocks (10-15) handled gracefully
  - Check row counts match: `SELECT COUNT(*) FROM ckpool_blocks WHERE block_accepted = TRUE`
- **⚠️ USER TESTING CHECKPOINT**: Show backfill results, get approval before production migration
- **Rollback Plan**: If backfill fails, DROP TABLE and restart

### Task 5.2: 🔴 CRITICAL - Test fetch_and_cache_blocks() dual-write
- **Test Scenarios**:
  1. Find new block while dev server running - verify writes to BOTH tables
  2. Simulate exception in metrics write - verify CKPoolBlock write still succeeds
  3. Missing network_difficulty - verify graceful fallback
  4. Missing hashrate - verify skips effort calc but still records block
  5. First block ever (no previous) - verify time_to_block = null
  6. Rapid duplicate submissions - verify deduplication still works
- **Monitoring**: Watch logs during block submission, check for errors
- **⚠️ USER TESTING CHECKPOINT**: Find test block on DGB, verify both tables updated correctly
- **Rollback Plan**: Git revert if block tracking breaks

### Task 5.3: 🟡 Test scheduler pruning jobs
- **Test on DEV**:
  - Create fake old CKPoolBlock entries (block_accepted=False, 31+ days old)
  - Create fake old CKPoolBlock entries (block_accepted=True, 31+ days old)
  - Create fake old CKPoolBlockMetrics entries (13+ months old)
  - Run pruning scheduler jobs manually
  - Verify: Non-accepted blocks deleted
  - Verify: Accepted blocks kept forever
  - Verify: Old metrics deleted (12+ months)
- **⚠️ USER TESTING CHECKPOINT**: Review what was deleted, confirm nothing important lost
- **Rollback Plan**: Database backup before first production prune

### Task 5.4: 🟡 Test dashboard tile navigation
- **Test**:
  - Click each CKPool tile (workers/effort/blocks/rewards) for each coin
  - Verify navigation to correct analytics page with coin parameter
  - Verify tiles still render correctly (no styling breakage)
  - Verify tiles still update with live data
- **⚠️ USER TESTING CHECKPOINT**: Click through all tiles, confirm no UI breakage

### Task 5.5: Verify effort calculation accuracy
- **Test**: Compare calculated effort with actual mining behavior
- **Verify**: 100% effort = exactly one difficulty worth of hashes
- **Check**: Historical blocks showing 100% default
- **Check**: New blocks calculating real effort correctly

### Task 5.6: Test with multiple coins and edge cases
- **Test**: DGB, BCH, BTC analytics pages load correctly
- **Test**: Empty state with 0 blocks
- **Test**: Single block found
- **Verify**: Correct network difficulty per coin
- **Check**: Stats calculations (median with odd/even counts)

### Task 5.7: Performance and UI review
- **Test**: Load time with 100+ blocks
- **Optimize**: Add database indexes if queries slow
- **Monitor**: Cache hit rates
- **Test**: Mobile responsiveness
- **Test**: Dark/light theme compatibility
- **Test**: Chart bands render correctly at 0%, 100%, 200%
- **Review**: Chart readability and interactivity

---

## PHASE 6: Documentation & Deployment (1.5 hours)
**Goal**: Document feature and deploy to production

### Task 6.1: Update FAQ
- **File**: `app/ui/templates/faq.html`
- **Section**: "CKPool Analytics"
- **Questions**:
  - What is mining effort?
  - How is effort calculated?
  - What does <100% effort mean?
  - What does >100% effort mean?

### Task 6.2: Production deployment
- Run database migration on production
- Deploy code update
- Monitor for errors
- Verify analytics pages load correctly

---

## Dependencies & Risks

### Dependencies
1. **Phase 2 depends on Phase 1**: Can't calculate effort without database fields
2. **Phase 3 depends on Phase 2**: API needs calculated data to return
3. **Phase 4 depends on Phase 3**: UI needs API endpoints
4. **Phase 6 depends on Phase 5**: Can't deploy untested code

### Risks
1. **Effort Calculation Accuracy**: If formula is wrong, all historical data is wrong
   - **Mitigation**: Test calculation thoroughly against known blocks
2. **Performance**: Large datasets could slow down charts/tables
   - **Mitigation**: Add caching, pagination (future), database indexes
3. **Historical Data Quality**: Backfilled blocks default to 100%
   - **Mitigation**: Mark as default value, focus on forward accuracy
4. **Breaking Changes**: Schema changes could impact existing code
   - **Mitigation**: Thorough testing before production deployment

---

## Development Time Estimate

- **Phase 1**: 2 hours (new table, migration, backfill, pruning scheduler)
- **Phase 2**: 3 hours (calculation logic, dual-write to both tables)
- **Phase 3**: 3 hours (API endpoint)
- **Phase 4**: 6 hours (UI implementation)
- **Phase 5**: 4 hours (testing with USER APPROVAL checkpoints)
- **Phase 6**: 1.5 hours (deployment)

**Total**: ~19.5 hours (3 development days)

## Implementation Order & Risk Management

1. **Start with LOW RISK items first**:
   - Phase 1 Task 1.1 & 1.2: New table creation (no impact on existing)
   - Phase 3: API endpoint (isolated)
   - Phase 4 Task 4.1: UI template (isolated)
   - Phase 4 Task 4.3, 4.4, 4.5: Sidebar and routes

2. **Test HIGH RISK items on DEV thoroughly**:
   - Phase 1 Task 1.3: Backfill (get USER APPROVAL before production)
   - Phase 1 Task 1.4: Pruning scheduler (get USER APPROVAL before production)
   - Phase 2 Task 2.1: fetch_and_cache_blocks() (get USER APPROVAL before production)
   - Phase 4 Task 4.2: Dashboard tiles (get USER APPROVAL after testing)

3. **Deploy with rollback ready**:
   - Database backup before migration
   - Git branch for easy rollback
   - Monitor logs closely for first 24h
   - Feature flag to disable metrics collection if issues

### Deployment Phases
1. **Development**: Complete Phases 1-5 locally
2. **Staging**: Test on production-like environment
3. **Production**: Deploy to miners.danvic.co.uk with monitoring
