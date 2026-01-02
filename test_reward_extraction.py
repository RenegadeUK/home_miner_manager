#!/usr/bin/env python3
"""
Test DigiExplorer transaction endpoint and extract reward
"""
import asyncio
import aiohttp
import json

async def test_reward_extraction():
    """Test extracting block reward from DigiExplorer API"""
    
    block_hash = "03a41cd99216ec690d00e54e77280ac37c4966fdd4abbdd718f4ff6b0321b109"
    
    # Correct endpoint: /api/block/{hash}/txs
    url = f"https://digiexplorer.info/api/block/{block_hash}/txs"
    
    print(f"Testing DigiExplorer transaction endpoint...")
    print(f"URL: {url}\n")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                print(f"Status Code: {response.status}\n")
                
                if response.status == 200:
                    txs = await response.json()
                    
                    if isinstance(txs, list) and len(txs) > 0:
                        # First transaction is coinbase
                        coinbase_tx = txs[0]
                        
                        print("✅ Coinbase Transaction Found")
                        print(f"   TXID: {coinbase_tx.get('txid')}")
                        
                        # Check if it's actually a coinbase transaction
                        if coinbase_tx.get('vin') and len(coinbase_tx['vin']) > 0:
                            is_coinbase = coinbase_tx['vin'][0].get('is_coinbase', False)
                            print(f"   Is Coinbase: {is_coinbase}")
                        
                        # Extract reward from vout (outputs)
                        if 'vout' in coinbase_tx:
                            print(f"\n📊 Block Reward Calculation:")
                            total_reward = 0.0
                            
                            for i, output in enumerate(coinbase_tx['vout']):
                                # Check for 'value' field
                                if 'value' in output:
                                    value = float(output['value'])
                                    total_reward += value
                                    addr = output.get('scriptpubkey_address', 'N/A')
                                    print(f"   Output {i}: {value} DGB -> {addr}")
                            
                            print(f"\n   Total Block Reward: {total_reward} DGB")
                            print(f"\n✅ This is the value we should store in the database!")
                        else:
                            print("\n⚠️ No 'vout' field found in coinbase transaction")
                            print(f"Available keys: {list(coinbase_tx.keys())}")
                    else:
                        print("⚠️ No transactions returned or invalid format")
                else:
                    text = await response.text()
                    print(f"❌ Failed with status {response.status}")
                    print(f"Response: {text[:500]}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reward_extraction())
