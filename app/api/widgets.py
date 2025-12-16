"""
Dashboard Widget Data API endpoints
Real-time data providers for dashboard widgets
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timedelta

from core.database import get_db, Miner, Telemetry, EnergyPrice, Pool, PoolHealth
from core.config import app_config

router = APIRouter()


@router.get("/widgets/miner-stats/{miner_id}")
async def get_miner_stats_widget(miner_id: int, db: AsyncSession = Depends(get_db)):
    """Get real-time stats for a specific miner"""
    # Get miner
    result = await db.execute(select(Miner).where(Miner.id == miner_id))
    miner = result.scalar_one_or_none()
    
    if not miner:
        raise HTTPException(status_code=404, detail="Miner not found")
    
    # Get latest telemetry
    result = await db.execute(
        select(Telemetry)
        .where(Telemetry.miner_id == miner_id)
        .order_by(Telemetry.timestamp.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    
    if not latest:
        return {
            "miner_id": miner_id,
            "miner_name": miner.name,
            "status": "offline",
            "hashrate": 0,
            "temperature": 0,
            "power": 0
        }
    
    # Determine hashrate unit
    hashrate = latest.hashrate or 0
    if hashrate >= 1000:
        hashrate_display = f"{hashrate / 1000:.2f} TH/s"
    else:
        hashrate_display = f"{hashrate:.2f} GH/s"
    
    return {
        "miner_id": miner_id,
        "miner_name": miner.name,
        "miner_type": miner.miner_type,
        "status": "online" if miner.enabled else "offline",
        "hashrate": hashrate,
        "hashrate_display": hashrate_display,
        "temperature": latest.temperature or 0,
        "power": latest.power_watts or 0,
        "pool": latest.pool_in_use or "Unknown",
        "shares_accepted": latest.shares_accepted or 0,
        "shares_rejected": latest.shares_rejected or 0,
        "last_update": latest.timestamp.isoformat() if latest.timestamp else None
    }


@router.get("/widgets/total-hashrate")
async def get_total_hashrate_widget(db: AsyncSession = Depends(get_db)):
    """Get total hashrate across all miners"""
    # Get all enabled miners
    result = await db.execute(
        select(Miner).where(Miner.enabled == True)
    )
    miners = result.scalars().all()
    
    if not miners:
        return {
            "total_hashrate": 0,
            "hashrate_display": "0 GH/s",
            "active_miners": 0,
            "total_miners": 0
        }
    
    # Get latest telemetry for each
    total_hashrate = 0
    active_count = 0
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    
    for miner in miners:
        result = await db.execute(
            select(Telemetry)
            .where(Telemetry.miner_id == miner.id)
            .where(Telemetry.timestamp >= cutoff)
            .order_by(Telemetry.timestamp.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        if latest and latest.hashrate:
            total_hashrate += latest.hashrate
            active_count += 1
    
    # Format display
    if total_hashrate >= 1000:
        hashrate_display = f"{total_hashrate / 1000:.2f} TH/s"
    else:
        hashrate_display = f"{total_hashrate:.2f} GH/s"
    
    return {
        "total_hashrate": total_hashrate,
        "hashrate_display": hashrate_display,
        "active_miners": active_count,
        "total_miners": len(miners)
    }


@router.get("/widgets/energy-price")
async def get_energy_price_widget(db: AsyncSession = Depends(get_db)):
    """Get current energy price"""
    region = app_config.get("agile_region", "B")
    
    # Get current price slot
    now = datetime.utcnow()
    result = await db.execute(
        select(EnergyPrice)
        .where(EnergyPrice.region == region)
        .where(EnergyPrice.valid_from <= now)
        .where(EnergyPrice.valid_to > now)
        .limit(1)
    )
    current = result.scalar_one_or_none()
    
    if not current:
        return {
            "price_pence": 0,
            "price_display": "-- p/kWh",
            "status": "No data",
            "valid_from": None,
            "valid_to": None
        }
    
    return {
        "price_pence": current.price_pence,
        "price_display": f"{current.price_pence:.2f} p/kWh",
        "status": "Current",
        "valid_from": current.valid_from.isoformat(),
        "valid_to": current.valid_to.isoformat()
    }


@router.get("/widgets/pool-health/{pool_id}")
async def get_pool_health_widget(pool_id: int, db: AsyncSession = Depends(get_db)):
    """Get pool health stats"""
    # Get pool
    result = await db.execute(select(Pool).where(Pool.id == pool_id))
    pool = result.scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    
    # Get latest health
    result = await db.execute(
        select(PoolHealth)
        .where(PoolHealth.pool_id == pool_id)
        .order_by(PoolHealth.timestamp.desc())
        .limit(1)
    )
    health = result.scalar_one_or_none()
    
    if not health:
        return {
            "pool_id": pool_id,
            "pool_name": pool.name,
            "health_score": 0,
            "status": "No data",
            "reachable": False
        }
    
    status = "Healthy" if health.health_score >= 70 else "Warning" if health.health_score >= 50 else "Critical"
    
    return {
        "pool_id": pool_id,
        "pool_name": pool.name,
        "health_score": health.health_score or 0,
        "status": status,
        "reachable": health.is_reachable,
        "response_time_ms": health.response_time_ms or 0,
        "reject_rate": health.reject_rate or 0,
        "last_check": health.timestamp.isoformat() if health.timestamp else None
    }


@router.get("/widgets/miners-list")
async def get_miners_list_widget(db: AsyncSession = Depends(get_db)):
    """Get list of all miners with basic stats"""
    result = await db.execute(select(Miner).order_by(Miner.name))
    miners = result.scalars().all()
    
    miners_data = []
    cutoff = datetime.utcnow() - timedelta(minutes=5)
    
    for miner in miners:
        # Get latest telemetry
        result = await db.execute(
            select(Telemetry)
            .where(Telemetry.miner_id == miner.id)
            .where(Telemetry.timestamp >= cutoff)
            .order_by(Telemetry.timestamp.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        
        status = "online" if (miner.enabled and latest) else "offline"
        hashrate = latest.hashrate if latest else 0
        
        miners_data.append({
            "id": miner.id,
            "name": miner.name,
            "type": miner.miner_type,
            "status": status,
            "hashrate": hashrate,
            "temperature": latest.temperature if latest else 0,
            "power": latest.power_watts if latest else 0
        })
    
    return {
        "miners": miners_data,
        "total": len(miners_data),
        "online": sum(1 for m in miners_data if m["status"] == "online")
    }


@router.get("/widgets/daily-cost")
async def get_daily_cost_widget(db: AsyncSession = Depends(get_db)):
    """Get 24-hour total energy cost"""
    # Get all miners
    result = await db.execute(select(Miner).where(Miner.enabled == True))
    miners = result.scalars().all()
    
    if not miners:
        return {
            "cost_gbp": 0,
            "cost_display": "£0.00",
            "period_hours": 24
        }
    
    # Get energy prices for last 24h
    cutoff = datetime.utcnow() - timedelta(hours=24)
    region = app_config.get("agile_region", "B")
    
    result = await db.execute(
        select(EnergyPrice)
        .where(EnergyPrice.region == region)
        .where(EnergyPrice.valid_from >= cutoff)
        .order_by(EnergyPrice.valid_from)
    )
    prices = result.scalars().all()
    
    if not prices:
        return {
            "cost_gbp": 0,
            "cost_display": "£0.00",
            "period_hours": 24
        }
    
    # Calculate cost (simplified - assumes constant power draw)
    total_cost = 0
    for price in prices:
        slot_duration_hours = 0.5  # 30-minute slots
        
        # Get average power for all miners during this slot
        total_power_kw = 0
        for miner in miners:
            result = await db.execute(
                select(Telemetry)
                .where(Telemetry.miner_id == miner.id)
                .where(Telemetry.timestamp >= price.valid_from)
                .where(Telemetry.timestamp < price.valid_to)
                .limit(1)
            )
            telemetry = result.scalar_one_or_none()
            if telemetry and telemetry.power_watts:
                total_power_kw += telemetry.power_watts / 1000
        
        # Cost = power (kW) * duration (h) * price (pence/kWh) / 100 (to GBP)
        slot_cost = (total_power_kw * slot_duration_hours * price.price_pence) / 100
        total_cost += slot_cost
    
    return {
        "cost_gbp": round(total_cost, 2),
        "cost_display": f"£{total_cost:.2f}",
        "period_hours": 24
    }


@router.get("/widgets/efficiency")
async def get_efficiency_widget(db: AsyncSession = Depends(get_db)):
    """Get efficiency metrics: J/TH across all miners"""
    result = await db.execute(select(Miner))
    miners = result.scalars().all()
    
    total_power_w = 0
    total_hashrate_th = 0
    
    for miner in miners:
        telemetry_result = await db.execute(
            select(Telemetry)
            .where(Telemetry.miner_id == miner.id)
            .order_by(Telemetry.timestamp.desc())
            .limit(1)
        )
        latest = telemetry_result.scalar_one_or_none()
        
        if latest and latest.power_watts and latest.hashrate:
            total_power_w += latest.power_watts
            # Convert GH/s to TH/s
            total_hashrate_th += latest.hashrate / 1000
    
    if total_hashrate_th > 0:
        efficiency_j_th = total_power_w / total_hashrate_th
    else:
        efficiency_j_th = 0
    
    return {
        "efficiency": round(efficiency_j_th, 2),
        "efficiency_display": f"{efficiency_j_th:.2f} J/TH",
        "total_power": total_power_w,
        "total_hashrate": total_hashrate_th
    }


@router.get("/widgets/uptime")
async def get_uptime_widget(db: AsyncSession = Depends(get_db)):
    """Get overall fleet uptime percentage"""
    result = await db.execute(select(Miner))
    miners = result.scalars().all()
    
    if not miners:
        return {
            "uptime_percent": 0,
            "uptime_display": "0%",
            "online_count": 0,
            "total_count": 0
        }
    
    online_count = 0
    for miner in miners:
        telemetry_result = await db.execute(
            select(Telemetry)
            .where(Telemetry.miner_id == miner.id)
            .where(Telemetry.timestamp >= datetime.utcnow() - timedelta(minutes=5))
            .limit(1)
        )
        if telemetry_result.scalar_one_or_none():
            online_count += 1
    
    uptime_percent = (online_count / len(miners)) * 100
    
    return {
        "uptime_percent": round(uptime_percent, 1),
        "uptime_display": f"{uptime_percent:.1f}%",
        "online_count": online_count,
        "total_count": len(miners)
    }


@router.get("/widgets/reject-rate")
async def get_reject_rate_widget(db: AsyncSession = Depends(get_db)):
    """Get average reject rate across all miners"""
    result = await db.execute(select(Miner))
    miners = result.scalars().all()
    
    if not miners:
        return {
            "reject_rate": 0,
            "reject_display": "0%",
            "total_shares": 0,
            "rejected_shares": 0
        }
    
    total_shares = 0
    total_rejected = 0
    
    for miner in miners:
        telemetry_result = await db.execute(
            select(Telemetry)
            .where(Telemetry.miner_id == miner.id)
            .order_by(Telemetry.timestamp.desc())
            .limit(1)
        )
        latest = telemetry_result.scalar_one_or_none()
        
        if latest:
            accepted = latest.accepted_shares or 0
            rejected = latest.rejected_shares or 0
            total_shares += (accepted + rejected)
            total_rejected += rejected
    
    reject_rate = (total_rejected / total_shares * 100) if total_shares > 0 else 0
    
    return {
        "reject_rate": round(reject_rate, 2),
        "reject_display": f"{reject_rate:.2f}%",
        "total_shares": total_shares,
        "rejected_shares": total_rejected
    }


@router.get("/widgets/temperature-alert")
async def get_temperature_alert_widget(db: AsyncSession = Depends(get_db)):
    """Get miners with temperature warnings"""
    result = await db.execute(select(Miner))
    miners = result.scalars().all()
    
    hot_miners = []
    
    for miner in miners:
        telemetry_result = await db.execute(
            select(Telemetry)
            .where(Telemetry.miner_id == miner.id)
            .order_by(Telemetry.timestamp.desc())
            .limit(1)
        )
        latest = telemetry_result.scalar_one_or_none()
        
        if latest and latest.temperature:
            # Type-aware thresholds
            threshold = 90 if miner.miner_type == 'avalon_nano' else 75
            
            if latest.temperature >= threshold:
                hot_miners.append({
                    "name": miner.name,
                    "temperature": latest.temperature,
                    "threshold": threshold
                })
    
    return {
        "alert_count": len(hot_miners),
        "hot_miners": hot_miners,
        "status": "warning" if hot_miners else "ok"
    }


@router.get("/widgets/profitability")
async def get_profitability_widget(db: AsyncSession = Depends(get_db)):
    """Get estimated 24h profitability (BTC mined - energy cost)"""
    # Get total hashrate
    result = await db.execute(select(Miner))
    miners = result.scalars().all()
    
    total_hashrate_th = 0
    for miner in miners:
        telemetry_result = await db.execute(
            select(Telemetry)
            .where(Telemetry.miner_id == miner.id)
            .order_by(Telemetry.timestamp.desc())
            .limit(1)
        )
        latest = telemetry_result.scalar_one_or_none()
        if latest and latest.hashrate:
            total_hashrate_th += latest.hashrate / 1000
    
    # Rough estimate: 1 TH/s = ~0.000000073 BTC/day at current difficulty
    # This is a simplified calculation - real pools would have actual earnings
    btc_per_day = total_hashrate_th * 0.000000073
    
    # Get energy cost from daily-cost widget
    energy_result = await get_daily_cost_widget(db)
    energy_cost_gbp = energy_result["cost_gbp"]
    
    # Convert to BTC (simplified - would need real exchange rate)
    # Assuming ~£50,000/BTC as placeholder
    btc_price_gbp = 50000
    energy_cost_btc = energy_cost_gbp / btc_price_gbp
    
    profit_btc = btc_per_day - energy_cost_btc
    profit_gbp = profit_btc * btc_price_gbp
    
    return {
        "profit_btc": round(profit_btc, 8),
        "profit_gbp": round(profit_gbp, 2),
        "profit_display": f"£{profit_gbp:.2f}",
        "btc_mined": round(btc_per_day, 8),
        "energy_cost": energy_cost_gbp,
        "status": "profit" if profit_btc > 0 else "loss"
    }


@router.get("/widgets/automation-status")
async def get_automation_status_widget(db: AsyncSession = Depends(get_db)):
    """Get automation rules status"""
    from core.database import AutomationRule
    
    result = await db.execute(select(AutomationRule))
    rules = result.scalars().all()
    
    enabled_count = sum(1 for r in rules if r.enabled)
    disabled_count = len(rules) - enabled_count
    
    return {
        "total_rules": len(rules),
        "enabled_rules": enabled_count,
        "disabled_rules": disabled_count,
        "status_display": f"{enabled_count}/{len(rules)} Active"
    }
