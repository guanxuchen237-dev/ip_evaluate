"""
模糊搜索书籍排名
"""
import pymysql
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend')

from train_model_j_oracle import IPGradingSystem

# 数据库配置
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

print("=" * 60)
print("模糊搜索书籍")
print("=" * 60)

# 获取数据
conn = pymysql.connect(**ZONGHENG_CONFIG)
df = pd.read_sql("""
    SELECT title, author, category, status, word_count,
           total_click, total_rec, monthly_ticket, fan_count,
           year, month
    FROM zongheng_book_ranks
    WHERE year >= 2023
""", conn)
conn.close()

# 模糊搜索
search_keywords = ['离婚', '惊艳', '明婳']

print("\n搜索关键词:", search_keywords)
print("-" * 60)

for keyword in search_keywords:
    matches = df[df['title'].str.contains(keyword, na=False, case=False)]
    if len(matches) > 0:
        print(f"\n包含'{keyword}'的书籍:")
        for _, row in matches.drop_duplicates(subset=['title']).head(5).iterrows():
            print(f"  - {row['title']} | {row['author']}")

# 搜索作者
print("\n" + "-" * 60)
author_matches = df[df['author'].str.contains('明婳', na=False)]
if len(author_matches) > 0:
    print(f"\n作者'明婳'的作品:")
    for _, row in author_matches.drop_duplicates(subset=['title']).iterrows():
        print(f"  - {row['title']} | {row['author']} | {row['category']}")

# 计算评分并排名
df['monthly_tickets'] = pd.to_numeric(df['monthly_ticket'], errors='coerce').fillna(0)
df['adjusted_tickets'] = df['monthly_tickets'] * 8.0

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
df['inter_bonus'] = np.minimum(1.0, np.log1p(df['total_rec'].fillna(0) / 100000) * 0.5)
df['wc_bonus'] = np.minimum(0.5, np.log1p(df['word_count'].fillna(0) / 500000) * 0.3)
df['ip_score'] = df['ticket_score'] + df['inter_bonus'] + df['wc_bonus']
df['ip_score'] = df['ip_score'].clip(45.0, 99.5)
df['ip_grade'] = df['ip_score'].apply(IPGradingSystem.score_to_grade)

# 去重排名
df_unique = df.sort_values(['year', 'month'], ascending=[False, False])
df_unique = df_unique.drop_duplicates(subset=['title', 'author'])
df_unique = df_unique.sort_values('ip_score', ascending=False).reset_index(drop=True)
df_unique['rank'] = range(1, len(df_unique) + 1)

# 如果找到目标书，显示排名
target = df_unique[df_unique['title'].str.contains('离婚', na=False)]
if len(target) > 0:
    print("\n" + "=" * 60)
    print("📊 找到目标书籍排名")
    print("=" * 60)
    row = target.iloc[0]
    print(f"\n📖 《{row['title']}》")
    print(f"   作者: {row['author']}")
    print(f"   排名: 第 {int(row['rank'])} 名 / 共 {len(df_unique)} 本")
    print(f"   IP评分: {row['ip_score']:.1f}")
    print(f"   IP等级: {row['ip_grade']}")

print("\n" + "=" * 60)
print("搜索完成!")
print("=" * 60)
