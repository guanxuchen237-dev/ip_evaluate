import pandas as pd
import numpy as np
import xgboost as xgb
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

DATA_DIR = r"d:\analysis-novel\data_analysis_v3"
IN_FILE = os.path.join(DATA_DIR, "final_featured_data.csv")
MODEL_FILE = os.path.join(DATA_DIR, "dual_engine_model.pkl")

def train_engine_a(df):
    print("\n=== Training Engine A (Maturity Model) ===")
    features = ['popularity', 'finance', 'interaction', 'word_count']
    target = 'IP_Score'
    
    X = df[features]
    y = df[target]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1, max_depth=5)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    print(f"Engine A RMSE: {rmse:.4f}")
    
    # Feature Importance
    print("Feature Importance:")
    for name, val in zip(features, model.feature_importances_):
        print(f"  - {name}: {val:.4f}")
        
    return model

def train_engine_b(df):
    print("\n=== Training Engine B (Introduction Model) ===")
    # Pre-calc abstract length if missing
    if 'abstract_length' not in df.columns:
        df['abstract_length'] = df['abstract'].fillna('').apply(len)
        
    features_numeric = ['sentiment_score', 'sentiment_intensity', 'abstract_length', 'growth_potential']
    # category is categorical, simpler to just use numeric for this demo or One-Hot
    # Using pandas get_dummies
    df_encoded = pd.get_dummies(df, columns=['category'], prefix='cat')
    
    # Identify all feature columns (numeric + encoded cats)
    feature_cols = features_numeric + [c for c in df_encoded.columns if c.startswith('cat_')]
    
    X = df_encoded[feature_cols]
    y = df_encoded['IP_Score']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1, max_depth=5)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    print(f"Engine B RMSE: {rmse:.4f}")
    
    # Feature Importance (Top 10)
    print("Top 10 Feature Importance:")
    imps = sorted(zip(feature_cols, model.feature_importances_), key=lambda x: x[1], reverse=True)[:10]
    for name, val in imps:
        print(f"  - {name}: {val:.4f}")
        
    return model

def main():
    if not os.path.exists(IN_FILE):
        print(f"Error: {IN_FILE} not found. Run feature engineering first.")
        return

    df = pd.read_csv(IN_FILE)
    
    # Convert types
    cols = ['popularity', 'finance', 'interaction', 'word_count', 'fans_count', 'week_recommend']
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # Split Data
    df_maturity = df[df['lifecycle_stage'] == 'Maturity'].copy()
    df_intro = df[df['lifecycle_stage'] == 'Introduction'].copy()
    
    print(f"Data Split: Maturity={len(df_maturity)}, Introduction={len(df_intro)}")
    
    models = {}
    if len(df_maturity) > 10:
        models['Engine_A'] = train_engine_a(df_maturity)
    else:
        print("Not enough data for Engine A")

    if len(df_intro) > 10:
        models['Engine_B'] = train_engine_b(df_intro)
    else:
        print("Not enough data for Engine B")
        
    # Save Models
    with open(MODEL_FILE, 'wb') as f:
        pickle.dump(models, f)
    print(f"\n✅ Models saved to {MODEL_FILE}")

if __name__ == "__main__":
    main()
