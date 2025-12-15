"""
Pool Health API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.pool_health import PoolHealthService


router = APIRouter()


@router.get("/pools/{pool_id}/health")
async def get_pool_health(pool_id: int, db: AsyncSession = Depends(get_db)):
    """Get current health status for a specific pool"""
    result = await PoolHealthService.monitor_pool(pool_id, db)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/pools/{pool_id}/health/history")
async def get_pool_health_history(
    pool_id: int,
    hours: int = 24,
    db: AsyncSession = Depends(get_db)
):
    """Get historical health metrics for a pool"""
    history = await PoolHealthService.get_pool_health_history(pool_id, db, hours)
    
    return {
        "pool_id": pool_id,
        "period_hours": hours,
        "history": history
    }


@router.get("/pools/health/overview")
async def get_pools_health_overview(db: AsyncSession = Depends(get_db)):
    """Get health status overview for all pools"""
    pools = await PoolHealthService.get_all_pools_status(db)
    
    # Calculate aggregate stats
    total_pools = len(pools)
    healthy_pools = sum(1 for p in pools if p["health_score"] and p["health_score"] >= 70)
    unhealthy_pools = sum(1 for p in pools if p["health_score"] and p["health_score"] < 50)
    
    avg_response_time = None
    response_times = [p["response_time_ms"] for p in pools if p["response_time_ms"] is not None]
    if response_times:
        avg_response_time = round(sum(response_times) / len(response_times), 2)
    
    avg_reject_rate = None
    reject_rates = [p["reject_rate"] for p in pools if p["reject_rate"] is not None]
    if reject_rates:
        avg_reject_rate = round(sum(reject_rates) / len(reject_rates), 2)
    
    return {
        "total_pools": total_pools,
        "healthy_pools": healthy_pools,
        "unhealthy_pools": unhealthy_pools,
        "avg_response_time_ms": avg_response_time,
        "avg_reject_rate": avg_reject_rate,
        "pools": pools
    }


@router.post("/pools/{pool_id}/health/check")
async def trigger_pool_health_check(pool_id: int, db: AsyncSession = Depends(get_db)):
    """Manually trigger a health check for a specific pool"""
    result = await PoolHealthService.monitor_pool(pool_id, db)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return {"message": "Health check completed", "result": result}
