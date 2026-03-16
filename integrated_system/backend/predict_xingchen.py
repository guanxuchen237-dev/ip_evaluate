"""
查询《星辰之主》历史数据并预测
"""
import pymysql
import pandas as pd
import numpy as np

# 数据库配置
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'qidian_data', 'charset': 'utf8mb4'
}

print("=" * 70)
print("《星辰之主》历史数据分析与预测")
print("=" * 70)

# ================================================================
#  1. 查询历史数据
# ================================================================

print("\n【步骤1】查询历史数据...")

try:
    conn = pymysql.connect(**QIDIAN_CONFIG)
    
    query = """
    SELECT 
        year, month, title, author, category, word_count,
        monthly_ticket_count, rank_on_list, recommendation_count,
        collection_count, is_vip, is_sign
    FROM novel_monthly_stats
    WHERE title LIKE '%星辰之主%'
    ORDER BY year, month
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"   找到 {len(df)} 条历史记录")
    
    if len(df) > 0:
        print(f"\n历史数据:")
        print(f"   时间范围: {int(df['year'].min())}年{int(df['month'].min())}月 - {int(df['year'].max())}年{int(df['month'].max())}月")
        
        # 显示最近几条记录
        print(f"\n最近记录:")
        for _, row in df.tail(6).iterrows():
            rank = row['rank_on_list'] if pd.notna(row['rank_on_list']) else 0
            print(f"   {int(row['year'])}年{int(row['month']):02d}月 | "
                  f"排名{int(rank):3d} | "
                  f"月票{int(row['monthly_ticket_count']):5d} | "
                  f"推荐{int(row['recommendation_count']):6d} | "
                  f"字数{row['word_count']/10000:.1f}万")
        
        # 最新数据
        latest = df.iloc[-1]
        latest_rank = int(latest['rank_on_list']) if pd.notna(latest['rank_on_list']) else 0
        latest_tickets = int(latest['monthly_ticket_count'])
        
except Exception as e:
    print(f"   查询错误: {e}")
    df = pd.DataFrame()
    latest_rank = 0
    latest_tickets = 0

# ================================================================
#  2. 当前数据
# ================================================================

print(f"\n{'='*70}")
print("当前数据（用户提供）")
print("=" * 70)

current_data = {
    'title': '星辰之主',
    'platform': 'Qidian',
    'category': '科幻·星空·未来·高武',
    'status': '连载中',
    'word_count': 8238000,  # 823.8万字
    'total_click': 17455000,  # 1745.5万点击
    'total_recommend': 3582000,  # 358.2万推荐
    'weekly_recommend': 4918,
    'chapter_count': 1298,
    'is_signed': 1
}

print(f"   书名: 《{current_data['title']}》")
print(f"   平台: {current_data['platform']}")
print(f"   题材: {current_data['category']}")
print(f"   字数: {current_data['word_count']/10000:.1f}万")
print(f"   总点击: {current_data['total_click']/10000:.1f}万")
print(f"   总推荐: {current_data['total_recommend']/10000:.1f}万")
print(f"   周推荐: {current_data['weekly_recommend']}")
print(f"   章节数: {current_data['chapter_count']}")

# ================================================================
#  3. IP评估
# ================================================================

print(f"\n{'='*70}")
print("IP评估")
print("=" * 70)

# 如果有历史数据，使用历史排名
if len(df) > 0 and latest_rank > 0:
    rank = latest_rank
    monthly_tickets = latest_tickets
    print(f"\n使用历史排名数据:")
else:
    # 基于周推荐估算排名
    # 起点周推荐4918 → 大约排名100-200
    rank = 150  # 估计
    monthly_tickets = current_data['weekly_recommend'] * 3  # 估计
    print(f"\n基于周推荐估算排名:")

print(f"   排名: 第{rank}名")
print(f"   月票: {monthly_tickets}")

# 计算IP评分
total_books = 500  # 起点有月票的书约500本
rank_pct = (rank - 1) / (total_books - 1)

# 基础分
ip_score = 99.0 - 49.0 * rank_pct

# 字数加成（823.8万字，超级大作）
word_count = current_data['word_count']
wc_bonus = min(5.0, np.log1p(word_count / 500000) * 2.0)  # 字数加成上限提高
ip_score += wc_bonus

# 题材加成（科幻，相对小众）
cat_bonus = 0.3
ip_score += cat_bonus

# 点击加成（1745.5万，超高）
total_click = current_data['total_click']
click_bonus = min(3.0, np.log1p(total_click / 1000000) * 1.5)
ip_score += click_bonus

# 推荐加成（358.2万，超高）
total_recommend = current_data['total_recommend']
rec_bonus = min(3.0, np.log1p(total_recommend / 100000) * 0.5)
ip_score += rec_bonus

# 月票加成
if monthly_tickets >= 50000:
    ticket_bonus = 5.0
elif monthly_tickets >= 20000:
    ticket_bonus = 3.0
elif monthly_tickets >= 10000:
    ticket_bonus = 2.0
elif monthly_tickets >= 5000:
    ticket_bonus = 1.0
else:
    ticket_bonus = 0

ip_score += ticket_bonus

ip_score = np.clip(ip_score, 45.0, 99.5)

def score_to_grade(score):
    if score >= 90: return 'S'
    elif score >= 80: return 'A'
    elif score >= 70: return 'B'
    elif score >= 60: return 'C'
    else: return 'D'

ip_grade = score_to_grade(ip_score)

print(f"\n评分计算:")
print(f"   排名百分位: 前{rank_pct*100:.1f}%")
print(f"   基础分: {99.0 - 49.0 * rank_pct:.1f}")
print(f"   字数加成: +{wc_bonus:.1f}（823.8万字超级大作）")
print(f"   题材加成: +{cat_bonus:.1f}")
print(f"   点击加成: +{click_bonus:.1f}（1745.5万点击）")
print(f"   推荐加成: +{rec_bonus:.1f}（358.2万推荐）")
print(f"   月票加成: +{ticket_bonus:.1f}")
print(f"   IP评分: {ip_score:.1f}")
print(f"   IP等级: {ip_grade}")

# 月票区间
if rank <= 10:
    ticket_range = (30000, 100000)
elif rank <= 50:
    ticket_range = (10000, 50000)
elif rank <= 100:
    ticket_range = (5000, 20000)
elif rank <= 200:
    ticket_range = (2000, 10000)
else:
    ticket_range = (500, 5000)

print(f"\n月票估算:")
print(f"   排名{rank}对应区间: [{ticket_range[0]}, {ticket_range[1]}]")
if len(df) > 0:
    print(f"   实际月票: {monthly_tickets}")
    print(f"   是否在区间内: {'✓ 是' if ticket_range[0] <= monthly_tickets <= ticket_range[1] else '✗ 否'}")

# ================================================================
#  4. 综合评估
# ================================================================

print(f"\n{'='*70}")
print("综合评估")
print("=" * 70)

# 好书判定
if ip_grade in ['S', 'A']:
    verdict = "⭐⭐⭐⭐⭐ 优质好书"
elif ip_grade == 'B':
    verdict = "⭐⭐⭐⭐ 良好书"
elif ip_grade == 'C':
    verdict = "⭐⭐⭐ 普通水平"
else:
    verdict = "⭐⭐ 待观察"

print(f"\n是否好书:")
print(f"   {verdict}")

print(f"\n商业价值:")
print(f"   ✓ 字数超级充足（{current_data['word_count']/10000:.0f}万字，超级大作）")
print(f"   ✓ 点击量超高（{current_data['total_click']/10000:.0f}万）")
print(f"   ✓ 推荐数超高（{current_data['total_recommend']/10000:.0f}万）")
print(f"   ✓ 章节数多（{current_data['chapter_count']}章）")
print(f"   △ 科幻题材相对小众")

print(f"\n投资建议:")
if ip_grade in ['S', 'A']:
    print(f"   强烈推荐关注，IP价值高")
elif ip_grade == 'B':
    print(f"   推荐关注，IP价值良好")
else:
    print(f"   可关注，IP价值一般")

print("\n" + "=" * 70)
print("分析完成!")
print("=" * 70)
