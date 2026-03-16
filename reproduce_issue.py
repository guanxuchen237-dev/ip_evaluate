import pandas as pd
import sys
import os

# Add path to backend to import modules
sys.path.append(os.path.join(os.getcwd(), 'integrated_system', 'backend'))

try:
    from data_manager import DataManager
except ImportError:
    # Try local import if running from root
    try:
        from integrated_system.backend.data_manager import DataManager
    except Exception as e:
        print(f"Import Error: {e}")
        exit(1)

def check_discrepancy():
    dm = DataManager()
    df = dm.df
    
    if df.empty:
        print("Dataframe is empty!")
        return

    with open('discrepancy_log.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total rows in raw DF: {len(df)}\n")
        
        # Dashboard Logic: Unique Titles
        dashboard_count = df['title'].nunique()
        f.write(f"Dashboard Count (Unique Titles): {dashboard_count}\n")
        
        # Library Logic: Group by Title, Author, Platform
        df_agg = df.groupby(['title', 'author', 'platform'], as_index=False).agg({'title':'first'})
        library_count = len(df_agg)
        f.write(f"Library Count (Unique Title+Author+Platform): {library_count}\n")
        
        # Find the difference
        diff = library_count - dashboard_count
        f.write(f"Difference: {diff}\n")
        
        if diff > 0:
            f.write("\nItems causing discrepancy (Same Title, Different Platform/Author):\n")
            title_counts = df_agg['title'].value_counts()
            dupe_titles = title_counts[title_counts > 1].index.tolist()
            
            for t in dupe_titles:
                entries = df_agg[df_agg['title'] == t]
                f.write(f" - Title: {t}\n")
                for _, row in entries.iterrows():
                    f.write(f"   * Platform: {row['platform']}, Author: {row['author']}\n")
    
    print("Log written to discrepancy_log.txt")

if __name__ == "__main__":
    check_discrepancy()
