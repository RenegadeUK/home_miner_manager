#!/usr/bin/env python3
"""
Test different DigiExplorer API endpoints to find transaction data
"""
import asyncio
import aiohttp
import json

async def test_endpoints():
    """Test various DigiExplorer API endpoints"""
    
    block_hash = "03a41cd99216ec690d00e54e77280ac37c4966fdd4abbdd718f4ff6b0321b109"
    block_height = 22727910
    
    endpoints = [
        f"https://digiexplorer.info/api/block/{block_hash}",
        f"https://digiexplorer.info/api/block/{block_hash}/txs",
        f"https://digiexplorer.info/api/block/{block_hash}/transactions",
        f"https://digiexplorer.info/api/block-height/{block_height}",
        f"https://digiexplorer.info/api/blocks/tip/height",
        # Try insight-api format (common for block explorers)
        f"https://digiexplorer.info/insight-api/block/{block_hash}",
        f"https://digiexplorer.info/api/v1/block/{block_hash}",
    ]
    
    async with aiohttp.ClientSession() as session:
        for url in endpoints:
            print(f"\n{'='*80}")
            print(f"Testing: {url}")
            print('='*80)
            
            try:
                async with session.get(url, timeout=10) as response:
                    print(f"Status: {response.status}")
                    
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        if 'json' in content_type:
                            data = await response.json()
                            print(f"✅ Success! Response structure:")
                            print(json.dumps(data, indent=2)[:1000] + "...")
                        else:
                            text = await response.text()
                            print(f"Non-JSON response ({content_type}):")
                            print(text[:500])
                    else:
                        print(f"❌ Failed with status {response.status}")
                        
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())
