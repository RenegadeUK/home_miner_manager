"""
Network Discovery API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel

from core.database import get_db, Miner
from core.discovery import MinerDiscoveryService


router = APIRouter()


class DiscoveryRequest(BaseModel):
    """Request model for discovery scan"""
    network_cidr: Optional[str] = None
    timeout: float = 2.0


class DiscoveredMiner(BaseModel):
    """Model for discovered miner"""
    ip: str
    port: int
    type: str
    name: str
    details: dict
    already_added: bool = False


class DiscoveryResponse(BaseModel):
    """Response model for discovery scan"""
    total_found: int
    new_miners: int
    existing_miners: int
    miners: List[DiscoveredMiner]


@router.post("/discovery/scan", response_model=DiscoveryResponse)
async def scan_network(
    request: DiscoveryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Scan the local network for mining hardware
    
    Returns list of discovered miners with indication of which are already added
    """
    # Perform discovery scan
    discovered = await MinerDiscoveryService.discover_miners(
        network_cidr=request.network_cidr,
        timeout=request.timeout
    )
    
    # Get existing miners from database
    result = await db.execute(select(Miner))
    existing_miners = result.scalars().all()
    
    # Create a set of (ip, port) tuples for existing miners
    existing_connections = {
        (m.ip_address, m.port) for m in existing_miners if m.ip_address
    }
    
    # Mark which miners are already added
    response_miners = []
    new_count = 0
    existing_count = 0
    
    for miner in discovered:
        is_existing = (miner['ip'], miner['port']) in existing_connections
        
        response_miners.append(DiscoveredMiner(
            ip=miner['ip'],
            port=miner['port'],
            type=miner['type'],
            name=miner['name'],
            details=miner['details'],
            already_added=is_existing
        ))
        
        if is_existing:
            existing_count += 1
        else:
            new_count += 1
    
    return DiscoveryResponse(
        total_found=len(discovered),
        new_miners=new_count,
        existing_miners=existing_count,
        miners=response_miners
    )


@router.post("/discovery/verify/{miner_id}")
async def verify_miner(
    miner_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify that a miner is still reachable at its configured address
    """
    result = await db.execute(select(Miner).where(Miner.id == miner_id))
    miner = result.scalar_one_or_none()
    
    if not miner:
        raise HTTPException(status_code=404, detail="Miner not found")
    
    if not miner.ip_address:
        raise HTTPException(status_code=400, detail="Miner has no IP address configured")
    
    is_reachable = await MinerDiscoveryService.verify_miner_connection(
        miner_type=miner.type,
        ip=miner.ip_address,
        port=miner.port
    )
    
    return {
        "miner_id": miner_id,
        "miner_name": miner.name,
        "ip_address": miner.ip_address,
        "port": miner.port,
        "is_reachable": is_reachable
    }


@router.get("/discovery/network-info")
async def get_network_info():
    """
    Get auto-detected network information
    """
    network_cidr = MinerDiscoveryService._get_local_network()
    
    if not network_cidr:
        raise HTTPException(status_code=500, detail="Could not determine local network")
    
    return {
        "network_cidr": network_cidr,
        "description": "Auto-detected local network range"
    }
