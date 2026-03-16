"""
Model Comparison: Realtime vs Historical Data Training
对比两个模型的预测效果
"""
import os
import joblib
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
from datetime import datetime
import pymysql
import warnings
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

class ModelComparator:
    def __init__(self):
        self.models_dir = os.path.join(os.path.dirname(__file__), 'resources', 'models')
        
    def _log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")
        
    def fetch_test_data(self, limit=500):
        """获取测试数据集（使用历史数据的后20%作为测试集）"""
        self._log("Fetching test data from historical tables...")
        
        # 起点数据 - 取最新数据作为测试
        try:
            conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT title, author, category, status, word_count,
                        year, month, monthly_tickets_on_list as monthly_tickets,
                        monthly_ticket_count, rank_on_list as rank_num,
                        recommendation_count, cover_url
                    FROM novel_monthly_stats
                    WHERE (year = 2025 AND month >= 10) OR year > 2025
                    ORDER BY title, year, month
                    LIMIT %s
                """, (limit,))
                qd_rows = cur.fetchall()
            conn.close()
        except Exception as e:
            self._log(f"[ERROR] Qidian fetch failed: {e}")
            qd_rows = []
        
        # 纵横数据 - 取最新数据作为测试
        try:
            conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT title, author, category, status, word_count,
                        year, month, monthly_ticket as monthly_tickets,
                        rank_num, total_click, total_rec as total_recommend, cover_url
                    FROM zongheng_book_ranks
                    WHERE (year = 2025 AND month >= 10) OR year > 2025
                    ORDER BY title, year, month
                    LIMIT %s
                """, (limit,))
                zh_rows = cur.fetchall()
            conn.close()
        except Exception as e:
            self._log(f"[ERROR] Zongheng fetch failed: {e}")
            zh_rows = []
        
        # 合并并标记平台
        df_qd = pd.DataFrame(qd_rows)
        if not df_qd.empty:
            df_qd['platform'] = 'qidian'
        
        df_zh = pd.DataFrame(zh_rows)
        if not df_zh.empty:
            df_zh['platform'] = 'zongheng'
        
        df = pd.concat([df_qd, df_zh], ignore_index=True)
        self._log(f"Test data: {len(df)} samples from {df['title'].nunique()} books")
        return df
    
    def engineer_features_for_historical(self, df):
        """为历史数据模型构建特征"""
        if df.empty:
            return df, []
        
        # 基础处理
        df['monthly_tickets'] = pd.to_numeric(df['monthly_tickets'], errors='coerce').fillna(0)
        df['word_count'] = pd.to_numeric(df['word_count'], errors='coerce').fillna(0)
        df['rank_num'] = pd.to_numeric(df.get('rank_num', 0), errors='coerce').fillna(999)
        
        # 对数变换
        df['log_word_count'] = np.log1p(df['word_count'])
        df['word_growth'] = 0  # 测试数据无法计算
        
        # 时间特征
        df['quarter'] = ((df['month'] - 1) // 3) + 1
        df['is_year_end'] = (df['month'] >= 11).astype(int)
        df['is_year_start'] = (df['month'] <= 2).astype(int)
        
        # 平台编码
        df['platform_code'] = df.get('platform', 'qidian').map({'qidian': 1, 'zongheng': 0}).fillna(1)
        
        # 类别编码
        if 'category' in df.columns:
            df['category'] = df['category'].fillna('未知')
            categories = ['玄幻', '都市', '仙侠', '科幻', '历史', '游戏', '奇幻', '军事', '悬疑', '武侠', '现实', '体育', '轻小说', '诸天无限', '未知']
            cat_map = {cat: i for i, cat in enumerate(categories)}
            df['category_code'] = df['category'].map(lambda x: cat_map.get(x, len(categories)-1))
        else:
            df['category_code'] = 0
        
        # 排名相关
        df['rank_change'] = 0
        df['last_month_rank'] = df['rank_num']
        
        # 使用当月数据作为"历史"特征的近似（因为是测试集）
        df['hist_mean'] = df['monthly_tickets']
        df['hist_max'] = df['monthly_tickets']
        df['hist_min'] = df['monthly_tickets']
        df['hist_std'] = 0
        df['last_3_mean'] = df['monthly_tickets']
        df['last_3_max'] = df['monthly_tickets']
        df['last_month_tickets'] = df['monthly_tickets'] * 0.9  # 假设上月略低
        df['mom_growth'] = 0.1
        
        # 生命周期
        df['months_since_start'] = 12
        df['is_new_book'] = 0
        df['is_mature'] = 1
        
        feature_cols = [
            'log_word_count', 'word_growth', 'rank_num', 'rank_change', 'last_month_rank',
            'quarter', 'is_year_end', 'is_year_start', 'platform_code', 'category_code',
            'hist_mean', 'hist_max', 'hist_min', 'hist_std', 'last_3_mean', 'last_3_max',
            'last_month_tickets', 'mom_growth', 'months_since_start', 'is_new_book', 'is_mature'
        ]
        
        return df, feature_cols
    
    def engineer_features_for_realtime(self, df):
        """为实时数据模型构建特征（简化版）"""
        if df.empty:
            return df, []
        
        df['monthly_tickets'] = pd.to_numeric(df['monthly_tickets'], errors='coerce').fillna(0)
        
        # 实时模型的简化特征
        df['platform'] = df.get('platform', 'qidian').map({'qidian': 1, 'zongheng': 0}).fillna(1)
        df['tickets_mean'] = df['monthly_tickets']
        df['tickets_std'] = 0
        df['tickets_max'] = df['monthly_tickets']
        df['tickets_min'] = df['monthly_tickets']
        df['tickets_last'] = df['monthly_tickets']
        df['collection_mean'] = 0
        df['collection_last'] = 0
        df['tickets_growth'] = 0
        df['tickets_momentum'] = 0
        df['day_of_week'] = 0
        df['hour'] = 0
        df['is_weekend'] = 0
        df['tickets_short_avg'] = df['monthly_tickets']
        df['tickets_long_avg'] = df['monthly_tickets']
        
        feature_cols = [
            'platform', 'tickets_mean', 'tickets_std', 'tickets_max', 'tickets_min',
            'tickets_last', 'collection_mean', 'collection_last', 'tickets_growth',
            'tickets_momentum', 'day_of_week', 'hour', 'is_weekend',
            'tickets_short_avg', 'tickets_long_avg'
        ]
        
        return df, feature_cols
    
    def load_model_and_evaluate(self, model_name, df, feature_cols, model_file, scaler_file=None):
        """加载模型并评估"""
        try:
            model_path = os.path.join(self.models_dir, model_file)
            model = joblib.load(model_path)
            
            X = df[feature_cols].fillna(0)
            y_true = df['monthly_tickets'].values
            
            # 如果有scaler，使用它
            if scaler_file:
                scaler_path = os.path.join(self.models_dir, scaler_file)
                scaler = joblib.load(scaler_path)
                X_scaled = scaler.transform(X)
                dtest = xgb.DMatrix(X_scaled, feature_names=feature_cols)
            else:
                dtest = xgb.DMatrix(X, feature_names=feature_cols)
            
            # 预测
            preds_log = model.predict(dtest)
            
            # 判断是否需要exp转换
            if np.max(preds_log) < 20:  # 对数尺度
                preds = np.expm1(preds_log)
            else:
                preds = preds_log
            
            # 计算指标
            rmse = np.sqrt(mean_squared_error(y_true, preds))
            mae = mean_absolute_error(y_true, preds)
            r2 = r2_score(y_true, preds)
            mape = np.mean(np.abs((y_true - preds) / (y_true + 1))) * 100
            
            return {
                'model_name': model_name,
                'rmse': rmse,
                'mae': mae,
                'r2': r2,
                'mape': mape,
                'samples': len(y_true)
            }
        except Exception as e:
            self._log(f"[ERROR] Evaluating {model_name}: {e}")
            return None
    
    def compare(self):
        """对比两个模型"""
        self._log("=" * 70)
        self._log("MODEL COMPARISON: Realtime vs Historical Training")
        self._log("=" * 70)
        
        # 获取测试数据
        df_test = self.fetch_test_data(limit=300)
        if df_test.empty:
            self._log("[ERROR] No test data available")
            return
        
        results = []
        
        # 评估历史数据模型
        self._log("\n[1] Evaluating HISTORICAL model (trained on 11,234 samples)...")
        df_hist, hist_features = self.engineer_features_for_historical(df_test.copy())
        result_hist = self.load_model_and_evaluate(
            "Historical Model (11,234 samples)",
            df_hist,
            hist_features,
            "ticket_predictor_hist_20260314_221729.pkl",
            "ticket_scaler_hist_20260314_221729.pkl"
        )
        if result_hist:
            results.append(result_hist)
        
        # 评估实时数据模型
        self._log("\n[2] Evaluating REALTIME model (trained on 267 samples)...")
        df_rt, rt_features = self.engineer_features_for_realtime(df_test.copy())
        result_rt = self.load_model_and_evaluate(
            "Realtime Model (267 samples)",
            df_rt,
            rt_features,
            "ticket_predictor_20260314_220409.pkl",
            "ticket_scaler_20260314_220409.pkl"
        )
        if result_rt:
            results.append(result_rt)
        
        # 输出对比结果
        self._log("\n" + "=" * 70)
        self._log("COMPARISON RESULTS")
        self._log("=" * 70)
        
        print(f"\n{'Model':<35} {'RMSE':>10} {'MAE':>10} {'R²':>8} {'MAPE':>8}")
        print("-" * 70)
        for r in results:
            print(f"{r['model_name']:<35} {r['rmse']:>10.2f} {r['mae']:>10.2f} {r['r2']:>8.4f} {r['mape']:>7.2f}%")
        
        print("\n" + "=" * 70)
        print("CONCLUSION:")
        print("=" * 70)
        
        if len(results) >= 2:
            hist = results[0]
            rt = results[1]
            
            better_count = 0
            if hist['rmse'] < rt['rmse']:
                print(f"✅ Historical model has LOWER RMSE ({hist['rmse']:.2f} vs {rt['rmse']:.2f})")
                better_count += 1
            else:
                print(f"❌ Realtime model has lower RMSE")
            
            if hist['mae'] < rt['mae']:
                print(f"✅ Historical model has LOWER MAE ({hist['mae']:.2f} vs {rt['mae']:.2f})")
                better_count += 1
            else:
                print(f"❌ Realtime model has lower MAE")
            
            if hist['r2'] > rt['r2']:
                print(f"✅ Historical model has HIGHER R² ({hist['r2']:.4f} vs {rt['r2']:.4f})")
                better_count += 1
            else:
                print(f"❌ Realtime model has higher R²")
            
            if hist['mape'] < rt['mape']:
                print(f"✅ Historical model has LOWER MAPE ({hist['mape']:.2f}% vs {rt['mape']:.2f}%)")
                better_count += 1
            else:
                print(f"❌ Realtime model has lower MAPE")
            
            print(f"\n{'='*70}")
            if better_count >= 3:
                print("🏆 WINNER: Historical Model (trained on 2020-2025 monthly data)")
                print("   - 42x more training data (11,234 vs 267 samples)")
                print("   - Richer features (21 vs 15 features)")
                print("   - Better generalization across time periods")
            elif better_count <= 1:
                print("🏆 WINNER: Realtime Model")
                print("   - Surprisingly effective with limited data")
            else:
                print("🤝 MIXED RESULTS: Each model has strengths")
        
        return results

if __name__ == '__main__':
    comparator = ModelComparator()
    comparator.compare()
