# Sam Knowledge Management Guide

## How Sam Stays Current as HMM Grows

Sam now uses a **hybrid knowledge system**:

### 1. Static Knowledge (System Prompt)
**Location**: `app/core/ai_assistant.py` → `_get_system_prompt()`

**What goes here**:
- Core concepts (mining basics, architecture principles)
- Database schema structure
- Sam's capabilities/limitations
- Communication guidelines

**When to update**: Rarely - only when fundamentals change

---

### 2. Dynamic Documentation (Markdown Files)
**Location**: `/config/docs/` (mounted volume)

**What goes here**:
- Feature explanations (`features/`)
- Coin-specific info (`coins/`)
- Strategy details (`strategies/`)
- Hardware quirks (`hardware/`)

**When to update**: Whenever you add/change features

**How Sam uses it**: 
- Reads all `.md` files on every query
- Gets latest feature docs without code changes
- Stays current automatically

---

### 3. Live Database Discovery
**What Sam discovers automatically**:
- ✅ **Supported coins**: Reads `CryptoPrice` table - if a coin has price data, Sam knows about it
- ✅ **Configured pools**: Reads `Pool` table to see what's actually set up
- ✅ **Active features**: Checks `app_config` for enabled integrations
- ✅ **Miner types**: Discovers from `Miner.miner_type` field
- ✅ **Current prices**: Reads latest crypto and electricity prices

**Benefit**: Add new coin → Add to CryptoPrice → Sam knows about it (no prompt update needed!)

---

## Workflow: Adding a New Feature

### Example: Adding Litecoin Support

#### Step 1: Implement the feature
```python
# Add LTC pools, adapters, etc.
```

#### Step 2: Add price tracking
```python
# Update crypto price fetcher to include litecoin
# It gets stored in CryptoPrice table
```

#### Step 3: Document for Sam
Create `/config/docs/coins/litecoin.md`:
```markdown
# Litecoin (LTC) Mining

**Block Reward**: 6.25 LTC (halves ~2027)
**Current Value**: ~£60/LTC
**Network Difficulty**: ~25 TH/s global
**Solo Mining Reality**: With 10 TH/s, expect blocks every 2-5 days

## Why LTC?
- Faster blocks than BTC (2.5 min vs 10 min)
- More valuable than DGB (~£60 vs £0.007)
- Good middle ground for profitability

## When to Mine LTC
- Electricity: 5-15p/kWh (medium-cheap range)
- Expected ROI: Better than DGB, more realistic than BTC
```

#### Step 4: Test Sam
Ask: "What coins can I mine and what's the profitability?"

Sam will:
1. See litecoin in `CryptoPrice` table ✅
2. Read `/config/docs/coins/litecoin.md` ✅
3. Give accurate, current information ✅

**No code changes to Sam required!**

---

## Documentation Best Practices

### ✅ DO:
- Keep docs concise (Sam has limited context)
- Include numbers (block rewards, prices, hashrates)
- Explain "why" and "when", not just "what"
- Update docs when features change
- Use real examples from user perspective

### ❌ DON'T:
- Duplicate what's already in system prompt
- Write novels (Sam pays per token)
- Include sensitive data (passwords, keys)
- Forget to update when code changes

---

## Example Documentation Templates

### New Coin Template
```markdown
# [Coin Name] ([SYMBOL]) Mining

**Block Reward**: X.XX SYMBOL (halving: YYYY)
**Current Value**: £X.XX per SYMBOL  
**Block Value**: ~£XXX per block
**Network Difficulty**: [Context for home miners]

## Why [SYMBOL]?
- [Key differentiator]
- [Profitability context]

## When to Mine
- Electricity price range: X-X p/kWh
- Expected frequency: [blocks per time period]
- ROI expectation: [realistic assessment]
```

### New Strategy Template
```markdown
# [Strategy Name]

**Purpose**: [One-line description]

## How It Works
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Configuration
- [Setting 1]: [Purpose]
- [Setting 2]: [Purpose]

## Expected Outcomes
- [Metric 1]: [Improvement]
- [Metric 2]: [Benefit]

## When to Use
- [Scenario 1]
- [Scenario 2]
```

### New Feature Template
```markdown
# [Feature Name]

**Status**: [Beta/Stable/Experimental]
**Location**: Settings → [Path]

## What It Does
[Clear explanation in user terms]

## How to Use
1. [Step 1]
2. [Step 2]

## Known Issues
- [Issue 1 and workaround]

## Tips
- [Best practice 1]
- [Best practice 2]
```

---

## Monitoring Sam's Knowledge

### Check What Sam Knows
Look at Sam's context in logs when he responds:
```json
{
  "documentation": {
    "README.md": "...",
    "coins/digibyte.md": "...",
    "strategies/agile-solo.md": "..."
  },
  "supported_coins": {
    "bitcoin": {"price_gbp": 78234.56, ...},
    "digibyte": {"price_gbp": 0.007, ...}
  }
}
```

### Verify Sam Reads Docs
```bash
# Check if docs are loaded
docker exec -it v0-miner-controller ls -la /config/docs/

# View a doc file
docker exec -it v0-miner-controller cat /config/docs/coins/digibyte.md
```

---

## Future Enhancements

### Planned:
- [ ] Web UI for editing docs (no SSH needed)
- [ ] Version control integration (Git)
- [ ] Doc validation (ensure format consistency)
- [ ] Usage analytics (which docs Sam references most)
- [ ] Auto-generated docs from code (docstrings → markdown)

### Ideas:
- Sam could suggest doc updates: "I don't have info about X, should we document it?"
- Community docs: Share best practices across HMM users
- Interactive tutorials: Sam walks users through setup

---

## Summary

**Old Way** (Static):
- Add feature → Update Sam's prompt → Rebuild container → Redeploy
- Sam's knowledge frozen at deployment time
- Hard to keep current

**New Way** (Dynamic):
- Add feature → Document in `/config/docs/` → Done
- Sam discovers new coins/pools from database automatically
- Knowledge stays current without code changes
- Easy to maintain and extend

**Result**: Sam scales with HMM as it grows! 🚀

**Last Updated**: January 24, 2026
