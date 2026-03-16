"""
查询《众仙俯首》历史数据并预测
"""
import pymysql
import pandas as pd
import numpy as np
import joblib
import xgboost as xgb
import jieba
from collections import Counter

# 数据库配置
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

print("=" * 70)
print("《众仙俯首》历史数据分析与预测")
print("=" * 70)

# ================================================================
#  1. 查询历史数据
# ================================================================

print("\n【步骤1】查询历史数据...")

try:
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    
    # 查询月度数据
    query = """
    SELECT 
        year, month, title, author, category, word_count,
        monthly_ticket, rank_num, total_rec, week_rec,
        total_click, fan_count, post_count, is_signed, status
    FROM zongheng_book_ranks
    WHERE title LIKE '%众仙俯首%'
    ORDER BY year, month
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"   找到 {len(df)} 条历史记录")
    
    if len(df) > 0:
        print(f"\n历史数据:")
        print(f"   时间范围: {df['year'].min()}年{df['month'].min()}月 - {df['year'].max()}年{df['month'].max()}月")
        
        # 显示最近几条记录
        print(f"\n最近记录:")
        for _, row in df.tail(6).iterrows():
            print(f"   {int(row['year'])}年{int(row['month']):02d}月 | "
                  f"排名{int(row['rank_num']):3d} | "
                  f"月票{int(row['monthly_ticket']):5d} | "
                  f"周推荐{int(row['week_rec']):4d} | "
                  f"字数{row['word_count']/10000:.1f}万")
        
        # 排名变化分析
        recent = df.tail(3)
        if len(recent) >= 2:
            latest = recent.iloc[-1]
            previous = recent.iloc[-2]
            
            rank_change = int(previous['rank_num']) - int(latest['rank_num'])
            ticket_change = int(latest['monthly_ticket']) - int(previous['monthly_ticket'])
            
            print(f"\n排名变化分析:")
            print(f"   上月排名: 第{int(previous['rank_num'])}名")
            print(f"   本月排名: 第{int(latest['rank_num'])}名")
            print(f"   排名变化: {'↑' if rank_change > 0 else '↓' if rank_change < 0 else '→'} {abs(rank_change)}名")
            print(f"   月票变化: {'+' if ticket_change > 0 else ''}{ticket_change}")
    else:
        print("   未找到历史数据")
        
except Exception as e:
    print(f"   查询错误: {e}")
    df = pd.DataFrame()

# ================================================================
#  2. 当前数据
# ================================================================

print(f"\n{'='*70}")
print("当前数据（用户提供）")
print("=" * 70)

current_data = {
    'title': '众仙俯首',
    'author': '未知',
    'platform': 'Zongheng',
    'category': '武侠仙侠',
    'status': '连载中',
    'word_count': 2677000,
    'total_click': 6420000,
    'total_recommend': 130000,
    'weekly_recommend': 2857,
    'chapter_count': 752,
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
#  3. 趋势预测
# ================================================================

print(f"\n{'='*70}")
print("趋势预测")
print("=" * 70)

if len(df) >= 3:
    # 计算趋势
    recent_3 = df.tail(3)
    
    avg_rank = recent_3['rank_num'].mean()
    avg_ticket = recent_3['monthly_ticket'].mean()
    avg_week_rec = recent_3['week_rec'].mean()
    
    # 排名趋势
    rank_trend = recent_3['rank_num'].values
    if rank_trend[0] > rank_trend[-1]:  # 排名数字变小 = 排名上升
        rank_trend_str = "↑ 上升"
    elif rank_trend[0] < rank_trend[-1]:
        rank_trend_str = "↓ 下降"
    else:
        rank_trend_str = "→ 稳定"
    
    # 月票趋势
    ticket_trend = recent_3['monthly_ticket'].values
    if ticket_trend[-1] > ticket_trend[0]:
        ticket_trend_str = "↑ 增长"
    elif ticket_trend[-1] < ticket_trend[0]:
        ticket_trend_str = "↓ 下降"
    else:
        ticket_trend_str = "→ 稳定"
    
    print(f"\n近3月趋势:")
    print(f"   排名趋势: {rank_trend_str}")
    print(f"   月票趋势: {ticket_trend_str}")
    print(f"   平均排名: {avg_rank:.0f}")
    print(f"   平均月票: {avg_ticket:.0f}")
    print(f"   平均周推荐: {avg_week_rec:.0f}")
    
    # 预测下月
    latest = df.iloc[-1]
    
    # 基于趋势预测
    if rank_trend[0] > rank_trend[-1]:
        predicted_rank = max(1, int(latest['rank_num']) - 5)
    else:
        predicted_rank = int(latest['rank_num']) + 5
    
    predicted_ticket = int(avg_ticket * 1.1)  # 假设增长10%
    
    print(f"\n下月预测:")
    print(f"   预测排名: 第{predicted_rank}名左右")
    print(f"   预测月票: {predicted_ticket}左右")

# ================================================================
#  4. IP评估
# ================================================================

print(f"\n{'='*70}")
print("IP评估")
print("=" * 70)

if len(df) > 0:
    latest = df.iloc[-1]
    rank = int(latest['rank_num'])
    monthly_ticket = int(latest['monthly_ticket'])
else:
    # 基于周推荐估算
    rank = 150  # 估计
    monthly_ticket = current_data['weekly_recommend'] * 2  # 估计

# 基于排名计算IP评分
total_books = 200  # 纵横有月票的书约200本
rank_pct = (rank - 1) / (total_books - 1)

ip_score = 99.0 - 49.0 * rank_pct

# 字数加成
wc_bonus = min(2.5, np.log1p(current_data['word_count'] / 500000) * 1.5)
ip_score += wc_bonus

# 题材加成
cat_bonus = 0.5  # 武侠仙侠
ip_score += cat_bonus

# 点击加成
click_bonus = min(2.0, np.log1p(current_data['total_click'] / 1000000) * 1.0)
ip_score += click_bonus

ip_score = np.clip(ip_score, 45.0, 99.5)

def score_to_grade(score):
    if score >= 90: return 'S'
    elif score >= 80: return 'A'
    elif score >= 70: return 'B'
    elif score >= 60: return 'C'
    else: return 'D'

ip_grade = score_to_grade(ip_score)

print(f"\n排名分析:")
print(f"   当前排名: 第{rank}名")
print(f"   百分位: 前{rank_pct*100:.1f}%")
print(f"   基础分: {99.0 - 49.0 * rank_pct:.1f}")
print(f"   字数加成: +{wc_bonus:.1f}")
print(f"   题材加成: +{cat_bonus:.1f}")
print(f"   点击加成: +{click_bonus:.1f}")
print(f"   IP评分: {ip_score:.1f}")
print(f"   IP等级: {ip_grade}")

# 月票区间
if rank <= 10:
    ticket_range = (10000, 50000)
elif rank <= 50:
    ticket_range = (3000, 15000)
elif rank <= 100:
    ticket_range = (1500, 8000)
elif rank <= 150:
    ticket_range = (800, 4000)
else:
    ticket_range = (400, 2000)

print(f"\n月票估算:")
print(f"   排名{rank}对应区间: [{ticket_range[0]}, {ticket_range[1]}]")
if len(df) > 0:
    print(f"   实际月票: {monthly_ticket}")
    print(f"   是否在区间内: {'✓ 是' if ticket_range[0] <= monthly_ticket <= ticket_range[1] else '✗ 否'}")

# ================================================================
#  5. 综合评估
# ================================================================

print(f"\n{'='*70}")
print("综合评估")
print("=" * 70)

# 好书判定
if ip_grade in ['S', 'A']:
    verdict = "⭐⭐⭐⭐⭐ 优质好书"
    advice = "强烈推荐关注，IP价值高"
elif ip_grade == 'B':
    verdict = "⭐⭐⭐⭐ 良好书"
    advice = "推荐关注，IP价值良好"
elif ip_grade == 'C':
    verdict = "⭐⭐⭐ 普通水平"
    advice = "可关注，IP价值一般"
else:
    verdict = "⭐⭐ 待观察"
    advice = "建议观察，IP价值待定"

print(f"\n是否好书:")
print(f"   {verdict}")

print(f"\n投资建议:")
print(f"   {advice}")

print(f"\n商业潜力:")
if current_data['word_count'] > 2000000:
    print(f"   ✓ 字数充足（{current_data['word_count']/10000:.0f}万），适合改编")
if current_data['total_click'] > 5000000:
    print(f"   ✓ 点击量高（{current_data['total_click']/10000:.0f}万），读者基础好")
if current_data['total_recommend'] > 100000:
    print(f"   ✓ 推荐数高（{current_data['total_recommend']/10000:.0f}万），口碑良好")

# 有声书信息
print(f"\n衍生作品:")
print(f"   ✓ 有声书已上线（懒人听书、QQ音乐等）")
print(f"   ✓ 有声书200集，诚意满满")

print("\n" + "=" * 70)
print("预测完成!")
print("=" * 70)
