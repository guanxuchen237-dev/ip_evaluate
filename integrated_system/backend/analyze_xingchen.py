"""
《星辰之主》实际数据对比分析
"""
import numpy as np

print("=" * 70)
print("《星辰之主》预测 vs 实际对比")
print("=" * 70)

# 预测结果
predicted = {
    'rank': 150,
    'monthly_tickets': 14754,
    'ip_score': 96.5,
    'ip_grade': 'S'
}

# 实际数据
actual = {
    'jan_rank': 23,  # 1月月票榜第23名
    'feb_rank': 16,  # 2月月票榜第16名
    'current_rank': 25,  # 现在排名第25名
    'monthly_tickets': 463,  # 月票463
}

print(f"\n{'指标':<20} {'预测值':<20} {'实际值':<20} {'差异':<20}")
print("-" * 80)
print(f"{'排名':<20} 第{predicted['rank']}名{'':<14} 第{actual['current_rank']}名{'':<14} 预测偏低")
print(f"{'月票':<20} {predicted['monthly_tickets']:<20} {actual['monthly_tickets']:<20} 预测偏高32倍")

# 排名变化
print(f"\n{'='*70}")
print("排名变化分析")
print("=" * 70)

print(f"\n   1月月票榜: 第{actual['jan_rank']}名")
print(f"   2月月票榜: 第{actual['feb_rank']}名")
print(f"   现在排名: 第{actual['current_rank']}名")

rank_change_jan_to_feb = actual['jan_rank'] - actual['feb_rank']
rank_change_feb_to_now = actual['feb_rank'] - actual['current_rank']

print(f"\n   1月→2月: {'↑' if rank_change_jan_to_feb > 0 else '↓'} {abs(rank_change_jan_to_feb)}名")
print(f"   2月→现在: {'↓' if rank_change_feb_to_now < 0 else '↑'} {abs(rank_change_feb_to_now)}名")
print(f"   趋势: 先升后降，波动中")

# 基于实际排名重新计算IP评分
print(f"\n{'='*70}")
print("基于实际数据的IP评估")
print("=" * 70)

rank = actual['current_rank']
monthly_tickets = actual['monthly_tickets']

# 起点平台
total_books = 500
rank_pct = (rank - 1) / (total_books - 1)

# 基础分
ip_score = 99.0 - 49.0 * rank_pct

# 字数加成（823.8万字）
word_count = 8238000
wc_bonus = min(5.0, np.log1p(word_count / 500000) * 2.0)
ip_score += wc_bonus

# 题材加成
cat_bonus = 0.3
ip_score += cat_bonus

# 点击加成（1745.5万）
total_click = 17455000
click_bonus = min(3.0, np.log1p(total_click / 1000000) * 1.5)
ip_score += click_bonus

# 推荐加成（358.2万）
total_recommend = 3582000
rec_bonus = min(3.0, np.log1p(total_recommend / 100000) * 0.5)
ip_score += rec_bonus

# 月票加成（很低，只有463）
if monthly_tickets >= 50000:
    ticket_bonus = 5.0
elif monthly_tickets >= 20000:
    ticket_bonus = 3.0
elif monthly_tickets >= 10000:
    ticket_bonus = 2.0
elif monthly_tickets >= 5000:
    ticket_bonus = 1.0
elif monthly_tickets >= 1000:
    ticket_bonus = 0.5
else:
    ticket_bonus = 0  # 月票太低，无加成

ip_score += ticket_bonus

ip_score = np.clip(ip_score, 45.0, 99.5)

def score_to_grade(score):
    if score >= 90: return 'S'
    elif score >= 80: return 'A'
    elif score >= 70: return 'B'
    elif score >= 60: return 'C'
    else: return 'D'

ip_grade = score_to_grade(ip_score)

print(f"\n排名分析:")
print(f"   当前排名: 第{rank}名（起点前{rank_pct*100:.0f}%）")
print(f"   百分位: {rank_pct*100:.1f}%")
print(f"   基础分: {99.0 - 49.0 * rank_pct:.1f}")
print(f"   字数加成: +{wc_bonus:.1f}（823.8万字超级大作）")
print(f"   点击加成: +{click_bonus:.1f}（1745.5万点击）")
print(f"   推荐加成: +{rec_bonus:.1f}（358.2万推荐）")
print(f"   月票加成: +{ticket_bonus:.1f}（月票仅{monthly_tickets}，无加成）")
print(f"   IP评分: {ip_score:.1f}")
print(f"   IP等级: {ip_grade}")

# 月票区间
if rank <= 10:
    ticket_range = (30000, 100000)
elif rank <= 20:
    ticket_range = (10000, 50000)
elif rank <= 50:
    ticket_range = (5000, 20000)
elif rank <= 100:
    ticket_range = (2000, 10000)
else:
    ticket_range = (500, 5000)

print(f"\n月票分析:")
print(f"   排名{rank}对应区间: [{ticket_range[0]}, {ticket_range[1]}]")
print(f"   实际月票: {monthly_tickets}")
print(f"   是否在区间内: ✗ 否（远低于预期）")

# 问题分析
print(f"\n{'='*70}")
print("问题分析")
print("=" * 70)

print(f"""
异常现象：
- 排名第25名（前5%）但月票仅463票
- 正常情况下第25名应有月票5000-20000票
- 实际月票仅为预期的1/10

可能原因：
1. 科幻题材读者付费意愿低
2. 读者群体以"白嫖"为主
3. 推荐高（358万）但转化率极低（0.01%）
4. 可能是旧书，读者流失严重

转化率分析：
- 月票/总推荐 = 463/3582000 = 0.013%
- 这是非常低的转化率
- 说明读者愿意推荐但不愿付费投票
""")

# 综合评估
print(f"\n{'='*70}")
print("综合评估")
print("=" * 70)

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
print(f"   ✓ 字数超级充足（824万字）")
print(f"   ✓ 点击量超高（1746万）")
print(f"   ✓ 推荐数超高（358万）")
print(f"   ✓ 排名靠前（第25名）")
print(f"   ✗ 月票极低（463票）")
print(f"   ✗ 付费转化率极低（0.013%）")

print(f"\n结论:")
print(f"   《星辰之主》是一本S级IP")
print(f"   但付费转化率极低，商业变现困难")
print(f"   推荐高但付费意愿低，典型'叫好不叫座'")

print("\n" + "=" * 70)
print("分析完成!")
print("=" * 70)
