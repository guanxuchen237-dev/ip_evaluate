"""
XGBoost + K-Means 双引擎月票预测模型
- 成熟期作品: XGBoost 预测月票
- 孵化期作品: K-Means 聚类预测月票
符合论文算法要求
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
import xgboost as xgb
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from datetime import datetime
import os

warnings.filterwarnings('ignore')

print("=" * 70)
print("XGBoost + K-Means 双引擎月票预测模型")
print("=" * 70)

# 数据库配置
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'qidian_data', 'charset': 'utf8mb4'
}
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

# ================================================================
#  1. 获取数据
# ================================================================

print("\n【步骤1】获取训练数据...")

def fetch_data():
    dfs = []
    
    # 起点
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG)
        df_qd = pd.read_sql("""
            SELECT title, author, category, status, word_count,
                   recommendation_count as total_recommend,
                   monthly_ticket_count as monthly_tickets,
                   collection_count,
                   year, month
            FROM novel_monthly_stats
            WHERE year >= 2024 AND monthly_ticket_count > 0
        """, conn)
        df_qd['platform'] = 'Qidian'
        df_qd['fan_count'] = 0
        conn.close()
        print(f"   起点: {len(df_qd)} 条")
        dfs.append(df_qd)
    except Exception as e:
        print(f"   起点: 获取失败 - {e}")
    
    # 纵横
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG)
        df_zh = pd.read_sql("""
            SELECT title, author, category, status, word_count,
                   total_recommend, monthly_tickets, collection_count,
                   fan_count, year, month
            FROM zongheng_monthly_stats
            WHERE year >= 2024 AND monthly_tickets > 0
        """, conn)
        df_zh['platform'] = 'Zongheng'
        conn.close()
        print(f"   纵横: {len(df_zh)} 条")
        dfs.append(df_zh)
    except Exception as e:
        print(f"   纵横: 获取失败 - {e}")
    
    if not dfs:
        print("   警告: 无法从数据库获取数据，使用模拟数据")
        return generate_mock_data()
    
    return pd.concat(dfs, ignore_index=True)

def generate_mock_data():
    """生成模拟数据用于测试"""
    np.random.seed(42)
    n = 5000
    
    titles = [f"小说{i}" for i in range(n)]
    categories = np.random.choice(['玄幻', '奇幻', '仙侠', '都市', '游戏', '科幻'], n)
    platforms = np.random.choice(['Qidian', 'Zongheng'], n)
    
    # 生成特征
    word_count = np.random.randint(10000, 5000000, n)
    monthly_tickets = np.random.exponential(scale=5000, size=n).astype(int) + 100
    collections = (monthly_tickets * np.random.uniform(3, 10, n)).astype(int)
    total_recommend = (monthly_tickets * np.random.uniform(0.5, 2, n)).astype(int)
    fan_count = (collections * np.random.uniform(0.1, 0.3, n)).astype(int)
    
    # 年月
    year = np.random.choice([2024, 2025], n)
    month = np.random.randint(1, 13, n)
    
    df = pd.DataFrame({
        'title': titles,
        'author': '作者',
        'category': categories,
        'status': '连载',
        'word_count': word_count,
        'monthly_tickets': monthly_tickets,
        'collection_count': collections,
        'total_recommend': total_recommend,
        'fan_count': fan_count,
        'year': year,
        'month': month,
        'platform': platforms
    })
    
    print(f"   模拟数据: {len(df)} 条")
    return df

df = fetch_data()

# ================================================================
#  2. 特征工程
# ================================================================

print("\n【步骤2】特征工程...")

# 平台归一化
platform_scale = {'Qidian': 1.0, 'Zongheng': 8.0}
df['tickets_normalized'] = df.apply(
    lambda x: x['monthly_tickets'] * platform_scale.get(x['platform'], 1.0), axis=1
)
df['collection_normalized'] = df.apply(
    lambda x: x['collection_count'] * platform_scale.get(x['platform'], 1.0), axis=1
)
df['recommend_normalized'] = df.apply(
    lambda x: x['total_recommend'] * platform_scale.get(x['platform'], 1.0), axis=1
)

# 计算派生特征
df['log_word_count'] = np.log1p(df['word_count'])
df['log_tickets'] = np.log1p(df['tickets_normalized'])
df['log_collection'] = np.log1p(df['collection_normalized'])
df['log_recommend'] = np.log1p(df['recommend_normalized'])

df['tickets_per_word'] = df['tickets_normalized'] / (df['word_count'] + 1) * 10000
df['collection_per_word'] = df['collection_normalized'] / (df['word_count'] + 1) * 10000
df['heat_index'] = (df['tickets_normalized'] + df['collection_normalized'] + df['recommend_normalized']) / 3

# 题材热度
HOT_GENRES = {'玄幻': 95, '奇幻': 90, '仙侠': 88, '都市': 85, '游戏': 82, '科幻': 80, '历史': 78, '悬疑': 75}
df['genre_hotness'] = df['category'].map(lambda x: HOT_GENRES.get(str(x), 70)).fillna(70)

# 计算作品活跃月数
df = df.sort_values(['title', 'author', 'year', 'month'])
df['months_active'] = df.groupby(['title', 'author']).cumcount() + 1

# 特征列表
feature_cols = [
    'word_count', 'collection_count', 'total_recommend', 'fan_count',
    'log_word_count', 'log_collection', 'log_recommend',
    'tickets_per_word', 'collection_per_word', 'heat_index',
    'genre_hotness', 'months_active'
]

# 填充缺失值
for col in feature_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

df = df.replace([np.inf, -np.inf], 0)

print(f"   特征数: {len(feature_cols)}")
print(f"   总样本: {len(df)}")

# ================================================================
#  3. 双引擎架构
# ================================================================

class TicketDualEngine:
    """XGBoost + K-Means 双引擎月票预测"""
    
    def __init__(self):
        self.xgb_engine = None      # Engine A: XGBoost (成熟期)
        self.kmeans_engine = None   # Engine B: K-Means (孵化期)
        self.scaler_xgb = None
        self.scaler_kmeans = None
        self.feature_cols = None
        self.cluster_tickets = None  # 每个聚类的平均月票
        
    def fit(self, X, y_tickets, months):
        """训练双引擎"""
        print("\n【双引擎训练】")
        
        # 分割数据
        mature_mask = months >= 6
        nascent_mask = months < 6
        
        X_mature = X[mature_mask]
        y_mature = y_tickets[mature_mask]
        
        X_nascent = X[nascent_mask]
        y_nascent = y_tickets[nascent_mask]
        
        print(f"  成熟期样本: {len(X_mature)} (使用XGBoost)")
        print(f"  孵化期样本: {len(X_nascent)} (使用K-Means)")
        
        # ========== Engine A: XGBoost (成熟期) ==========
        if len(X_mature) > 50:
            print("\n  训练Engine A (XGBoost - 成熟期)...")
            self.scaler_xgb = StandardScaler()
            X_mature_scaled = self.scaler_xgb.fit_transform(X_mature)
            
            self.xgb_engine = xgb.XGBRegressor(
                objective='reg:squarederror',
                n_estimators=300,
                max_depth=8,
                learning_rate=0.1,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=42,
                n_jobs=-1
            )
            self.xgb_engine.fit(X_mature_scaled, y_mature)
            
            # 验证
            y_pred_mature = self.xgb_engine.predict(X_mature_scaled)
            rmse_mature = np.sqrt(mean_squared_error(y_mature, y_pred_mature))
            mae_mature = mean_absolute_error(y_mature, y_pred_mature)
            r2_mature = r2_score(y_mature, y_pred_mature)
            print(f"    XGBoost RMSE: {rmse_mature:.2f}")
            print(f"    XGBoost MAE: {mae_mature:.2f}")
            print(f"    XGBoost R²: {r2_mature:.4f}")
        else:
            print("  警告: 成熟期样本不足，跳过XGBoost训练")
        
        # ========== Engine B: K-Means (孵化期) ==========
        if len(X_nascent) > 30:
            print("\n  训练Engine B (K-Means - 孵化期)...")
            self.scaler_kmeans = StandardScaler()
            X_nascent_scaled = self.scaler_kmeans.fit_transform(X_nascent)
            
            # 确定聚类数
            n_clusters = min(10, max(3, len(X_nascent) // 50))
            self.kmeans_engine = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = self.kmeans_engine.fit_predict(X_nascent_scaled)
            
            # 计算每个聚类的平均月票
            self.cluster_tickets = {}
            for i in range(n_clusters):
                mask = clusters == i
                if mask.sum() > 0:
                    self.cluster_tickets[i] = y_nascent[mask].mean()
                else:
                    self.cluster_tickets[i] = y_nascent.mean()
            
            print(f"    K-Means聚类数: {n_clusters}")
            print(f"    各聚类平均月票:")
            for i, tickets in sorted(self.cluster_tickets.items()):
                count = (clusters == i).sum()
                print(f"      聚类{i}: 月票={tickets:.0f}, 样本数={count}")
            
            # 验证
            y_pred_nascent = np.array([self.cluster_tickets[c] for c in clusters])
            rmse_nascent = np.sqrt(mean_squared_error(y_nascent, y_pred_nascent))
            mae_nascent = mean_absolute_error(y_nascent, y_pred_nascent)
            print(f"    K-Means RMSE: {rmse_nascent:.2f}")
            print(f"    K-Means MAE: {mae_nascent:.2f}")
        else:
            print("  警告: 孵化期样本不足，跳过K-Means训练")
        
        self.feature_cols = feature_cols
        return self
    
    def predict(self, X, months):
        """预测月票"""
        predictions = []
        
        for i, (x, m) in enumerate(zip(X, months)):
            if m >= 6 and self.xgb_engine is not None and self.scaler_xgb is not None:
                # 成熟期: XGBoost
                x_scaled = self.scaler_xgb.transform(x.reshape(1, -1))
                pred = self.xgb_engine.predict(x_scaled)[0]
            elif self.kmeans_engine is not None and self.scaler_kmeans is not None:
                # 孵化期: K-Means
                x_scaled = self.scaler_kmeans.transform(x.reshape(1, -1))
                cluster = self.kmeans_engine.predict(x_scaled)[0]
                pred = self.cluster_tickets.get(cluster, 1000)
            else:
                # 回退: 使用平均值
                pred = 1000
            
            predictions.append(max(0, pred))
        
        return np.array(predictions)

# ================================================================
#  4. 训练模型
# ================================================================

print("\n【步骤3】训练双引擎模型...")

X = df[feature_cols].values
y_tickets = df['tickets_normalized'].values
months = df['months_active'].values

# 训练
engine = TicketDualEngine()
engine.fit(X, y_tickets, months)

# ================================================================
#  5. 验证评估
# ================================================================

print("\n【步骤4】验证评估...")

# 使用训练数据验证
y_pred = engine.predict(X, months)
rmse = np.sqrt(mean_squared_error(y_tickets, y_pred))
mae = mean_absolute_error(y_tickets, y_pred)
r2 = r2_score(y_tickets, y_pred)

print(f"  整体RMSE: {rmse:.2f}")
print(f"  整体MAE: {mae:.2f}")
print(f"  整体R²: {r2:.4f}")

# 误差分布
errors = np.abs(y_tickets - y_pred)
print(f"  误差分布:")
print(f"    25分位: {np.percentile(errors, 25):.0f}")
print(f"    50分位: {np.percentile(errors, 50):.0f}")
print(f"    75分位: {np.percentile(errors, 75):.0f}")

# ================================================================
#  6. 保存模型
# ================================================================

print("\n【步骤5】保存模型...")

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'resources', 'models', 'ticket_dual_engine.pkl')

model_data = {
    'dual_engine': engine,
    'features': feature_cols,
    'version': 'TicketDualEngine_v1.0',
    'timestamp': datetime.now().isoformat(),
    'metrics': {
        'rmse': rmse,
        'mae': mae,
        'r2': r2
    }
}

joblib.dump(model_data, MODEL_PATH)
print(f"  模型已保存: {MODEL_PATH}")

# ================================================================
#  7. 测试预测
# ================================================================

print("\n【步骤6】测试预测...")

# 测试样本
test_samples = [
    {'word_count': 500000, 'collections': 50000, 'recommendations': 5000, 'fans': 10000, 'months': 12},
    {'word_count': 100000, 'collections': 5000, 'recommendations': 500, 'fans': 500, 'months': 3},
]

for i, sample in enumerate(test_samples):
    # 构建特征
    x = np.array([[
        sample['word_count'],
        sample['collections'],
        sample['recommendations'],
        sample['fans'],
        np.log1p(sample['word_count']),
        np.log1p(sample['collections']),
        np.log1p(sample['recommendations']),
        sample['collections'] / (sample['word_count'] + 1) * 10000,
        sample['collections'] / (sample['word_count'] + 1) * 10000,
        (sample['collections'] + sample['recommendations']) / 2,
        90,  # genre_hotness
        sample['months']
    ]])
    
    pred = engine.predict(x, [sample['months']])[0]
    engine_type = 'XGBoost' if sample['months'] >= 6 else 'K-Means'
    print(f"  样本{i+1}: 预测月票={pred:.0f}, 引擎={engine_type}")

print("\n" + "=" * 70)
print("训练完成!")
print("=" * 70)
