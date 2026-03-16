import pandas as pd
import numpy as np
import os
from snownlp import SnowNLP

DATA_DIR = r"d:\analysis-novel\data_analysis_v3"
RAW_FILE = os.path.join(DATA_DIR, "raw_data.csv")
OUT_FILE = os.path.join(DATA_DIR, "featured_data.csv")

def calculate_entropy_score(df, cols):
    """
    Entropy Weight Method to calculate IP Score
    """
    # 1. Normalization (Min-Max)
    # Add small epsilon to avoid log(0)
    df_norm = df.copy()
    for col in cols:
        min_v = df[col].min()
        max_v = df[col].max()
        if max_v - min_v == 0:
            df_norm[col] = 0
        else:
            df_norm[col] = (df[col] - min_v) / (max_v - min_v)
    
    # 2. P_ij
    data = df_norm[cols].values + 1e-5 # avoid 0
    k = 1.0 / np.log(len(df))
    p = data / data.sum(axis=0)
    
    # 3. Entropy
    e = -k * (p * np.log(p)).sum(axis=0)
    
    # 4. Weights
    d = 1 - e
    w = d / d.sum()
    
    # 5. Score
    # IP Score = weighted sum * 100
    score = np.dot(df_norm[cols].values, w) * 100
    return score, w

def get_sentiment(text):
    if not isinstance(text, str) or not text.strip():
        return 0.5
    try:
        return SnowNLP(text[:500]).sentiments # Limit length
    except:
        return 0.5

def main():
    print("Loading data...")
    df = pd.read_csv(RAW_FILE)

    # === Task 1: Cleaning & Preprocessing ===
    print("Preprocessing...")
    # 1. Lifecycle Partitioning (Eslami 2022)
    # Introduction: word_count < 300,000 AND status == '连载'
    def get_lifecycle(row):
        if row['word_count'] < 300000 and row['status'] == '连载':
            return 'Introduction'
        return 'Maturity'
    
    df['lifecycle_stage'] = df.apply(get_lifecycle, axis=1)
    
    # 2. Outlier Handling (Cold Start) for Introduction
    # Fill 0 popularity/finance with Category Median
    df['is_simulated'] = 0
    
    # Calculate medians per category
    cat_medians = df.groupby('category')[['popularity', 'finance']].median()
    
    # Iterate and fill
    for idx, row in df.iterrows():
        if row['lifecycle_stage'] == 'Introduction':
            p_val = row['popularity']
            f_val = row['finance']
            
            # Simple heuristic: if value is effectively 0
            if p_val <= 1 or f_val <= 1:
                cat = row['category']
                if cat in cat_medians.index:
                    if p_val <= 1:
                        df.at[idx, 'popularity'] = cat_medians.at[cat, 'popularity']
                        df.at[idx, 'is_simulated'] = 1
                    if f_val <= 1:
                        df.at[idx, 'finance'] = cat_medians.at[cat, 'finance']
                        df.at[idx, 'is_simulated'] = 1
    
    # 3. Data Alignment
    df['finance'] = df['finance'].fillna(0)
    df['fans_count'] = df['fans_count'].fillna(0)
    
    print("Preprocessing done.")

    # === Task 2: Advanced Feature Engineering ===
    print("Engineering Features...")
    
    # 1. Core Fan Ratio (Jiang Hao 2022)
    df['core_fan_ratio'] = df['fans_count'] / (df['popularity'] + 1)
    
    # 2. Sentiment Intensity (Li Hui 2024)
    print("Running Sentiment Analysis (this may take a while)...")
    # Batch apply
    df['sentiment_score'] = df['abstract'].apply(get_sentiment)
    df['sentiment_intensity'] = (df['sentiment_score'] - 0.5).abs() * 2
    
    # 3. Growth Potential (Li et al. 2022)
    df['growth_potential'] = df['week_recommend'] / (df['interaction'] + 1)
    
    # 4. Conversion Difficulty (Xue Xinyu 2024)
    def get_diff(cat):
        if not isinstance(cat, str): return 0.5
        if cat in ['玄幻', '仙侠', 'Oriental Mystery', 'Xianxia']: # Add potential translations if needed
            return 0.8
        if cat in ['都市', 'Urban']:
            return 0.2
        return 0.5 # Default
    
    df['conversion_difficulty'] = df['category'].apply(get_diff)
    
    # === Task 3 Prep: Ground Truth IP Score ===
    print("Calculating IP Scores (Entropy Method)...")
    indicators = ['popularity', 'interaction', 'finance', 'fans_count']
    score, weights = calculate_entropy_score(df, indicators)
    df['IP_Score'] = score
    print(f"Entropy Weights: {dict(zip(indicators, weights))}")
    
    # Save
    df.to_csv(OUT_FILE, index=False, encoding='utf-8-sig')
    print(f"✅ Feature Engineering Complete! Saved to {OUT_FILE}")

if __name__ == "__main__":
    main()
