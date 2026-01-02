#!/usr/bin/env python3
"""
Test script to verify DigiExplorer API responses
"""
import asyncio
import aiohttp
import json

async def test_digiexplorer_api():
    """Test DigiExplorer API with a known block hash"""
    
    # Use a recent block hash from the DigiExplorer homepage
    test_block_hash = "03a41cd99216ec690d00e54e77280ac37c4966fdd4abbdd718f4ff6b0321b109"
    
    url = f"https://digiexplorer.info/api/block/{test_block_hash}"
    
    print(f"Testing DigiExplorer API...")
    print(f"URL: {url}\n")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                print(f"Status Code: {response.status}")
                print(f"Content Type: {response.headers.get('Content-Type')}\n")
                
                if response.status == 200:
                    data = await response.json()
                    print("✅ API Response (formatted):")
                    print(json.dumps(data, indent=2))
                    
                    # Check for coinbase transaction
                    if 'tx' in data and len(data['tx']) > 0:
                        print("\n📊 Coinbase Transaction Analysis:")
                        coinbase_tx = data['tx'][0]
                        print(f"  Coinbase TX keys: {list(coinbase_tx.keys())}")
                        
                        if 'vout' in coinbase_tx:
                            total_reward = 0.0
                            print(f"\n  Outputs (vout):")
                            for i, output in enumerate(coinbase_tx['vout']):
                                value = float(output.get('value', 0))
                                total_reward += value
                                print(f"    Output {i}: {value} DGB")
                            print(f"\n  Total Block Reward: {total_reward} DGB")
                        else:
                            print("  ⚠️ 'vout' field not found in coinbase transaction")
                    else:
                        print("\n⚠️ No transactions found in response")
                else:
                    text = await response.text()
                    print(f"❌ Failed with status {response.status}")
                    print(f"Response: {text[:500]}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_digiexplorer_api())
