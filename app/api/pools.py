"""
Pool management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel

from core.database import get_db, Pool


router = APIRouter()


class PoolCreate(BaseModel):
    name: str
    url: str
    port: int
    user: str
    password: str
    enabled: bool = True


class PoolUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None
    enabled: bool | None = None


class PoolResponse(BaseModel):
    id: int
    name: str
    url: str
    port: int
    user: str
    password: str
    enabled: bool
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[PoolResponse])
async def list_pools(db: AsyncSession = Depends(get_db)):
    """List all pools"""
    from sqlalchemy import func
    result = await db.execute(select(Pool).order_by(func.lower(Pool.name)))
    pools = result.scalars().all()
    return pools


@router.get("/{pool_id}", response_model=PoolResponse)
async def get_pool(pool_id: int, db: AsyncSession = Depends(get_db)):
    """Get pool by ID"""
    result = await db.execute(select(Pool).where(Pool.id == pool_id))
    pool = result.scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    
    return pool


@router.post("/", response_model=PoolResponse)
async def create_pool(pool: PoolCreate, db: AsyncSession = Depends(get_db)):
    """Create new pool"""
    db_pool = Pool(
        name=pool.name,
        url=pool.url,
        port=pool.port,
        user=pool.user,
        password=pool.password,
        enabled=pool.enabled
    )
    
    db.add(db_pool)
    await db.commit()
    await db.refresh(db_pool)
    
    return db_pool


@router.put("/{pool_id}", response_model=PoolResponse)
async def update_pool(pool_id: int, pool_update: PoolUpdate, db: AsyncSession = Depends(get_db)):
    """Update pool configuration"""
    result = await db.execute(select(Pool).where(Pool.id == pool_id))
    pool = result.scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    
    # Update fields
    if pool_update.name is not None:
        pool.name = pool_update.name
    if pool_update.url is not None:
        pool.url = pool_update.url
    if pool_update.port is not None:
        pool.port = pool_update.port
    if pool_update.user is not None:
        pool.user = pool_update.user
    if pool_update.password is not None:
        pool.password = pool_update.password
    if pool_update.enabled is not None:
        pool.enabled = pool_update.enabled
    
    await db.commit()
    await db.refresh(pool)
    
    return pool


@router.delete("/{pool_id}")
async def delete_pool(pool_id: int, db: AsyncSession = Depends(get_db)):
    """Delete pool"""
    result = await db.execute(select(Pool).where(Pool.id == pool_id))
    pool = result.scalar_one_or_none()
    
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    
    await db.delete(pool)
    await db.commit()
    
    return {"status": "deleted"}
