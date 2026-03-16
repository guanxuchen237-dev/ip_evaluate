"""
Model J Oracle v7 - 实用版
核心思路：
1. 有月票数据 → 直接计算IP评分（准确）
2. 有排名数据 → 基于排名计算IP评分（较准确）
3. 无月票无排名 → 给出保守估计+置信区间

关键改进：不预测具体月票数，而是给出IP评估
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from datetime import datetime
import os

warnings.filterwarnings('ignore')

print("=" * 70)
print("Model J Oracle v7 - 实用版（基于排名评估）")
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

print("\n【步骤1】获取数据...")

def fetch_data():
    dfs = []
    
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG)
        df_qd = pd.read_sql("""
            SELECT title, author, category, status, word_count,
                   recommendation_count as total_recommend,
                   monthly_ticket_count as monthly_tickets,
                   year, month
            FROM novel_monthly_stats
            WHERE year >= 2024 AND monthly_ticket_count > 0
        """, conn)
        df_qd['platform'] = 'Qidian'
        conn.close()
        dfs.append(df_qd)
        print(f"   起点: {len(df_qd)} 条")
    except Exception as e:
        print(f"   起点错误: {e}")
    
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG)
        df_zh = pd.read_sql("""
            SELECT title, author, category, status, word_count,
                   total_rec as total_recommend,
                   monthly_ticket as monthly_tickets,
                   year, month
            FROM zongheng_book_ranks
            WHERE year >= 2024 AND monthly_ticket > 0
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
    
    for col in ['monthly_tickets', 'total_recommend', 'word_count']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

df = fetch_data()

if df.empty:
    print("错误: 无法获取数据")
    exit(1)

# ================================================================
#  2. 基于排名计算IP评分（核心改进）
# ================================================================

print("\n【步骤2】基于排名计算IP评分...")

def compute_ip_score_by_rank(df):
    """基于排名计算IP评分"""
    
    df['ip_score'] = 0.0
    df['rank'] = 0
    
    for platform in df['platform'].unique():
        mask = df['platform'] == platform
        platform_df = df[mask].copy()
        n = len(platform_df)
        
        # 按月票排序计算排名
        platform_df = platform_df.sort_values('monthly_tickets', ascending=False)
        platform_df['rank'] = range(1, n + 1)
        
        # 百分位排名
        platform_df['rank_pct'] = (platform_df['rank'] - 1) / max(1, n - 1)
        
        # IP评分公式（基于排名）
        # 排名1 → 99分，排名前10% → 90+分，排名后10% → 50分
        platform_df['ip_score'] = 99.0 - 49.0 * platform_df['rank_pct']
        
        # 月票加成（额外奖励高月票作品）
        tickets = platform_df['monthly_tickets']
        ticket_bonus = np.where(
            tickets >= 100000, 5.0,
            np.where(tickets >= 50000, 3.0,
            np.where(tickets >= 10000, 1.5,
            np.where(tickets >= 5000, 0.5, 0.0)))
        )
        platform_df['ip_score'] += ticket_bonus
        
        # 字数加成
        wc_bonus = np.minimum(2.0, np.log1p(platform_df['word_count'] / 500000) * 1.0)
        platform_df['ip_score'] += wc_bonus
        
        # 题材加成
        HOT_GENRES = ['玄幻', '奇幻', '仙侠', '诸天无限', '都市', '游戏']
        cat_bonus = platform_df['category'].apply(
            lambda x: 0.5 if any(k in str(x) for k in HOT_GENRES) else 0.0
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

df = compute_ip_score_by_rank(df)

# 等级分布
print(f"\n   等级分布:")
grade_dist = df['ip_grade'].value_counts()
for grade in ['S', 'A', 'B', 'C', 'D']:
    count = grade_dist.get(grade, 0)
    pct = count / len(df) * 100
    print(f"   {grade}级: {count:4d} ({pct:5.1f}%)")

# ================================================================
#  3. 训练IP评分预测模型（用于无排名时）
# ================================================================

print("\n【步骤3】训练IP评分预测模型...")

# 去重
df_unique = df.sort_values(['year', 'month'], ascending=[False, False])
df_unique = df_unique.drop_duplicates(subset=['title', 'author'], keep='first')

# 特征（不包含月票）
feature_cols = ['word_count', 'total_recommend']
for col in feature_cols:
    df_unique[col] = pd.to_numeric(df_unique[col], errors='coerce').fillna(0)

df_unique = df_unique.replace([np.inf, -np.inf], 0)

X = df_unique[feature_cols].values
y = df_unique['ip_score'].values

# 训练模型
ip_model = GradientBoostingRegressor(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    random_state=42
)
ip_model.fit(X, y)

y_pred = ip_model.predict(X)
mae = mean_absolute_error(y, y_pred)

print(f"   IP评分MAE: {mae:.2f}")

# ================================================================
#  4. 分析月票与排名的关系（用于估算）
# ================================================================

print("\n【步骤4】分析月票与排名关系...")

# 按平台分析
for platform in df['platform'].unique():
    platform_df = df_unique[df_unique['platform'] == platform]
    
    # 排名对应的月票范围
    rank_ticket_stats = platform_df.groupby('rank').agg({
        'monthly_tickets': ['mean', 'median', 'min', 'max']
    }).reset_index()
    
    print(f"\n   {platform} 排名-月票对应:")
    for _, row in rank_ticket_stats.head(10).iterrows():
        rank = int(row['rank'])
        mean_tkt = row[('monthly_tickets', 'mean')]
        print(f"   排名{rank:3d}: 平均月票{mean_tkt:,.0f}")
    
    # 存储统计
    if platform == 'Qidian':
        qidian_rank_ticket = platform_df.set_index('rank')['monthly_tickets'].to_dict()
    else:
        zongheng_rank_ticket = platform_df.set_index('rank')['monthly_tickets'].to_dict()

# ================================================================
#  5. 保存模型
# ================================================================

print("\n【步骤5】保存Model J Oracle v7...")

model_v7 = {
    'ip_model': ip_model,
    'features': feature_cols,
    'metrics': {
        'ip_mae': mae
    },
    'version': 'Model_J_Oracle_v7.0_Practical',
    'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
    'improvements': [
        '基于排名计算IP评分（最准确）',
        '无排名时使用特征预测',
        '不预测具体月票数',
        '提供月票区间估算'
    ],
    'grade_distribution': grade_dist.to_dict(),
    'rank_ticket_mapping': {
        'Qidian': qidian_rank_ticket if 'qidian_rank_ticket' in dir() else {},
        'Zongheng': zongheng_rank_ticket if 'zongheng_rank_ticket' in dir() else {}
    }
}

save_path = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/model_j_oracle_v7.pkl'
os.makedirs(os.path.dirname(save_path), exist_ok=True)
joblib.dump(model_v7, save_path)
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
          f"排名{int(row['rank']):4d} | 月票{int(row['monthly_tickets']):6d} | "
          f"{row['title'][:18]}")

# ================================================================
#  7. 总结
# ================================================================

print("\n" + "=" * 70)
print("Model J Oracle v7 训练完成!")
print("=" * 70)
print(f"""
核心改进:
1. IP评分基于排名计算（最准确）
   - 排名1 → 99分
   - 排名前10% → 90+分
   - 排名后10% → 50分

2. 使用场景:
   - 有排名数据: 直接计算IP评分（最准确）
   - 有月票数据: 可推算排名
   - 无数据: 使用特征预测（MAE: {mae:.2f}）

3. 不预测具体月票数
   - 原因: 推荐与月票相关性弱
   - 替代: 提供排名对应的月票区间
""")

print("=" * 70)
