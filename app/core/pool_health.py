"""
Pool Health Monitoring Service
"""
import asyncio
import socket
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import Pool, PoolHealth, Telemetry, Miner


class PoolHealthService:
    """Service for monitoring and scoring pool health"""
    
    @staticmethod
    async def check_pool_connectivity(pool: Pool, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Check if a pool is reachable and measure response time
        
        Returns:
            Dict with is_reachable, response_time_ms, error_message
        """
        start_time = time.time()
        
        try:
            # Resolve hostname
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.getaddrinfo(pool.url, pool.port, socket.AF_INET, socket.SOCK_STREAM),
                timeout=timeout
            )
            
            # Try to connect
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(pool.url, pool.port),
                timeout=timeout
            )
            
            writer.close()
            await writer.wait_closed()
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                "is_reachable": True,
                "response_time_ms": round(response_time, 2),
                "error_message": None
            }
            
        except asyncio.TimeoutError:
            return {
                "is_reachable": False,
                "response_time_ms": None,
                "error_message": f"Connection timeout after {timeout}s"
            }
        except socket.gaierror:
            return {
                "is_reachable": False,
                "response_time_ms": None,
                "error_message": "DNS resolution failed"
            }
        except ConnectionRefusedError:
            return {
                "is_reachable": False,
                "response_time_ms": None,
                "error_message": "Connection refused"
            }
        except Exception as e:
            return {
                "is_reachable": False,
                "response_time_ms": None,
                "error_message": str(e)
            }
    
    @staticmethod
    async def calculate_pool_reject_rate(pool_id: int, db: AsyncSession, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate reject rate for a pool based on telemetry from miners using it
        
        Returns:
            Dict with reject_rate, shares_accepted, shares_rejected
        """
        # Get pool details
        result = await db.execute(select(Pool).where(Pool.id == pool_id))
        pool = result.scalar_one_or_none()
        
        if not pool:
            return {"error": "Pool not found"}
        
        # Get telemetry from miners using this pool
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        pool_url = f"{pool.url}:{pool.port}"
        
        result = await db.execute(
            select(Telemetry)
            .where(Telemetry.timestamp >= cutoff)
            .where(Telemetry.pool_in_use.like(f"%{pool.url}%"))
            .order_by(Telemetry.timestamp.desc())
        )
        telemetry_data = result.scalars().all()
        
        if not telemetry_data:
            return {
                "reject_rate": None,
                "shares_accepted": 0,
                "shares_rejected": 0,
                "error": "No telemetry data"
            }
        
        # Calculate aggregate stats
        total_accepted = 0
        total_rejected = 0
        
        # Group by miner to get latest shares from each
        miner_shares = {}
        for telem in telemetry_data:
            if telem.miner_id not in miner_shares:
                miner_shares[telem.miner_id] = {
                    "accepted": telem.shares_accepted or 0,
                    "rejected": telem.shares_rejected or 0
                }
        
        # Sum up shares
        for shares in miner_shares.values():
            total_accepted += shares["accepted"]
            total_rejected += shares["rejected"]
        
        total_shares = total_accepted + total_rejected
        reject_rate = (total_rejected / total_shares * 100) if total_shares > 0 else 0
        
        return {
            "reject_rate": round(reject_rate, 2),
            "shares_accepted": total_accepted,
            "shares_rejected": total_rejected
        }
    
    @staticmethod
    async def calculate_health_score(
        is_reachable: bool,
        response_time_ms: Optional[float],
        reject_rate: Optional[float],
        recent_failures: int = 0
    ) -> float:
        """
        Calculate overall health score for a pool (0-100)
        
        Scoring:
        - Reachability: 40 points (all or nothing)
        - Response time: 30 points (0-50ms=30, 50-150ms=20, 150-300ms=10, >300ms=0)
        - Reject rate: 30 points (<1%=30, 1-3%=20, 3-5%=10, >5%=0)
        - Recent failures penalty: -10 per failure (last hour)
        """
        score = 0.0
        
        # Reachability (40 points)
        if is_reachable:
            score += 40
        
        # Response time (30 points)
        if response_time_ms is not None:
            if response_time_ms < 50:
                score += 30
            elif response_time_ms < 150:
                score += 20
            elif response_time_ms < 300:
                score += 10
        
        # Reject rate (30 points)
        if reject_rate is not None:
            if reject_rate < 1:
                score += 30
            elif reject_rate < 3:
                score += 20
            elif reject_rate < 5:
                score += 10
        
        # Penalty for recent failures
        score -= (recent_failures * 10)
        
        return max(0, min(100, score))
    
    @staticmethod
    async def monitor_pool(pool_id: int, db: AsyncSession) -> Dict[str, Any]:
        """
        Perform full health check on a pool and record metrics
        
        Returns:
            Dict with all health metrics
        """
        # Get pool
        result = await db.execute(select(Pool).where(Pool.id == pool_id))
        pool = result.scalar_one_or_none()
        
        if not pool:
            return {"error": "Pool not found"}
        
        # Check connectivity
        connectivity = await PoolHealthService.check_pool_connectivity(pool)
        
        # Calculate reject rate
        reject_stats = await PoolHealthService.calculate_pool_reject_rate(pool_id, db)
        
        # Count recent failures (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        result = await db.execute(
            select(PoolHealth)
            .where(and_(
                PoolHealth.pool_id == pool_id,
                PoolHealth.timestamp >= one_hour_ago,
                PoolHealth.is_reachable == False
            ))
        )
        recent_failures = len(result.scalars().all())
        
        # Calculate health score
        health_score = await PoolHealthService.calculate_health_score(
            connectivity["is_reachable"],
            connectivity["response_time_ms"],
            reject_stats.get("reject_rate"),
            recent_failures
        )
        
        # Record metrics
        pool_health = PoolHealth(
            pool_id=pool_id,
            timestamp=datetime.utcnow(),
            response_time_ms=connectivity["response_time_ms"],
            is_reachable=connectivity["is_reachable"],
            reject_rate=reject_stats.get("reject_rate"),
            shares_accepted=reject_stats.get("shares_accepted"),
            shares_rejected=reject_stats.get("shares_rejected"),
            health_score=health_score,
            error_message=connectivity["error_message"]
        )
        
        db.add(pool_health)
        await db.commit()
        
        return {
            "pool_id": pool_id,
            "pool_name": pool.name,
            "is_reachable": connectivity["is_reachable"],
            "response_time_ms": connectivity["response_time_ms"],
            "reject_rate": reject_stats.get("reject_rate"),
            "shares_accepted": reject_stats.get("shares_accepted"),
            "shares_rejected": reject_stats.get("shares_rejected"),
            "health_score": health_score,
            "recent_failures": recent_failures,
            "error_message": connectivity["error_message"]
        }
    
    @staticmethod
    async def get_pool_health_history(
        pool_id: int,
        db: AsyncSession,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get historical health metrics for a pool"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        result = await db.execute(
            select(PoolHealth)
            .where(and_(
                PoolHealth.pool_id == pool_id,
                PoolHealth.timestamp >= cutoff
            ))
            .order_by(PoolHealth.timestamp.asc())
        )
        health_records = result.scalars().all()
        
        return [
            {
                "timestamp": record.timestamp.isoformat(),
                "is_reachable": record.is_reachable,
                "response_time_ms": record.response_time_ms,
                "reject_rate": record.reject_rate,
                "health_score": record.health_score,
                "error_message": record.error_message
            }
            for record in health_records
        ]
    
    @staticmethod
    async def get_all_pools_status(db: AsyncSession) -> List[Dict[str, Any]]:
        """Get current health status for all enabled pools"""
        # Get all enabled pools
        result = await db.execute(select(Pool).where(Pool.enabled == True))
        pools = result.scalars().all()
        
        pool_statuses = []
        
        for pool in pools:
            # Get latest health record
            result = await db.execute(
                select(PoolHealth)
                .where(PoolHealth.pool_id == pool.id)
                .order_by(PoolHealth.timestamp.desc())
                .limit(1)
            )
            latest_health = result.scalar_one_or_none()
            
            # Get count of miners using this pool
            result = await db.execute(
                select(Telemetry)
                .where(Telemetry.timestamp >= datetime.utcnow() - timedelta(minutes=5))
                .where(Telemetry.pool_in_use.like(f"%{pool.url}%"))
            )
            active_telemetry = result.scalars().all()
            active_miners = len(set([t.miner_id for t in active_telemetry]))
            
            pool_statuses.append({
                "pool_id": pool.id,
                "pool_name": pool.name,
                "pool_url": f"{pool.url}:{pool.port}",
                "active_miners": active_miners,
                "is_reachable": latest_health.is_reachable if latest_health else None,
                "response_time_ms": latest_health.response_time_ms if latest_health else None,
                "reject_rate": latest_health.reject_rate if latest_health else None,
                "health_score": latest_health.health_score if latest_health else None,
                "last_checked": latest_health.timestamp.isoformat() if latest_health else None,
                "error_message": latest_health.error_message if latest_health else None
            })
        
        return pool_statuses
