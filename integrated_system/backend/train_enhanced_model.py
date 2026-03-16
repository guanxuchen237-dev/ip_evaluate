"""
Enhanced XGBoost Model Training with Full Feature Set
使用完整特征集训练月票预测模型
数据划分: 2020-2023训练集, 2024测试集, 2025+预测集
"""
import os
import joblib
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler, LabelEncoder
from datetime import datetime, timedelta
import pymysql
import warnings
import re
warnings.filterwarnings('ignore')

# Database configs
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'qidian_data', 'charset': 'utf8mb4'
}
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

class EnhancedTicketModelTrainer:
    def __init__(self):
        self.models_dir = os.path.join(os.path.dirname(__file__), 'resources', 'models')
        os.makedirs(self.models_dir, exist_ok=True)
        self.le_category = LabelEncoder()
        self.le_author = LabelEncoder()
        
    def _log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")
        
    def fetch_qidian_full_data(self):
        """获取起点完整数据，包含所有可用字段"""
        self._log("Fetching Qidian full data...")
        
        try:
            conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                # 获取所有可用字段
                cur.execute("""
                    SELECT 
                        year, month,
                        title, author, category, status,
                        word_count,
                        collection_count,
                        collection_rank,
                        monthly_tickets_on_list as monthly_tickets,
                        monthly_ticket_count,
                        rank_on_list as monthly_ticket_rank,
                        recommendation_count,
                        reward_count as bang_count,
                        is_vip,
                        is_sign as is_signed,
                        synopsis as intro,
                        latest_chapter,
                        updated_at as latest_update_time,
                        week_recommendation_count as weekly_recommend,
                        adaptations as adaptation_info,
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
            self._log(f"[ERROR] Qidian fetch failed: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def fetch_zongheng_full_data(self):
        """获取纵横完整数据，包含所有可用字段"""
        self._log("Fetching Zongheng full data...")
        
        try:
            conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        year, month,
                        title, author, category,
                        word_count,
                        monthly_ticket,
                        rank_num as monthly_ticket_rank,
                        month_donate as contribution_value,
                        total_click,
                        total_rec as total_recommend,
                        week_rec as weekly_recommend,
                        post_count,
                        fan_count,
                        is_signed,
                        status as completion_status,
                        abstract as intro,
                        latest_chapter,
                        updated_at as latest_update_time,
                        update_frequency,
                        chapter_interval,
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
            self._log(f"[ERROR] Zongheng fetch failed: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def calculate_update_frequency(self, df):
        """计算更新频率特征"""
        if 'latest_update_time' not in df.columns or df.empty:
            return df
        
        self._log("Calculating update frequency features...")
        
        # 转换时间
        df['update_time'] = pd.to_datetime(df['latest_update_time'], errors='coerce')
        
        # 按书籍分组计算更新间隔
        def calc_freq(group):
            if len(group) < 2:
                return pd.Series([0] * len(group), index=group.index)
            
            times = group['update_time'].dropna()
            if len(times) < 2:
                return pd.Series([0] * len(group), index=group.index)
            
            # 计算平均更新间隔(天)
            diffs = times.diff().dt.total_seconds() / 86400
            avg_interval = diffs.mean()
            
            # 更新频率 = 1/间隔 (次/天)
            freq = 1.0 / max(avg_interval, 0.5) if avg_interval > 0 else 0
            return pd.Series([freq] * len(group), index=group.index)
        
        df['update_freq_calculated'] = df.groupby('title').apply(calc_freq).reset_index(level=0, drop=True)
        df['update_freq_calculated'] = df['update_freq_calculated'].fillna(0)
        
        return df
    
    def extract_adaptation_features(self, df):
        """从改编情况提取特征"""
        if 'adaptation_info' not in df.columns or df.empty:
            df['has_adaptation'] = 0
            df['adaptation_count'] = 0
            return df
        
        self._log("Extracting adaptation features...")
        
        def parse_adaptation(val):
            if pd.isna(val) or val == '' or val == '无':
                return 0, 0
            # 统计改编类型数量
            adaptations = ['漫画', '动画', '影视', '游戏', '有声', '出版']
            count = sum(1 for a in adaptations if a in str(val))
            return 1 if count > 0 else 0, count
        
        adaptations = df['adaptation_info'].apply(parse_adaptation)
        df['has_adaptation'] = [a[0] for a in adaptations]
        df['adaptation_count'] = [a[1] for a in adaptations]
        
        return df
    
    def engineer_comprehensive_features(self, df, platform='qidian'):
        """构建全面的特征集"""
        if df.empty:
            return df, []
        
        self._log(f"Engineering comprehensive features for {platform}...")
        
        # 数值型特征处理
        numeric_cols = ['word_count', 'monthly_tickets', 'total_click', 
                       'recommendation_count', 'collection_count', 'fan_count',
                       'contribution_value', 'post_count', 'weekly_recommend',
                       'bang_count', 'monthly_ticket_rank', 'collection_rank']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            else:
                df[col] = 0
        
        # 对数变换特征
        df['log_word_count'] = np.log1p(df['word_count'])
        df['log_monthly_tickets'] = np.log1p(df['monthly_tickets'])
        df['log_collection'] = np.log1p(df['collection_count'])
        df['log_click'] = np.log1p(df['total_click'])
        df['log_recommend'] = np.log1p(df['recommendation_count'])
        
        # 时间特征
        df['period'] = df['year'] * 100 + df['month']
        df['quarter'] = ((df['month'] - 1) // 3) + 1
        df['is_year_end'] = (df['month'].isin([11, 12])).astype(int)
        df['is_year_start'] = (df['month'].isin([1, 2])).astype(int)
        df['is_summer'] = (df['month'].isin([7, 8])).astype(int)
        
        # 按书籍分组计算时序特征
        grouped = df.groupby('title')
        
        # 历史统计特征
        df['hist_tickets_mean'] = grouped['monthly_tickets'].transform(lambda x: x.expanding().mean().shift(1)).fillna(0)
        df['hist_tickets_max'] = grouped['monthly_tickets'].transform(lambda x: x.expanding().max().shift(1)).fillna(0)
        df['hist_tickets_min'] = grouped['monthly_tickets'].transform(lambda x: x.expanding().min().shift(1)).fillna(0)
        df['hist_tickets_std'] = grouped['monthly_tickets'].transform(lambda x: x.expanding().std().shift(1)).fillna(0)
        
        # 收藏相关历史
        df['hist_collection_mean'] = grouped['collection_count'].transform(lambda x: x.expanding().mean().shift(1)).fillna(0)
        
        # 短期趋势 (3个月)
        df['tickets_ma3'] = grouped['monthly_tickets'].transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean()).fillna(0)
        df['tickets_ma6'] = grouped['monthly_tickets'].transform(lambda x: x.shift(1).rolling(6, min_periods=1).mean()).fillna(0)
        df['tickets_ma12'] = grouped['monthly_tickets'].transform(lambda x: x.shift(1).rolling(12, min_periods=1).mean()).fillna(0)
        
        # 上月数据
        df['last_month_tickets'] = grouped['monthly_tickets'].shift(1).fillna(0)
        df['last_month_rank'] = grouped['monthly_ticket_rank'].shift(1).fillna(999)
        df['last_month_collection'] = grouped['collection_count'].shift(1).fillna(0)
        
        # 增长率特征
        df['tickets_mom'] = (df['monthly_tickets'] - df['last_month_tickets']) / (df['last_month_tickets'] + 1)
        df['tickets_mom'] = df['tickets_mom'].clip(-5, 5)
        
        # 排名变化
        df['rank_change'] = df['last_month_rank'] - df['monthly_ticket_rank']
        
        # 生命周期特征
        df['months_since_start'] = grouped.cumcount()
        df['is_new_book'] = (df['months_since_start'] <= 3).astype(int)
        df['is_mature'] = (df['months_since_start'] >= 12).astype(int)
        df['is_long_running'] = (df['months_since_start'] >= 24).astype(int)
        
        # 平台特征
        df['is_qidian'] = 1 if platform == 'qidian' else 0
        
        # 类别编码
        if 'category' in df.columns:
            df['category'] = df['category'].fillna('未知')
            categories = ['玄幻', '都市', '仙侠', '科幻', '历史', '游戏', '奇幻', '军事', '悬疑', '武侠', '现实', '体育', '轻小说', '诸天无限', '未知']
            cat_map = {cat: i for i, cat in enumerate(categories)}
            df['category_code'] = df['category'].map(lambda x: cat_map.get(str(x), len(categories)-1))
        else:
            df['category_code'] = 0
        
        # 状态特征
        if 'status' in df.columns:
            df['is_completed'] = df['status'].str.contains('完结', na=False).astype(int)
        else:
            df['is_completed'] = 0
        
        # VIP和签约特征
        if 'is_vip' in df.columns:
            df['is_vip'] = df['is_vip'].apply(lambda x: 1 if str(x).upper() in ['VIP', '1', 'TRUE', 'YES'] else 0)
        else:
            df['is_vip'] = 0
            
        if 'is_signed' in df.columns:
            df['is_signed'] = df['is_signed'].apply(lambda x: 1 if str(x).upper() in ['已签约', '1', 'TRUE', 'YES', 'SIGNED'] else 0)
        else:
            df['is_signed'] = 0
        
        # 比率特征
        df['tickets_per_word'] = df['monthly_tickets'] / (df['word_count'] / 10000 + 1)
        df['collection_per_word'] = df['collection_count'] / (df['word_count'] / 10000 + 1)
        df['recommend_per_collection'] = df['recommendation_count'] / (df['collection_count'] + 1)
        
        # 竞争力指标 (排名倒数)
        df['rank_inverse'] = 1.0 / (df['monthly_ticket_rank'] + 1)
        
        # 纵横特有特征
        if platform == 'zongheng':
            df['has_contribution'] = (df['contribution_value'] > 0).astype(int)
            df['has_fans'] = (df['fan_count'] > 0).astype(int)
            df['has_posts'] = (df['post_count'] > 0).astype(int)
            
            # 社区活跃度
            df['community_score'] = np.log1p(df['fan_count']) + np.log1p(df['post_count'])
        else:
            df['has_contribution'] = 0
            df['has_fans'] = 0
            df['has_posts'] = 0
            df['community_score'] = 0
        
        # 更新频率特征
        df = self.calculate_update_frequency(df)
        
        # 改编特征
        df = self.extract_adaptation_features(df)
        
        # 定义所有特征列
        feature_cols = [
            # 对数基础特征
            'log_word_count', 'log_collection', 'log_click', 'log_recommend',
            
            # 时间特征
            'quarter', 'is_year_end', 'is_year_start', 'is_summer',
            'months_since_start', 'is_new_book', 'is_mature', 'is_long_running',
            
            # 历史统计
            'hist_tickets_mean', 'hist_tickets_max', 'hist_tickets_min', 'hist_tickets_std',
            'hist_collection_mean',
            
            # 移动平均
            'tickets_ma3', 'tickets_ma6', 'tickets_ma12',
            
            # 近期数据
            'last_month_tickets', 'last_month_rank', 'last_month_collection',
            'tickets_mom', 'rank_change', 'rank_inverse',
            
            # 类别与状态
            'category_code', 'is_completed', 'is_vip', 'is_signed', 'is_qidian',
            
            # 比率特征
            'tickets_per_word', 'collection_per_word', 'recommend_per_collection',
            
            # 平台特有
            'has_contribution', 'has_fans', 'has_posts', 'community_score',
            
            # 更新与改编
            'update_freq_calculated', 'has_adaptation', 'adaptation_count',
        ]
        
        self._log(f"Total features engineered: {len(feature_cols)}")
        return df, feature_cols
    
    def prepare_datasets(self):
        """按时间划分数据集"""
        self._log("=" * 70)
        self._log("Preparing Datasets with Time-based Split")
        self._log("Train: 2020-2023 | Test: 2024 | Predict: 2025+")
        self._log("=" * 70)
        
        # 获取数据
        df_qd = self.fetch_qidian_full_data()
        df_zh = self.fetch_zongheng_full_data()
        
        # 标记平台
        if not df_qd.empty:
            df_qd['platform'] = 'qidian'
        if not df_zh.empty:
            df_zh['platform'] = 'zongheng'
        
        # 合并
        df = pd.concat([df_qd, df_zh], ignore_index=True)
        
        if df.empty:
            raise ValueError("No data fetched from database")
        
        self._log(f"Total records: {len(df)}")
        self._log(f"Unique books: {df['title'].nunique()}")
        self._log(f"Date range: {df['year'].min()}-{df['month'].min()} to {df['year'].max()}-{df['month'].max()}")
        
        # 特征工程
        df_qd_feat, qd_features = self.engineer_comprehensive_features(df_qd.copy(), 'qidian')
        df_zh_feat, zh_features = self.engineer_comprehensive_features(df_zh.copy(), 'zongheng')
        
        # 合并（使用共同的特征）
        df_all = pd.concat([df_qd_feat, df_zh_feat], ignore_index=True)
        
        # 使用起点特征作为基准（两者几乎相同）
        feature_cols = qd_features
        
        # 过滤需要有上月数据的样本（首月无法预测）
        df_all = df_all[df_all['last_month_tickets'] > 0].copy()
        
        self._log(f"Valid samples after filtering: {len(df_all)}")
        
        # 按时间划分
        train_mask = (df_all['year'] >= 2020) & (df_all['year'] <= 2023)
        test_mask = (df_all['year'] == 2024)
        predict_mask = (df_all['year'] >= 2025)
        
        df_train = df_all[train_mask].copy()
        df_test = df_all[test_mask].copy()
        df_predict = df_all[predict_mask].copy()
        
        self._log(f"\nDataset split:")
        self._log(f"  Train (2020-2023): {len(df_train)} samples")
        self._log(f"  Test (2024): {len(df_test)} samples")
        self._log(f"  Predict (2025+): {len(df_predict)} samples")
        
        return df_train, df_test, df_predict, feature_cols
    
    def train(self):
        """训练增强版XGBoost模型"""
        self._log("\n" + "=" * 70)
        self._log("Starting Enhanced XGBoost Model Training")
        self._log("=" * 70)
        
        try:
            # 准备数据集
            df_train, df_test, df_predict, feature_cols = self.prepare_datasets()
            
            if len(df_train) < 100:
                return {"status": "error", "message": f"Insufficient training data: {len(df_train)}"}
            
            # 准备特征和目标
            X_train = df_train[feature_cols].fillna(0)
            y_train = np.log1p(df_train['monthly_tickets'].fillna(0))
            
            X_test = df_test[feature_cols].fillna(0) if len(df_test) > 0 else None
            y_test_orig = df_test['monthly_tickets'].fillna(0) if len(df_test) > 0 else None
            
            self._log(f"\nFeature matrix shape: {X_train.shape}")
            self._log(f"Features: {feature_cols}")
            
            # 特征缩放
            self._log("Scaling features...")
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            
            # 创建DMatrix
            dtrain = xgb.DMatrix(X_train_scaled, label=y_train, feature_names=feature_cols)
            
            # 如果有测试集
            if X_test is not None and len(X_test) > 0:
                X_test_scaled = scaler.transform(X_test)
                dtest = xgb.DMatrix(X_test_scaled, label=np.log1p(y_test_orig), feature_names=feature_cols)
                evals = [(dtrain, 'train'), (dtest, 'eval')]
                early_stopping = 50
            else:
                evals = [(dtrain, 'train')]
                early_stopping = None
            
            # 训练参数 - 增强版
            params = {
                'objective': 'reg:squarederror',
                'eval_metric': 'rmse',
                'max_depth': 12,
                'learning_rate': 0.02,
                'subsample': 0.9,
                'colsample_bytree': 0.9,
                'colsample_bylevel': 0.85,
                'min_child_weight': 3,
                'gamma': 0.05,
                'reg_alpha': 0.05,
                'reg_lambda': 0.5,
            }
            
            self._log(f"\nTraining with params:")
            for k, v in params.items():
                self._log(f"  {k}: {v}")
            
            # 训练模型
            results = {}
            model = xgb.train(
                params,
                dtrain,
                num_boost_round=1000,
                evals=evals,
                early_stopping_rounds=early_stopping,
                evals_result=results,
                verbose_eval=50
            )
            
            # 评估
            if X_test is not None and len(X_test) > 0:
                preds_log = model.predict(dtest)
                preds = np.expm1(preds_log)
                y_test = y_test_orig.values
                
                rmse = np.sqrt(mean_squared_error(y_test, preds))
                mae = mean_absolute_error(y_test, preds)
                r2 = r2_score(y_test, preds)
                mape = np.mean(np.abs((y_test - preds) / (y_test + 1))) * 100
                
                self._log("\n" + "=" * 70)
                self._log("Test Set Evaluation (2024 Data)")
                self._log("=" * 70)
                self._log(f"RMSE: {rmse:.2f}")
                self._log(f"MAE: {mae:.2f}")
                self._log(f"R²: {r2:.4f}")
                self._log(f"MAPE: {mape:.2f}%")
            else:
                rmse, mae, r2, mape = None, None, None, None
                self._log("[WARNING] No test data available for evaluation")
            
            # 特征重要性
            importance = model.get_score(importance_type='gain')
            sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
            
            self._log("\nTop 20 Feature Importance:")
            for i, (fname, score) in enumerate(sorted_imp[:20], 1):
                self._log(f"  {i:2d}. {fname}: {score:.2f}")
            
            # 保存模型
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            model_path = os.path.join(self.models_dir, f"ticket_enhanced_{timestamp}.pkl")
            scaler_path = os.path.join(self.models_dir, f"scaler_enhanced_{timestamp}.pkl")
            features_path = os.path.join(self.models_dir, f"features_enhanced_{timestamp}.pkl")
            
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)
            joblib.dump(feature_cols, features_path)
            
            # 更新默认模型
            joblib.dump(model, os.path.join(self.models_dir, "xgboost_model.pkl"))
            joblib.dump(scaler, os.path.join(self.models_dir, "scaler.pkl"))
            joblib.dump(feature_cols, os.path.join(self.models_dir, "feature_names.pkl"))
            
            self._log(f"\nModel saved:")
            self._log(f"  - {model_path}")
            self._log(f"  - xgboost_model.pkl (default)")
            
            return {
                "status": "success",
                "metrics": {
                    "rmse": float(rmse) if rmse else None,
                    "mae": float(mae) if mae else None,
                    "r2": float(r2) if r2 else None,
                    "mape": float(mape) if mape else None,
                    "train_samples": len(df_train),
                    "test_samples": len(df_test) if df_test is not None else 0,
                    "features": len(feature_cols)
                },
                "model_path": model_path,
                "feature_importance": sorted_imp[:20]
            }
            
        except Exception as e:
            self._log(f"[ERROR] Training failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    def validate_with_realtime(self):
        """用实时监测数据验证模型准确性"""
        self._log("\n" + "=" * 70)
        self._log("Validating with Realtime Tracking Data")
        self._log("=" * 70)
        
        # 这里需要实现从实时表获取数据并验证的逻辑
        # 简化版：返回说明
        self._log("[INFO] Realtime validation to be implemented")
        self._log("  - Fetch latest data from novel_realtime_tracking")
        self._log("  - Compare predictions with actual values")
        self._log("  - Calculate drift metrics")

if __name__ == '__main__':
    trainer = EnhancedTicketModelTrainer()
    result = trainer.train()
    
    # 验证
    trainer.validate_with_realtime()
    
    print("\n" + "=" * 70)
    print("FINAL RESULT")
    print("=" * 70)
    if result['status'] == 'success':
        print(f"✅ Training Successful!")
        print(f"   Train samples: {result['metrics']['train_samples']}")
        print(f"   Test samples: {result['metrics']['test_samples']}")
        print(f"   Features: {result['metrics']['features']}")
        if result['metrics']['r2']:
            print(f"   Test RMSE: {result['metrics']['rmse']:.2f}")
            print(f"   Test MAE: {result['metrics']['mae']:.2f}")
            print(f"   Test R²: {result['metrics']['r2']:.4f}")
            print(f"   Test MAPE: {result['metrics']['mape']:.2f}%")
        print(f"   Model: {result['model_path']}")
    else:
        print(f"❌ Failed: {result['message']}")
    print("=" * 70)
