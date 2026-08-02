import os

from mp_api.client import MPRester

API_KEY = os.environ.get("MP_API_KEY")
if not API_KEY:
    raise RuntimeError("请先设置环境变量 MP_API_KEY。")

try:
    with MPRester(API_KEY) as m:
        print("Methods available:")
        print([x for x in dir(m) if 'structure' in x and 'get' in x])
        print([x for x in dir(m) if 'dos' in x and 'get' in x])
        print([x for x in dir(m) if 'band' in x and 'get' in x])
        
        # Also check sub-routes
        print("\nSub-routes:")
        if hasattr(m, 'materials'): print(f"materials has: {[x for x in dir(m.materials) if 'get' in x]}")
        if hasattr(m, 'electronic_structure'): print(f"electronic_structure has: {[x for x in dir(m.electronic_structure) if 'get' in x]}")
        
except Exception as e:
    print(f"Error: {e}")
