#!/usr/bin/env python3
"""
Backfill network difficulty for existing high difficulty shares
Run this once to populate network_difficulty field for % of Block calculation
"""
import asyncio
import sys
sys.path.insert(0, '/app')

from core.database import AsyncSessionLocal
from core.high_diff_tracker import backfill_network_difficulty


async def main():
    """Run network difficulty backfill"""
    print("🔄 Starting network difficulty backfill...")
    
    async with AsyncSessionLocal() as db:
        await backfill_network_difficulty(db)
    
    print("✅ Backfill complete!")


if __name__ == "__main__":
    asyncio.run(main())
