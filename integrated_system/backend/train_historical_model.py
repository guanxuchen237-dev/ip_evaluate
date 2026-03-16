"""
Train XGBoost Model from Historical Monthly Ticket Data (2020-2025)
使用历史月票数据训练高性能预测模型
- novel_monthly_stats: 起点数据
- zongheng_book_ranks: 纵横数据
"""
import os
import sys
import joblib
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler, LabelEncoder
from datetime import datetime
import pymysql
import warnings
warnings.filterwarnings('ignore')

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

class HistoricalTicketModelTrainer:
    def __init__(self):
        self.models_dir = os.path.join(os.path.dirname(__file__), 'resources', 'models')
        os.makedirs(self.models_dir, exist_ok=True)
        self.le_category = LabelEncoder()
        
    def _log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")
        
    def fetch_qidian_data(self):
        """从 novel_monthly_stats 获取起点历史数据"""
        self._log("Fetching Qidian historical data from novel_monthly_stats...")
        
        try:
            conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                # 获取所有历史数据 (2020-2025)
                cur.execute("""
                    SELECT 
                        title, author, category, status, word_count,
                        year, month, 
                        monthly_tickets_on_list as monthly_tickets,
                        monthly_ticket_count,
                        rank_on_list as rank_num,
                        recommendation_count,
                        cover_url
                    FROM novel_monthly_stats
                    WHERE year >= 2020 AND year <= 2025
                    ORDER BY title, year, month
                """)
                rows = cur.fetchall()
                self._log(f"Fetched {len(rows)} records from Qidian")
            conn.close()
            return pd.DataFrame(rows)
        except Exception as e:
            self._log(f"[ERROR] Failed to fetch Qidian data: {e}")
            return pd.DataFrame()
    
    def fetch_zongheng_data(self):
        """从 zongheng_book_ranks 获取纵横历史数据"""
        self._log("Fetching Zongheng historical data from zongheng_book_ranks...")
        
        try:
            conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        title, author, category, status, word_count,
                        year, month,
                        monthly_ticket as monthly_tickets,
                        rank_num,
                        total_click,
                        total_rec as total_recommend,
                        cover_url
                    FROM zongheng_book_ranks
                    WHERE year >= 2020 AND year <= 2025
                    ORDER BY title, year, month
                """)
                rows = cur.fetchall()
                self._log(f"Fetched {len(rows)} records from Zongheng")
            conn.close()
            return pd.DataFrame(rows)
        except Exception as e:
            self._log(f"[ERROR] Failed to fetch Zongheng data: {e}")
            return pd.DataFrame()
    
    def engineer_features(self, df):
        """构建丰富的时序特征"""
        if df.empty:
            return df
            
        self._log("Engineering features...")
        
        # 基础数值特征处理
        df['monthly_tickets'] = pd.to_numeric(df['monthly_tickets'], errors='coerce').fillna(0)
        df['word_count'] = pd.to_numeric(df['word_count'], errors='coerce').fillna(0)
        df['rank_num'] = pd.to_numeric(df.get('rank_num', 0), errors='coerce').fillna(999)
        
        # 对数变换（处理长尾分布）
        df['log_tickets'] = np.log1p(df['monthly_tickets'])
        df['log_word_count'] = np.log1p(df['word_count'])
        
        # 时间特征
        df['period'] = df['year'] * 100 + df['month']
        df['quarter'] = ((df['month'] - 1) // 3) + 1
        df['is_year_end'] = (df['month'] >= 11).astype(int)
        df['is_year_start'] = (df['month'] <= 2).astype(int)
        
        # 按书籍分组计算时序特征
        grouped = df.groupby('title')
        
        # 历史统计特征
        df['hist_mean'] = grouped['monthly_tickets'].transform(lambda x: x.expanding().mean().shift(1)).fillna(0)
        df['hist_max'] = grouped['monthly_tickets'].transform(lambda x: x.expanding().max().shift(1)).fillna(0)
        df['hist_min'] = grouped['monthly_tickets'].transform(lambda x: x.expanding().min().shift(1)).fillna(0)
        df['hist_std'] = grouped['monthly_tickets'].transform(lambda x: x.expanding().std().shift(1)).fillna(0)
        
        # 近期趋势（最近3个月）
        df['last_3_mean'] = grouped['monthly_tickets'].transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean()).fillna(0)
        df['last_3_max'] = grouped['monthly_tickets'].transform(lambda x: x.shift(1).rolling(3, min_periods=1).max()).fillna(0)
        
        # 上月数据
        df['last_month_tickets'] = grouped['monthly_tickets'].shift(1).fillna(0)
        df['last_month_rank'] = grouped['rank_num'].shift(1).fillna(999)
        
        # 环比增长率
        df['mom_growth'] = (df['monthly_tickets'] - df['last_month_tickets']) / (df['last_month_tickets'] + 1)
        df['mom_growth'] = df['mom_growth'].clip(-10, 10)  # 限制异常值
        
        # 字数增长（如果数据可用）
        df['last_word_count'] = grouped['word_count'].shift(1).fillna(df['word_count'])
        df['word_growth'] = df['word_count'] - df['last_word_count']
        
        # 排名变化
        df['rank_change'] = df['last_month_rank'] - df['rank_num']
        
        # 平台编码
        df['platform_code'] = df.get('platform', 'qidian').map({'qidian': 1, 'zongheng': 0}).fillna(1)
        
        # 类别编码
        if 'category' in df.columns:
            df['category'] = df['category'].fillna('未知')
            # 使用统一编码
            categories = df['category'].unique()
            cat_map = {cat: i for i, cat in enumerate(categories)}
            df['category_code'] = df['category'].map(cat_map)
        else:
            df['category_code'] = 0
        
        # 书籍生命周期特征
        df['months_since_start'] = grouped.cumcount()
        df['is_new_book'] = (df['months_since_start'] <= 3).astype(int)
        df['is_mature'] = (df['months_since_start'] >= 12).astype(int)
        
        self._log(f"Feature engineering complete. Shape: {df.shape}")
        return df
    
    def prepare_dataset(self):
        """准备训练数据集"""
        self._log("=" * 60)
        self._log("Preparing Training Dataset from Historical Data")
        self._log("=" * 60)
        
        # 获取两个平台的数据
        df_qd = self.fetch_qidian_data()
        df_zh = self.fetch_zongheng_data()
        
        # 添加平台标识
        if not df_qd.empty:
            df_qd['platform'] = 'qidian'
        if not df_zh.empty:
            df_zh['platform'] = 'zongheng'
        
        # 合并数据
        df = pd.concat([df_qd, df_zh], ignore_index=True)
        
        if df.empty:
            raise ValueError("No data fetched from database")
        
        self._log(f"Total raw records: {len(df)}")
        self._log(f"Unique books: {df['title'].nunique()}")
        self._log(f"Date range: {df['year'].min()}-{df['month'].min()} to {df['year'].max()}-{df['month'].max()}")
        
        # 特征工程
        df = self.engineer_features(df)
        
        # 定义特征列
        feature_cols = [
            # 基础特征
            'log_word_count', 'word_growth',
            'rank_num', 'rank_change', 'last_month_rank',
            'quarter', 'is_year_end', 'is_year_start',
            'platform_code', 'category_code',
            
            # 历史统计
            'hist_mean', 'hist_max', 'hist_min', 'hist_std',
            'last_3_mean', 'last_3_max',
            
            # 近期数据
            'last_month_tickets', 
            
            # 趋势特征
            'mom_growth',
            
            # 生命周期
            'months_since_start', 'is_new_book', 'is_mature',
        ]
        
        # 过滤有效数据（需要有上个月数据作为特征）
        df_valid = df[df['last_month_tickets'] > 0].copy()
        
        if len(df_valid) < 100:
            self._log(f"[WARNING] Only {len(df_valid)} valid samples. Using all data.")
            df_valid = df.copy()
        
        self._log(f"Valid samples for training: {len(df_valid)}")
        
        # 准备 X 和 y
        X = df_valid[feature_cols].fillna(0)
        y = df_valid['monthly_tickets'].fillna(0)
        
        # 对目标进行对数变换（减小大数值的影响）
        y_log = np.log1p(y)
        
        self._log(f"Features: {feature_cols}")
        self._log(f"Target range: {y.min():.0f} ~ {y.max():.0f}")
        
        return X, y, y_log, feature_cols, df_valid
    
    def train(self):
        """训练 XGBoost 模型"""
        self._log("\n" + "=" * 60)
        self._log("Starting XGBoost Model Training")
        self._log("=" * 60)
        
        try:
            # 准备数据
            X, y, y_log, feature_names, df_raw = self.prepare_dataset()
            
            if len(X) < 100:
                return {
                    "status": "error", 
                    "message": f"Insufficient data: only {len(X)} samples"
                }
            
            # 数据集划分
            X_train, X_test, y_train, y_test = train_test_split(
                X, y_log, test_size=0.2, random_state=42
            )
            
            self._log(f"Training set: {len(X_train)}, Test set: {len(X_test)}")
            
            # 特征缩放
            self._log("Scaling features...")
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # 转换为 DMatrix
            dtrain = xgb.DMatrix(X_train_scaled, label=y_train, feature_names=feature_names)
            dtest = xgb.DMatrix(X_test_scaled, label=y_test, feature_names=feature_names)
            
            # 训练参数 - 针对历史数据优化
            params = {
                'objective': 'reg:squarederror',
                'eval_metric': 'rmse',
                'max_depth': 10,
                'learning_rate': 0.03,
                'subsample': 0.85,
                'colsample_bytree': 0.85,
                'colsample_bylevel': 0.8,
                'min_child_weight': 5,
                'gamma': 0.1,
                'reg_alpha': 0.1,
                'reg_lambda': 1.0,
            }
            
            self._log(f"Training params: max_depth={params['max_depth']}, lr={params['learning_rate']}")
            
            # 训练模型
            evals = [(dtrain, 'train'), (dtest, 'eval')]
            results = {}
            
            model = xgb.train(
                params,
                dtrain,
                num_boost_round=500,
                evals=evals,
                early_stopping_rounds=30,
                evals_result=results,
                verbose_eval=25
            )
            
            # 评估 - 转换回原始尺度
            preds_log = model.predict(dtest)
            preds = np.expm1(preds_log)  # 从对数转换回来
            y_test_orig = np.expm1(y_test)
            
            rmse = np.sqrt(mean_squared_error(y_test_orig, preds))
            mae = mean_absolute_error(y_test_orig, preds)
            r2 = r2_score(y_test_orig, preds)
            mape = np.mean(np.abs((y_test_orig - preds) / (y_test_orig + 1))) * 100
            
            self._log("\n" + "=" * 60)
            self._log("Training Complete!")
            self._log("=" * 60)
            self._log(f"RMSE: {rmse:.2f}")
            self._log(f"MAE: {mae:.2f}")
            self._log(f"R²: {r2:.4f}")
            self._log(f"MAPE: {mape:.2f}%")
            
            # 特征重要性
            importance = model.get_score(importance_type='gain')
            sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
            
            self._log("\nTop 15 Feature Importance:")
            for i, (fname, score) in enumerate(sorted_imp[:15], 1):
                self._log(f"  {i:2d}. {fname}: {score:.2f}")
            
            # 保存模型
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 版本化保存
            model_path = os.path.join(self.models_dir, f"ticket_predictor_hist_{timestamp}.pkl")
            scaler_path = os.path.join(self.models_dir, f"ticket_scaler_hist_{timestamp}.pkl")
            features_path = os.path.join(self.models_dir, f"ticket_features_hist_{timestamp}.pkl")
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            joblib.dump(feature_names, features_path)
            
            # 默认名称（供系统使用）
            joblib.dump(model, os.path.join(self.models_dir, "xgboost_model.pkl"))
            joblib.dump(scaler, os.path.join(self.models_dir, "scaler.pkl"))
            joblib.dump(feature_names, os.path.join(self.models_dir, "feature_names.pkl"))
            
            self._log(f"\nModel saved:")
            self._log(f"  - {model_path}")
            self._log(f"  - xgboost_model.pkl (default)")
            
            return {
                "status": "success",
                "metrics": {
                    "rmse": float(rmse),
                    "mae": float(mae),
                    "r2": float(r2),
                    "mape": float(mape),
                    "samples": len(X),
                    "features": len(feature_names)
                },
                "model_path": model_path,
                "feature_importance": sorted_imp[:15]
            }
            
        except Exception as e:
            self._log(f"[ERROR] Training failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

if __name__ == '__main__':
    trainer = HistoricalTicketModelTrainer()
    result = trainer.train()
    
    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    if result['status'] == 'success':
        print(f"✅ Training Successful!")
        print(f"   Samples: {result['metrics']['samples']}")
        print(f"   Features: {result['metrics']['features']}")
        print(f"   RMSE: {result['metrics']['rmse']:.2f}")
        print(f"   MAE: {result['metrics']['mae']:.2f}")
        print(f"   R²: {result['metrics']['r2']:.4f}")
        print(f"   MAPE: {result['metrics']['mape']:.2f}%")
        print(f"   Model: {result['model_path']}")
    else:
        print(f"❌ Failed: {result['message']}")
    print("=" * 60)
