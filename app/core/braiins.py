"""
Braiins Pool API Integration Service
"""
import aiohttp
from typing import Optional, Dict, Any


class BraiinsPoolService:
    """Service for interacting with Braiins Pool API"""
    
    BASE_URL = "https://pool.braiins.com/api/v1"
    POOL_URL = "stratum.braiins.com"
    POOL_PORT = 3333
    
    @staticmethod
    def is_braiins_pool(url: str, port: int) -> bool:
        """Check if a pool URL/port combination is Braiins Pool"""
        return "braiins.com" in url.lower() and port == BraiinsPoolService.POOL_PORT
    
    @staticmethod
    async def get_workers(api_token: str) -> Optional[Dict[str, Any]]:
        """
        Get workers information from Braiins Pool API
        
        Args:
            api_token: Bearer token for authentication
            
        Returns:
            Dict with workers data or None if request fails
        """
        headers = {
            "Authorization": f"Bearer {api_token}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{BraiinsPoolService.BASE_URL}/workers",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Braiins API error (workers): {response.status}")
                        return None
        except Exception as e:
            print(f"Failed to fetch Braiins workers: {e}")
            return None
    
    @staticmethod
    async def get_rewards(api_token: str) -> Optional[Dict[str, Any]]:
        """
        Get rewards information from Braiins Pool API
        
        Args:
            api_token: Bearer token for authentication
            
        Returns:
            Dict with rewards data (confirmed and pending) or None if request fails
        """
        headers = {
            "Authorization": f"Bearer {api_token}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{BraiinsPoolService.BASE_URL}/rewards",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Braiins API error (rewards): {response.status}")
                        return None
        except Exception as e:
            print(f"Failed to fetch Braiins rewards: {e}")
            return None
    
    @staticmethod
    async def get_payouts(api_token: str) -> Optional[Dict[str, Any]]:
        """
        Get payout history from Braiins Pool API
        
        Args:
            api_token: Bearer token for authentication
            
        Returns:
            Dict with payout history data or None if request fails
        """
        headers = {
            "Authorization": f"Bearer {api_token}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{BraiinsPoolService.BASE_URL}/payouts",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Braiins API error (payouts): {response.status}")
                        return None
        except Exception as e:
            print(f"Failed to fetch Braiins payouts: {e}")
            return None
    
    @staticmethod
    def format_stats_summary(workers_data: Optional[Dict], rewards_data: Optional[Dict], 
                            payouts_data: Optional[Dict]) -> Dict[str, Any]:
        """
        Format Braiins Pool data into a summary
        
        Args:
            workers_data: Workers API response
            rewards_data: Rewards API response
            payouts_data: Payouts API response
            
        Returns:
            Formatted statistics dictionary
        """
        summary = {
            "workers_online": 0,
            "workers_offline": 0,
            "total_hashrate": 0,
            "confirmed_rewards": 0,
            "pending_rewards": 0,
            "total_paid": 0,
            "recent_payouts": []
        }
        
        # Parse workers data
        if workers_data:
            # Adjust based on actual API response structure
            summary["workers_online"] = workers_data.get("active_workers", 0)
            summary["workers_offline"] = workers_data.get("inactive_workers", 0)
            summary["total_hashrate"] = workers_data.get("hashrate", 0)
        
        # Parse rewards data
        if rewards_data:
            summary["confirmed_rewards"] = rewards_data.get("confirmed", 0)
            summary["pending_rewards"] = rewards_data.get("pending", 0)
        
        # Parse payouts data
        if payouts_data:
            payouts = payouts_data.get("payouts", [])
            total_paid = sum(p.get("amount", 0) for p in payouts)
            summary["total_paid"] = total_paid
            summary["recent_payouts"] = payouts[:5]  # Last 5 payouts
        
        return summary
