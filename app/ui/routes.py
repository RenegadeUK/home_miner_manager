"""
UI routes for Jinja2 templates
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from core.database import get_db, Miner, Pool, AutomationRule


templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    """Dashboard page"""
    # Get basic stats
    result = await db.execute(select(Miner))
    miners = result.scalars().all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "page_title": "Dashboard",
        "breadcrumbs": [{"label": "Dashboard", "url": "/"}],
        "miners_count": len(miners)
    })


@router.get("/miners", response_class=HTMLResponse)
async def miners_list(request: Request, db: AsyncSession = Depends(get_db)):
    """Miners list page"""
    result = await db.execute(select(Miner))
    miners = result.scalars().all()
    
    return templates.TemplateResponse("miners/list.html", {
        "request": request,
        "page_title": "Miners",
        "breadcrumbs": [
            {"label": "Dashboard", "url": "/"},
            {"label": "Miners", "url": "/miners"}
        ],
        "miners": miners
    })


@router.get("/miners/add", response_class=HTMLResponse)
async def add_miner(request: Request):
    """Add miner wizard"""
    return templates.TemplateResponse("miners/add.html", {
        "request": request,
        "page_title": "Add Miner",
        "breadcrumbs": [
            {"label": "Dashboard", "url": "/"},
            {"label": "Miners", "url": "/miners"},
            {"label": "Add Miner", "url": "/miners/add"}
        ]
    })


@router.get("/pools", response_class=HTMLResponse)
async def pools_list(request: Request, db: AsyncSession = Depends(get_db)):
    """Pools list page"""
    result = await db.execute(select(Pool))
    pools = result.scalars().all()
    
    return templates.TemplateResponse("pools/list.html", {
        "request": request,
        "page_title": "Mining Pools",
        "breadcrumbs": [
            {"label": "Dashboard", "url": "/"},
            {"label": "Pools", "url": "/pools"}
        ],
        "pools": pools
    })


@router.get("/pools/add", response_class=HTMLResponse)
async def add_pool(request: Request):
    """Add pool page"""
    return templates.TemplateResponse("pools/add.html", {
        "request": request,
        "page_title": "Add Pool",
        "breadcrumbs": [
            {"label": "Dashboard", "url": "/"},
            {"label": "Pools", "url": "/pools"},
            {"label": "Add Pool", "url": "/pools/add"}
        ]
    })


@router.get("/automation", response_class=HTMLResponse)
async def automation_list(request: Request, db: AsyncSession = Depends(get_db)):
    """Automation rules list page"""
    result = await db.execute(select(AutomationRule))
    rules = result.scalars().all()
    
    return templates.TemplateResponse("automation/list.html", {
        "request": request,
        "page_title": "Automation Rules",
        "breadcrumbs": [
            {"label": "Dashboard", "url": "/"},
            {"label": "Automation", "url": "/automation"}
        ],
        "rules": rules
    })


@router.get("/automation/add", response_class=HTMLResponse)
async def add_rule(request: Request):
    """Add automation rule wizard"""
    return templates.TemplateResponse("automation/add.html", {
        "request": request,
        "page_title": "Add Automation Rule",
        "breadcrumbs": [
            {"label": "Dashboard", "url": "/"},
            {"label": "Automation", "url": "/automation"},
            {"label": "Add Rule", "url": "/automation/add"}
        ]
    })


@router.get("/energy", response_class=HTMLResponse)
async def energy_pricing(request: Request):
    """Energy pricing page"""
    return templates.TemplateResponse("energy/pricing.html", {
        "request": request,
        "page_title": "Energy Pricing",
        "breadcrumbs": [
            {"label": "Dashboard", "url": "/"},
            {"label": "Energy Pricing", "url": "/energy"}
        ]
    })


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    """Settings page"""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "page_title": "Settings",
        "breadcrumbs": [
            {"label": "Dashboard", "url": "/"},
            {"label": "Settings", "url": "/settings"}
        ]
    })
