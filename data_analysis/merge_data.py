import pymongo
import pandas as pd
import re

# Config
MONGO_URI = "mongodb://127.0.0.1:27017"
DB_NAME = "novel_analysis"
OUTPUT_FILE = "d:/analysis-novel/data_analysis/combined_features.csv"

def clean_word_count(val):
    # Convert '123.45万' or 1234500 to raw number
    if isinstance(val, (int, float)):
        return float(val)
    if not val:
        return 0
    val = str(val).replace('字', '').replace('数', '')
    if '万' in val:
        try:
            return float(val.replace('万', '')) * 10000
        except:
            return 0
    try:
        return float(val)
    except:
        return 0

def merge():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # 1. Fetch Qidian (Target: 100)
    q_data = list(db['qidian_novels'].find({}, {'_id':0}))
    df_q = pd.DataFrame(q_data)
    df_q['platform'] = 'Qidian'
    # Ensure cols
    df_q.rename(columns={'monthly_ticket_count': 'month_tickets'}, inplace=True) # Standardize Name
    
    # 2. Fetch Zongheng (Target: 100)
    z_data = list(db['novels'].find({}, {'_id':0}))
    df_z = pd.DataFrame(z_data)
    df_z['platform'] = 'Zongheng'
    
    # Mapping Zongheng schema to Qidian
    # ZH: total_words -> word_count
    # ZH: monthly_ticket_count -> month_tickets
    # ZH: total_recommendation_count -> total_recommendation_count
    # ZH: nickname / author_name -> author_name
    
    cols_map = {
        'total_words': 'word_count',
        'monthly_ticket_count': 'month_tickets',
        'pseudonym': 'author_name',
        'cateFineName': 'category_name' # Zongheng field
    }
    df_z.rename(columns=cols_map, inplace=True)
    
    # Combined DF
    common_cols = ['title', 'author_name', 'word_count', 'month_tickets', 'total_recommendation_count', 'status', 'category_name', 'platform']
    
    # Select and Clean
    df_final = pd.DataFrame()
    
    for df in [df_q, df_z]:
        # Missing columns fix
        for c in common_cols:
            if c not in df.columns:
                df[c] = 0 if 'count' in c or 'tickets' in c else ''
                
        temp = df[common_cols].copy()
        
        # Clean numeric
        temp['word_count'] = temp['word_count'].apply(clean_word_count)
        temp['month_tickets'] = pd.to_numeric(temp['month_tickets'], errors='coerce').fillna(0)
        temp['total_recommendation_count'] = pd.to_numeric(temp['total_recommendation_count'], errors='coerce').fillna(0)
        
        df_final = pd.concat([df_final, temp], ignore_index=True)
        
    print(f"Merged Data: {len(df_final)} rows (Qidian: {len(df_q)}, Zongheng: {len(df_z)})")
    
    # Feature Engineering (Unified)
    # Engagement = Month Tickets / (Words/10k)
    df_final['engagement_score'] = df_final.apply(lambda x: x['month_tickets'] / (x['word_count']/10000 + 1), axis=1)
    
    df_final.to_csv(OUTPUT_FILE, index=False, encoding='utf-8_sig')
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    merge()
