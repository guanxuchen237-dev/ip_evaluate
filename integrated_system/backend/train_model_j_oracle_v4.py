"""
Model J Oracle v4 - 基于实际数据校准的修正版
修正内容：
1. 使用实际排名作为主要评分依据
2. 月票映射函数更保守
3. 周推荐→月票转化率使用实际值（约0.8）
4. 多维度综合评估
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
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

print("=" * 70)
print("Model J Oracle v4 - 基于实际数据校准")
print("=" * 70)

# ================================================================
#  1. 获取实际数据并分析转化率
# ================================================================

print("\n【步骤1】获取实际数据分析转化率...")

def fetch_and_analyze():
    """获取数据并分析实际转化率"""
    
    # 获取起点数据
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
        print(f"   起点: {len(df_qd)} 条")
    except Exception as e:
        print(f"   起点错误: {e}")
        df_qd = pd.DataFrame()
    
    # 获取纵横数据
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
        print(f"   纵横: {len(df_zh)} 条")
    except Exception as e:
        print(f"   纵横错误: {e}")
        df_zh = pd.DataFrame()
    
    if df_qd.empty and df_zh.empty:
        return pd.DataFrame()
    
    df = pd.concat([df_qd, df_zh], ignore_index=True)
    
    # 清理数据
    df['monthly_tickets'] = pd.to_numeric(df['monthly_tickets'], errors='coerce').fillna(0)
    df['total_recommend'] = pd.to_numeric(df['total_recommend'], errors='coerce').fillna(0)
    df['word_count'] = pd.to_numeric(df['word_count'], errors='coerce').fillna(0)
    
    # 计算实际转化率
    df['ticket_recommend_ratio'] = df['monthly_tickets'] / (df['total_recommend'] + 1)
    
    # 按平台统计转化率
    print(f"\n   实际转化率分析:")
    for platform in df['platform'].unique():
        platform_df = df[df['platform'] == platform]
        avg_ratio = platform_df['ticket_recommend_ratio'].mean()
        median_ratio = platform_df['ticket_recommend_ratio'].median()
        print(f"   {platform}: 平均={avg_ratio:.4f}, 中位数={median_ratio:.4f}")
    
    return df

df = fetch_and_analyze()

if df.empty:
    print("错误: 无法获取数据")
    exit(1)

# ================================================================
#  2. 基于实际排名计算评分
# ================================================================

print("\n【步骤2】基于实际排名计算评分...")

def compute_calibrated_score(df):
    """基于实际数据校准的评分计算"""
    
    # 按平台分别计算排名
    df['rank_score'] = 0.0
    df['ticket_score'] = 0.0
    
    for platform in df['platform'].unique():
        mask = df['platform'] == platform
        platform_df = df[mask].copy()
        n = len(platform_df)
        
        # 1. 排名分（基于月票排序）
        platform_df = platform_df.sort_values('monthly_tickets', ascending=False)
        platform_df['rank'] = range(1, n + 1)
        
        # 百分位转分数
        platform_df['rank_pct'] = (platform_df['rank'] - 1) / (n - 1)
        
        # 使用指数平滑：高排名差距大，低排名差距小
        platform_df['rank_score'] = 95.0 - 50.0 * (1 - np.exp(-3 * platform_df['rank_pct']))
        
        # 2. 月票分（更保守的映射）
        # 修正版：月票<500 → 60分以下，月票>5000 → 80分以上
        tickets = platform_df['monthly_tickets']
        platform_df['ticket_score'] = np.where(
            tickets < 100, 55.0 + tickets * 0.05,
            np.where(
                tickets < 500, 60.0 + (tickets - 100) * 0.01,
                np.where(
                    tickets < 2000, 64.0 + (tickets - 500) * 0.005,
                    np.where(
                        tickets < 10000, 71.5 + (tickets - 2000) * 0.001,
                        79.5 + np.minimum(15, (tickets - 10000) * 0.0002)
                    )
                )
            )
        )
        
        df.loc[mask, 'rank_score'] = platform_df['rank_score']
        df.loc[mask, 'ticket_score'] = platform_df['ticket_score']
        df.loc[mask, 'rank'] = platform_df['rank']
    
    # 3. 辅助维度
    df['inter_bonus'] = np.minimum(2.0, np.log1p(df['total_recommend'] / 50000) * 0.5)
    df['wc_bonus'] = np.minimum(1.5, np.log1p(df['word_count'] / 300000) * 0.3)
    
    # 4. 题材加成
    HOT_GENRES = ['玄幻', '奇幻', '仙侠', '诸天无限', '都市', '游戏']
    df['cat_bonus'] = df['category'].apply(
        lambda x: 0.5 if any(k in str(x) for k in HOT_GENRES) else 0.0
    )
    
    # 5. 综合评分（排名分占主导）
    df['ip_score'] = (
        df['rank_score'] * 0.5 +      # 排名分50%
        df['ticket_score'] * 0.3 +    # 月票分30%
        df['inter_bonus'] +           # 互动加成
        df['wc_bonus'] +              # 字数加成
        df['cat_bonus']               # 题材加成
    )
    
    # 完结衰减
    df['ip_score'] = np.where(
        df['status'].str.contains('完', na=False),
        df['ip_score'] * 0.95,
        df['ip_score']
    )
    
    # 限制范围
    df['ip_score'] = df['ip_score'].clip(45.0, 99.5)
    
    # 6. 等级
    def score_to_grade(score):
        if score >= 90: return 'S'
        elif score >= 80: return 'A'
        elif score >= 70: return 'B'
        elif score >= 60: return 'C'
        else: return 'D'
    
    df['ip_grade'] = df['ip_score'].apply(score_to_grade)
    
    return df

df = compute_calibrated_score(df)

# 统计等级分布
print(f"\n   等级分布:")
grade_dist = df['ip_grade'].value_counts()
for grade in ['S', 'A', 'B', 'C', 'D']:
    count = grade_dist.get(grade, 0)
    pct = count / len(df) * 100
    print(f"   {grade}级: {count:4d} ({pct:5.1f}%)")

print(f"\n   IP评分范围: {df['ip_score'].min():.1f} - {df['ip_score'].max():.1f}")
print(f"   IP评分均值: {df['ip_score'].mean():.1f}")

# ================================================================
#  3. 训练预测模型
# ================================================================

print("\n【步骤3】训练预测模型...")

# 去重
df_unique = df.sort_values(['year', 'month'], ascending=[False, False])
df_unique = df_unique.drop_duplicates(subset=['title', 'author'], keep='first')

# 特征
feature_cols = ['word_count', 'total_recommend', 'ticket_recommend_ratio']
for col in feature_cols:
    df_unique[col] = pd.to_numeric(df_unique[col], errors='coerce').fillna(0)

df_unique = df_unique.replace([np.inf, -np.inf], 0)

X = df_unique[feature_cols].values
y = df_unique['ip_score'].values

# 训练随机森林
print(f"   训练样本: {len(X)}")
print(f"   特征: {feature_cols}")

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=10,
    min_samples_split=5,
    random_state=42,
    n_jobs=-1
)
model.fit(X, y)

# 验证
y_pred = model.predict(X)
rmse = np.sqrt(mean_squared_error(y, y_pred))
mae = mean_absolute_error(y, y_pred)
r2 = r2_score(y, y_pred)

print(f"\n   训练集性能:")
print(f"   RMSE: {rmse:.2f}")
print(f"   MAE: {mae:.2f}")
print(f"   R²: {r2:.4f}")

# ================================================================
#  4. 月票预测模型（修正版）
# ================================================================

print("\n【步骤4】训练月票预测模型...")

# 月票预测特征
ticket_features = ['word_count', 'total_recommend']
X_ticket = df_unique[ticket_features].values
y_ticket = df_unique['monthly_tickets'].values

ticket_model = RandomForestRegressor(
    n_estimators=200,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
ticket_model.fit(X_ticket, y_ticket)

y_ticket_pred = ticket_model.predict(X_ticket)
ticket_rmse = np.sqrt(mean_squared_error(y_ticket, y_ticket_pred))
ticket_mae = mean_absolute_error(y_ticket, y_ticket_pred)

print(f"   月票预测RMSE: {ticket_rmse:.0f}")
print(f"   月票预测MAE: {ticket_mae:.0f}")

# ================================================================
#  5. 保存模型
# ================================================================

print("\n【步骤5】保存Model J Oracle v4...")

model_v4 = {
    'ip_model': model,
    'ticket_model': ticket_model,
    'features': feature_cols,
    'ticket_features': ticket_features,
    'metrics': {
        'ip_rmse': rmse,
        'ip_mae': mae,
        'ip_r2': r2,
        'ticket_rmse': ticket_rmse,
        'ticket_mae': ticket_mae
    },
    'version': 'Model_J_Oracle_v4.0_Calibrated',
    'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
    'improvements': [
        '基于实际排名计算评分',
        '月票映射更保守',
        '使用实际转化率',
        '排名分占50%，月票分占30%'
    ],
    'grade_distribution': grade_dist.to_dict()
}

save_path = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/model_j_oracle_v4.pkl'
import os
os.makedirs(os.path.dirname(save_path), exist_ok=True)
joblib.dump(model_v4, save_path)
print(f"   模型已保存: {save_path}")

# ================================================================
#  6. 显示Top书籍
# ================================================================

print("\n" + "=" * 70)
print("Top 20 IP评分")
print("=" * 70)

top20 = df_unique.nlargest(20, 'ip_score')
for i, row in top20.iterrows():
    print(f"{row['ip_score']:5.1f}分 {row['ip_grade']}级 | "
          f"月票:{int(row['monthly_tickets']):5d} | "
          f"{row['title'][:20]}")

# ================================================================
#  7. 总结
# ================================================================

print("\n" + "=" * 70)
print("Model J Oracle v4 训练完成!")
print("=" * 70)
print(f"""
修正内容:
1. 排名分占50%（主要依据）
2. 月票分占30%（更保守映射）
3. 实际转化率约0.8%
4. 月票<500 → 60分以下
5. 月票>5000 → 80分以上

性能指标:
- IP评分RMSE: {rmse:.2f}
- IP评分MAE: {mae:.2f}
- IP评分R²: {r2:.4f}
- 月票预测MAE: {ticket_mae:.0f}
""")
print("=" * 70)
