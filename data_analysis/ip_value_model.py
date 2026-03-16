import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import os

# Config
input_file = "d:/analysis-novel/data_analysis/qidian_nlp.csv"
output_file = "d:/analysis-novel/data_analysis/qidian_final_model.csv"

def calculate_ip_value():
    print("Loading data for Modeling...")
    df = pd.read_csv(input_file)
    
    # --- DIMENSION CALCULATION ---
    scaler = MinMaxScaler()

    # 1. Market Performance (30%)
    # Metrics: Total Recommendations, Inverse Rank (Top rank = high score)
    # Note: Rank 1 is best. We invert it: (max_rank - rank) / max_rank
    max_rank = df['rank'].max()
    df['market_score_raw'] = 0.7 * (df['total_recommendation_count']) + 0.3 * ((max_rank - df['rank'] + 1) * 10000) 
    # (Simplified combination, will rely on Scaler later)
    
    # 2. Content Quality (25%)
    # Metrics: Word Count, Status
    df['content_score_raw'] = df['word_count'] * df['status_score']

    # 3. User Reputation (20%)
    # Metrics: Sentiment Score (already 0-1)
    df['reputation_score_raw'] = df['sentiment_score']

    # 4. User Engagement (15%)
    # Metrics: Ticket density (loyalty/intensity)
    df['engagement_score_raw'] = df['ticket_per_10k'] + df['reward_count'] * 10 

    # 5. Growth Potential (10%)
    # Metrics: Week Recs / Total Recs (Heat Ratio)
    df['potential_score_raw'] = df['heat_ratio'] * df['week_recommendation_count']

    # --- NORMALIZATION (0-100 Scale) ---
    dims = ['market_score', 'content_score', 'reputation_score', 'engagement_score', 'potential_score']
    
    for dim in dims:
        raw_col = dim + '_raw'
        # Log transform for highly skewed data (like word counts or tickets)? 
        # For simplicity in this demo, just MinMax.
        df[dim] = scaler.fit_transform(df[[raw_col]]) * 100
    
    # --- FINAL IP VALUE ---
    # Weights from Literature (Sang Ziwen): 0.3, 0.25, 0.2, 0.15, 0.1
    df['IP_Value'] = (
        0.30 * df['market_score'] +
        0.25 * df['content_score'] +
        0.20 * df['reputation_score'] +
        0.15 * df['engagement_score'] +
        0.10 * df['potential_score']
    )
    
    # Sort
    df = df.sort_values(by='IP_Value', ascending=False)
    
    # Add Rank
    df['Model_Rank'] = range(1, len(df) + 1)
    
    # Select cols
    final_cols = ['title', 'IP_Value', 'Model_Rank'] + dims + ['topic_id', 'sentiment_score', 'word_count']
    final_df = df[final_cols]
    
    print("\nTop 10 High-Value IPs:")
    print(final_df.head(10))
    
    final_df.to_csv(output_file, index=False, encoding='utf-8_sig')
    print(f"\nFinal Model saved to {output_file}")

if __name__ == "__main__":
    calculate_ip_value()
