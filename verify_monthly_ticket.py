import sys
import os

# Add path to backend to import modules
sys.path.append(os.path.join(os.getcwd(), 'integrated_system', 'backend'))

try:
    from data_manager import DataManager
except ImportError:
    try:
        from integrated_system.backend.data_manager import DataManager
    except Exception as e:
        print(f"Import Error: {e}")
        exit(1)

def verify_ticket_logic():
    print("Initializing DataManager...")
    dm = DataManager()
    
    # Check "捞尸人"
    target_book = "捞尸人"
    
    # We use get_library_data to see the final output
    print(f"Fetching library data for {target_book}...")
    result = dm.get_library_data(page=1, page_size=10, filters={'search': target_book})
    
    items = result.get('items', [])
    if not items:
        print(f"❌ Book {target_book} not found in library.")
        return

    for item in items:
        if item['title'] == target_book:
            print(f"Book: {item['title']}")
            print(f"Platform: {item['platform']}")
            print(f"Monthly Tickets (Finance): {item['monthly_tickets']}")
            
            # Heuristic check: Single month tickets shouldn't be millions usually, unless it's a super hit.
            # But definitely should be lower than the SUM seen before (5.3M).
            if item['monthly_tickets'] < 5000000:
                 print("✅ VERIFIED: Value is significantly lower than cumulative sum (5.3M).")
            else:
                 print("⚠️ WARNING: Value is still very high. Check if raw data is cumulative.")

if __name__ == "__main__":
    verify_ticket_logic()
