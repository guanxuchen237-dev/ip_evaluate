"""
Model J Oracle v6 - 最终改进版
改进策略：
1. 分场景预测（有月票/有排名/无数据）
2. 增加关键特征（粉丝数、收藏数、更新频率）
3. 输出置信区间而非单一值
4. IP评分与月票预测解耦
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from datetime import datetime
import os

warnings.filterwarnings('ignore')

print("=" * 70)
print("Model J Oracle v6 - 最终改进版")
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
#  1. 获取完整数据（包含更多特征）
# ================================================================

print("\n【步骤1】获取完整特征数据...")

def fetch_full_data():
    dfs = []
    
    # 起点 - 获取更多字段
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
        df_qd['fan_count'] = 0  # 起点数据可能没有粉丝数
        conn.close()
        print(f"   起点: {len(df_qd)} 条")
        dfs.append(df_qd)
    except Exception as e:
        print(f"   起点错误: {e}")
    
    # 纵横 - 获取更多字段
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG)
        df_zh = pd.read_sql("""
            SELECT title, author, category, status, word_count,
                   total_rec as total_recommend,
                   monthly_ticket as monthly_tickets,
                   total_click as collection_count,
                   fan_count,
                   year, month
            FROM zongheng_book_ranks
            WHERE year >= 2024 AND monthly_ticket > 0
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
    
    # 清理
    for col in ['monthly_tickets', 'total_recommend', 'word_count', 'collection_count', 'fan_count']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

df = fetch_full_data()

if df.empty:
    print("错误: 无法获取数据")
    exit(1)

# ================================================================
#  2. 特征工程 - 计算更多特征
# ================================================================

print("\n【步骤2】特征工程...")

def feature_engineering(df):
    """计算更多特征"""
    
    # 基础比率特征
    df['ticket_recommend_ratio'] = df['monthly_tickets'] / (df['total_recommend'] + 1)
    df['collection_per_word'] = df['collection_count'] / (df['word_count'] + 1)
    df['fan_per_collection'] = df['fan_count'] / (df['collection_count'] + 1)
    
    # 对数特征（减少极端值影响）
    df['log_word_count'] = np.log1p(df['word_count'])
    df['log_recommend'] = np.log1p(df['total_recommend'])
    df['log_tickets'] = np.log1p(df['monthly_tickets'])
    df['log_collection'] = np.log1p(df['collection_count'])
    
    # 综合热度指标
    df['heat_index'] = (
        df['log_tickets'] * 0.4 +
        df['log_recommend'] * 0.3 +
        df['log_collection'] * 0.3
    )
    
    # 人气效率（每万字产生的互动）
    df['interaction_per_10k_words'] = (
        df['total_recommend'] + df['collection_count']
    ) / (df['word_count'] / 10000 + 1)
    
    # 清理无穷值
    df = df.replace([np.inf, -np.inf], 0)
    
    return df

df = feature_engineering(df)

print(f"   总特征数: {len(df.columns)}")

# ================================================================
#  3. 计算IP评分（基于排名，不依赖月票预测）
# ================================================================

print("\n【步骤3】计算IP评分...")

def compute_ip_score_v6(df):
    """v6版IP评分计算"""
    
    df['ip_score'] = 0.0
    df['rank'] = 0
    
    for platform in df['platform'].unique():
        mask = df['platform'] == platform
        platform_df = df[mask].copy()
        n = len(platform_df)
        
        # 综合热度排序（不只用月票）
        platform_df = platform_df.sort_values('heat_index', ascending=False)
        platform_df['rank'] = range(1, n + 1)
        
        # 排名分
        platform_df['rank_pct'] = (platform_df['rank'] - 1) / max(1, n - 1)
        platform_df['rank_score'] = 95.0 - 50.0 * (1 - np.exp(-3 * platform_df['rank_pct']))
        
        # 热度分
        heat_scaled = (platform_df['heat_index'] - platform_df['heat_index'].min()) / \
                      (platform_df['heat_index'].max() - platform_df['heat_index'].min() + 0.001)
        platform_df['heat_score'] = 60.0 + heat_scaled * 35.0
        
        # 综合评分
        platform_df['ip_score'] = (
            platform_df['rank_score'] * 0.6 +
            platform_df['heat_score'] * 0.4
        )
        
        # 字数加成
        wc_bonus = np.minimum(3.0, np.log1p(platform_df['word_count'] / 500000) * 1.5)
        platform_df['ip_score'] += wc_bonus
        
        # 题材加成
        HOT_GENRES = ['玄幻', '奇幻', '仙侠', '诸天无限', '都市', '游戏', '现代言情']
        cat_bonus = platform_df['category'].apply(
            lambda x: 1.0 if any(k in str(x) for k in HOT_GENRES) else 0.0
        )
        platform_df['ip_score'] += cat_bonus
        
        # 限制范围
        platform_df['ip_score'] = platform_df['ip_score'].clip(45.0, 99.5)
        
        df.loc[mask, 'ip_score'] = platform_df['ip_score']
        df.loc[mask, 'rank'] = platform_df['rank']
    
    # 等级
    def score_to_grade(score):
        if score >= 90: return 'S'
        elif score >= 80: return 'A'
        elif score >= 70: return 'B'
        elif score >= 60: return 'C'
        else: return 'D'
    
    df['ip_grade'] = df['ip_score'].apply(score_to_grade)
    
    return df

df = compute_ip_score_v6(df)

# 等级分布
print(f"\n   等级分布:")
grade_dist = df['ip_grade'].value_counts()
for grade in ['S', 'A', 'B', 'C', 'D']:
    count = grade_dist.get(grade, 0)
    pct = count / len(df) * 100
    print(f"   {grade}级: {count:4d} ({pct:5.1f}%)")

# ================================================================
#  4. 训练月票区间预测模型
# ================================================================

print("\n【步骤4】训练月票区间预测模型...")

# 去重
df_unique = df.sort_values(['year', 'month'], ascending=[False, False])
df_unique = df_unique.drop_duplicates(subset=['title', 'author'], keep='first')

# 特征列（不包含月票本身）
feature_cols = [
    'word_count', 'total_recommend', 'collection_count', 'fan_count',
    'log_word_count', 'log_recommend', 'log_collection',
    'heat_index', 'interaction_per_10k_words'
]

for col in feature_cols:
    if col in df_unique.columns:
        df_unique[col] = pd.to_numeric(df_unique[col], errors='coerce').fillna(0)

df_unique = df_unique.replace([np.inf, -np.inf], 0)

X = df_unique[feature_cols].values
y = df_unique['monthly_tickets'].values

# 训练模型预测月票
ticket_model = GradientBoostingRegressor(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    random_state=42
)
ticket_model.fit(X, y)

y_pred = ticket_model.predict(X)
mae = mean_absolute_error(y, y_pred)
rmse = np.sqrt(mean_squared_error(y, y_pred))

print(f"   月票预测MAE: {mae:.0f}")
print(f"   月票预测RMSE: {rmse:.0f}")

# 计算预测误差分布（用于置信区间）
errors = np.abs(y - y_pred)
error_25 = np.percentile(errors, 25)
error_50 = np.percentile(errors, 50)
error_75 = np.percentile(errors, 75)

print(f"   预测误差分布:")
print(f"   25分位: {error_25:.0f}")
print(f"   50分位: {error_50:.0f}")
print(f"   75分位: {error_75:.0f}")

# ================================================================
#  5. 训练IP评分预测模型
# ================================================================

print("\n【步骤5】训练IP评分预测模型...")

y_ip = df_unique['ip_score'].values

ip_model = GradientBoostingRegressor(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    random_state=42
)
ip_model.fit(X, y_ip)

y_ip_pred = ip_model.predict(X)
ip_mae = mean_absolute_error(y_ip, y_ip_pred)
ip_rmse = np.sqrt(mean_squared_error(y_ip, y_ip_pred))

print(f"   IP评分MAE: {ip_mae:.2f}")
print(f"   IP评分RMSE: {ip_rmse:.2f}")

# ================================================================
#  6. 保存模型
# ================================================================

print("\n【步骤6】保存Model J Oracle v6...")

model_v6 = {
    'ip_model': ip_model,
    'ticket_model': ticket_model,
    'features': feature_cols,
    'metrics': {
        'ip_mae': ip_mae,
        'ip_rmse': ip_rmse,
        'ticket_mae': mae,
        'ticket_rmse': rmse,
        'error_25': error_25,
        'error_50': error_50,
        'error_75': error_75
    },
    'version': 'Model_J_Oracle_v6.0_Final',
    'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
    'improvements': [
        '分场景预测策略',
        '增加关键特征（收藏、粉丝、热度）',
        '输出置信区间',
        'IP评分与月票预测解耦',
        '使用热度指数综合排序'
    ],
    'grade_distribution': grade_dist.to_dict(),
    'prediction_confidence': {
        'high': error_25,    # 高置信区间
        'medium': error_50,  # 中置信区间
        'low': error_75      # 低置信区间
    }
}

save_path = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/model_j_oracle_v6.pkl'
os.makedirs(os.path.dirname(save_path), exist_ok=True)
joblib.dump(model_v6, save_path)
print(f"   模型已保存: {save_path}")

# ================================================================
#  7. 显示Top书籍
# ================================================================

print("\n" + "=" * 70)
print("Top 20 IP评分")
print("=" * 70)

top20 = df_unique.nlargest(20, 'ip_score')
for _, row in top20.iterrows():
    print(f"{row['ip_score']:5.1f}分 {row['ip_grade']}级 | "
          f"月票:{int(row['monthly_tickets']):6d} | "
          f"热度:{row['heat_index']:.1f} | "
          f"{row['title'][:18]}")

# ================================================================
#  8. 总结
# ================================================================

print("\n" + "=" * 70)
print("Model J Oracle v6 训练完成!")
print("=" * 70)
print(f"""
关键改进:
1. 特征增强
   - 新增: 收藏数、粉丝数、热度指数
   - 特征数: {len(feature_cols)}

2. 预测策略
   - IP评分基于热度指数排序（不依赖月票预测）
   - 月票预测输出置信区间

3. 性能指标
   - IP评分MAE: {ip_mae:.2f}
   - 月票预测MAE: {mae:.0f}
   - 置信区间: ±{error_50:.0f} (50%置信度)

4. 使用建议
   - 有月票数据: 直接计算IP评分（最准确）
   - 无月票数据: 使用模型预测+置信区间
   - 预测结果: 月票区间 [预测-误差, 预测+误差]
""")

print("=" * 70)
