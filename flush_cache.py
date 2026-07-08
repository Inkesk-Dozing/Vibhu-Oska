"""
Flush all response_cache:* keys from the CacheManager.
Run this once to clear stale Sovereign GPT junk from the cache.
"""
import asyncio, sys
sys.path.insert(0, r'c:\Users\USER\Desktop\Extras\.i-oska\Vibhu-Oska')

from Backend.Plugins.CacheManager.CacheManager import CacheManager

async def flush():
    cm = CacheManager()
    await cm.initialize()
    
    # Try Redis KEYS pattern first
    try:
        keys = await cm.execute("keys", pattern="response_cache:*")
        if keys:
            print(f"Found {len(keys)} cached keys:")
            for k in keys:
                print(f"  DELETE: {k}")
                await cm.execute("delete", key=k)
            print("Done.")
        else:
            print("No response_cache keys found (may be empty or in-memory).")
    except Exception as e:
        print(f"KEYS failed: {e}")
        # Try clearing via the cache manager's own flush if available
        try:
            await cm.execute("flush")
            print("Flushed entire cache.")
        except Exception as e2:
            print(f"Flush also failed: {e2}")
            # Direct dict clear if it's an in-memory implementation
            if hasattr(cm, '_store') or hasattr(cm, '_cache'):
                store = getattr(cm, '_store', None) or getattr(cm, '_cache', None)
                if isinstance(store, dict):
                    before = len(store)
                    keys_to_del = [k for k in store if k.startswith('response_cache:')]
                    for k in keys_to_del:
                        del store[k]
                    print(f"Cleared {len(keys_to_del)} in-memory cache entries.")
                else:
                    print(f"Unknown store type: {type(store)}")
    await cm.shutdown()

asyncio.run(flush())
