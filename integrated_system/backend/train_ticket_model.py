"""
Train Ticket Prediction Model from Database Time-Series Data
从数据库实时追踪表训练月票预测模型
"""
import os
import sys
import joblib
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
import pymysql

# Database configs - 使用与 data_manager 相同的配置
QIDIAN_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'qidian_data',
    'charset': 'utf8mb4'
}

ZONGHENG_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'zongheng_analysis_v8',
    'charset': 'utf8mb4'
}

class TicketPredictionTrainer:
    def __init__(self):
        self.models_dir = os.path.join(os.path.dirname(__file__), 'resources', 'models')
        os.makedirs(self.models_dir, exist_ok=True)
        
    def _log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")
        
    def fetch_time_series_data(self, platform='qidian', min_records=5):
        """
        从数据库获取时序数据
        特征：历史月票趋势、收藏增长、时间特征
        """
        self._log(f"Fetching time-series data from {platform}...")
        
        config = QIDIAN_CONFIG if platform == 'qidian' else ZONGHENG_CONFIG
        table = 'novel_realtime_tracking' if platform == 'qidian' else 'zongheng_realtime_tracking'
        col_field = 'collection_count' if platform == 'qidian' else 'total_recommend'
        
        try:
            conn = pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                # 获取有足量数据的书籍列表
                cur.execute(f"""
                    SELECT title, COUNT(*) as cnt 
                    FROM {table} 
                    GROUP BY title 
                    HAVING cnt >= %s
                    ORDER BY cnt DESC
                    LIMIT 200
                """, (min_records,))
                books = cur.fetchall()
                self._log(f"Found {len(books)} books with >= {min_records} records")
                
                if not books:
                    return pd.DataFrame()
                
                # 为每本书提取时序特征
                all_data = []
                for book in books:
                    title = book['title']
                    cur.execute(f"""
                        SELECT crawl_time, monthly_tickets, {col_field} as collection_count
                        FROM {table}
                        WHERE title = %s
                        ORDER BY crawl_time ASC
                    """, (title,))
                    rows = cur.fetchall()
                    
                    if len(rows) < min_records:
                        continue
                    
                    # 构建时序特征
                    for i in range(len(rows)):
                        if i < 3:  # 跳过前几个，需要历史数据
                            continue
                            
                        # 目标：下一个月的月票（或未来7天的平均）
                        future_tickets = [r['monthly_tickets'] or 0 for r in rows[i:min(i+7, len(rows))]]
                        target = np.mean(future_tickets) if future_tickets else 0
                        
                        # 特征：历史窗口
                        hist_window = rows[max(0, i-7):i]
                        hist_tickets = [r['monthly_tickets'] or 0 for r in hist_window]
                        hist_collections = [r['collection_count'] or 0 for r in hist_window]
                        
                        if not hist_tickets or len(hist_tickets) < 3:
                            continue
                        
                        feature = {
                            'title': title,
                            'platform': 1 if platform == 'qidian' else 0,
                            'target': target,
                            
                            # 基础统计特征
                            'tickets_mean': np.mean(hist_tickets),
                            'tickets_std': np.std(hist_tickets),
                            'tickets_max': max(hist_tickets),
                            'tickets_min': min(hist_tickets),
                            'tickets_last': hist_tickets[-1],
                            
                            # 收藏特征
                            'collection_mean': np.mean(hist_collections) if hist_collections else 0,
                            'collection_last': hist_collections[-1] if hist_collections else 0,
                            
                            # 增长特征
                            'tickets_growth': hist_tickets[-1] - hist_tickets[0] if len(hist_tickets) > 1 else 0,
                            'tickets_momentum': (hist_tickets[-1] - hist_tickets[-2]) if len(hist_tickets) > 1 else 0,
                            
                            # 时间特征
                            'day_of_week': rows[i]['crawl_time'].weekday() if hasattr(rows[i]['crawl_time'], 'weekday') else 0,
                            'hour': rows[i]['crawl_time'].hour if hasattr(rows[i]['crawl_time'], 'hour') else 0,
                            'is_weekend': 1 if (rows[i]['crawl_time'].weekday() >= 5 if hasattr(rows[i]['crawl_time'], 'weekday') else False) else 0,
                            
                            # 长短期趋势
                            'tickets_short_avg': np.mean(hist_tickets[-3:]) if len(hist_tickets) >= 3 else np.mean(hist_tickets),
                            'tickets_long_avg': np.mean(hist_tickets),
                        }
                        
                        all_data.append(feature)
                
            conn.close()
            
            df = pd.DataFrame(all_data)
            self._log(f"Extracted {len(df)} training samples from {platform}")
            return df
            
        except Exception as e:
            self._log(f"[ERROR] Failed to fetch {platform} data: {e}")
            return pd.DataFrame()
    
    def prepare_dataset(self):
        """合并两个平台的数据"""
        self._log("Preparing training dataset from database...")
        
        df_qidian = self.fetch_time_series_data('qidian', min_records=5)
        df_zongheng = self.fetch_time_series_data('zongheng', min_records=5)
        
        if df_qidian.empty and df_zongheng.empty:
            raise ValueError("No training data available from database")
        
        df = pd.concat([df_qidian, df_zongheng], ignore_index=True)
        
        if df.empty:
            raise ValueError("Empty dataset after merging")
        
        # 准备特征和标签
        feature_cols = [c for c in df.columns if c not in ['title', 'target']]
        X = df[feature_cols].fillna(0)
        y = df['target'].fillna(0)
        
        self._log(f"Dataset ready: {len(X)} samples, {len(feature_cols)} features")
        self._log(f"Feature columns: {feature_cols}")
        
        return X, y, feature_cols, df
    
    def train(self):
        """训练月票预测模型"""
        self._log("=" * 50)
        self._log("Starting Ticket Prediction Model Training")
        self._log("=" * 50)
        
        try:
            # 准备数据
            X, y, feature_names, df_raw = self.prepare_dataset()
            
            if len(X) < 50:
                return {
                    "status": "error", 
                    "message": f"Insufficient data: only {len(X)} samples, need at least 50"
                }
            
            # 数据集划分
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # 特征缩放
            self._log("Scaling features...")
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # 转换为DMatrix
            dtrain = xgb.DMatrix(X_train_scaled, label=y_train, feature_names=feature_names)
            dtest = xgb.DMatrix(X_test_scaled, label=y_test, feature_names=feature_names)
            
            # 训练参数 - 针对月票预测优化
            params = {
                'objective': 'reg:squarederror',
                'eval_metric': 'rmse',
                'max_depth': 8,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'min_child_weight': 3,
                'gamma': 0.1,
                'n_estimators': 200
            }
            
            self._log(f"Training with params: {params}")
            
            # 训练模型
            evals = [(dtrain, 'train'), (dtest, 'eval')]
            results = {}
            
            model = xgb.train(
                params,
                dtrain,
                num_boost_round=params['n_estimators'],
                evals=evals,
                early_stopping_rounds=20,
                evals_result=results,
                verbose_eval=10
            )
            
            # 评估
            preds = model.predict(dtest)
            rmse = np.sqrt(mean_squared_error(y_test, preds))
            r2 = r2_score(y_test, preds)
            mae = np.mean(np.abs(y_test - preds))
            
            self._log(f"=" * 50)
            self._log(f"Training Complete!")
            self._log(f"RMSE: {rmse:.2f}")
            self._log(f"MAE: {mae:.2f}")
            self._log(f"R²: {r2:.4f}")
            self._log(f"=" * 50)
            
            # 特征重要性
            importance = model.get_score(importance_type='gain')
            sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
            self._log("\nTop 10 Important Features:")
            for fname, score in sorted_imp[:10]:
                self._log(f"  {fname}: {score:.2f}")
            
            # 保存模型
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = os.path.join(self.models_dir, f"ticket_predictor_{timestamp}.pkl")
            scaler_path = os.path.join(self.models_dir, f"ticket_scaler_{timestamp}.pkl")
            features_path = os.path.join(self.models_dir, f"ticket_features_{timestamp}.pkl")
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            joblib.dump(feature_names, features_path)
            
            self._log(f"\nModel saved to: {model_path}")
            
            # 同时保存为默认模型名称供系统使用
            default_model = os.path.join(self.models_dir, "xgboost_model.pkl")
            default_scaler = os.path.join(self.models_dir, "scaler.pkl")
            default_features = os.path.join(self.models_dir, "feature_names.pkl")
            
            joblib.dump(model, default_model)
            joblib.dump(scaler, default_scaler)
            joblib.dump(feature_names, default_features)
            
            self._log(f"Also saved as default: xgboost_model.pkl")
            
            return {
                "status": "success",
                "metrics": {
                    "rmse": float(rmse),
                    "mae": float(mae),
                    "r2": float(r2),
                    "samples": len(X)
                },
                "model_path": model_path,
                "feature_importance": sorted_imp[:10]
            }
            
        except Exception as e:
            self._log(f"[ERROR] Training failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

if __name__ == '__main__':
    trainer = TicketPredictionTrainer()
    result = trainer.train()
    
    print("\n" + "=" * 50)
    print("TRAINING RESULT:")
    print("=" * 50)
    if result['status'] == 'success':
        print(f"✅ Success!")
        print(f"   RMSE: {result['metrics']['rmse']:.2f}")
        print(f"   R²: {result['metrics']['r2']:.4f}")
        print(f"   Samples: {result['metrics']['samples']}")
        print(f"   Model: {result['model_path']}")
    else:
        print(f"❌ Failed: {result['message']}")
    print("=" * 50)
