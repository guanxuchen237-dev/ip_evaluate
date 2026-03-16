"""
查询书籍排名
"""
import pymysql
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend')

from train_model_j_oracle import OracleScoreIntegrator, IPGradingSystem

# 数据库配置
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

print("=" * 60)
print("查询书籍排名")
print("=" * 60)

# 目标书籍
target_title = '离婚后她惊艳了世界'
target_author = '明婳'

# 获取纵横数据
try:
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    df = pd.read_sql("""
        SELECT title, author, category, status, word_count,
               total_click, total_rec, monthly_ticket, fan_count,
               year, month
        FROM zongheng_book_ranks
        WHERE year >= 2023
    """, conn)
    conn.close()
    print(f"\n✅ 获取纵横数据: {len(df)} 条")
except Exception as e:
    print(f"❌ 数据库错误: {e}")
    exit(1)

# 计算预言机评分
print("\n计算预言机评分...")
integrator = OracleScoreIntegrator()

df['monthly_tickets'] = pd.to_numeric(df['monthly_ticket'], errors='coerce').fillna(0)
df['word_count'] = pd.to_numeric(df['word_count'], errors='coerce').fillna(0)
df['total_click'] = pd.to_numeric(df['total_click'], errors='coerce').fillna(0)
df['total_rec'] = pd.to_numeric(df['total_rec'], errors='coerce').fillna(0)

# 平台缩放
df['adjusted_tickets'] = df['monthly_tickets'] * 8.0

# 月票锚定分
def ticket_to_score(tickets):
    if tickets <= 0:
        return 55.0
    if tickets < 100:
        return 55.0 + tickets * 0.1
    elif tickets < 1000:
        return 65.0 + (tickets - 100) * 0.015
    elif tickets < 10000:
        return 78.5 + (tickets - 1000) * 0.001
    else:
        return min(95.0, 87.5 + (tickets - 10000) * 0.0001)

df['ticket_score'] = df['adjusted_tickets'].apply(ticket_to_score)

# 辅助维度
df['inter_bonus'] = np.minimum(1.0, np.log1p(df['total_rec'] / 100000) * 0.5)
df['wc_bonus'] = np.minimum(0.5, np.log1p(df['word_count'] / 500000) * 0.3)

# 题材加成
df['cat_bonus'] = df['category'].apply(
    lambda x: 0.5 if any(k in str(x) for k in ['玄幻', '奇幻', '仙侠']) else 0.0
)

# 综合评分
df['ip_score'] = df['ticket_score'] + df['inter_bonus'] + df['wc_bonus'] + df['cat_bonus']

# 完结衰减
df['ip_score'] = np.where(
    df['status'].str.contains('完', na=False),
    df['ip_score'] * 0.90,
    df['ip_score']
)
df['ip_score'] = df['ip_score'].clip(45.0, 99.5)

# 等级
df['ip_grade'] = df['ip_score'].apply(IPGradingSystem.score_to_grade)

# 去重，取每本书最新数据
df_unique = df.sort_values(['year', 'month'], ascending=[False, False])
df_unique = df_unique.drop_duplicates(subset=['title', 'author'])

print(f"去重后书籍数: {len(df_unique)}")

# 计算排名
df_unique = df_unique.sort_values('ip_score', ascending=False).reset_index(drop=True)
df_unique['rank'] = range(1, len(df_unique) + 1)

# 找目标书籍
target_book = df_unique[
    (df_unique['title'].str.contains(target_title, na=False)) & 
    (df_unique['author'].str.contains(target_author, na=False))
]

print("\n" + "=" * 60)
print("📊 排名结果")
print("=" * 60)

if len(target_book) > 0:
    row = target_book.iloc[0]
    rank = int(row['rank'])
    total = len(df_unique)
    percentile = (1 - rank / total) * 100
    
    print(f"\n📖 《{row['title']}》")
    print(f"   作者: {row['author']}")
    print(f"   题材: {row['category']}")
    print(f"   字数: {row['word_count']/10000:.1f}万字")
    print(f"   月票: {int(row['monthly_tickets'])}")
    
    print(f"\n🏆 排名信息:")
    print(f"   总排名: 第 {rank} 名 / 共 {total} 本书")
    print(f"   百分位: Top {percentile:.1f}%")
    print(f"   IP评分: {row['ip_score']:.1f}")
    print(f"   IP等级: {row['ip_grade']}")
    
    # 同题材排名
    df_cat = df_unique[df_unique['category'] == row['category']]
    cat_rank = df_cat['rank'].rank(method='min').loc[row.name] if row.name in df_cat.index else 'N/A'
    cat_total = len(df_cat)
    print(f"\n📚 同题材排名:")
    print(f"   题材: {row['category']}")
    print(f"   排名: 第 {int(cat_rank) if isinstance(cat_rank, (int, float)) else cat_rank} 名 / 共 {cat_total} 本")
else:
    print(f"\n❌ 未找到《{target_title}》- {target_author}")

# 显示Top 10
print("\n" + "=" * 60)
print("🏆 纵横平台 Top 10")
print("=" * 60)

top10 = df_unique.head(10)
for i, row in top10.iterrows():
    print(f"{row['rank']:3d}. {row['title'][:20]:20s} | {row['author'][:8]:8s} | {row['ip_score']:5.1f}分 | {row['ip_grade']}级")

# 等级分布
print("\n" + "=" * 60)
print("📊 等级分布")
print("=" * 60)

grade_dist = df_unique['ip_grade'].value_counts()
for grade in ['S', 'A', 'B', 'C', 'D']:
    count = grade_dist.get(grade, 0)
    pct = count / len(df_unique) * 100
    bar = '█' * int(pct / 2)
    print(f"{grade}级: {count:5d} ({pct:5.1f}%) {bar}")

print("\n" + "=" * 60)
print("查询完成!")
print("=" * 60)
