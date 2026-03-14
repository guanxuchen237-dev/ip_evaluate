"""
Model Trainer for IP Value Prediction
负责模型训练、评估和保存
"""
import os
import joblib
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from datetime import datetime

# Import DataManager instance to reuse data loading & feature engineering
from data_manager import data_manager
from interaction_manager import interaction_manager

class ModelTrainer:
    def __init__(self):
        self.models_dir = data_manager.models_dir
        self.default_params = {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'objective': 'reg:squarederror',
            'n_jobs': -1
        }
        self.last_training_log = []
        self.is_training = False

    def _log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        print(entry)
        self.last_training_log.append(entry)
        # Keep log size manageable
        if len(self.last_training_log) > 100:
            self.last_training_log.pop(0)

    def prepare_dataset(self):
        """
        准备训练数据：
        1. 获取书籍基础数据 (DataManager)
        2. 获取交互特征 (InteractionManager)
        3. 合并特征
        4. 构建 Target (y)
        """
        self._log("Loading base book data...")
        # 强制刷新数据
        data_manager.load_data()
        df = data_manager.df.copy()
        
        if df.empty:
            raise ValueError("No book data available for training")
            
        self._log(f"Loaded {len(df)} books. Loading interaction data...")
        
        # 获取交互特征
        df_interact = interaction_manager.get_interaction_features()
        if not df_interact.empty:
            # 构建 Key
            df['book_key'] = df['platform'] + '|' + df['title'] + '|' + df['author']
            
            # Left Join
            df = df.merge(df_interact, on='book_key', how='left')
            
            # Fill NaN for interaction features
            interaction_cols = ['total_msgs', 'user_msgs', 'avg_user_len', 'engagement_score']
            for c in interaction_cols:
                if c in df.columns:
                    df[c] = df[c].fillna(0)
            self._log(f"Merged interaction data. Found {len(df_interact)} interactions.")
        else:
            # 如无交互数据，填充0
            self._log("No interaction data found. Using empty features.")
            for c in ['total_msgs', 'user_msgs', 'avg_user_len', 'engagement_score']:
                df[c] = 0

        # 复用 DataManager 的特征工程
        self._log("Engineering features...")
        df_encoded = data_manager._engineer_features_batch(df)
        
        # 确保交互特征存在于 encoded df (如果 _engineer_features_batch 过滤了它们)
        # 假设 _engineer_features_batch 只返回它知道的列，我们需要把 interaction columns 加回去
        # 检查 DataManager 源码，它确实可能会丢弃它不认识的列？
        # 实际上 _engineer_features_batch 返回的是 copy，所以我们可以手动添加
        
        # Define Feature Columns for Training
        feature_cols = [
            'word_count', 'interaction', 'finance', 'popularity', 
            'word_count_log', 'popularity_log', 'interaction_log', 
            'cat_东方玄幻', 'cat_其他', 'cat_都市', # ... (简化，实际应包含所有 dummy cols)
            'status_0', 'plat_qidian', 'plat_zongheng',
            # 新增交互特征
            'engagement_score', 'total_msgs'
        ]
        
        # Auto-detect dummy columns from dataframe
        all_cols = df_encoded.columns.tolist()
        final_features = []
        for c in feature_cols:
            if c in all_cols:
                final_features.append(c)
            # Add dynamic cat_ columns
            elif c.startswith('cat_') or c.startswith('plat_'):
                 # It might be there under similar names, but let's trust auto-detection
                 pass
        
        # Better strategy: Use numerical + all bool/dummies
        numeric_cols = ['word_count', 'interaction', 'finance', 'popularity', 'engagement_score', 'total_msgs']
        # Log variants
        numeric_cols += [c for c in all_cols if '_log' in c]
        
        dummy_cols = [c for c in all_cols if c.startswith('cat_') or c.startswith('plat_') or c.startswith('status_')]
        
        X_cols = numeric_cols + dummy_cols
        X_cols = [c for c in X_cols if c in df_encoded.columns] # Validate existence
        
        # Prepare X and y
        X = df_encoded[X_cols].fillna(0)
        
        # Construct Target y: Composite Score of Popularity + Finance
        # Log transform to reduce skew
        # y = 0.4 * log(pop) + 0.4 * log(finance) + 0.2 * log(interaction)
        # Handle zeros
        pop_log = np.log1p(df['popularity'].fillna(0))
        fin_log = np.log1p(df['finance'].fillna(0))
        int_log = np.log1p(df['interaction'].fillna(0))
        
        # Normalize to 0-1 range for target to make it easier
        def minmax(series):
            return (series - series.min()) / (series.max() - series.min() + 1e-6)
            
        y_raw = 0.4 * minmax(pop_log) + 0.4 * minmax(fin_log) + 0.2 * minmax(int_log)
        y = y_raw * 100 # Scale to 0-100
        
        self._log(f"Dataset prepared. Features: {len(X_cols)}, Samples: {len(X)}")
        return X, y, X_cols

    def train(self, params=None):
        if self.is_training:
            return {"status": "error", "message": "Training already in progress"}
            
        self.is_training = True
        self.last_training_log = []
        try:
            train_params = self.default_params.copy()
            if params:
                train_params.update(params)
                
            X, y, feature_names = self.prepare_dataset()
            
            # ===== 交叉验证评估 =====
            from sklearn.model_selection import cross_val_score
            self._log("Running 5-fold Cross Validation...")
            
            # 使用 sklearn 包装器进行交叉验证
            xgb_estimator = xgb.XGBRegressor(
                n_estimators=int(train_params.get('n_estimators', 100)),
                max_depth=int(train_params.get('max_depth', 6)),
                learning_rate=train_params.get('learning_rate', 0.1),
                subsample=train_params.get('subsample', 0.8),
                colsample_bytree=train_params.get('colsample_bytree', 0.8),
                n_jobs=-1
            )
            
            cv_scores = cross_val_score(xgb_estimator, X, y, cv=5, scoring='r2')
            self._log(f"CV R2 Scores: {[f'{s:.4f}' for s in cv_scores]}")
            self._log(f"CV Mean R2: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
            
            # ===== 正式训练 =====
            # Split
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale
            self._log("Scaling features...")
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Convert to DMatrix
            dtrain = xgb.DMatrix(X_train_scaled, label=y_train, feature_names=feature_names)
            dtest = xgb.DMatrix(X_test_scaled, label=y_test, feature_names=feature_names)
            
            # Train
            self._log(f"Starting XGBoost training with params: {train_params}")
            evals = [(dtrain, 'train'), (dtest, 'eval')]
            
            results = {}
            model = xgb.train(
                train_params,
                dtrain,
                num_boost_round=int(train_params.get('n_estimators', 100)),
                evals=evals,
                early_stopping_rounds=10,
                evals_result=results,
                verbose_eval=False 
            )
            
            self._log("Training completed.")
            
            # Evaluation
            preds = model.predict(dtest)
            rmse = np.sqrt(mean_squared_error(y_test, preds))
            r2 = r2_score(y_test, preds)
            
            self._log(f"Evaluation Results: RMSE={rmse:.4f}, R2={r2:.4f}")
            
            # ===== 特征重要性 =====
            importance = model.get_score(importance_type='gain')
            sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)
            self._log("Top 10 Feature Importance (gain):")
            for fname, score in sorted_importance[:10]:
                self._log(f"  {fname}: {score:.2f}")
            
            # Save Model & Scaler
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_filename = f"ip_predictor_v3_{timestamp}.pkl"
            scaler_filename = f"scaler_v3_{timestamp}.pkl"
            
            save_path_model = os.path.join(self.models_dir, model_filename)
            save_path_scaler = os.path.join(self.models_dir, scaler_filename)
            
            joblib.dump(model, save_path_model)
            joblib.dump(scaler, save_path_scaler)
            
            # Also save feature names for future inference
            joblib.dump(feature_names, os.path.join(self.models_dir, f"features_{timestamp}.pkl"))
            
            self._log(f"Model saved to {model_filename}")
            
            return {
                "status": "success",
                "metrics": {
                    "rmse": rmse, 
                    "r2": r2,
                    "cv_mean_r2": float(cv_scores.mean()),
                    "cv_std_r2": float(cv_scores.std())
                },
                "feature_importance": sorted_importance[:15],
                "model_path": model_filename,
                "log": self.last_training_log
            }
            
        except Exception as e:
            self._log(f"[ERROR] Training failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e), "log": self.last_training_log}
        finally:
            self.is_training = False

# Global Instance
model_trainer = ModelTrainer()
