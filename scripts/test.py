import time
try:
    from backend.database import get_connection
    print("Getting main connection...")
    conn = get_connection()
    print(f"Main DB connected.")

    print("Instantiating ShadowDOMScanner...")
    from backend.dom_deep_serializer import ShadowDOMScanner
    scanner = ShadowDOMScanner(headless=True, db_path="kuzu_db", driver=None, conn=conn)
    print("Scanner instantiated.")
    
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
