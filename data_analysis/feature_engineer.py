import pandas as pd
import os

# Config
input_file = "d:/analysis-novel/data_analysis/qidian_data.csv"
output_file = "d:/analysis-novel/data_analysis/qidian_features.csv"

def process_features():
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} rows.")

    # 1. Cleaning & Type Conv
    # Ensure numeric
    num_cols = ['monthly_ticket_count', 'reward_count', 
                'total_recommendation_count', 'week_recommendation_count', 'word_count']
    
    for col in num_cols:
         if col not in df.columns:
             df[col] = 0
         else:
             df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 2. Derived Features
    # A. Interaction Intensity (Tickets per 10k words)
    df['ticket_per_10k'] = df.apply(lambda x: x['monthly_ticket_count'] / (x['word_count']/10000 + 1) if x['word_count'] > 0 else 0, axis=1)

    # B. Current Heat (Week Rec / Total Rec) - Proxy for "Growth Potential"
    df['heat_ratio'] = df.apply(lambda x: x['week_recommendation_count'] / (x['total_recommendation_count'] + 1), axis=1)
    
    # C. Fan Loyalty (Reward / Ticket) - Proxy for "User Engagement" quality
    df['loyalty_score'] = df.apply(lambda x: x['reward_count'] / (x['monthly_ticket_count'] + 1), axis=1)

    # D. Status Score (Serialized=1, Finished=0.5? Literature says Finished is better for immediate IP but Serialized has engagement)
    # Let's just keep status as is for now, maybe One-Hot later. 
    # But for simple score, let's map: 连载=1, 完结=0.8 (Assumption: Active books have more current value)
    df['status_score'] = df['status'].map({'连载': 1.0, '完本': 0.8, '完结': 0.8}).fillna(0.5)
    
    # 3. Normalization (Min-Max) for scoring
    # We will do this in the modeling step, here just save the raw features.
    
    print("Features engineered:")
    print(df[['title', 'ticket_per_10k', 'heat_ratio', 'loyalty_score']].head())

    df.to_csv(output_file, index=False, encoding='utf-8_sig')
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    process_features()
