"""
Bitaxe 601 adapter using REST API
"""
import aiohttp
from typing import Dict, List, Optional
from adapters.base import MinerAdapter, MinerTelemetry


class BitaxeAdapter(MinerAdapter):
    """Adapter for Bitaxe 601 miners"""
    
    MODES = ["eco", "standard", "turbo", "oc"]
    
    def __init__(self, miner_id: int, ip_address: str, port: Optional[int] = None, config: Optional[Dict] = None):
        super().__init__(miner_id, ip_address, port or 80, config)
        self.base_url = f"http://{ip_address}"
    
    async def get_telemetry(self) -> Optional[MinerTelemetry]:
        """Get telemetry from REST API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/system/info", timeout=5) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    
                    return MinerTelemetry(
                        miner_id=self.miner_id,
                        hashrate=data.get("hashRate", 0) / 1_000_000_000,  # Convert to GH/s
                        temperature=data.get("temp", 0),
                        power_watts=data.get("power", 0),
                        shares_accepted=data.get("sharesAccepted", 0),
                        shares_rejected=data.get("sharesRejected", 0),
                        pool_in_use=data.get("poolURL"),
                        extra_data={
                            "frequency": data.get("frequency"),
                            "voltage": data.get("voltage"),
                            "uptime": data.get("uptimeSeconds")
                        }
                    )
        except Exception as e:
            print(f"❌ Failed to get telemetry from Bitaxe {self.ip_address}: {e}")
            return None
    
    async def set_mode(self, mode: str) -> bool:
        """Set operating mode"""
        if mode not in self.MODES:
            print(f"❌ Invalid mode: {mode}. Valid modes: {self.MODES}")
            return False
        
        try:
            # Map mode to frequency/voltage presets
            mode_config = {
                "eco": {"frequency": 400, "voltage": 1100},
                "standard": {"frequency": 500, "voltage": 1150},
                "turbo": {"frequency": 575, "voltage": 1200},
                "oc": {"frequency": 625, "voltage": 1250}
            }
            
            config = mode_config.get(mode)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/system/settings",
                    json=config,
                    timeout=5
                ) as response:
                    return response.status == 200
        except Exception as e:
            print(f"❌ Failed to set mode on Bitaxe: {e}")
            return False
    
    async def get_available_modes(self) -> List[str]:
        """Get available modes"""
        return self.MODES
    
    async def switch_pool(self, pool_url: str, pool_user: str, pool_password: str) -> bool:
        """Switch mining pool"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/system/settings",
                    json={
                        "poolURL": pool_url,
                        "poolUser": pool_user,
                        "poolPassword": pool_password
                    },
                    timeout=5
                ) as response:
                    return response.status == 200
        except Exception as e:
            print(f"❌ Failed to switch pool on Bitaxe: {e}")
            return False
    
    async def restart(self) -> bool:
        """Restart miner"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/system/restart", timeout=5) as response:
                    return response.status == 200
        except Exception as e:
            print(f"❌ Failed to restart Bitaxe: {e}")
            return False
    
    async def is_online(self) -> bool:
        """Check if miner is online"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/system/info", timeout=3) as response:
                    return response.status == 200
        except:
            return False
