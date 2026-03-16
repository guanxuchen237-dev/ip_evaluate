import pandas as pd
import os

DATA_FILE = r"d:\analysis-novel\data_analysis_v3\featured_data.csv"

def verify_data():
    if not os.path.exists(DATA_FILE):
        print("Data file not found.")
        return

    df = pd.read_csv(DATA_FILE)
    print("=== Data Distribution Verification ===")
    print(df['platform'].value_counts())
    
    # Check for text content presence
    print("\n=== Text Content Check ===")
    zh_mask = df['platform'] == 'Zongheng'
    qd_mask = df['platform'] == 'Qidian'
    
    print(f"Zongheng Empty Abstracts: {df[zh_mask]['abstract'].isna().sum() + (df[zh_mask]['abstract'] == '').sum()} / {zh_mask.sum()}")
    print(f"Qidian Empty Abstracts: {df[qd_mask]['abstract'].isna().sum() + (df[qd_mask]['abstract'] == '').sum()} / {qd_mask.sum()}")

if __name__ == "__main__":
    verify_data()
