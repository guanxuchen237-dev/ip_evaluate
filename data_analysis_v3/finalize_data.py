import pandas as pd
import numpy as np
import os
from sklearn.preprocessing import MinMaxScaler

DATA_DIR = r"d:\analysis-novel\data_analysis_v3"
IN_FILE = os.path.join(DATA_DIR, "featured_data_v2.csv")
OUT_FILE = os.path.join(DATA_DIR, "final_featured_data.csv")

def calculate_entropy_score(df, cols):
    """
    Entropy Weight Method to calculate IP Score (Raw)
    """
    df_norm = df.copy()
    for col in cols:
        min_v = df[col].min()
        max_v = df[col].max()
        if max_v - min_v == 0:
            df_norm[col] = 0
        else:
            df_norm[col] = (df[col] - min_v) / (max_v - min_v)
    
    data = df_norm[cols].values + 1e-5
    k = 1.0 / np.log(len(df))
    p = data / data.sum(axis=0)
    e = -k * (p * np.log(p)).sum(axis=0)
    d = 1 - e
    w = d / d.sum()
    
    score = np.dot(df_norm[cols].values, w)
    return score, w

def finalize():
    print("Loading featured_data_v2.csv...")
    if not os.path.exists(IN_FILE):
        print(f"Error: {IN_FILE} not found.")
        return
        
    df = pd.read_csv(IN_FILE)
    
    # 1. Refine Logic: Lifecycle
    # < 500,000 words AND '连载' => Introduction
    def get_lifecycle(row):
        if row['word_count'] < 500000 and row['status'] == '连载':
            return 'Introduction'
        return 'Maturity'
    df['lifecycle_stage'] = df.apply(get_lifecycle, axis=1)
    
    # 2. Refine Logic: Conversion Difficulty
    # Contains "玄幻" or "仙侠" => 0.8
    def get_diff(cat):
        if not isinstance(cat, str): return 0.5
        cat = cat.lower()
        if '玄幻' in cat or '仙侠' in cat or 'oriental mystery' in cat or 'xianxia' in cat:
            return 0.8
        if '都市' in cat or 'urban' in cat:
            return 0.2
        return 0.5
    df['conversion_difficulty'] = df['category'].apply(get_diff)
    
    # 3. Recalculate IP Score (Entropy)
    print("Recalculating Entropy Score...")
    indicators = ['popularity', 'interaction', 'finance', 'fans_count']
    raw_score, _ = calculate_entropy_score(df, indicators)
    
    # 4. Score Scaling (MinMax to 40-100)
    scaler = MinMaxScaler(feature_range=(40, 100))
    # Reshape for scalar
    scaled_score = scaler.fit_transform(raw_score.reshape(-1, 1)).flatten()
    df['IP_Score'] = np.round(scaled_score, 1)
    
    # 5. Grading
    def get_grade(s):
        if s >= 90: return 'S'
        if s >= 80: return 'A'
        if s >= 70: return 'B'
        return 'C'
    df['Grade'] = df['IP_Score'].apply(get_grade)
    
    # Save
    df.to_csv(OUT_FILE, index=False, encoding='utf-8-sig')
    print(f"✅ Final data saved to {OUT_FILE}")
    print("Distribution of Grades:")
    print(df['Grade'].value_counts())

if __name__ == "__main__":
    finalize()
