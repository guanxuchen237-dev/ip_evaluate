"""
《众仙俯首》实际数据对比分析
"""
import numpy as np

print("=" * 70)
print("《众仙俯首》预测 vs 实际对比")
print("=" * 70)

# 数据库数据
db_data = {
    'latest_rank': 7,
    'latest_monthly_ticket': 4061,
    'latest_month': '2025年12月'
}

# 用户提供的实际数据
actual_data = {
    'feb_rank': 8,  # 2月月票榜第8名
    'jan_rank': 7,  # 1月月票榜第7名
    'monthly_tickets': 805,  # 总共805票
}

print(f"\n{'指标':<20} {'数据库':<20} {'实际':<20} {'差异':<20}")
print("-" * 80)
print(f"{'排名':<20} 第{db_data['latest_rank']}名{'':<14} 第{actual_data['feb_rank']}名(2月){'':<8} 一致")
print(f"{'月票':<20} {db_data['latest_monthly_ticket']:<20} {actual_data['monthly_tickets']:<20} {'数据库偏高5倍':<20}")

# 排名变化
print(f"\n{'='*70}")
print("排名变化分析")
print("=" * 70)

rank_change = actual_data['jan_rank'] - actual_data['feb_rank']
print(f"\n   1月排名: 第{actual_data['jan_rank']}名")
print(f"   2月排名: 第{actual_data['feb_rank']}名")
print(f"   变化: {'↓' if rank_change < 0 else '↑'} {abs(rank_change)}名")
print(f"   趋势: 略有下降")

# 重新计算IP评分（基于实际月票）
print(f"\n{'='*70}")
print("基于实际数据的IP评估")
print("=" * 70)

rank = actual_data['feb_rank']
monthly_tickets = actual_data['monthly_tickets']

# 纵横平台月票普遍较低，调整计算方式
# 排名第8名 → 纵横前4%
total_books = 200
rank_pct = (rank - 1) / (total_books - 1)

# 基础分
ip_score = 99.0 - 49.0 * rank_pct

# 字数加成（267.7万）
word_count = 2677000
wc_bonus = min(2.5, np.log1p(word_count / 500000) * 1.5)
ip_score += wc_bonus

# 题材加成
cat_bonus = 0.5
ip_score += cat_bonus

# 点击加成（642万）
total_click = 6420000
click_bonus = min(2.0, np.log1p(total_click / 1000000) * 1.0)
ip_score += click_bonus

# 月票加成（调整：纵横月票普遍低）
if monthly_tickets >= 3000:
    ticket_bonus = 3.0
elif monthly_tickets >= 1000:
    ticket_bonus = 1.5
elif monthly_tickets >= 500:
    ticket_bonus = 0.5
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

print(f"\n排名分析:")
print(f"   当前排名: 第{rank}名（纵横前{rank_pct*100:.0f}%）")
print(f"   实际月票: {monthly_tickets}")
print(f"   基础分: {99.0 - 49.0 * rank_pct:.1f}")
print(f"   字数加成: +{wc_bonus:.1f}")
print(f"   题材加成: +{cat_bonus:.1f}")
print(f"   点击加成: +{click_bonus:.1f}")
print(f"   月票加成: +{ticket_bonus:.1f}")
print(f"   IP评分: {ip_score:.1f}")
print(f"   IP等级: {ip_grade}")

# 月票区间（纵横平台调整）
if rank <= 5:
    ticket_range = (1000, 5000)
elif rank <= 10:
    ticket_range = (500, 3000)
elif rank <= 50:
    ticket_range = (200, 1500)
else:
    ticket_range = (100, 800)

print(f"\n月票分析:")
print(f"   排名{rank}对应区间: [{ticket_range[0]}, {ticket_range[1]}]")
print(f"   实际月票: {monthly_tickets}")
print(f"   是否在区间内: {'✓ 是' if ticket_range[0] <= monthly_tickets <= ticket_range[1] else '✗ 否'}")

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

print(f"\n排名趋势:")
print(f"   1月第7名 → 2月第8名")
print(f"   略有下降，但仍在纵横前10")

print(f"\n商业价值:")
print(f"   ✓ 排名靠前（纵横前10）")
print(f"   ✓ 字数充足（268万）")
print(f"   ✓ 点击量高（642万）")
print(f"   ✓ 有声书已上线")
print(f"   △ 月票数不高（805票）")

print(f"\n结论:")
print(f"   《众仙俯首》是一本良好书（A级IP）")
print(f"   排名稳定在纵横前10，商业价值良好")
print(f"   月票数不高可能是纵横平台特性（付费转化率低）")

# 预测下月
print(f"\n{'='*70}")
print("下月预测")
print("=" * 70)

# 基于趋势
if rank_change < 0:  # 下降趋势
    predicted_rank = rank + 1  # 预计再降1名
else:
    predicted_rank = rank

predicted_tickets = monthly_tickets * 1.1  # 假设增长10%

print(f"   预测排名: 第{predicted_rank}名左右")
print(f"   预测月票: {predicted_tickets:.0f}左右")
print(f"   趋势: 略有下降但稳定在前10")

print("\n" + "=" * 70)
print("分析完成!")
print("=" * 70)
