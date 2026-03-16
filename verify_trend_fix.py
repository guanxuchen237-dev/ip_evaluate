
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'integrated_system/backend'))
from data_manager import DataManager
import json

def verify_trends():
    print("=== Testing Trend Chart Recovery (DB Direct Query) ===")
    dm = DataManager()
    
    platforms = ['qidian', 'zongheng']
    for p in platforms:
        print(f"\n--- Platform: {p} ---")
        trend = dm.get_long_term_trend(platform=p)
        print(f"Dates found: {len(trend['dates'])}")
        if trend['dates']:
            print(f"Date Range: {trend['dates'][0]} to {trend['dates'][-1]}")
            
        for s in trend['series']:
            name = s['name']
            data = s['data']
            non_zero = [v for v in data if v > 0]
            print(f"Book: {name} | Data points: {len(data)} | Non-zero points: {len(non_zero)}")
            # If de-duplication was the cause, non-zero should now be > 1
            if len(non_zero) <= 1:
                 print(f"⚠️ Warning: {name} still has only {len(non_zero)} data points.")
            else:
                 print(f"✅ Success: {name} recovered {len(non_zero)} historical points.")

if __name__ == "__main__":
    verify_trends()
