"""
SupportXMR pool integration service
"""
import aiohttp
from typing import Optional, Dict, Any


class SupportXMRService:
    """Service for interacting with SupportXMR nodejs-pool API"""
    
    API_BASE = "https://supportxmr.com/api"
    POOL_URLS = ["pool.supportxmr.com"]
    PORTS = [3333, 5555, 7777, 9000]  # Common SupportXMR ports
    
    @staticmethod
    def is_supportxmr_pool(pool_url: str, pool_port: int) -> bool:
        """Check if pool is a SupportXMR pool"""
        return pool_url in SupportXMRService.POOL_URLS and pool_port in SupportXMRService.PORTS
    
    @staticmethod
    def extract_address(pool_user: str) -> str:
        """Extract wallet address from pool user (remove .workername/.paymentid if present)"""
        # Pool user format: "wallet_address" or "wallet_address.payment_id" or "wallet_address.workername"
        return pool_user.split('.')[0] if pool_user else ""
    
    @staticmethod
    async def get_miner_stats(address: str) -> Optional[Dict[str, Any]]:
        """Fetch miner stats from SupportXMR API"""
        if not address:
            return None
        
        try:
            url = f"{SupportXMRService.API_BASE}/miner/{address}/stats"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        print(f"⚠️ SupportXMR API returned status {response.status} for address {address}")
                        return None
        except Exception as e:
            print(f"❌ Failed to fetch SupportXMR stats for {address}: {e}")
            return None
    
    @staticmethod
    async def get_miner_payments(address: str) -> Optional[Dict[str, Any]]:
        """Fetch payment history from SupportXMR API"""
        if not address:
            return None
        
        try:
            url = f"{SupportXMRService.API_BASE}/miner/{address}/payments"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        print(f"⚠️ SupportXMR Payments API returned status {response.status} for address {address}")
                        return None
        except Exception as e:
            print(f"❌ Failed to fetch SupportXMR payments for {address}: {e}")
            return None
    
    @staticmethod
    async def get_miner_identifiers(address: str) -> Optional[Dict[str, Any]]:
        """Fetch worker/identifier stats from SupportXMR API"""
        if not address:
            return None
        
        try:
            url = f"{SupportXMRService.API_BASE}/miner/{address}/identifiers"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        print(f"⚠️ SupportXMR Identifiers API returned status {response.status} for address {address}")
                        return None
        except Exception as e:
            print(f"❌ Failed to fetch SupportXMR identifiers for {address}: {e}")
            return None
    
    @staticmethod
    def format_hashrate(hashrate: float) -> str:
        """Format hashrate in H/s to appropriate unit"""
        if hashrate >= 1_000_000_000:
            return f"{hashrate / 1_000_000_000:.2f} GH/s"
        elif hashrate >= 1_000_000:
            return f"{hashrate / 1_000_000:.2f} MH/s"
        elif hashrate >= 1_000:
            return f"{hashrate / 1_000:.2f} KH/s"
        else:
            return f"{hashrate:.2f} H/s"
    
    @staticmethod
    def format_xmr(amount_atomic: int) -> str:
        """Format XMR amount from atomic units (piconero) to XMR"""
        # 1 XMR = 1,000,000,000,000 atomic units (piconero)
        return f"{amount_atomic / 1_000_000_000_000:.6f}"
