"""
CKPool Local Node Integration Service
"""
import aiohttp
from typing import Optional, Dict, Any, List
from datetime import datetime


class CKPoolService:
    """Service for interacting with CKPool local node API"""
    
    DEFAULT_PORT = 3333
    DEFAULT_API_PORT = 80
    
    @staticmethod
    def is_ckpool(pool_url: str, pool_port: int) -> bool:
        """
        Check if a pool is a local CKPool instance.
        We detect CKPool by port 3333 and local IP ranges.
        """
        is_local_ip = (
            pool_url.startswith("192.168.") or 
            pool_url.startswith("10.") or 
            pool_url.startswith("172.16.") or
            pool_url.startswith("172.17.") or
            pool_url.startswith("172.18.") or
            pool_url.startswith("172.19.") or
            pool_url.startswith("172.20.") or
            pool_url.startswith("172.21.") or
            pool_url.startswith("172.22.") or
            pool_url.startswith("172.23.") or
            pool_url.startswith("172.24.") or
            pool_url.startswith("172.25.") or
            pool_url.startswith("172.26.") or
            pool_url.startswith("172.27.") or
            pool_url.startswith("172.28.") or
            pool_url.startswith("172.29.") or
            pool_url.startswith("172.30.") or
            pool_url.startswith("172.31.") or
            pool_url == "localhost" or
            pool_url == "127.0.0.1"
        )
        return is_local_ip and pool_port == CKPoolService.DEFAULT_PORT
    
    @staticmethod
    async def get_pool_stats(pool_ip: str, api_port: int = DEFAULT_API_PORT) -> Optional[Dict[str, Any]]:
        """
        Fetch pool statistics from CKPool's HTTP API
        
        Args:
            pool_ip: IP address of the CKPool instance
            api_port: HTTP API port (default 80)
            
        Returns:
            Dict with pool stats or None if request fails
            
        Example response structure:
        {
            "runtime": 9240,
            "lastupdate": 1767000053,
            "Users": 1,
            "Workers": 4,
            "Idle": 1,
            "Disconnected": 3,
            "hashrate1m": "1.71T",
            "hashrate5m": "1.79T",
            "hashrate15m": "1.8T",
            "hashrate1hr": "1.48T",
            "hashrate6hr": "439G",
            "hashrate1d": "121G",
            "hashrate7d": "17.8G",
            "diff": 0.24,
            "accepted": 2525312,
            "rejected": 637048,
            "bestshare": 169302,
            "SPS1m": 0.398,
            "SPS5m": 0.42,
            "SPS15m": 0.429,
            "SPS1h": 0.351
        }
        """
        try:
            url = f"http://{pool_ip}:{api_port}/pool/pool.status"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        text = await response.text()
                        # Response is JSON lines format - parse each line
                        lines = text.strip().split('\n')
                        combined_stats = {}
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith('Pretty print'):
                                import json
                                data = json.loads(line)
                                combined_stats.update(data)
                        return combined_stats
                    else:
                        print(f"⚠️ CKPool API returned status {response.status} for {pool_ip}")
                        return None
        except Exception as e:
            print(f"❌ Failed to fetch CKPool stats from {pool_ip}: {e}")
            return None
    
    @staticmethod
    def parse_hashrate(hashrate_str: str) -> float:
        """
        Parse CKPool hashrate string to float in GH/s
        
        Args:
            hashrate_str: Hashrate string like "1.71T", "439G", "121M"
            
        Returns:
            Hashrate in GH/s
        """
        if not hashrate_str:
            return 0.0
        
        hashrate_str = hashrate_str.strip()
        try:
            # Extract numeric value and unit
            if hashrate_str.endswith('T'):
                return float(hashrate_str[:-1]) * 1000  # TH/s to GH/s
            elif hashrate_str.endswith('G'):
                return float(hashrate_str[:-1])  # Already GH/s
            elif hashrate_str.endswith('M'):
                return float(hashrate_str[:-1]) / 1000  # MH/s to GH/s
            elif hashrate_str.endswith('K'):
                return float(hashrate_str[:-1]) / 1_000_000  # KH/s to GH/s
            else:
                return float(hashrate_str) / 1_000_000_000  # H/s to GH/s
        except:
            return 0.0
    
    @staticmethod
    def format_stats_summary(raw_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format raw CKPool stats into a standardized summary
        
        Returns:
            {
                "runtime": seconds,
                "users": int,
                "workers": int,
                "workers_idle": int,
                "workers_disconnected": int,
                "hashrate_1m_gh": float,
                "hashrate_5m_gh": float,
                "hashrate_15m_gh": float,
                "hashrate_1h_gh": float,
                "hashrate_6h_gh": float,
                "hashrate_1d_gh": float,
                "hashrate_7d_gh": float,
                "difficulty": float,
                "shares_accepted": int,
                "shares_rejected": int,
                "reject_rate": float (0-100),
                "best_share": int,
                "sps_1m": float,
                "sps_5m": float,
                "sps_15m": float,
                "sps_1h": float
            }
        """
        if not raw_stats:
            return {}
        
        accepted = raw_stats.get("accepted", 0)
        rejected = raw_stats.get("rejected", 0)
        total_shares = accepted + rejected
        reject_rate = (rejected / total_shares * 100) if total_shares > 0 else 0.0
        
        return {
            "runtime": raw_stats.get("runtime", 0),
            "last_update": raw_stats.get("lastupdate", 0),
            "users": raw_stats.get("Users", 0),
            "workers": raw_stats.get("Workers", 0),
            "workers_idle": raw_stats.get("Idle", 0),
            "workers_disconnected": raw_stats.get("Disconnected", 0),
            "hashrate_1m_gh": CKPoolService.parse_hashrate(raw_stats.get("hashrate1m", "0")),
            "hashrate_5m_gh": CKPoolService.parse_hashrate(raw_stats.get("hashrate5m", "0")),
            "hashrate_15m_gh": CKPoolService.parse_hashrate(raw_stats.get("hashrate15m", "0")),
            "hashrate_1h_gh": CKPoolService.parse_hashrate(raw_stats.get("hashrate1hr", "0")),
            "hashrate_6h_gh": CKPoolService.parse_hashrate(raw_stats.get("hashrate6hr", "0")),
            "hashrate_1d_gh": CKPoolService.parse_hashrate(raw_stats.get("hashrate1d", "0")),
            "hashrate_7d_gh": CKPoolService.parse_hashrate(raw_stats.get("hashrate7d", "0")),
            "difficulty": raw_stats.get("diff", 0.0),
            "shares_accepted": accepted,
            "shares_rejected": rejected,
            "reject_rate": round(reject_rate, 2),
            "best_share": raw_stats.get("bestshare", 0),
            "sps_1m": raw_stats.get("SPS1m", 0.0),
            "sps_5m": raw_stats.get("SPS5m", 0.0),
            "sps_15m": raw_stats.get("SPS15m", 0.0),
            "sps_1h": raw_stats.get("SPS1h", 0.0)
        }
    
    @staticmethod
    async def fetch_and_cache_blocks(pool_ip: str, pool_id: int, api_port: int = DEFAULT_API_PORT):
        """
        Fetch ckpool.log from remote server and cache block submissions to database
        
        Args:
            pool_ip: IP address of the CKPool instance
            pool_id: Database ID of the pool
            api_port: HTTP API port (default 80)
        """
        try:
            # Fetch the ckpool.log file
            url = f"http://{pool_ip}:{api_port}/ckpool.log"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        print(f"⚠️ Could not fetch ckpool.log from {pool_ip}: HTTP {response.status}")
                        return
                    
                    log_content = await response.text()
            
            # Parse log for "Submitting block data" entries
            from core.database import AsyncSessionLocal, CKPoolBlock
            from sqlalchemy import select
            import re
            
            async with AsyncSessionLocal() as db:
                # Get existing blocks to avoid duplicates
                result = await db.execute(
                    select(CKPoolBlock.log_entry).where(CKPoolBlock.pool_id == pool_id)
                )
                existing_entries = {row[0] for row in result.all()}
                
                # Parse log lines for both submitted and accepted blocks
                new_blocks = 0
                for line in log_content.split('\n'):
                    is_submitted = "Submitting block data" in line
                    is_accepted = "BLOCK ACCEPTED" in line
                    
                    if is_submitted or is_accepted:
                        # Avoid duplicate entries
                        if line in existing_entries:
                            continue
                        
                        # Extract timestamp from log line (format: [2025-12-29 09:15:23.456])
                        timestamp_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                        if timestamp_match:
                            from datetime import datetime
                            timestamp_str = timestamp_match.group(1)
                            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        else:
                            timestamp = datetime.utcnow()
                        
                        # Create block record
                        block = CKPoolBlock(
                            pool_id=pool_id,
                            pool_ip=pool_ip,
                            block_accepted=is_accepted,
                            timestamp=timestamp,
                            log_entry=line
                        )
                        db.add(block)
                        new_blocks += 1
                
                if new_blocks > 0:
                    await db.commit()
                    print(f"✅ Cached {new_blocks} new block submission(s) from CKPool {pool_ip}")
        
        except Exception as e:
            print(f"❌ Failed to fetch/cache CKPool blocks from {pool_ip}: {e}")
    
    @staticmethod
    async def get_blocks_24h(pool_id: int) -> int:
        """
        Get count of blocks submitted in last 24 hours for a CKPool instance
        
        Args:
            pool_id: Database ID of the pool
            
        Returns:
            Number of blocks submitted in last 24 hours
        """
        try:
            from core.database import AsyncSessionLocal, CKPoolBlock
            from sqlalchemy import select, func
            from datetime import datetime, timedelta
            
            async with AsyncSessionLocal() as db:
                cutoff = datetime.utcnow() - timedelta(hours=24)
                result = await db.execute(
                    select(func.count(CKPoolBlock.id))
                    .where(CKPoolBlock.pool_id == pool_id)
                    .where(CKPoolBlock.timestamp >= cutoff)
                )
                count = result.scalar()
                return count or 0
        except Exception as e:
            print(f"❌ Failed to get blocks_24h for pool {pool_id}: {e}")
            return 0
    
    @staticmethod
    async def get_blocks_accepted(pool_id: int, days: int) -> int:
        """
        Get count of ACCEPTED blocks (not just submitted) in last N days
        
        Args:
            pool_id: Database ID of the pool
            days: Number of days to look back
            
        Returns:
            Number of blocks accepted
        """
        try:
            from core.database import AsyncSessionLocal, CKPoolBlock
            from sqlalchemy import select, func
            from datetime import datetime, timedelta
            
            async with AsyncSessionLocal() as db:
                cutoff = datetime.utcnow() - timedelta(days=days)
                result = await db.execute(
                    select(func.count(CKPoolBlock.id))
                    .where(CKPoolBlock.pool_id == pool_id)
                    .where(CKPoolBlock.block_accepted == True)
                    .where(CKPoolBlock.timestamp >= cutoff)
                )
                count = result.scalar()
                return count or 0
        except Exception as e:
            print(f"❌ Failed to get blocks_accepted for pool {pool_id}: {e}")
            return 0
