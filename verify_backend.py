import sys
import os
sys.path.append(os.getcwd())

print("Attempting to import ai_service...")
try:
    from integrated_system.backend.ai_service import ai_service
    print("✅ ai_service imported successfully")
except Exception as e:
    print(f"❌ ai_service import failed: {e}")
    import traceback
    traceback.print_exc()

print("Attempting to import app...")
try:
    from integrated_system.backend.app import app
    print("✅ app imported successfully")
except Exception as e:
    print(f"❌ app import failed: {e}")
    import traceback
    traceback.print_exc()
