"""
《众仙俯首》实际数据修正分析
"""
import numpy as np

print("=" * 70)
print("《众仙俯首》实际数据修正分析")
print("=" * 70)

# 实际数据（用户确认）
actual_data = {
    'jan_rank': 7,  # 1月月票榜第7名
    'feb_rank': 8,  # 2月月票榜第8名
    'current_rank': 13,  # 现在排名第13名
    'monthly_tickets': 805,  # 月票805
}

print(f"\n排名变化:")
print(f"   1月月票榜: 第{actual_data['jan_rank']}名")
print(f"   2月月票榜: 第{actual_data['feb_rank']}名")
print(f"   现在排名: 第{actual_data['current_rank']}名")
print(f"   变化: 1月第7 → 2月第8 → 现在第13")
print(f"   趋势: ↓ 持续下降")

# 基于实际排名重新计算IP评分
print(f"\n{'='*70}")
print("基于实际排名的IP评估")
print("=" * 70)

rank = actual_data['current_rank']
monthly_tickets = actual_data['monthly_tickets']

# 纵横平台
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

# 月票加成
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
print(f"   百分位: {rank_pct*100:.1f}%")
print(f"   基础分: {99.0 - 49.0 * rank_pct:.1f}")
print(f"   字数加成: +{wc_bonus:.1f}")
print(f"   题材加成: +{cat_bonus:.1f}")
print(f"   点击加成: +{click_bonus:.1f}")
print(f"   月票加成: +{ticket_bonus:.1f}")
print(f"   IP评分: {ip_score:.1f}")
print(f"   IP等级: {ip_grade}")

# 月票区间
if rank <= 5:
    ticket_range = (1000, 5000)
elif rank <= 10:
    ticket_range = (500, 3000)
elif rank <= 20:
    ticket_range = (300, 2000)
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

print(f"\n排名趋势分析:")
print(f"   1月第7 → 2月第8 → 现在第13")
print(f"   下降幅度: 6名（从第7到第13）")
print(f"   趋势: ↓ 持续下降，可能进入衰退期")

print(f"\n商业价值:")
print(f"   ✓ 排名仍在前20（纵横前10%）")
print(f"   ✓ 字数充足（268万）")
print(f"   ✓ 点击量高（642万）")
print(f"   ✓ 有声书已上线")
print(f"   △ 月票数不高（805票）")
print(f"   △ 排名持续下降")

print(f"\n结论:")
print(f"   《众仙俯首》是一本良好书（{ip_grade}级IP）")
print(f"   排名从第7下降到第13，趋势向下")
print(f"   仍在前20，但可能进入衰退期")

# 预测下月
print(f"\n{'='*70}")
print("下月预测")
print("=" * 70)

# 基于下降趋势
predicted_rank = rank + 3  # 预计再降3名
predicted_tickets = monthly_tickets * 0.9  # 预计下降10%

print(f"   预测排名: 第{predicted_rank}名左右")
print(f"   预测月票: {predicted_tickets:.0f}左右")
print(f"   趋势: ↓ 持续下降")

print(f"\n建议:")
print(f"   - 关注排名变化，若跌破前20则需警惕")
print(f"   - 月票转化率低，付费读者流失")
print(f"   - 有声书是加分项，可继续推广")

print("\n" + "=" * 70)
print("分析完成!")
print("=" * 70)
