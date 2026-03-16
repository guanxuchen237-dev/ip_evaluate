"""
Model J Oracle v2 - 优化月票映射，提升排名准确性
改进：使用对数映射替代分段线性，更好保留排名顺序
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
import os
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.utils import resample
import xgboost as xgb
from datetime import datetime

warnings.filterwarnings('ignore')

# 数据库配置
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'qidian_data', 'charset': 'utf8mb4'
}
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

print("="*70)
print("Model J Oracle v2 - 优化排名准确性")
print("="*70)

# ================================================================
#  改进的月票锚定映射（对数映射，更好保留排名）
# ================================================================

class ImprovedOracleScoreIntegrator:
    """改进版预言机评分整合器"""
    
    def __init__(self):
        self.platform_scale = {'Zongheng': 8.0, 'Qidian': 1.0}
        
    def _ticket_to_score(self, tickets, platform='Qidian'):
        """改进版月票锚定 - 对数映射更好保留排名"""
        if tickets <= 0:
            return 55.0
        
        # 平台缩放
        adjusted = tickets * self.platform_scale.get(platform, 1.0)
        
        # 使用对数映射，更好保留排名顺序
        # 基础分55 + 对数增长，上限95
        log_score = 55.0 + 15.0 * np.log1p(adjusted / 1000) / np.log1p(50)
        
        # 确保单调性：月票越多，分数越高
        return min(95.0, log_score)
    
    def compute_oracle_features(self, df):
        """计算预言机特征"""
        print("\n【改进版预言机特征计算】")
        
        # 1. 改进版月票锚定分
        df['oracle_ticket_score'] = df.apply(
            lambda row: self._ticket_to_score(
                row['monthly_tickets'], 
                row['platform']
            ), axis=1
        )
        
        # 2. 互动量修正（对数压缩，避免极端值影响）
        df['oracle_inter_bonus'] = np.minimum(
            1.0, 
            np.log1p(df['total_recommend'] / 50000) * 0.3
        )
        
        # 3. 字数修正
        df['oracle_wc_bonus'] = np.minimum(
            0.5, 
            np.log1p(df['word_count'] / 300000) * 0.25
        )
        
        # 4. 题材微调
        hot_genres = ['玄幻', '奇幻', '仙侠', '都市', '言情']
        df['oracle_cat_bonus'] = df['category'].map(
            lambda x: 0.5 if any(k in str(x) for k in hot_genres) else 0.0
        )
        
        # 5. 人气加成（使用点击数）
        df['oracle_pop_bonus'] = np.minimum(
            2.0,
            np.log1p(df['collection_count'] / 100000) * 0.4
        )
        
        # 6. 改进版预言机综合评分
        df['oracle_composite'] = (
            df['oracle_ticket_score'] * 0.7 +  # 月票占主导
            df['oracle_inter_bonus'] * 2 +
            df['oracle_wc_bonus'] * 2 +
            df['oracle_cat_bonus'] * 2 +
            df['oracle_pop_bonus']
        )
        
        # 完结衰减
        if 'status' in df.columns:
            df['oracle_composite'] = np.where(
                df['status'].str.contains('完', na=False),
                df['oracle_composite'] * 0.92,
                df['oracle_composite']
            )
        
        # 限制范围
        df['oracle_composite'] = df['oracle_composite'].clip(45.0, 99.5)
        
        print(f"  月票锚定分范围: {df['oracle_ticket_score'].min():.1f} - {df['oracle_ticket_score'].max():.1f}")
        print(f"  预言机评分均值: {df['oracle_composite'].mean():.2f}")
        print(f"  预言机评分范围: {df['oracle_composite'].min():.1f} - {df['oracle_composite'].max():.1f}")
        
        return df

# ================================================================
#  IP等级制评分系统
# ================================================================

class IPGradingSystem:
    """IP等级制评分系统"""
    
    GRADES = {
        'S': {'min': 90, 'max': 100, 'desc': '顶级IP'},
        'A': {'min': 80, 'max': 89, 'desc': '优质IP'},
        'B': {'min': 70, 'max': 79, 'desc': '良好IP'},
        'C': {'min': 60, 'max': 69, 'desc': '普通IP'},
        'D': {'min': 45, 'max': 59, 'desc': '低价值IP'},
    }
    
    @staticmethod
    def score_to_grade(score):
        if score >= 90:
            return 'S'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        else:
            return 'D'

# ================================================================
#  数据获取
# ================================================================

def fetch_data():
    """获取数据"""
    print("\n1. 获取数据...")
    
    dfs = []
    
    # 起点数据
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG)
        df_qd = pd.read_sql("""
            SELECT title, author, category, status, word_count,
                   collection_count, recommendation_count as total_recommend,
                   monthly_ticket_count as monthly_tickets,
                   year, month, synopsis as abstract
            FROM novel_monthly_stats
            WHERE year >= 2023
        """, conn)
        df_qd['platform'] = 'Qidian'
        conn.close()
        print(f"   起点: {len(df_qd)} 条")
        dfs.append(df_qd)
    except Exception as e:
        print(f"   起点错误: {e}")
    
    # 纵横数据
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG)
        df_zh = pd.read_sql("""
            SELECT title, author, category, status, word_count,
                   total_click as collection_count, total_rec as total_recommend,
                   monthly_ticket as monthly_tickets,
                   fan_count, year, month, abstract
            FROM zongheng_book_ranks
            WHERE year >= 2023
        """, conn)
        df_zh['platform'] = 'Zongheng'
        conn.close()
        print(f"   纵横: {len(df_zh)} 条")
        dfs.append(df_zh)
    except Exception as e:
        print(f"   纵横错误: {e}")
    
    if not dfs:
        return pd.DataFrame()
    
    df = pd.concat(dfs, ignore_index=True)
    
    # 清理数据
    df['monthly_tickets'] = pd.to_numeric(df['monthly_tickets'], errors='coerce').fillna(0)
    df['word_count'] = pd.to_numeric(df['word_count'], errors='coerce').fillna(0)
    df['collection_count'] = pd.to_numeric(df['collection_count'], errors='coerce').fillna(0)
    df['total_recommend'] = pd.to_numeric(df['total_recommend'], errors='coerce').fillna(0)
    
    print(f"   总计: {len(df)} 条")
    
    return df

# ================================================================
#  数据平衡
# ================================================================

def balance_data(df):
    """数据平衡处理"""
    print("\n【数据平衡处理】")
    
    # 添加等级列
    df['ip_grade'] = df['ip_score'].apply(IPGradingSystem.score_to_grade)
    
    # 统计原始分布
    grade_dist = df['ip_grade'].value_counts()
    print(f"  原始分布:")
    for grade in ['S', 'A', 'B', 'C', 'D']:
        count = grade_dist.get(grade, 0)
        print(f"    {grade}级: {count} ({count/len(df)*100:.1f}%)")
    
    # 分离各等级
    df_s = df[df['ip_grade'] == 'S']
    df_a = df[df['ip_grade'] == 'A']
    df_b = df[df['ip_grade'] == 'B']
    df_c = df[df['ip_grade'] == 'C']
    df_d = df[df['ip_grade'] == 'D']
    
    # 混合策略
    target_per_class = max(500, len(df_s), len(df_a))
    
    df_s_up = resample(df_s, n_samples=min(target_per_class, len(df_s)*3), replace=True, random_state=42) if len(df_s) > 0 else df_s
    df_a_up = resample(df_a, n_samples=min(target_per_class, len(df_a)*2), replace=True, random_state=42) if len(df_a) > 0 else df_a
    df_b_up = resample(df_b, n_samples=min(target_per_class, len(df_b)), replace=True, random_state=42) if len(df_b) > 0 else df_b
    df_c_up = resample(df_c, n_samples=min(target_per_class, len(df_c)), replace=True, random_state=42) if len(df_c) > 0 else df_c
    df_d_down = resample(df_d, n_samples=min(len(df_d), 1500), replace=False, random_state=42)
    
    df_balanced = pd.concat([df_s_up, df_a_up, df_b_up, df_c_up, df_d_down], ignore_index=True)
    df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # 统计新分布
    grade_dist_new = df_balanced['ip_grade'].value_counts()
    print(f"\n  平衡后分布:")
    for grade in ['S', 'A', 'B', 'C', 'D']:
        count = grade_dist_new.get(grade, 0)
        print(f"    {grade}级: {count} ({count/len(df_balanced)*100:.1f}%)")
    
    return df_balanced

# ================================================================
#  特征工程
# ================================================================

def extract_features(df):
    """特征工程"""
    print("\n【特征工程】")
    
    # 预言机特征
    integrator = ImprovedOracleScoreIntegrator()
    df = integrator.compute_oracle_features(df)
    
    # 6大维度特征
    df['update_freq'] = df.groupby(['title', 'author'])['word_count'].diff().fillna(0)
    df['months_active'] = df.groupby(['title', 'author']).cumcount() + 1
    
    if 'fan_count' in df.columns:
        df['retention'] = df['fan_count'] / (df['collection_count'] + 1) * 100
    else:
        df['retention'] = df['collection_count'] / (df['total_recommend'] + 1)
    df['retention'] = np.clip(df['retention'], 0, 100)
    
    # 题材热度
    HOT_GENRES = {
        '玄幻': 95, '奇幻': 92, '都市': 90, '仙侠': 88, '游戏': 85,
        '武侠': 85, '历史': 82, '科幻': 80, '悬疑': 78, '轻小说': 75,
        '现代言情': 85, '言情': 82
    }
    df['genre_hotness'] = df['category'].map(lambda x: HOT_GENRES.get(str(x).strip(), 70)).fillna(70)
    
    # 改编潜力
    df['adaptation_potential'] = (
        np.clip(df['word_count'] / 500000, 0, 1) * 50 +
        df['genre_hotness'] * 0.3
    )
    
    # 商业爆发力
    df['base_power'] = (
        np.log1p(df['monthly_tickets']) * 20 +
        np.log1p(df['collection_count']) * 15 +
        np.log1p(df['total_recommend']) * 10
    )
    
    # 清理无穷值
    df = df.replace([np.inf, -np.inf], 0)
    
    print(f"  总特征数: {len(df.columns)}")
    
    return df

# ================================================================
#  改进版双引擎
# ================================================================

class ImprovedDualEngine:
    """改进版双引擎"""
    
    def __init__(self):
        self.xgb_engine = None
        self.kmeans_engine = None
        self.scaler_xgb = None
        self.scaler_kmeans = None
        self.feature_cols = None
        self.cluster_scores = None
        
    def fit(self, X, y, months, grades):
        """训练双引擎"""
        print("\n【改进版双引擎训练】")
        
        # 分割数据
        mature_mask = months >= 6
        nascent_mask = months < 6
        
        X_mature = X[mature_mask]
        y_mature = y[mature_mask]
        
        X_nascent = X[nascent_mask]
        y_nascent = y[nascent_mask]
        grades_nascent = grades[nascent_mask]
        
        print(f"  成熟期样本: {len(X_mature)} (XGBoost)")
        print(f"  孵化期样本: {len(X_nascent)} (K-Means)")
        
        # Engine A: XGBoost
        if len(X_mature) > 0:
            print("\n  训练Engine A (XGBoost)...")
            self.scaler_xgb = StandardScaler()
            X_mature_scaled = self.scaler_xgb.fit_transform(X_mature)
            
            self.xgb_engine = xgb.XGBRegressor(
                objective='reg:squarederror',
                n_estimators=300,
                max_depth=7,
                learning_rate=0.05,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=42,
                n_jobs=-1
            )
            self.xgb_engine.fit(X_mature_scaled, y_mature)
            
            y_pred = self.xgb_engine.predict(X_mature_scaled)
            rmse = np.sqrt(mean_squared_error(y_mature, y_pred))
            r2 = r2_score(y_mature, y_pred)
            print(f"    XGBoost RMSE: {rmse:.2f}, R²: {r2:.4f}")
        
        # Engine B: K-Means
        if len(X_nascent) > 0:
            print("\n  训练Engine B (K-Means)...")
            self.scaler_kmeans = StandardScaler()
            X_nascent_scaled = self.scaler_kmeans.fit_transform(X_nascent)
            
            unique_grades = grades_nascent.unique()
            n_clusters = max(5, min(12, len(unique_grades) * 2, len(X_nascent) // 30))
            
            self.kmeans_engine = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = self.kmeans_engine.fit_predict(X_nascent_scaled)
            
            # 加权评分
            self.cluster_scores = {}
            for i in range(n_clusters):
                mask = clusters == i
                if mask.sum() > 0:
                    cluster_grades = grades_nascent[mask]
                    cluster_scores = y_nascent[mask]
                    
                    weights = cluster_grades.map({
                        'S': 5.0, 'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0
                    }).values
                    
                    weighted_score = np.average(cluster_scores, weights=weights)
                    self.cluster_scores[i] = weighted_score
                else:
                    self.cluster_scores[i] = 60.0
            
            y_pred_nascent = np.array([self.cluster_scores[c] for c in clusters])
            rmse_nascent = np.sqrt(mean_squared_error(y_nascent, y_pred_nascent))
            print(f"    K-Means聚类数: {n_clusters}, RMSE: {rmse_nascent:.2f}")
        
        print("\n  双引擎训练完成")
        return self
    
    def predict(self, X, months):
        """双引擎预测"""
        predictions = np.zeros(len(X))
        engines = []
        
        for i in range(len(X)):
            m = months.iloc[i] if hasattr(months, 'iloc') else months[i]
            x = X[i:i+1]
            
            if m >= 6 and self.xgb_engine is not None:
                x_scaled = self.scaler_xgb.transform(x)
                predictions[i] = self.xgb_engine.predict(x_scaled)[0]
                engines.append('XGBoost')
            elif m < 6 and self.kmeans_engine is not None:
                x_scaled = self.scaler_kmeans.transform(x)
                cluster = self.kmeans_engine.predict(x_scaled)[0]
                predictions[i] = self.cluster_scores.get(cluster, 60.0)
                engines.append('K-Means')
            else:
                predictions[i] = 60.0
                engines.append('Fallback')
        
        predictions = np.clip(predictions, 45.0, 99.5)
        return predictions, engines

# ================================================================
#  主训练流程
# ================================================================

def train_model_j_oracle_v2():
    """训练Model J Oracle v2"""
    
    # 1. 获取数据
    df = fetch_data()
    if df.empty:
        print("错误: 无法获取数据")
        return None
    
    # 2. 特征工程
    df = extract_features(df)
    
    # 使用预言机评分作为标签
    df['ip_score'] = df['oracle_composite']
    
    # 3. 数据平衡
    df = balance_data(df)
    
    # 4. 准备特征
    print("\n2. 准备训练数据...")
    exclude = ['title', 'author', 'category', 'platform', 'year', 'month',
               'status', 'abstract', 'ip_grade', 'ip_score']
    feature_cols = [c for c in df.columns if c not in exclude and df[c].dtype in ['int64', 'float64', 'int32', 'float32']]
    
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], 0)
    
    print(f"   特征数: {len(feature_cols)}")
    
    # 5. 时间切分
    train_mask = df['year'] <= 2024
    val_mask = df['year'] >= 2024
    
    X_train = df[train_mask][feature_cols].values
    y_train = df[train_mask]['ip_score'].values
    months_train = df[train_mask]['months_active']
    grades_train = df[train_mask]['ip_grade']
    
    X_val = df[val_mask][feature_cols].values
    y_val = df[val_mask]['ip_score'].values
    months_val = df[val_mask]['months_active']
    
    print(f"   训练集: {len(X_train)} 条")
    print(f"   验证集: {len(X_val)} 条")
    
    # 6. 训练双引擎
    print("\n" + "="*70)
    print("训练改进版双引擎")
    print("="*70)
    
    dual_engine = ImprovedDualEngine()
    dual_engine.fit(X_train, y_train, months_train.reset_index(drop=True), grades_train.reset_index(drop=True))
    dual_engine.feature_cols = feature_cols
    
    # 7. 验证
    print("\n【验证集评估】")
    y_pred, engines = dual_engine.predict(X_val, months_val.reset_index(drop=True))
    
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    mae = mean_absolute_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)
    
    pred_grades = [IPGradingSystem.score_to_grade(s) for s in y_pred]
    actual_grades = df[val_mask]['ip_grade'].values
    grade_accuracy = np.mean([p == a for p, a in zip(pred_grades, actual_grades)])
    
    print(f"  RMSE: {rmse:.2f}")
    print(f"  MAE: {mae:.2f}")
    print(f"  R²: {r2:.4f}")
    print(f"  等级准确率: {grade_accuracy*100:.1f}%")
    
    # 引擎使用统计
    engine_counts = pd.Series(engines).value_counts()
    print(f"\n  引擎使用分布:")
    for engine, count in engine_counts.items():
        print(f"    {engine}: {count} ({count/len(engines)*100:.1f}%)")
    
    # 8. 保存模型
    print("\n" + "="*70)
    print("保存Model J Oracle v2")
    print("="*70)
    
    model_j_oracle_v2 = {
        'dual_engine': dual_engine,
        'features': feature_cols,
        'metrics': {
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'grade_accuracy': grade_accuracy
        },
        'version': 'Model_J_Oracle_v2.0',
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'description': '优化排名准确性的改进版IP评估模型',
        'improvements': [
            '对数映射替代分段线性',
            '更好保留月票排名顺序',
            '增加人气加成',
            '优化K-Means聚类'
        ]
    }
    
    save_path = 'resources/models/model_j_oracle_v2.pkl'
    joblib.dump(model_j_oracle_v2, save_path)
    print(f"   模型已保存: {save_path}")
    
    # 9. 总结
    print("\n" + "="*70)
    print("Model J Oracle v2 训练完成!")
    print("="*70)
    print(f"   总样本: {len(df)}")
    print(f"   总特征: {len(feature_cols)}")
    print(f"\n   性能指标:")
    print(f"     RMSE: {rmse:.2f}")
    print(f"     MAE: {mae:.2f}")
    print(f"     R²: {r2:.4f}")
    print(f"     等级准确率: {grade_accuracy*100:.1f}%")
    print("="*70)
    
    return model_j_oracle_v2

if __name__ == "__main__":
    model = train_model_j_oracle_v2()
