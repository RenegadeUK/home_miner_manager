"""
v0 Miner Controller - Main Application Entry Point
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from core.config import settings
from core.database import init_db
from core.mqtt import mqtt_client
from core.scheduler import scheduler
from api import miners, pools, automation, dashboard
from ui import routes as ui_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    print(f"🚀 Starting v0 Miner Controller on port {settings.WEB_PORT}")
    
    # Initialize database
    await init_db()
    
    # Start MQTT client
    await mqtt_client.start()
    
    # Start scheduler
    scheduler.start()
    
    yield
    
    # Shutdown
    print("🛑 Shutting down v0 Miner Controller")
    await mqtt_client.stop()
    scheduler.shutdown()


app = FastAPI(
    title="v0 Miner Controller",
    description="Modern ASIC Miner Management Platform",
    version="0.1.0",
    lifespan=lifespan
)

# Mount static files
static_dir = Path(__file__).parent / "ui" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Setup templates
templates_dir = Path(__file__).parent / "ui" / "templates"
templates_dir.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# Include API routes
app.include_router(miners.router, prefix="/api/miners", tags=["miners"])
app.include_router(pools.router, prefix="/api/pools", tags=["pools"])
app.include_router(automation.router, prefix="/api/automation", tags=["automation"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])

# Include UI routes
app.include_router(ui_routes.router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.1.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.WEB_PORT,
        reload=False
    )
