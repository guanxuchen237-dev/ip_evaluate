"""
《纯阳！》实际数据对比分析
"""
import numpy as np

print("=" * 70)
print("《纯阳！》预测 vs 实际对比")
print("=" * 70)

# 预测结果
predicted = {
    'monthly_tickets': 16909,
    'ip_score': 80.7,
    'ip_grade': 'A',
    'verdict': '⭐⭐⭐⭐⭐ 优质好书'
}

# 实际数据
actual = {
    'monthly_tickets': 728,
    'rank': 500,
    'word_count': 2609700,
    'total_recommend': 73400,
    'weekly_recommend': 488
}

print(f"\n{'指标':<20} {'预测值':<20} {'实际值':<20} {'偏差':<20}")
print("-" * 80)
print(f"{'月票':<20} {predicted['monthly_tickets']:<20} {actual['monthly_tickets']:<20} ×{predicted['monthly_tickets']/actual['monthly_tickets']:.0f}倍")
print(f"{'IP等级':<20} {predicted['ip_grade']:<20} {'?':<20} {'偏高':<20}")

# 使用排名重新计算IP评分
print(f"\n{'='*70}")
print("基于实际排名的IP评估")
print("=" * 70)

rank = actual['rank']
total_books = 500  # 假设

# 百分位排名
rank_pct = (rank - 1) / (total_books - 1)

# IP评分公式
ip_score = 99.0 - 49.0 * rank_pct

# 字数加成
wc_bonus = min(2.0, np.log1p(actual['word_count'] / 500000) * 1.0)
ip_score += wc_bonus

# 题材加成（玄幻热门）
cat_bonus = 0.5
ip_score += cat_bonus

ip_score = np.clip(ip_score, 45.0, 99.5)

def score_to_grade(score):
    if score >= 90: return 'S'
    elif score >= 80: return 'A'
    elif score >= 70: return 'B'
    elif score >= 60: return 'C'
    else: return 'D'

ip_grade = score_to_grade(ip_score)

print(f"\n排名分析:")
print(f"   排名: 第{rank}名")
print(f"   百分位: 前{rank_pct*100:.1f}%")
print(f"   基础分: {99.0 - 49.0 * rank_pct:.1f}")
print(f"   字数加成: +{wc_bonus:.1f}")
print(f"   题材加成: +{cat_bonus:.1f}")
print(f"   IP评分: {ip_score:.1f}")
print(f"   IP等级: {ip_grade}")

# 月票区间估算
if rank <= 10:
    ticket_range = (30000, 100000)
elif rank <= 50:
    ticket_range = (10000, 50000)
elif rank <= 100:
    ticket_range = (5000, 20000)
elif rank <= 200:
    ticket_range = (1500, 6000)
elif rank <= 500:
    ticket_range = (400, 1500)
else:
    ticket_range = (100, 600)

print(f"\n月票估算:")
print(f"   排名{rank}对应区间: [{ticket_range[0]}, {ticket_range[1]}]")
print(f"   实际月票: {actual['monthly_tickets']}")
print(f"   是否在区间内: {'✓ 是' if ticket_range[0] <= actual['monthly_tickets'] <= ticket_range[1] else '✗ 否'}")

# 好书判定
print(f"\n是否好书:")
if ip_grade in ['S', 'A']:
    verdict = "⭐⭐⭐⭐⭐ 优质好书"
elif ip_grade == 'B':
    verdict = "⭐⭐⭐⭐ 良好书"
elif ip_grade == 'C':
    verdict = "⭐⭐⭐ 普通水平"
else:
    verdict = "⭐⭐ 待观察"

print(f"   {verdict}")

# 问题分析
print(f"\n{'='*70}")
print("问题分析")
print("=" * 70)

print(f"""
预测偏差原因:
1. 增强模型缺少评论数据（63/97特征为0）
2. 周推荐488 → 模型预测16,909，但实际转化率很低
3. 总推荐7.34万 vs 月票728 → 转化率仅0.99%

实际转化率分析:
   月票/总推荐 = 728/73400 = 0.99%
   月票/周推荐 = 728/488 = 1.49

这说明:
- 读者推荐意愿高（7.34万推荐）
- 但付费投票意愿低（仅728月票）
- 典型的"白嫖"读者群体

正确评估:
- 排名500 → D级普通IP
- 月票728在预测区间[400, 1500]内
- 不是好书，属于普通水平
""")

# 对比总结
print(f"\n{'='*70}")
print("对比总结")
print("=" * 70)

print(f"\n{'模型':<25} {'月票预测':<20} {'IP等级':<10} {'准确性':<20}")
print("-" * 75)
print(f"{'增强模型(缺评论)':<25} {'16,909':<20} {'A级':<10} {'❌ 偏高23倍':<20}")
print(f"{'排名直接计算':<25} {'[400, 1500]':<20} {f'{ip_grade}级':<10} {'✓ 月票在区间内':<20}")

print(f"\n结论:")
print(f"   《纯阳！》排名500，月票728")
print(f"   IP评分{ip_score:.1f}，{ip_grade}级")
print(f"   {verdict}")
print(f"   推荐高但付费转化低，属于普通作品")

print("\n" + "=" * 70)
