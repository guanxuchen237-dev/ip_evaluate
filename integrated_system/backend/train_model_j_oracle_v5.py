"""
Model J Oracle v5 - 最终修正版
核心改进：直接使用实际转化率预测月票
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from datetime import datetime
import os

warnings.filterwarnings('ignore')

print("=" * 70)
print("Model J Oracle v5 - 最终修正版")
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
#  1. 获取数据并计算实际转化率
# ================================================================

print("\n【步骤1】获取数据计算实际转化率...")

def fetch_data():
    dfs = []
    
    # 起点
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG)
        df_qd = pd.read_sql("""
            SELECT title, author, category, status, word_count,
                   recommendation_count as total_recommend,
                   monthly_ticket_count as monthly_tickets,
                   year, month
            FROM novel_monthly_stats
            WHERE year >= 2024 AND monthly_ticket_count > 0
               AND recommendation_count > 1000
        """, conn)
        df_qd['platform'] = 'Qidian'
        conn.close()
        dfs.append(df_qd)
        print(f"   起点: {len(df_qd)} 条")
    except Exception as e:
        print(f"   起点错误: {e}")
    
    # 纵横
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG)
        df_zh = pd.read_sql("""
            SELECT title, author, category, status, word_count,
                   total_rec as total_recommend,
                   monthly_ticket as monthly_tickets,
                   year, month
            FROM zongheng_book_ranks
            WHERE year >= 2024 AND monthly_ticket > 0
               AND total_rec > 1000
        """, conn)
        df_zh['platform'] = 'Zongheng'
        conn.close()
        dfs.append(df_zh)
        print(f"   纵横: {len(df_zh)} 条")
    except Exception as e:
        print(f"   纵横错误: {e}")
    
    if not dfs:
        return pd.DataFrame()
    
    df = pd.concat(dfs, ignore_index=True)
    
    # 清理
    df['monthly_tickets'] = pd.to_numeric(df['monthly_tickets'], errors='coerce').fillna(0)
    df['total_recommend'] = pd.to_numeric(df['total_recommend'], errors='coerce').fillna(0)
    df['word_count'] = pd.to_numeric(df['word_count'], errors='coerce').fillna(0)
    
    # 计算转化率
    df['ticket_ratio'] = df['monthly_tickets'] / (df['total_recommend'] + 1)
    
    # 按平台统计
    print(f"\n   实际转化率统计:")
    for platform in df['platform'].unique():
        platform_df = df[df['platform'] == platform]
        print(f"   {platform}:")
        print(f"      平均转化率: {platform_df['ticket_ratio'].mean():.4f}")
        print(f"      中位数转化率: {platform_df['ticket_ratio'].median():.4f}")
        print(f"      25分位: {platform_df['ticket_ratio'].quantile(0.25):.4f}")
        print(f"      75分位: {platform_df['ticket_ratio'].quantile(0.75):.4f}")
    
    return df

df = fetch_data()

if df.empty:
    print("错误: 无法获取数据")
    exit(1)

# ================================================================
#  2. 计算IP评分（基于排名）
# ================================================================

print("\n【步骤2】计算IP评分...")

def compute_ip_score(df):
    """基于实际排名计算IP评分"""
    
    df['rank_score'] = 0.0
    df['ticket_score'] = 0.0
    df['rank'] = 0
    
    for platform in df['platform'].unique():
        mask = df['platform'] == platform
        platform_df = df[mask].copy()
        n = len(platform_df)
        
        # 按月票排序
        platform_df = platform_df.sort_values('monthly_tickets', ascending=False)
        platform_df['rank'] = range(1, n + 1)
        
        # 排名分（指数平滑）
        platform_df['rank_pct'] = (platform_df['rank'] - 1) / max(1, n - 1)
        platform_df['rank_score'] = 95.0 - 50.0 * (1 - np.exp(-3 * platform_df['rank_pct']))
        
        # 月票分（更保守）
        tickets = platform_df['monthly_tickets']
        platform_df['ticket_score'] = np.where(
            tickets < 100, 55.0 + tickets * 0.05,
            np.where(
                tickets < 500, 60.0 + (tickets - 100) * 0.008,
                np.where(
                    tickets < 2000, 64.0 + (tickets - 500) * 0.004,
                    np.where(
                        tickets < 10000, 70.0 + (tickets - 2000) * 0.001,
                        78.0 + np.minimum(15, (tickets - 10000) * 0.0001)
                    )
                )
            )
        )
        
        df.loc[mask, 'rank_score'] = platform_df['rank_score']
        df.loc[mask, 'ticket_score'] = platform_df['ticket_score']
        df.loc[mask, 'rank'] = platform_df['rank']
    
    # 辅助维度
    df['inter_bonus'] = np.minimum(2.0, np.log1p(df['total_recommend'] / 50000) * 0.5)
    df['wc_bonus'] = np.minimum(1.5, np.log1p(df['word_count'] / 300000) * 0.3)
    
    # 题材加成
    HOT_GENRES = ['玄幻', '奇幻', '仙侠', '诸天无限', '都市', '游戏', '现代言情']
    df['cat_bonus'] = df['category'].apply(
        lambda x: 0.5 if any(k in str(x) for k in HOT_GENRES) else 0.0
    )
    
    # 综合评分
    df['ip_score'] = (
        df['rank_score'] * 0.5 +
        df['ticket_score'] * 0.3 +
        df['inter_bonus'] +
        df['wc_bonus'] +
        df['cat_bonus']
    )
    
    # 完结衰减
    df['ip_score'] = np.where(
        df['status'].str.contains('完', na=False),
        df['ip_score'] * 0.95,
        df['ip_score']
    )
    
    df['ip_score'] = df['ip_score'].clip(45.0, 99.5)
    
    # 等级
    def score_to_grade(score):
        if score >= 90: return 'S'
        elif score >= 80: return 'A'
        elif score >= 70: return 'B'
        elif score >= 60: return 'C'
        else: return 'D'
    
    df['ip_grade'] = df['ip_score'].apply(score_to_grade)
    
    return df

df = compute_ip_score(df)

# 等级分布
print(f"\n   等级分布:")
grade_dist = df['ip_grade'].value_counts()
for grade in ['S', 'A', 'B', 'C', 'D']:
    count = grade_dist.get(grade, 0)
    pct = count / len(df) * 100
    print(f"   {grade}级: {count:4d} ({pct:5.1f}%)")

# ================================================================
#  3. 月票预测模型（使用实际转化率）
# ================================================================

print("\n【步骤3】训练月票预测模型...")

# 去重
df_unique = df.sort_values(['year', 'month'], ascending=[False, False])
df_unique = df_unique.drop_duplicates(subset=['title', 'author'], keep='first')

# 按平台分别训练
ticket_models = {}

for platform in ['Qidian', 'Zongheng']:
    platform_df = df_unique[df_unique['platform'] == platform]
    
    if len(platform_df) < 10:
        continue
    
    # 特征：字数、总推荐、转化率
    X = platform_df[['word_count', 'total_recommend', 'ticket_ratio']].values
    y = platform_df['monthly_tickets'].values
    
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=8,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X, y)
    
    y_pred = model.predict(X)
    mae = mean_absolute_error(y, y_pred)
    
    # 存储模型和转化率统计
    ticket_models[platform] = {
        'model': model,
        'median_ratio': platform_df['ticket_ratio'].median(),
        'mean_ratio': platform_df['ticket_ratio'].mean(),
        'mae': mae
    }
    
    print(f"   {platform}: MAE={mae:.0f}, 中位转化率={platform_df['ticket_ratio'].median():.4f}")

# ================================================================
#  4. IP评分预测模型
# ================================================================

print("\n【步骤4】训练IP评分预测模型...")

feature_cols = ['word_count', 'total_recommend', 'ticket_ratio']
for col in feature_cols:
    df_unique[col] = pd.to_numeric(df_unique[col], errors='coerce').fillna(0)

df_unique = df_unique.replace([np.inf, -np.inf], 0)

X_ip = df_unique[feature_cols].values
y_ip = df_unique['ip_score'].values

ip_model = RandomForestRegressor(
    n_estimators=200,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
ip_model.fit(X_ip, y_ip)

y_ip_pred = ip_model.predict(X_ip)
ip_rmse = np.sqrt(mean_squared_error(y_ip, y_ip_pred))
ip_mae = mean_absolute_error(y_ip, y_ip_pred)

print(f"   IP评分RMSE: {ip_rmse:.2f}")
print(f"   IP评分MAE: {ip_mae:.2f}")

# ================================================================
#  5. 保存模型
# ================================================================

print("\n【步骤5】保存Model J Oracle v5...")

model_v5 = {
    'ip_model': ip_model,
    'ticket_models': ticket_models,
    'features': feature_cols,
    'metrics': {
        'ip_rmse': ip_rmse,
        'ip_mae': ip_mae
    },
    'version': 'Model_J_Oracle_v5.0_Final',
    'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
    'improvements': [
        '使用实际转化率预测月票',
        '按平台分别训练月票模型',
        'IP评分基于排名计算',
        '更保守的评分映射'
    ],
    'grade_distribution': grade_dist.to_dict(),
    'platform_stats': {
        platform: {
            'median_ratio': data['median_ratio'],
            'mean_ratio': data['mean_ratio'],
            'mae': data['mae']
        }
        for platform, data in ticket_models.items()
    }
}

save_path = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/model_j_oracle_v5.pkl'
os.makedirs(os.path.dirname(save_path), exist_ok=True)
joblib.dump(model_v5, save_path)
print(f"   模型已保存: {save_path}")

# ================================================================
#  6. 显示Top书籍
# ================================================================

print("\n" + "=" * 70)
print("Top 20 IP评分")
print("=" * 70)

top20 = df_unique.nlargest(20, 'ip_score')
for _, row in top20.iterrows():
    print(f"{row['ip_score']:5.1f}分 {row['ip_grade']}级 | "
          f"月票:{int(row['monthly_tickets']):6d} | "
          f"{row['title'][:20]}")

# ================================================================
#  7. 总结
# ================================================================

print("\n" + "=" * 70)
print("Model J Oracle v5 训练完成!")
print("=" * 70)
print(f"""
关键改进:
1. 月票预测使用实际转化率
   - 起点: 中位转化率 {ticket_models.get('Qidian', {}).get('median_ratio', 0):.4f}
   - 纵横: 中位转化率 {ticket_models.get('Zongheng', {}).get('median_ratio', 0):.4f}

2. IP评分基于排名计算
   - 排名分占50%
   - 月票分占30%
   
3. 性能指标
   - IP评分MAE: {ip_mae:.2f}
""")

print("=" * 70)
