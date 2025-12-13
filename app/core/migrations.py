"""
Database migrations for schema changes
"""
from sqlalchemy import text
from core.database import engine


async def run_migrations():
    """Run all pending migrations"""
    async with engine.begin() as conn:
        # Migration 1: Add last_executed_at and last_execution_context to automation_rules
        try:
            await conn.execute(text("""
                ALTER TABLE automation_rules 
                ADD COLUMN last_executed_at DATETIME
            """))
            print("✓ Added last_executed_at column to automation_rules")
        except Exception:
            # Column already exists
            pass
        
        try:
            await conn.execute(text("""
                ALTER TABLE automation_rules 
                ADD COLUMN last_execution_context JSON
            """))
            print("✓ Added last_execution_context column to automation_rules")
        except Exception:
            # Column already exists
            pass
