import pandas as pd
import pymysql
import os

# Configuration
DATA_DIR = r"d:\analysis-novel\data_analysis_v3"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data', 'charset': 'utf8mb4'
}

def extract_zongheng():
    print("Extracting Zongheng data...")
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    try:
        # Map columns to standard names
        # Standard: title, author, category, abstract, status, platform, word_count, popularity, interaction, finance, fans_count, week_recommend
        sql = """
        SELECT 
            title, 
            author, 
            category, 
            status, 
            word_count, 
            total_click as popularity, 
            total_rec as interaction, 
            monthly_ticket as finance, 
            fan_count as fans_count, 
            week_rec as week_recommend
        FROM zongheng_book_ranks
        """
        df = pd.read_sql(sql, conn)
        df['platform'] = 'Zongheng'
        df['abstract'] = '' # Zongheng missing abstract
        
        # Normalize Status
        # Zongheng might be '连载中' or '已完结'
        # Target: '连载' or '完结' (keep consistent)
        df['status'] = df['status'].apply(lambda x: '连载' if '连载' in str(x) else '完结')
        
        print(f"Zongheng: {len(df)} rows")
        return df
    finally:
        conn.close()

def extract_qidian():
    print("Extracting Qidian data...")
    conn = pymysql.connect(**QIDIAN_CONFIG)
    try:
        # Standard names mapping
        # Qidian: collection_count -> popularity (Proxy), recommendation_count -> interaction, monthly_ticket_count -> finance, reward_count -> fans_count, week_recommendation_count -> week_recommend
        sql = """
        SELECT 
            title, 
            author, 
            category as category_raw, 
            status, 
            word_count, 
            collection_count as popularity, 
            recommendation_count as interaction, 
            monthly_ticket_count as finance, 
            reward_count as fans_count, 
            week_recommendation_count as week_recommend,
            synopsis as abstract
        FROM novel_monthly_stats
        """
        df = pd.read_sql(sql, conn)
        df['platform'] = 'Qidian'
        df.rename(columns={'category_raw': 'category'}, inplace=True)
        
        # Normalize Status
        # Qidian might be 'serializing' or 'completed'
        df['status'] = df['status'].apply(lambda x: '连载' if str(x) in ['serializing', '连载'] else '完结')
        
        print(f"Qidian: {len(df)} rows")
        return df
    finally:
        conn.close()

def main():
    try:
        df_zh = extract_zongheng()
        df_qd = extract_qidian()
        
        # Combine
        df_all = pd.concat([df_zh, df_qd], ignore_index=True)
        
        # Final column order
        cols = ['title', 'author', 'category', 'abstract', 'status', 'platform', 
                'word_count', 'popularity', 'interaction', 'finance', 'fans_count', 'week_recommend']
        
        # Ensure all columns exist, fill missing with 0/empty
        for c in cols:
            if c not in df_all.columns:
                df_all[c] = 0
                
        df_all = df_all[cols]
        
        # Save
        out_path = os.path.join(DATA_DIR, "raw_data.csv")
        df_all.to_csv(out_path, index=False, encoding='utf-8-sig')
        print(f"✅ Combined data saved to {out_path} ({len(df_all)} rows)")
        
    except Exception as e:
        print(f"❌ Extraction Failed: {e}")

if __name__ == "__main__":
    main()
