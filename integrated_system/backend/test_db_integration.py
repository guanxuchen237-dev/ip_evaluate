
import sys
import os
import pandas as pd

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_manager import DataManager

def test_integration():
    print("🚀 Initializing DataManager (triggers DB fetch)...")
    dm = DataManager()
    
    if dm.df is None or dm.df.empty:
        print("❌ DataManager.df is empty! Fetch failed.")
        return
        
    print(f"✅ Data Loaded: {len(dm.df)} records.")
    print(f"Columns: {list(dm.df.columns)}")
    
    if 'IP_Score' in dm.df.columns:
        print(f"✅ IP_Score present.")
        print(dm.df[['title', 'platform', 'IP_Score']].head(5))
        
        avg_score = dm.df['IP_Score'].mean()
        print(f"Average IP Score: {avg_score:.2f}")
    else:
        print("❌ IP_Score MISSING!")
        
    if 'platform' in dm.df.columns:
        print("Platform Distribution:")
        print(dm.df['platform'].value_counts())

if __name__ == "__main__":
    test_integration()
