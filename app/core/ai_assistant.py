"""
Sam - AI Mining Assistant
OpenAI-powered assistant for mining operation optimization
"""
import logging
from typing import List, Dict, Optional, AsyncGenerator
from datetime import datetime, timedelta
from openai import AsyncOpenAI
import json
import os
from pathlib import Path

from core.config import app_config
from core.database import AsyncSessionLocal, Miner, Telemetry, BlockFound, EnergyPrice, HighDiffShare
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Documentation directory (mounted in /config volume)
DOCS_DIR = Path("/config/docs")
STARTER_DOCS_DIR = Path(__file__).parent.parent / "docs" / "starter"

def _initialize_docs():
    """
    Copy starter documentation to /config/docs/ if it doesn't exist.
    This runs once on first startup to provide default docs.
    Users can then customize them without losing changes on updates.
    """
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Only copy if /config/docs/ is empty
    if not any(DOCS_DIR.rglob("*.md")):
        if STARTER_DOCS_DIR.exists():
            logger.info("Initializing Sam documentation from starter templates...")
            import shutil
            shutil.copytree(STARTER_DOCS_DIR, DOCS_DIR, dirs_exist_ok=True)
            logger.info(f"Documentation initialized: {len(list(DOCS_DIR.rglob('*.md')))} files")
        else:
            logger.warning("Starter docs not found - Sam will work but with limited context")

# Initialize docs on module load (runs once per container start)
_initialize_docs()


def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key from config (encrypted storage)"""
    config = app_config.get("openai", {})
    if not config.get("enabled", False):
        return None
    
    api_key = config.get("api_key")
    if not api_key:
        return None
    
    # TODO: Decrypt if encrypted
    # For now, store plaintext (will encrypt in production)
    return api_key


class SamAssistant:
    """Sam - AI Mining Assistant using OpenAI GPT-4"""
    
    def __init__(self):
        self.api_key = get_openai_api_key()
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None
        
        config = app_config.get("openai", {})
        self.model = config.get("model", "gpt-4o")
        self.max_tokens = config.get("max_tokens", 1000)
    
    def is_enabled(self) -> bool:
        """Check if Sam is enabled and configured"""
        return self.client is not None
    
    def _load_documentation(self) -> Dict[str, str]:
        """
        Load markdown documentation files from /config/docs/
        
        This allows features to be documented externally and Sam stays current.
        Files are organized by category:
        - /config/docs/features/*.md - Feature documentation
        - /config/docs/coins/*.md - Coin-specific info
        - /config/docs/strategies/*.md - Strategy explanations
        - /config/docs/README.md - Overview
        
        Returns:
            Dict mapping filename to content
        """
        docs = {}
        
        if not DOCS_DIR.exists():
            return docs
        
        # Recursively find all .md files
        for md_file in DOCS_DIR.rglob("*.md"):
            try:
                relative_path = md_file.relative_to(DOCS_DIR)
                content = md_file.read_text(encoding='utf-8')
                docs[str(relative_path)] = content
                logger.debug(f"Loaded documentation: {relative_path}")
            except Exception as e:
                logger.warning(f"Failed to load {md_file}: {e}")
        
        return docs
    
    async def test_connection(self) -> Dict:
        """Test OpenAI API connection"""
        if not self.client:
            return {"success": False, "error": "API key not configured"}
        
        try:
            # Simple test call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return {
                "success": True,
                "model": self.model,
                "response": response.choices[0].message.content
            }
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def chat(
        self,
        user_message: str,
        conversation_history: List[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Chat with Sam (streaming response)
        
        Args:
            user_message: User's question
            conversation_history: Previous messages in conversation
        
        Yields:
            Chunks of Sam's response
        """
        if not self.client:
            yield "Sam is not configured. Please add an OpenAI API key in Settings > Integrations."
            return
        
        try:
            # Build context from current system state
            context = await self._build_context()
            
            # Build message history
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "system", "content": f"Current System State:\n{json.dumps(context, indent=2)}"}
            ]
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history[-10:])  # Last 10 messages
            
            # Add user message
            messages.append({"role": "user", "content": user_message})
            
            # Stream response
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                stream=True,
                temperature=0.7
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            logger.error(f"Sam chat error: {e}")
            yield f"Sorry, I encountered an error: {str(e)}"
    
    def _get_system_prompt(self) -> str:
        """Get Sam's system prompt with comprehensive knowledge - both static and dynamic"""
        return """You are Sam, an AI assistant specializing in Bitcoin mining operations for Home Miner Manager (HMM).
You help miners optimize their operations by analyzing real-time and historical data.

## YOUR PERSONALITY
- Knowledgeable, concise, data-driven, and helpful
- Always back up recommendations with numbers from the system state
- Use emojis sparingly for readability (⚡💰📊⛏️ are good choices)
- Explain technical concepts simply but accurately
- **BE HONEST ABOUT LIMITATIONS**: You are read-only. You CANNOT control miners, change settings, or execute actions.
- **STAY CURRENT**: When features/coins/pools are added, check the 'documentation' and 'supported_coins' sections in system state

## WHAT YOU CAN AND CANNOT DO

**✅ YOU CAN:**
- Analyze current data and provide insights
- Recommend actions based on electricity prices and performance
- Explain how features work
- Troubleshoot issues by identifying problems in the data
- Answer questions about mining concepts and strategies

**❌ YOU CANNOT:**
- Turn miners on or off (that's done manually by the user or external automation)
- Change miner modes or pools
- Enable/disable automation features
- Modify any settings in the system
- Execute any commands or actions

**When asked to "do" something**: Politely explain you can only provide recommendations, then tell them WHAT to do and WHERE to do it (e.g., "Go to Settings → Energy Optimization to enable auto-optimization").

## DATA YOU HAVE ACCESS TO
You receive a comprehensive JSON object called "Current System State" with every query containing:

### Energy Data
- `current_electricity_price_pence`: Current Octopus Agile price in pence/kWh
- `next_6h_prices`: Array of upcoming 30-minute price slots (12 slots = 6 hours)

### Miner Data (per miner)
- `name`, `type` (avalon_nano_3, bitaxe_601, nerdqaxe, nmminer), `enabled`, `current_mode`, `pool`
- `current_state`: Latest telemetry snapshot (hashrate, temperature, power_watts, shares, uptime, last_seen)
- `24h_averages`: Rolling 24h stats (avg hashrate/temp/power, total shares, reject_rate_percent)

### Pool Data
- `pools`: Array of configured pools (name, pool_type, priority, url - NO PASSWORDS)
- `pool_health`: Per-pool health metrics (health_score 0-100, reachable, response_time_ms, reject_rate)

### Blocks & Shares
- `all_blocks_found`: Complete history of blocks found (miner, coin, difficulty, timestamp, confirmed)
- `top_high_diff_shares`: Top 20 high difficulty shares from last 7 days (difficulty, percentage of network diff)

### Automation & Strategies
- `active_automation_rules`: Rules enabled (name, trigger_type, action_type, last_triggered)
- `energy_optimization`: Auto-optimization settings (enabled, price_threshold)
- `agile_solo_strategy`: If enrolled, which miners switch between Solo/Braiins based on price

### Health Scores
- `miner_health_scores`: Per-miner health breakdown (0-100 scores for uptime, temperature, hashrate, reject_rate)

### System Events
- `recent_system_events`: Last 50 automated actions in 24h (pool switches, mode changes, reconciliations)

## DATABASE SCHEMA KNOWLEDGE
You should understand the HMM data model to answer questions accurately:

**Miner Table**: id, name, miner_type, ip_address, enabled, current_mode, current_pool, enrolled_in_strategy
**Telemetry Table**: miner_id, timestamp, hashrate, hashrate_unit, temperature, power, shares_accepted, shares_rejected, uptime
**Pool Table**: id, name, pool_type (solo/team), url, priority
**BlockFound Table**: miner_name, coin, difficulty, timestamp, confirmed (validated against external APIs)
**HighDiffShare Table**: miner_name, coin, difficulty, network_difficulty, timestamp
**EnergyPrice Table**: valid_from, valid_to, price_pence, tariff (octopus_agile)
**AutomationRule Table**: name, enabled, trigger_type (price_threshold/time_window/hybrid), action_type (set_mode/switch_pool)
**PoolHealth Table**: pool_name, timestamp, health_score (0-100), reachable, response_time_ms, reject_rate
**HealthScore Table**: miner_name, timestamp, health_score, uptime_score, temperature_score, hashrate_score, reject_rate_score
**AuditLog Table**: action (e.g., agile_strategy_executed, pool_strategy_reconciled), triggered_by (automation/user), timestamp

## KEY RELATIONSHIPS
- One miner → many telemetry records (time-series)
- One miner → many blocks found (historical)
- One miner → many high diff shares (historical)
- One pool → many health checks (time-series)
- Energy prices are 30-minute slots (Octopus Agile half-hourly pricing)

## MINING CONCEPTS YOU MUST UNDERSTAND
**Solo Mining**: Mine to your own wallet, get full block reward (3.125 BTC post-April 2024 halving) but very low probability
**Pool Mining**: Share rewards with others, consistent small payouts
**Difficulty**: How hard it is to find a block (higher = harder). Network diff vs share diff.
**Shares**: Proof of work submitted to pool. Accepted = valid, Rejected = invalid (network issues/stale)
**Reject Rate**: shares_rejected / (shares_accepted + shares_rejected) * 100. Good: <1%, Warning: 1-3%, Bad: >3%
**Hashrate Units**: H/s (hashes), kH/s (thousand), MH/s (million), GH/s (billion), GH/s typical for Avalon Nano, TH/s (trillion) typical for Bitaxe/NerdQaxe
**ASIC Modes**: Miners have power modes (low/eco, medium/standard, high/turbo/oc) trading power for hashrate
**Agile Pricing**: UK Octopus Energy variable tariff, changes every 30min based on wholesale prices

## MINING INCOME & ECONOMICS - BE BRUTALLY HONEST

**Current Bitcoin Economics (Jan 2026):**
- Block Reward: 3.125 BTC (post-April 2024 halving, next halving ~2028 → 1.5625 BTC)
- Bitcoin Price: ~$95,000-$105,000 (varies)
- Network Difficulty: ~100+ EH/s (exahashes) total network hashrate
- Block found every ~10 minutes on average across entire network

**Small-Scale Home Mining Reality:**
- HMM users typically have: 1-20 TH/s total (few Bitaxe/Avalon Nano devices)
- **THIS IS HOBBY/LOTTERY MINING, NOT A PROFITABLE BUSINESS**
- Main motivations: Education, fun, supporting Bitcoin network, lottery ticket for jackpot
- Most users LOSE money on electricity (unless solar, or smart arbitrage with Agile negative pricing)

**Solo Mining Income Expectations (Lottery):**
- With 1 TH/s: Finding a block takes 50-200+ YEARS statistically
- With 10 TH/s: Still 5-20+ years on average
- With 25 TH/s: Maybe 2-8 years on average (pure luck though)
- IF you win: 3.125 BTC = ~$300,000+ at current prices
- **Bottom line: Don't realistically expect to ever find a block with home miners**
- Analogy: Like buying lottery tickets - fun to dream, but don't mortgage your house

**Pool Mining Income (Consistent but Pennies):**
- Rough estimates (varies with BTC price, difficulty, pool fees 1-3%):
  - 1 TH/s: ~$0.05-$0.15 per day = ~$1.50-$4.50/month
  - 10 TH/s: ~$0.50-$1.50 per day = ~$15-$45/month
  - 25 TH/s: ~$1.25-$3.75 per day = ~$37-$112/month
- These are GROSS earnings BEFORE electricity costs
- **Reality check: This typically doesn't cover electricity bills in most regions**

**Electricity Cost Impact (UK context):**
- Typical small miner power consumption:
  - Avalon Nano: 15-25W depending on mode
  - Bitaxe/NerdQaxe: 10-20W
  - NMMiner: 5-10W
- UK electricity costs:
  - Average tariff: ~24p/kWh
  - Octopus Agile average: ~15p/kWh
  - Running 15W 24/7 at 24p/kWh: ~£0.09/day = £2.70/month per miner
  - Running 10 miners: ~£27/month just in electricity
- **Agile NEGATIVE pricing periods**: You get PAID to mine (electricity cost is negative!)
- **This is why Agile Solo Strategy matters**: Mine only during cheap/free/negative pricing windows

**Multi-Coin Support - CRITICAL:**
HMM supports 5 different coins with VASTLY different values:
- **BTC** (Bitcoin): 3.125 BTC reward = ~£78,000 @ £25k/BTC (main target, hardest difficulty)
- **BCH** (Bitcoin Cash): 3.125 BCH reward = ~£1,000 @ £320/BCH (easier than BTC)
- **DGB** (DigiByte): 277.376 DGB reward = ~£2 @ £0.007/DGB (much easier, frequent blocks possible)
- **BC2** (Bellscoin): Low value alt-coin
- **XMR** (Monero): CPU mining only (XMRig), different pool structure (SupportXMR)

**Income DEPENDS on which coin they're mining!**
- Solo mining DGB with 10 TH/s: Could find blocks WEEKLY (worth £2 each)
- Solo mining BTC with 10 TH/s: Could take DECADES (but worth £78k)
- Pool mining varies MASSIVELY by coin value

**When Asked About Income - Your Response Template:**
1. **Check what coins they're actually mining**: Look at pool URLs and blocks_found table
2. **Check coin prices from CryptoPrice table**: BTC, BCH, DGB prices are cached in database
3. **Calculate per-coin**:
   - DGB solo: Easier difficulty, frequent blocks (days/weeks), but only £2 each
   - BTC solo: Massive difficulty, rare blocks (years/decades), but £78k jackpot
   - Pool income: Proportional to coin value (BTC pools pay most, DGB pools pay least)
4. **Electricity cost**: Same calculation regardless of coin
5. **Be coin-specific**: "You're mining DGB which has frequent small wins vs BTC which is rare big jackpot"
6. **Agile Solo Strategy context**: System switches between DGB (medium prices) and BTC (cheap prices) automatically

**Example Good Response (Multi-Coin Aware):**
"Let me give you a realistic breakdown based on what you're actually mining.

Looking at your setup:
- You have 15 TH/s combined hashrate
- Your pools show you're mining **DigiByte (DGB)** and **Bitcoin (BTC)** depending on price

**DigiByte (DGB) solo mining** (medium electricity prices):
- With 15 TH/s, you could find DGB blocks every few weeks
- Each block: 277 DGB = ~£2 at current prices (£0.007/DGB)
- Annual estimate: Maybe 20-30 blocks = £40-60/year
- This is more about frequent small wins than big jackpots

**Bitcoin (BTC) solo mining** (cheap electricity prices):
- With 15 TH/s, finding a BTC block could take 3-10+ years statistically
- But ONE block: 3.125 BTC = ~£78,000 at current prices
- Pure lottery - you could hit tomorrow or never
- This is the 'life-changing jackpot' scenario

**Pool mining** (free/negative electricity):
- BTC pools: ~£1-3/day with 15 TH/s (because BTC has high value)
- DGB pools: ~£0.10-0.30/day (because DGB has low value)
- Your system switches to pools during free electricity to maximize guaranteed returns

**Electricity costs**: Running those miners 24/7 at UK average prices (~24p/kWh) would cost £20-30/month.

**The Agile Solo Strategy brilliance**: Your system automatically:
- Medium prices → DGB solo (frequent £2 wins, low electricity waste)
- Cheap prices → BTC solo (swinging for £78k jackpot)
- Free/negative → BTC pool (guaranteed income, no electricity cost)

**Bottom line**: This is a hobby with potential upside. The Agile automation makes it sustainable by only mining during cheap periods. The real thrill is the lottery ticket - every share could be THE one that wins £78k."

## AGILE SOLO STRATEGY (CRITICAL)
This is HMM's killer feature - automatically manages miners based on electricity price:

**The ACTUAL Logic** (price-based optimization):
1. **High Prices (Expensive)** → Miners turned OFF completely (not worth running) - **USER DOES THIS MANUALLY**
2. **Medium Prices** → Switch to easier-to-mine crypto like DigiByte (DGB), use lower power modes (eco/low)
3. **Cheap Prices** → Increase power modes (medium/high), can mine Bitcoin profitably
4. **Free/Negative Prices** → POOL MINING is most effective (consistent rewards maximize the value of free electricity)

**IMPORTANT**: Turning miners physically ON/OFF is done EXTERNALLY by the user. HMM automates pool switching, mode changes, and coin selection - but the user controls the power switch.

## HOW MINERS ARE MANAGED IN HMM

There are **multiple ways** to control miners, each with different capabilities:

**1. Manual Control (via HMM UI)**
- User clicks buttons to change modes, switch pools, restart miners
- Direct control through Miners page
- Immediate, one-time actions

**2. Automation Rules (Settings → Automation)**
- User-defined IF/THEN rules
- Triggers: price thresholds, time windows, temperature, pool failures
- Actions: set mode, switch pool, apply profile
- Runs continuously based on conditions

**3. Agile Solo Strategy (Settings → Agile Solo Strategy)**
- Specialized automation for price-based pool/mode optimization
- Enrolled miners automatically adjust to price bands
- Handles DGB switching, mode scaling, pool selection
- More sophisticated than simple automation rules

**4. Energy Optimization (Settings → Energy Optimization)**
- Monitors electricity prices and recommends/executes actions
- Can work with automation rules for coordinated control
- Price-aware power management

**5. External Control (Outside HMM)**
- Smart plugs (TP-Link, Shelly, etc.) - physically power on/off
- HEMA integration - coordinates with home energy management
- Manual power switches - user physically turns off miners
- HMM has NO control over physical power state

**When users ask about "managing miners"**, clarify WHICH type of control they mean:
- "Do you want to manually control it now?" → Manual control
- "Do you want it to happen automatically?" → Automation rules or strategies
- "Do you want to turn it physically on/off?" → External control (smart plugs, manual)

**Why Pool Mining at Free Prices?**
- Solo mining is a lottery - you might waste free electricity finding nothing
- Pool mining guarantees consistent payouts - you convert ALL that free power into actual earnings
- When electricity is free, it's about MAXIMIZING revenue, not minimizing costs

**Common Misconception**: People think "cheap electricity = solo mining" but that's WRONG. Solo is for when you want to reduce pool fees at moderate prices. When electricity is FREE, you want guaranteed returns (pool), not lottery tickets (solo).

**Hysteresis**: Uses confirmation across 2+ consecutive 30-min slots to prevent rapid switching

## WHEN ANSWERING QUESTIONS

**Performance Questions**: Compare current vs 24h averages, identify outliers, check health scores
**Optimization Questions**: Analyze electricity price + next 6h forecast, recommend mode/pool changes
**Profitability Questions**: Calculate (hashrate * block_reward - power_watts * price_pence)
**Troubleshooting Questions**: Check health scores, reject rates, pool health, recent events
**Historical Questions**: Reference blocks_found, high_diff_shares, but note telemetry retention is 48h

**Example Good Responses**:
- "⚡ Miner A is running hot - 72°C vs 24h avg of 68°C. Consider dropping to medium mode."
- "💰 Price is 8p now and dropping to 6p next slot. Good time to switch to Solo mining!"
- "📊 Your reject rate on Braiins jumped to 2.1% (was 0.5% yesterday). Check pool connectivity."

**Be Proactive**: If you see problems in the data, mention them even if not directly asked.
**Be Specific**: Use actual numbers from the system state, not generic advice.
**Be Actionable**: Tell users WHAT to do and WHY, with expected outcomes.

Remember: You're looking at LIVE operational data. Users trust you to help optimize their mining business.
Be accurate, be helpful, be worth the API costs."""
    
    async def _build_context(self) -> Dict:
        """
        Build comprehensive system context for Sam
        
        SECURITY: Explicitly filters out sensitive data (passwords, API keys, tokens)
        ACCESS: Provides operational data needed for insights and recommendations
        DYNAMIC: Reads actual database state + documentation files for current features
        """
        async with AsyncSessionLocal() as db:
            from core.database import Pool, AutomationRule, PoolHealth, HealthScore, AuditLog, CryptoPrice
            
            context = {}
            now = datetime.utcnow()
            cutoff_24h = now - timedelta(hours=24)
            
            # === DYNAMIC DOCUMENTATION ===
            # Load any markdown docs from /config/docs/ to stay current with features
            context['documentation'] = self._load_documentation()
            
            # === SUPPORTED COINS (Dynamic Discovery) ===
            # Instead of hardcoding, discover what coins actually have price data
            result = await db.execute(select(CryptoPrice))
            crypto_prices = result.scalars().all()
            context['supported_coins'] = {
                cp.coin_id: {
                    'price_gbp': cp.price_gbp,
                    'source': cp.source,
                    'updated_at': cp.updated_at.isoformat() if cp.updated_at else None
                }
                for cp in crypto_prices
            }
            
            # === ENERGY DATA ===
            # Current price
            result = await db.execute(
                select(EnergyPrice)
                .where(EnergyPrice.valid_from <= now)
                .where(EnergyPrice.valid_to > now)
                .limit(1)
            )
            current_price = result.scalar_one_or_none()
            if current_price:
                context["current_electricity_price_pence"] = float(current_price.price_pence)
            
            # Next 6 hours pricing
            result = await db.execute(
                select(EnergyPrice)
                .where(EnergyPrice.valid_from >= now)
                .order_by(EnergyPrice.valid_from)
                .limit(12)  # 6 hours at 30min intervals
            )
            future_prices = result.scalars().all()
            context["next_6h_prices"] = [
                {
                    "time": p.valid_from.isoformat(),
                    "price_pence": float(p.price_pence)
                }
                for p in future_prices
            ]
            
            # === MINER DATA ===
            result = await db.execute(select(Miner))
            all_miners = result.scalars().all()
            
            miners_data = []
            for miner in all_miners:
                # Latest telemetry
                telem_result = await db.execute(
                    select(Telemetry)
                    .where(Telemetry.miner_id == miner.id)
                    .order_by(desc(Telemetry.timestamp))
                    .limit(1)
                )
                latest = telem_result.scalar_one_or_none()
                
                # Last 24h average telemetry
                cutoff_24h = now - timedelta(hours=24)
                avg_result = await db.execute(
                    select(
                        func.avg(Telemetry.hashrate).label('avg_hashrate'),
                        func.avg(Telemetry.temperature).label('avg_temp'),
                        func.avg(Telemetry.power).label('avg_power'),
                        func.sum(Telemetry.shares_accepted).label('total_accepted'),
                        func.sum(Telemetry.shares_rejected).label('total_rejected')
                    )
                    .where(Telemetry.miner_id == miner.id)
                    .where(Telemetry.timestamp >= cutoff_24h)
                )
                avg_data = avg_result.first()
                
                miner_info = {
                    "name": miner.name,
                    "type": miner.miner_type,
                    "enabled": miner.enabled,
                    "current_mode": miner.current_mode,
                    "pool": miner.current_pool  # Just pool name, not credentials
                }
                
                if latest:
                    miner_info["current_state"] = {
                        "hashrate": float(latest.hashrate) if latest.hashrate else 0,
                        "hashrate_unit": latest.hashrate_unit,
                        "temperature": float(latest.temperature) if latest.temperature else 0,
                        "power_watts": float(latest.power) if latest.power else 0,
                        "shares_accepted": latest.shares_accepted or 0,
                        "shares_rejected": latest.shares_rejected or 0,
                        "uptime_seconds": latest.uptime or 0,
                        "last_seen": latest.timestamp.isoformat()
                    }
                
                if avg_data and avg_data.avg_hashrate:
                    miner_info["24h_averages"] = {
                        "hashrate": float(avg_data.avg_hashrate),
                        "temperature": float(avg_data.avg_temp) if avg_data.avg_temp else 0,
                        "power_watts": float(avg_data.avg_power) if avg_data.avg_power else 0,
                        "total_shares_accepted": int(avg_data.total_accepted or 0),
                        "total_shares_rejected": int(avg_data.total_rejected or 0),
                        "reject_rate_percent": (float(avg_data.total_rejected) / float(avg_data.total_accepted + avg_data.total_rejected) * 100) if (avg_data.total_accepted or avg_data.total_rejected) else 0
                    }
                
                miners_data.append(miner_info)
            
            context["miners"] = miners_data
            
            # === POOL DATA (NO CREDENTIALS) ===
            result = await db.execute(select(Pool))
            pools = result.scalars().all()
            context["pools"] = [
                {
                    "name": p.name,
                    "pool_type": p.pool_type,
                    "priority": p.priority,
                    "url": p.url  # URL is OK, just no passwords
                }
                for p in pools
            ]
            
            # Pool health
            result = await db.execute(
                select(PoolHealth)
                .where(PoolHealth.timestamp >= cutoff_24h)
                .order_by(desc(PoolHealth.timestamp))
            )
            pool_health_records = result.scalars().all()
            pool_health_summary = {}
            for ph in pool_health_records:
                if ph.pool_name not in pool_health_summary:
                    pool_health_summary[ph.pool_name] = {
                        "latest_health_score": ph.health_score,
                        "reachable": ph.reachable,
                        "response_time_ms": ph.response_time_ms,
                        "reject_rate": ph.reject_rate
                    }
            context["pool_health"] = pool_health_summary
            
            # === BLOCKS & HIGH DIFF SHARES ===
            # All blocks (not just 24h)
            result = await db.execute(
                select(BlockFound).order_by(desc(BlockFound.timestamp))
            )
            all_blocks = result.scalars().all()
            context["all_blocks_found"] = [
                {
                    "miner": b.miner_name,
                    "coin": b.coin,
                    "difficulty": float(b.difficulty),
                    "timestamp": b.timestamp.isoformat(),
                    "confirmed": b.confirmed
                }
                for b in all_blocks
            ]
            
            # Top high diff shares (last 7 days)
            cutoff_7d = now - timedelta(days=7)
            result = await db.execute(
                select(HighDiffShare)
                .where(HighDiffShare.timestamp >= cutoff_7d)
                .order_by(desc(HighDiffShare.difficulty))
                .limit(20)
            )
            high_shares = result.scalars().all()
            context["top_high_diff_shares"] = [
                {
                    "miner": s.miner_name,
                    "coin": s.coin,
                    "difficulty": float(s.difficulty),
                    "network_difficulty": float(s.network_difficulty) if s.network_difficulty else None,
                    "percentage": (float(s.difficulty) / float(s.network_difficulty) * 100) if s.network_difficulty else None,
                    "timestamp": s.timestamp.isoformat()
                }
                for s in high_shares
            ]
            
            # === AUTOMATION & OPTIMIZATION ===
            # Active automation rules
            result = await db.execute(
                select(AutomationRule).where(AutomationRule.enabled == True)
            )
            active_rules = result.scalars().all()
            context["active_automation_rules"] = [
                {
                    "name": r.name,
                    "trigger_type": r.trigger_type,
                    "action_type": r.action_type,
                    "last_triggered": r.last_triggered.isoformat() if r.last_triggered else None
                }
                for r in active_rules
            ]
            
            # Energy optimization state (from app_config instead of database)
            energy_config = app_config.get("energy_optimization", {})
            if energy_config:
                context["energy_optimization"] = {
                    "auto_optimization_enabled": energy_config.get("auto_optimization_enabled", False),
                    "price_threshold": energy_config.get("price_threshold_pence")
                }
            
            # Agile Solo Strategy
            from core.agile_solo_strategy import AgileSoloStrategy
            enrolled_miners = await AgileSoloStrategy.get_enrolled_miners(db)
            if enrolled_miners:
                context["agile_solo_strategy"] = {
                    "enrolled_miners": [m.name for m in enrolled_miners],
                    "description": "Automatically switches between Solo/Braiins based on electricity prices"
                }
            
            # === DEVICE HEALTH ===
            result = await db.execute(
                select(HealthScore)
                .where(HealthScore.timestamp >= cutoff_24h)
                .order_by(desc(HealthScore.timestamp))
            )
            health_records = result.scalars().all()
            health_summary = {}
            for h in health_records:
                if h.miner_name not in health_summary:
                    health_summary[h.miner_name] = {
                        "health_score": h.health_score,
                        "uptime_score": h.uptime_score,
                        "temperature_score": h.temperature_score,
                        "hashrate_score": h.hashrate_score,
                        "reject_rate_score": h.reject_rate_score,
                        "timestamp": h.timestamp.isoformat()
                    }
            context["miner_health_scores"] = health_summary
            
            # === RECENT SYSTEM EVENTS (NO SENSITIVE AUDIT LOGS) ===
            result = await db.execute(
                select(AuditLog)
                .where(AuditLog.timestamp >= cutoff_24h)
                .where(AuditLog.action.not_in(['api_key_saved', 'password_changed']))  # Exclude sensitive actions
                .order_by(desc(AuditLog.timestamp))
                .limit(50)
            )
            recent_events = result.scalars().all()
            context["recent_system_events"] = [
                {
                    "action": e.action,
                    "triggered_by": e.triggered_by,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in recent_events
            ]
            
            return context
