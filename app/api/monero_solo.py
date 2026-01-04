"""
Monero Solo Mining API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from core.database import get_db, MoneroSoloSettings
from core.monero_solo import MoneroSoloService
from core.monero_node import MoneroNodeRPC
from core.monero_wallet import MoneroWalletRPC

router = APIRouter()


class MoneroSoloSettingsUpdate(BaseModel):
    """Request model for updating Monero solo settings"""
    enabled: bool
    wallet_rpc_ip: Optional[str] = None
    wallet_rpc_port: int = 18083
    wallet_rpc_user: Optional[str] = None
    wallet_rpc_pass: Optional[str] = None


class MoneroSoloSettingsResponse(BaseModel):
    """Response model for Monero solo settings"""
    id: int
    enabled: bool
    wallet_rpc_ip: Optional[str]
    wallet_rpc_port: int
    wallet_rpc_user: Optional[str]
    wallet_rpc_pass: Optional[str]
    wallet_address: Optional[str]
    last_sync: Optional[datetime]
    
    class Config:
        from_attributes = True


class TestConnectionRequest(BaseModel):
    """Request model for testing RPC connections"""
    ip: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None


class TestConnectionResponse(BaseModel):
    """Response model for connection tests"""
    success: bool
    message: str
    address: Optional[str] = None


@router.get("/settings/monero-solo", response_model=MoneroSoloSettingsResponse)
async def get_monero_solo_settings(db: AsyncSession = Depends(get_db)):
    """Get Monero solo mining settings"""
    service = MoneroSoloService(db)
    settings = await service.get_or_create_settings()
    return settings


@router.put("/settings/monero-solo", response_model=MoneroSoloSettingsResponse)
async def update_monero_solo_settings(
    settings_update: MoneroSoloSettingsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update Monero solo mining settings"""
    service = MoneroSoloService(db)
    settings = await service.get_or_create_settings()
    
    # Update fields
    settings.enabled = settings_update.enabled
    settings.wallet_rpc_ip = settings_update.wallet_rpc_ip
    settings.wallet_rpc_port = settings_update.wallet_rpc_port
    settings.wallet_rpc_user = settings_update.wallet_rpc_user
    settings.wallet_rpc_pass = settings_update.wallet_rpc_pass
    
    # If enabled and wallet RPC configured, try to fetch wallet address
    if settings.enabled and settings.wallet_rpc_ip:
        try:
            wallet_rpc = MoneroWalletRPC(
                host=settings.wallet_rpc_ip,
                port=settings.wallet_rpc_port,
                username=settings.wallet_rpc_user,
                password=settings.wallet_rpc_pass
            )
            address = await wallet_rpc.get_address()
            if address:
                settings.wallet_address = address
        except Exception as e:
            # Don't fail the update if we can't fetch the address
            pass
    
    await db.commit()
    await db.refresh(settings)
    
    return settings


@router.post("/settings/monero-solo/test-wallet", response_model=TestConnectionResponse)
async def test_wallet_connection(request: TestConnectionRequest):
    """Test connection to Monero wallet RPC"""
    try:
        wallet_rpc = MoneroWalletRPC(
            host=request.ip,
            port=request.port,
            username=request.username,
            password=request.password
        )
        
        # Test connection by getting wallet address
        address = await wallet_rpc.get_address()
        
        if address:
            return TestConnectionResponse(
                success=True,
                message="Successfully connected to wallet RPC",
                address=address
            )
        else:
            return TestConnectionResponse(
                success=False,
                message="Failed to retrieve wallet address"
            )
            
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


@router.post("/settings/monero-solo/test-node", response_model=TestConnectionResponse)
async def test_node_connection(request: TestConnectionRequest):
    """Test connection to Monero node RPC"""
    try:
        node_rpc = MoneroNodeRPC(
            host=request.ip,
            port=request.port,
            username=request.username,
            password=request.password
        )
        
        # Test connection by getting node info
        info = await node_rpc.get_info()
        
        if info:
            height = info.get("height", 0)
            return TestConnectionResponse(
                success=True,
                message=f"Successfully connected to node RPC (height: {height})"
            )
        else:
            return TestConnectionResponse(
                success=False,
                message="Failed to retrieve node information"
            )
            
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=f"Connection failed: {str(e)}"
        )


@router.get("/settings/monero-solo/stats")
async def get_monero_solo_stats(db: AsyncSession = Depends(get_db)):
    """Get Monero solo mining statistics for dashboard"""
    service = MoneroSoloService(db)
    settings = await service.get_settings()
    
    if not settings or not settings.enabled:
        return {
            "enabled": False,
            "worker_count": 0,
            "total_hashrate": 0,
            "current_effort": 0,
            "today_reward_xmr": 0,
            "today_reward_gbp": 0,
            "alltime_reward_xmr": 0,
            "alltime_reward_gbp": 0
        }
    
    # Get hashrate data
    hashrate_data = await service.aggregate_hashrate()
    
    # Get effort (simplified - using first pool)
    # TODO: Implement proper pool selection
    
    # Get wallet balance and rewards
    # TODO: Implement reward calculations
    
    return {
        "enabled": True,
        "worker_count": hashrate_data["worker_count"],
        "total_hashrate": hashrate_data["total_hashrate"],
        "current_effort": 0.0,  # TODO
        "today_reward_xmr": 0.0,  # TODO
        "today_reward_gbp": 0.0,  # TODO
        "alltime_reward_xmr": 0.0,  # TODO
        "alltime_reward_gbp": 0.0,  # TODO
    }
