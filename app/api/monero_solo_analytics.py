"""
Monero Solo Mining Analytics API
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Optional

from core.database import (
    get_db, 
    MoneroSoloSettings,
    MoneroSoloEffort,
    MoneroBlock,
    MoneroWalletTransaction,
    MoneroHashrateSnapshot
)
from core.monero_solo import MoneroSoloService

router = APIRouter()


@router.get("/analytics/monero-solo")
async def get_monero_solo_analytics(
    range: str = Query("7d", regex="^(6h|24h|7d|30d|all)$"),
    db: AsyncSession = Depends(get_db)
):
    """Get Monero solo mining analytics data"""
    service = MoneroSoloService(db)
    settings = await service.get_or_create_settings()
    
    if not settings.enabled:
        return {
            "enabled": False,
            "message": "Monero solo mining is not enabled"
        }
    
    # Calculate time range
    now = datetime.utcnow()
    if range == "6h":
        start_time = now - timedelta(hours=6)
    elif range == "24h":
        start_time = now - timedelta(days=1)
    elif range == "7d":
        start_time = now - timedelta(days=7)
    elif range == "30d":
        start_time = now - timedelta(days=30)
    else:  # all
        start_time = datetime(2020, 1, 1)  # Far enough back
    
    # Get current hashrate
    hashrate_data = await service.aggregate_hashrate()
    
    # Get current effort
    effort_stmt = select(MoneroSoloEffort).order_by(
        MoneroSoloEffort.timestamp.desc()
    ).limit(1)
    result = await db.execute(effort_stmt)
    latest_effort = result.scalar_one_or_none()
    current_effort = latest_effort.effort_percent if latest_effort else 0.0
    
    # Count total blocks
    blocks_stmt = select(func.count(MoneroBlock.id))
    result = await db.execute(blocks_stmt)
    blocks_count = result.scalar() or 0
    
    # Get period earnings
    period_earnings_stmt = select(func.sum(MoneroWalletTransaction.amount_xmr)).where(
        MoneroWalletTransaction.timestamp >= start_time
    )
    result = await db.execute(period_earnings_stmt)
    period_earnings = result.scalar() or 0.0
    
    # Get all-time earnings
    total_earnings_stmt = select(func.sum(MoneroWalletTransaction.amount_xmr))
    result = await db.execute(total_earnings_stmt)
    total_earnings = result.scalar() or 0.0
    
    # Get hashrate history
    hashrate_stmt = select(MoneroHashrateSnapshot).where(
        MoneroHashrateSnapshot.timestamp >= start_time
    ).order_by(MoneroHashrateSnapshot.timestamp)
    result = await db.execute(hashrate_stmt)
    hashrate_history = result.scalars().all()
    
    # Get effort history
    effort_stmt = select(MoneroSoloEffort).where(
        MoneroSoloEffort.timestamp >= start_time
    ).order_by(MoneroSoloEffort.timestamp)
    result = await db.execute(effort_stmt)
    effort_history = result.scalars().all()
    
    # Get blocks
    blocks_stmt = select(MoneroBlock).order_by(
        MoneroBlock.block_height.desc()
    ).limit(50)
    result = await db.execute(blocks_stmt)
    blocks = result.scalars().all()
    
    # Get transactions
    transactions_stmt = select(MoneroWalletTransaction).where(
        MoneroWalletTransaction.timestamp >= start_time
    ).order_by(MoneroWalletTransaction.timestamp.desc()).limit(50)
    result = await db.execute(transactions_stmt)
    transactions = result.scalars().all()
    
    return {
        "enabled": True,
        "worker_count": hashrate_data["worker_count"],
        "current_hashrate_formatted": hashrate_data["total_hashrate_formatted"],
        "current_effort_percent": float(current_effort),
        "blocks_found": blocks_count,
        "period_earnings_xmr": float(period_earnings),
        "total_earnings_xmr": float(total_earnings),
        "hashrate_history": [
            {
                "timestamp": h.timestamp.isoformat(),
                "hashrate": float(h.total_hashrate),
                "worker_count": h.worker_count
            }
            for h in hashrate_history
        ],
        "effort_history": [
            {
                "timestamp": e.timestamp.isoformat(),
                "effort_percent": float(e.effort_percent),
                "total_hashes": float(e.total_hashes)
            }
            for e in effort_history
        ],
        "blocks": [
            {
                "block_height": b.block_height,
                "block_hash": b.block_hash,
                "timestamp": b.timestamp.isoformat(),
                "reward_xmr": float(b.reward_xmr),
                "difficulty": float(b.difficulty)
            }
            for b in blocks
        ],
        "transactions": [
            {
                "tx_hash": t.tx_hash,
                "timestamp": t.timestamp.isoformat(),
                "amount_xmr": float(t.amount_xmr),
                "confirmations": t.confirmations,
                "block_height": t.block_height
            }
            for t in transactions
        ]
    }
