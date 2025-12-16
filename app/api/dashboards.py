"""
Custom Dashboard API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from core.database import get_db, CustomDashboard, DashboardWidget

router = APIRouter()


class WidgetPosition(BaseModel):
    x: int = 0
    y: int = 0
    w: int = 4
    h: int = 3
    autoPosition: Optional[bool] = False


class WidgetCreate(BaseModel):
    widget_type: str
    config: dict
    position: WidgetPosition


class WidgetResponse(BaseModel):
    id: int
    dashboard_id: int
    widget_type: str
    config: dict
    position: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    layout: dict = {"cols": 12, "rowHeight": 100}
    widgets: List[WidgetCreate] = []


class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    layout: Optional[dict] = None


class DashboardResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    layout: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardDetailResponse(DashboardResponse):
    widgets: List[WidgetResponse]


@router.get("/dashboards", response_model=List[DashboardResponse])
async def list_dashboards(db: AsyncSession = Depends(get_db)):
    """List all custom dashboards"""
    result = await db.execute(select(CustomDashboard).order_by(CustomDashboard.created_at))
    dashboards = result.scalars().all()
    return dashboards


@router.get("/dashboards/{dashboard_id}", response_model=DashboardDetailResponse)
async def get_dashboard(dashboard_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific dashboard with its widgets"""
    result = await db.execute(
        select(CustomDashboard).where(CustomDashboard.id == dashboard_id)
    )
    dashboard = result.scalar_one_or_none()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    # Get widgets
    widgets_result = await db.execute(
        select(DashboardWidget).where(DashboardWidget.dashboard_id == dashboard_id)
    )
    widgets = list(widgets_result.scalars().all())
    
    # Auto-arrange widgets if they're all at x=0 (stacked)
    if widgets and all(w.position.get('x', 0) == 0 for w in widgets):
        cols = dashboard.layout.get('cols', 12)
        x_pos = 0
        y_pos = 0
        
        for widget in widgets:
            w = widget.position.get('w', 4)
            h = widget.position.get('h', 3)
            
            # Check if widget fits in current row
            if x_pos + w > cols:
                x_pos = 0
                y_pos += h
            
            # Update position
            widget.position['x'] = x_pos
            widget.position['y'] = y_pos
            widget.position['autoPosition'] = False
            
            x_pos += w
    
    return {
        **dashboard.__dict__,
        "widgets": widgets
    }


@router.post("/dashboards", response_model=DashboardResponse)
async def create_dashboard(
    dashboard: DashboardCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new custom dashboard"""
    new_dashboard = CustomDashboard(
        name=dashboard.name,
        description=dashboard.description,
        layout=dashboard.layout
    )
    
    db.add(new_dashboard)
    await db.flush()
    
    # Add widgets
    for widget in dashboard.widgets:
        new_widget = DashboardWidget(
            dashboard_id=new_dashboard.id,
            widget_type=widget.widget_type,
            config=widget.config,
            position=widget.position.model_dump()
        )
        db.add(new_widget)
    
    await db.commit()
    await db.refresh(new_dashboard)
    
    return new_dashboard


@router.put("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: int,
    dashboard: DashboardUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a dashboard"""
    result = await db.execute(
        select(CustomDashboard).where(CustomDashboard.id == dashboard_id)
    )
    existing = result.scalar_one_or_none()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    if dashboard.name is not None:
        existing.name = dashboard.name
    if dashboard.description is not None:
        existing.description = dashboard.description
    if dashboard.layout is not None:
        existing.layout = dashboard.layout
    
    existing.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(existing)
    
    return existing


@router.delete("/dashboards/{dashboard_id}")
async def delete_dashboard(dashboard_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a dashboard and all its widgets"""
    result = await db.execute(
        select(CustomDashboard).where(CustomDashboard.id == dashboard_id)
    )
    dashboard = result.scalar_one_or_none()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    # Delete widgets first
    await db.execute(
        delete(DashboardWidget).where(DashboardWidget.dashboard_id == dashboard_id)
    )
    
    # Delete dashboard
    await db.delete(dashboard)
    await db.commit()
    
    return {"message": "Dashboard deleted successfully"}


@router.post("/dashboards/{dashboard_id}/widgets", response_model=WidgetResponse)
async def add_widget(
    dashboard_id: int,
    widget: WidgetCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add a widget to a dashboard"""
    # Verify dashboard exists
    result = await db.execute(
        select(CustomDashboard).where(CustomDashboard.id == dashboard_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    new_widget = DashboardWidget(
        dashboard_id=dashboard_id,
        widget_type=widget.widget_type,
        config=widget.config,
        position=widget.position.model_dump()
    )
    
    db.add(new_widget)
    await db.commit()
    await db.refresh(new_widget)
    
    return new_widget


@router.put("/dashboards/{dashboard_id}/widgets/{widget_id}", response_model=WidgetResponse)
async def update_widget(
    dashboard_id: int,
    widget_id: int,
    widget: WidgetCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update a widget"""
    result = await db.execute(
        select(DashboardWidget).where(
            DashboardWidget.id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id
        )
    )
    existing = result.scalar_one_or_none()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    existing.widget_type = widget.widget_type
    existing.config = widget.config
    existing.position = widget.position.model_dump()
    existing.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(existing)
    
    return existing


@router.delete("/dashboards/{dashboard_id}/widgets/{widget_id}")
async def delete_widget(
    dashboard_id: int,
    widget_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a widget"""
    result = await db.execute(
        select(DashboardWidget).where(
            DashboardWidget.id == widget_id,
            DashboardWidget.dashboard_id == dashboard_id
        )
    )
    widget = result.scalar_one_or_none()
    
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    await db.delete(widget)
    await db.commit()
    
    return {"message": "Widget deleted successfully"}
