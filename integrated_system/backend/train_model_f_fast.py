"""
Model F - 快速实用版
基于Model E + 开题报告创新点
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
from scipy.stats import entropy
from datetime import datetime
import os

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
print("Model F - 基于Model E + 开题报告创新点")
print("="*70)

# 1. 加载Model E的NLP和评论特征（已训练好的）
print("\n1. 加载Model E特征...")
model_e_path = 'resources/models/ticket_comments_enhanced_20260315_000101.pkl'
if os.path.exists(model_e_path):
    model_e_data = joblib.load(model_e_path)
    print(f"  Model E加载成功")
    print(f"  原特征数: {len(model_e_data.get('feature_names', []))}")
else:
    print(f"  Model E未找到: {model_e_path}")
    model_e_data = None

# 2. 获取改编标签数据
print("\n2. 获取改编标签...")
conn = pymysql.connect(**QIDIAN_CONFIG)
adaptation_sql = """
SELECT title, author, 
       CASE WHEN adaptations IS NOT NULL AND LENGTH(adaptations) > 3 
            THEN 1 ELSE 0 END as has_adaptation,
       CASE WHEN adaptations IS NOT NULL 
            THEN LENGTH(adaptations) - LENGTH(REPLACE(adaptations, ',', '')) + 1 
            ELSE 0 END as adaptation_count
FROM novel_monthly_stats
WHERE year >= 2020
GROUP BY title, author, adaptations
"""
df_adaptation = pd.read_sql(adaptation_sql, conn)
conn.close()
print(f"  改编数据: {df_adaptation['has_adaptation'].sum()} 本有改编")

# 3. 计算更新熵（开题报告创新点2）
print("\n3. 计算更新熵...")
conn = pymysql.connect(**QIDIAN_CONFIG)
df_qidian = pd.read_sql("""
    SELECT title, author, year, month, word_count, monthly_tickets_on_list as monthly_tickets
    FROM novel_monthly_stats 
    WHERE year >= 2020
    ORDER BY title, author, year, month
""", conn)
conn.close()

# 按书计算更新熵
def calc_update_entropy(group):
    group = group.sort_values(['year', 'month'])
    word_diff = group['word_count'].diff().fillna(0)
    update_volumes = word_diff[word_diff > 0].values
    
    if len(update_volumes) > 1:
        total = update_volumes.sum()
        if total > 0:
            probs = update_volumes / total
            update_entropy = entropy(probs, base=2)
        else:
            update_entropy = 0
        
        mean_update = update_volumes.mean()
        std_update = update_volumes.std() if len(update_volumes) > 1 else 0
        update_regularity = std_update / (mean_update + 1)
        drop_months = (word_diff == 0).sum()
        
        # 最长连续更新
        consecutive = max_consecutive = 0
        for diff in word_diff:
            if diff > 0:
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0
    else:
        update_entropy = update_regularity = 0
        drop_months = max_consecutive = 0
    
    return pd.Series({
        'update_entropy': update_entropy,
        'update_regularity': update_regularity,
        'drop_month_count': drop_months,
        'max_consecutive_months': max_consecutive
    })

entropy_features = df_qidian.groupby(['title', 'author']).apply(calc_update_entropy).reset_index()
print(f"  更新熵计算完成: {len(entropy_features)} 本")

# 4. IP基因聚类（开题报告创新点3）
print("\n4. 训练IP基因聚类...")

# 获取用于聚类的特征
conn = pymysql.connect(**QIDIAN_CONFIG)
df_cluster = pd.read_sql("""
    SELECT title, author, 
           AVG(word_count) as avg_word_count,
           AVG(monthly_tickets_on_list) as avg_monthly_tickets,
           AVG(collection_count) as avg_collection,
           MAX(CASE WHEN adaptations IS NOT NULL AND LENGTH(adaptations) > 3 THEN 1 ELSE 0 END) as has_adaptation
    FROM novel_monthly_stats
    WHERE year >= 2020
    GROUP BY title, author
""", conn)
conn.close()

# 合并更新熵特征
df_cluster = df_cluster.merge(entropy_features, on=['title', 'author'], how='left')
df_cluster = df_cluster.fillna(0)

# 定义成功作品（月票>10000或有改编）
success_mask = (df_cluster['avg_monthly_tickets'] > 10000) | (df_cluster['has_adaptation'] == 1)
success_books = df_cluster[success_mask].copy()
print(f"  成功作品样本: {len(success_books)} 本")

# 训练K-Means
cluster_features = ['avg_word_count', 'avg_monthly_tickets', 'avg_collection', 
                   'update_regularity', 'has_adaptation']
X = success_books[cluster_features].values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
success_books['ip_gene_cluster'] = kmeans.fit_predict(X_scaled)

print(f"  聚类分布: {dict(success_books['ip_gene_cluster'].value_counts().sort_index())}")

# 为所有书计算相似度
X_all = df_cluster[cluster_features].values
X_all_scaled = scaler.transform(X_all)
cluster_ids = kmeans.predict(X_all_scaled)
df_cluster['ip_gene_cluster'] = cluster_ids

similarities = []
for i, x in enumerate(X_all_scaled):
    center = kmeans.cluster_centers_[cluster_ids[i]]
    distance = np.linalg.norm(x - center)
    similarity = max(0, 100 - distance * 10)
    similarities.append(similarity)

df_cluster['ip_gene_similarity'] = similarities
print(f"  平均IP基因相似度: {df_cluster['ip_gene_similarity'].mean():.2f}")

# 5. 双引擎模型训练（开题报告创新点1）
print("\n5. 双引擎模型训练...")

# 准备完整数据
conn = pymysql.connect(**QIDIAN_CONFIG)
df_train = pd.read_sql("""
    SELECT year, month, title, author, category, word_count,
           collection_count, monthly_tickets_on_list as monthly_tickets,
           recommendation_count as total_recommend,
           week_recommendation_count as weekly_recommend,
           reward_count
    FROM novel_monthly_stats
    WHERE year >= 2020
""", conn)
conn.close()

# 合并所有特征
df_train = df_train.merge(entropy_features, on=['title', 'author'], how='left')
df_train = df_train.merge(df_cluster[['title', 'author', 'ip_gene_similarity', 'has_adaptation']], 
                          on=['title', 'author'], how='left')
df_train = df_train.fillna(0)

# 基础特征工程
df_train['log_word_count'] = np.log1p(df_train['word_count'])
df_train['log_collection'] = np.log1p(df_train['collection_count'])
df_train['log_recommend'] = np.log1p(df_train['total_recommend'])
df_train['tickets_per_word'] = df_train['monthly_tickets'] / (df_train['word_count'] + 1) * 10000
df_train['recommend_per_collection'] = df_train['total_recommend'] / (df_train['collection_count'] + 1)
df_train['year_month'] = df_train['year'] * 12 + df_train['month']

# 计算连载月数
start_dates = df_train.groupby(['title', 'author'])['year_month'].transform('min')
df_train['months_since_start'] = df_train['year_month'] - start_dates

# 购买力指数（开题报告创新点1补充）
df_train['purchasing_power_index'] = (
    np.log1p(df_train['reward_count'] / (df_train['collection_count'] + 1) * 100) * 30 +
    np.log1p(df_train['recommend_per_collection']) * 20 +
    np.minimum(50, df_train['monthly_tickets'] / 1000)
).clip(0, 100)

# 时序特征
df_train = df_train.sort_values(['title', 'author', 'year', 'month'])
df_train['tickets_mom'] = df_train.groupby(['title', 'author'])['monthly_tickets'].pct_change().fillna(0).replace([np.inf, -np.inf], 0)

print(f"  总特征数: {len(df_train.columns)}")

# 双引擎划分
feature_cols = ['log_word_count', 'log_collection', 'log_recommend',
                'update_entropy', 'update_regularity', 'max_consecutive_months',
                'ip_gene_similarity', 'has_adaptation', 'purchasing_power_index',
                'tickets_mom', 'tickets_per_word', 'recommend_per_collection']

train_mask = df_train['year'] <= 2023
val_mask = df_train['year'] == 2024

mature_mask = df_train['months_since_start'] >= 6
immature_mask = df_train['months_since_start'] < 6

print(f"\n  成熟期样本: {(train_mask & mature_mask).sum()} 条")
print(f"  孵化期样本: {(train_mask & immature_mask).sum()} 条")

# Engine A: XGBoost for Mature Books
print("\n  【Engine A】XGBoost (成熟期)...")
mature_train = df_train[train_mask & mature_mask]

X_train = mature_train[feature_cols]
y_train = np.log1p(mature_train['monthly_tickets'])

scaler_xgb = StandardScaler()
X_train_scaled = scaler_xgb.fit_transform(X_train)

dtrain = xgb.DMatrix(X_train_scaled, label=y_train, feature_names=feature_cols)

params = {
    'objective': 'reg:squarederror',
    'max_depth': 8,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'eval_metric': 'rmse',
    'seed': 42
}

model_a = xgb.train(params, dtrain, num_boost_round=500)
print("  Engine A训练完成")

# Engine B: Rule-based for Immature Books
print("\n  【Engine B】孵化期评分规则...")
engine_b_weights = {
    'tickets_mom': 0.3,
    'update_regularity': 0.25,
    'max_consecutive_months': 0.2,
    'purchasing_power_index': 0.15,
    'ip_gene_similarity': 0.1
}
print(f"  权重: {engine_b_weights}")

# 6. 验证
print("\n6. 模型验证...")
if val_mask.sum() > 0:
    val_df = df_train[val_mask].copy()
    
    predictions = []
    for _, row in val_df.iterrows():
        if row['months_since_start'] >= 6:
            # Engine A
            X = pd.DataFrame([row[feature_cols].values], columns=feature_cols)
            X_scaled = scaler_xgb.transform(X)
            dmatrix = xgb.DMatrix(X_scaled, feature_names=feature_cols)
            pred = np.expm1(model_a.predict(dmatrix))[0]
        else:
            # Engine B
            score = sum(row[feat] * weight * 100 for feat, weight in engine_b_weights.items() if feat in row)
            pred = score
        predictions.append(pred)
    
    val_df['prediction'] = predictions
    y_true = val_df['monthly_tickets'].values
    y_pred = val_df['prediction'].values
    
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1))) * 100
    
    print(f"\n  验证集性能:")
    print(f"    RMSE: {rmse:.2f}")
    print(f"    MAE: {mae:.2f}")
    print(f"    R²: {r2:.4f}")
    print(f"    MAPE: {mape:.2f}%")

# 7. 保存模型
print("\n7. 保存Model F...")
model_f = {
    'engine_a': {'model': model_a, 'scaler': scaler_xgb, 'features': feature_cols},
    'engine_b': {'weights': engine_b_weights},
    'ip_clustering': {'kmeans': kmeans, 'scaler': scaler, 'features': cluster_features},
    'entropy_features': entropy_features,
    'adaptation_data': df_adaptation,
    'version': 'Model_F_v1.0',
    'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
}

save_path = 'resources/models/model_f_complete.pkl'
joblib.dump(model_f, save_path)
print(f"  模型已保存: {save_path}")

print("\n" + "="*70)
print("Model F 训练完成!")
print("="*70)
print(f"  总样本: {len(df_train)}")
print(f"  有改编: {df_train['has_adaptation'].sum()} 本")
print(f"  成熟期: {(df_train['months_since_start'] >= 6).sum()} 本")
print(f"  孵化期: {(df_train['months_since_start'] < 6).sum()} 本")
print(f"  MAPE: {mape:.2f}%")
print("="*70)
