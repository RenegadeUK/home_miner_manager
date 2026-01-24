# Home Miner Manager - Sam's Documentation

This directory contains documentation that Sam (AI Assistant) reads to stay current with HMM's features.

## Purpose

As HMM grows and adds new features, coins, strategies, or hardware support, Sam needs to stay informed. Rather than hardcoding everything in the system prompt, we use this documentation system for dynamic knowledge.

## How It Works

1. **Sam reads these files** on every query (via `_load_documentation()`)
2. **Files are organized by category** (features/, coins/, strategies/, hardware/)
3. **Written in Markdown** for easy editing and versioning
4. **Stored in /config volume** so they persist across container rebuilds

## What to Document Here

### Features (features/)
- New automation types
- New dashboard widgets
- New API integrations
- New settings pages

### Coins (coins/)
- Block rewards (current, halving schedule)
- Network difficulty context
- Pool recommendations
- Profitability factors

### Strategies (strategies/)
- How strategies work
- When to use each strategy
- Configuration options
- Expected outcomes

### Hardware (hardware/)
- New miner types
- Adapter capabilities
- Mode/tuning options
- Known issues/quirks

## Documentation Guidelines

**Keep it concise**: Sam has limited context window
**Focus on what's different**: Don't repeat basics Sam already knows
**Include numbers**: Block rewards, typical hashrates, price ranges
**Update when features change**: Keep docs current with code

## Example: Adding a New Coin

When adding support for a new coin (e.g., Litecoin):

1. Create `coins/litecoin.md`:
```markdown
# Litecoin (LTC) Mining

**Block Reward**: 6.25 LTC (halves ~2027)
**Current Value**: ~£60/LTC (Jan 2026)
**Network Difficulty**: ~25 TH/s global
**Solo Mining Reality**: With 10 TH/s, expect blocks every 2-5 days
**Pool Recommendations**: Litecoinpool.org, ViaBTC
**Profitability**: Medium - easier than BTC, more valuable than DGB
```

2. Ensure LTC price is in CryptoPrice table (Sam auto-discovers it)
3. Sam now knows about Litecoin without code changes!

## Current Documentation Status

- ✅ README.md - This file
- 🚧 More docs coming as features are added

**Last Updated**: January 24, 2026
