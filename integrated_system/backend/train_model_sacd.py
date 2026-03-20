"""
XGBoost + K-Means 双引擎IP评分模型 (S/A/C/D等级制)
- 成熟期作品: XGBoost 预测IP评分
- 孵化期作品: K-Means 聚类预测IP评分
- 评分等级: S/A/C/D (无B级)
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
print("XGBoost + K-Means 双引擎IP评分模型 (S/A/C/D等级制)")
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
#  评分等级定义 (S/A/C/D)
# ================================================================

def score_to_grade_sabcd(score):
    """S/A/B/C/D等级转换"""
    if score >= 88:
        return 'S'
    elif score >= 80:
        return 'A'
    elif score >= 70:
        return 'B'
    elif score >= 60:
        return 'C'
    else:
        return 'D'

GRADE_INFO = {
    'S': {'range': (88, 100), 'desc': '顶级IP', 'color': '[红]'},
    'A': {'range': (80, 87), 'desc': '优质IP', 'color': '[黄]'},
    'B': {'range': (70, 79), 'desc': '良好IP', 'color': '[蓝]'},
    'C': {'range': (60, 69), 'desc': '普通IP', 'color': '[绿]'},
    'D': {'range': (0, 59), 'desc': '待观察', 'color': '[灰]'},
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
        df_qd['rank'] = 0  # 默认无排名
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
        df_zh['rank'] = 0
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
    
    # 生成特征 - 确保有不同质量等级
    # S级: 5%
    s_mask = np.random.random(n) < 0.05
    # A级: 15%
    a_mask = (~s_mask) & (np.random.random(n) < 0.20)
    # C级: 40%
    c_mask = (~s_mask) & (~a_mask) & (np.random.random(n) < 0.67)
    # D级: 剩余
    
    word_count = np.random.randint(10000, 5000000, n)
    monthly_tickets = np.zeros(n, dtype=int)
    collections = np.zeros(n, dtype=int)
    
    # S级作品
    monthly_tickets[s_mask] = np.random.randint(30000, 100000, s_mask.sum())
    collections[s_mask] = np.random.randint(200000, 500000, s_mask.sum())
    
    # A级作品
    monthly_tickets[a_mask] = np.random.randint(10000, 30000, a_mask.sum())
    collections[a_mask] = np.random.randint(50000, 200000, a_mask.sum())
    
    # C级作品
    monthly_tickets[c_mask] = np.random.randint(2000, 10000, c_mask.sum())
    collections[c_mask] = np.random.randint(5000, 50000, c_mask.sum())
    
    # D级作品
    d_mask = ~(s_mask | a_mask | c_mask)
    monthly_tickets[d_mask] = np.random.randint(100, 2000, d_mask.sum())
    collections[d_mask] = np.random.randint(500, 5000, d_mask.sum())
    
    total_recommend = (monthly_tickets * np.random.uniform(0.5, 2, n)).astype(int)
    fan_count = (collections * np.random.uniform(0.1, 0.3, n)).astype(int)
    
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
        'platform': platforms,
        'rank': 0
    })
    
    print(f"   模拟数据: {len(df)} 条")
    return df

df = fetch_data()

# ================================================================
#  2. 计算IP评分（确保区分度）
# ================================================================

print("\n【步骤2】计算IP评分...")

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

# 计算IP评分（基于排名+月票，确保区分度）
def compute_ip_score(row):
    tickets = row['tickets_normalized']
    colls = row['collection_normalized']
    recommend = row['recommend_normalized']
    words = row['word_count']
    rank = row.get('rank', 0)
    
    # 基础分：根据排名确定（主要分级依据）
    if rank > 0 and rank <= 10:
        base_score = 95  # S级基础分
    elif rank > 0 and rank <= 50:
        base_score = 85  # A级基础分
    elif rank > 0 and rank <= 100:
        base_score = 75  # A级基础分
    elif rank > 0 and rank <= 200:
        base_score = 65  # C级基础分
    else:
        # 无排名时，根据月票判断
        if tickets >= 30000:
            base_score = 92  # S级
        elif tickets >= 10000:
            base_score = 82  # A级
        elif tickets >= 3000:
            base_score = 70  # C级
        else:
            base_score = 50  # D级
    
    # 月票调整分（±10分）
    tickets_log = np.log1p(tickets)
    tickets_adj = (tickets_log / np.log1p(50000) - 0.5) * 20  # -10到+10
    tickets_adj = np.clip(tickets_adj, -10, 10)
    
    # 收藏调整分（±5分）
    colls_log = np.log1p(colls)
    colls_adj = (colls_log / np.log1p(300000) - 0.5) * 10
    colls_adj = np.clip(colls_adj, -5, 5)
    
    # 字数调整分（±3分）
    word_adj = (words / 500000 - 0.5) * 6
    word_adj = np.clip(word_adj, -3, 3)
    
    # 综合评分
    ip_score = base_score + tickets_adj + colls_adj + word_adj
    ip_score = np.clip(ip_score, 0, 100)
    
    return ip_score

df['ip_score'] = df.apply(compute_ip_score, axis=1)
df['ip_grade'] = df['ip_score'].apply(score_to_grade_sabcd)

# 统计等级分布
print(f"\n  IP评分统计:")
print(f"    均值: {df['ip_score'].mean():.2f}")
print(f"    标准差: {df['ip_score'].std():.2f}")
print(f"    最小值: {df['ip_score'].min():.2f}")
print(f"    最大值: {df['ip_score'].max():.2f}")

print(f"\n  等级分布:")
for grade in ['S', 'A', 'B', 'C', 'D']:
    count = (df['ip_grade'] == grade).sum()
    pct = count / len(df) * 100
    info = GRADE_INFO[grade]
    print(f"    {info['color']} {grade}级 ({info['range'][0]}-{info['range'][1]}): {count}本 ({pct:.1f}%)")

# ================================================================
#  3. 特征工程
# ================================================================

print("\n【步骤3】特征工程...")

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
    'genre_hotness', 'months_active', 'tickets_normalized'
]

# 填充缺失值
for col in feature_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

df = df.replace([np.inf, -np.inf], 0)

print(f"   特征数: {len(feature_cols)}")
print(f"   总样本: {len(df)}")

# ================================================================
#  4. 双引擎架构
# ================================================================

class IPDualEngineSACD:
    """XGBoost + K-Means 双引擎IP评分 (S/A/C/D等级)"""
    
    def __init__(self):
        self.xgb_engine = None
        self.kmeans_engine = None
        self.scaler_xgb = None
        self.scaler_kmeans = None
        self.feature_cols = None
        self.cluster_scores = None
        
    def fit(self, X, y_scores, months):
        """训练双引擎"""
        print("\n【双引擎训练】")
        
        # 分割数据
        mature_mask = months >= 6
        nascent_mask = months < 6
        
        X_mature = X[mature_mask]
        y_mature = y_scores[mature_mask]
        
        X_nascent = X[nascent_mask]
        y_nascent = y_scores[nascent_mask]
        
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
            
            # 检查预测范围
            print(f"    预测范围: [{y_pred_mature.min():.1f}, {y_pred_mature.max():.1f}]")
        else:
            print("  警告: 成熟期样本不足，跳过XGBoost训练")
        
        # ========== Engine B: K-Means (孵化期) ==========
        if len(X_nascent) > 30:
            print("\n  训练Engine B (K-Means - 孵化期)...")
            self.scaler_kmeans = StandardScaler()
            X_nascent_scaled = self.scaler_kmeans.fit_transform(X_nascent)
            
            n_clusters = min(10, max(3, len(X_nascent) // 50))
            self.kmeans_engine = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = self.kmeans_engine.fit_predict(X_nascent_scaled)
            
            # 计算每个聚类的平均IP评分
            self.cluster_scores = {}
            for i in range(n_clusters):
                mask = clusters == i
                if mask.sum() > 0:
                    self.cluster_scores[i] = y_nascent[mask].mean()
                else:
                    self.cluster_scores[i] = y_nascent.mean()
            
            print(f"    K-Means聚类数: {n_clusters}")
            print(f"    各聚类平均IP评分:")
            for i, score in sorted(self.cluster_scores.items()):
                count = (clusters == i).sum()
                grade = score_to_grade_sabcd(score)
                print(f"      聚类{i}: IP={score:.1f} ({grade}级), 样本数={count}")
            
            # 验证
            y_pred_nascent = np.array([self.cluster_scores[c] for c in clusters])
            rmse_nascent = np.sqrt(mean_squared_error(y_nascent, y_pred_nascent))
            mae_nascent = mean_absolute_error(y_nascent, y_pred_nascent)
            print(f"    K-Means RMSE: {rmse_nascent:.2f}")
            print(f"    K-Means MAE: {mae_nascent:.2f}")
        else:
            print("  警告: 孵化期样本不足，跳过K-Means训练")
        
        self.feature_cols = feature_cols
        return self
    
    def predict(self, X, months):
        """预测IP评分"""
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
                pred = self.cluster_scores.get(cluster, 50)
            else:
                # 回退: 使用平均值
                pred = 50
            
            predictions.append(np.clip(pred, 0, 100))
        
        return np.array(predictions)

# ================================================================
#  5. 训练模型
# ================================================================

print("\n【步骤4】训练双引擎模型...")

X = df[feature_cols].values
y_scores = df['ip_score'].values
months = df['months_active'].values

# 训练
engine = IPDualEngineSACD()
engine.fit(X, y_scores, months)

# ================================================================
#  6. 验证评估
# ================================================================

print("\n【步骤5】验证评估...")

# 使用训练数据验证
y_pred = engine.predict(X, months)
rmse = np.sqrt(mean_squared_error(y_scores, y_pred))
mae = mean_absolute_error(y_scores, y_pred)
r2 = r2_score(y_scores, y_pred)

print(f"  整体RMSE: {rmse:.2f}")
print(f"  整体MAE: {mae:.2f}")
print(f"  整体R²: {r2:.4f}")

# 等级预测准确率
y_pred_grades = [score_to_grade_sabcd(s) for s in y_pred]
y_true_grades = df['ip_grade'].values
accuracy = sum(p == t for p, t in zip(y_pred_grades, y_true_grades)) / len(y_pred_grades)
print(f"  等级预测准确率: {accuracy*100:.1f}%")

# 预测范围
print(f"\n  预测IP评分范围: [{y_pred.min():.1f}, {y_pred.max():.1f}]")
print(f"  预测等级分布:")
for grade in ['S', 'A', 'B', 'C', 'D']:
    count = sum(1 for g in y_pred_grades if g == grade)
    pct = count / len(y_pred_grades) * 100
    print(f"    {grade}级: {count}本 ({pct:.1f}%)")

# ================================================================
#  7. 保存模型
# ================================================================

print("\n【步骤6】保存模型...")

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'resources', 'models', 'model_sacd.pkl')

model_data = {
    'dual_engine': engine,
    'features': feature_cols,
    'version': 'IPDualEngine_SACD_v1.0',
    'timestamp': datetime.now().isoformat(),
    'grade_system': 'SACD',  # S/A/C/D等级制
    'metrics': {
        'rmse': rmse,
        'mae': mae,
        'r2': r2,
        'grade_accuracy': accuracy
    }
}

joblib.dump(model_data, MODEL_PATH)
print(f"  模型已保存: {MODEL_PATH}")

# ================================================================
#  8. 测试预测
# ================================================================

print("\n【步骤7】测试预测...")

test_cases = [
    ('顶级(第1)', 50000, 300000, 3000000, 1),
    ('优秀(第10)', 30000, 150000, 1000000, 10),
    ('良好(第50)', 10000, 50000, 500000, 50),
    ('中等(第100)', 5000, 20000, 300000, 100),
    ('普通(第200)', 1000, 5000, 100000, 200),
    ('新作(无排名)', 100, 500, 30000, 0),
]

for name, tickets, colls, words, rank in test_cases:
    # 构建特征向量
    X = np.array([[
        words,
        colls,
        colls * 0.1,  # total_recommend
        colls * 0.1,  # fan_count
        np.log1p(words),
        np.log1p(colls),
        np.log1p(colls * 0.1),
        tickets / (words + 1) * 10000,
        colls / (words + 1) * 10000,
        (tickets + colls + colls * 0.1) / 3,
        95,  # genre_hotness
        12,  # months_active
        tickets  # tickets_normalized
    ]])
    
    pred = engine.predict(X, [12])[0]
    grade = score_to_grade_sabcd(pred)
    engine_type = 'XGBoost' if 12 >= 6 else 'K-Means'
    print(f"  {name}: 月票={tickets}, 收藏={colls} -> IP={pred:.1f} ({grade}级) [{engine_type}]")

print("\n" + "=" * 70)
print("训练完成!")
print("=" * 70)
