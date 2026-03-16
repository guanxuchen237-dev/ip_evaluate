"""
修正版预测 - 基于实际数据校准
"""
import numpy as np

# 实际数据
book_info = {
    'title': '白手起家，蝙蝠侠干碎我的致富梦',
    'author': '火星咖啡',
    'category': '诸天无限',
    'platform': 'Qidian',
    'status': '连载中',
    'word_count': 1777600,
    'total_recommend': 162000,
    'week_recommend': 897,
    'monthly_tickets': 746,  # 实际月票
    'rank': 484,             # 实际排名
}

print("=" * 70)
print("修正版预测分析")
print("=" * 70)

print(f"\n实际数据:")
print(f"   书名: 《{book_info['title']}》")
print(f"   月票: {book_info['monthly_tickets']}")
print(f"   排名: 第{book_info['rank']}名")
print(f"   周推荐: {book_info['week_recommend']}")
print(f"   总推荐: {book_info['total_recommend']/10000:.1f}万")

# 分析实际转化率
print(f"\n实际转化率分析:")
print(f"   月票/周推荐 = {book_info['monthly_tickets']}/{book_info['week_recommend']} = {book_info['monthly_tickets']/book_info['week_recommend']:.2f}")
print(f"   月票/总推荐 = {book_info['monthly_tickets']}/{book_info['total_recommend']} = {book_info['monthly_tickets']/book_info['total_recommend']*100:.2f}%")

# 基于实际排名的IP评估
print("\n" + "=" * 70)
print("基于实际排名的IP评估")
print("=" * 70)

# 假设起点总书籍数约5000本
total_books = 5000
rank = book_info['rank']

# 百分位排名 → 评分
# 排名484/5000 = 前9.7%
rank_pct = rank / total_books
rank_score = 95.0 - rank_pct * 50.0  # 前10%约90分，后10%约45分

print(f"\n排名分析:")
print(f"   排名: 第{rank}名 / {total_books}本")
print(f"   百分位: 前{rank_pct*100:.1f}%")
print(f"   排名分: {rank_score:.1f}")

# 月票评分（基于实际月票746）
tickets = book_info['monthly_tickets']
if tickets < 100:
    ticket_score = 55.0 + tickets * 0.1
elif tickets < 500:
    ticket_score = 60.0 + (tickets - 100) * 0.02
elif tickets < 2000:
    ticket_score = 68.0 + (tickets - 500) * 0.005
else:
    ticket_score = 75.0 + min(20, (tickets - 2000) * 0.001)

print(f"\n月票分析:")
print(f"   月票: {tickets}")
print(f"   月票分: {ticket_score:.1f}")

# 综合评分
inter_bonus = min(1.0, np.log1p(book_info['total_recommend'] / 100000) * 0.5)
wc_bonus = min(0.5, np.log1p(book_info['word_count'] / 500000) * 0.3)
cat_bonus = 0.5  # 诸天无限

ip_score = (rank_score * 0.5 + ticket_score * 0.3) + inter_bonus + wc_bonus + cat_bonus
ip_score = np.clip(ip_score, 45.0, 99.5)

def score_to_grade(score):
    if score >= 90: return 'S'
    elif score >= 80: return 'A'
    elif score >= 70: return 'B'
    elif score >= 60: return 'C'
    else: return 'D'

ip_grade = score_to_grade(ip_score)

print(f"\n综合IP评估:")
print(f"   排名分(50%): {rank_score * 0.5:.1f}")
print(f"   月票分(30%): {ticket_score * 0.3:.1f}")
print(f"   互动加成: +{inter_bonus:.2f}")
print(f"   字数加成: +{wc_bonus:.2f}")
print(f"   题材加成: +{cat_bonus:.2f}")
print(f"   IP评分: {ip_score:.1f}")
print(f"   IP等级: {ip_grade}")

# 实际评价
print(f"\n实际评价:")
if ip_grade in ['S', 'A']:
    verdict = "优质IP"
elif ip_grade == 'B':
    verdict = "良好IP"
elif ip_grade == 'C':
    verdict = "普通IP"
else:
    verdict = "低价值IP"

print(f"   等级: {ip_grade}级 ({verdict})")
print(f"   月票746，排名484 → 中等偏下水平")

# 好书判定（修正版）
print(f"\n是否好书（修正版）:")
print(f"   月票746 → 中等偏下（不是好书指标）")
print(f"   排名484 → 前10%，但月票低说明读者付费意愿不高")
print(f"   字数177万 → 中篇，内容尚可")
print(f"   总推荐16.2万 → 读者基础不错")
print(f"\n   结论: ⭐⭐⭐ 一般水平，不是好书")

print("\n" + "=" * 70)
print("模型问题总结")
print("=" * 70)

print(f"""
❌ 原模型问题:
   1. 周推荐→月票转化系数错误（×4.5应为×0.83）
   2. 过度乐观的IP评分（A级应为C/B级）
   3. 忽略了排名与月票的关系
   
✅ 修正方案:
   1. 使用实际排名作为主要评分依据
   2. 月票映射函数需要更保守
   3. 综合排名+月票+推荐多维度
""")

print("\n" + "=" * 70)
print("修正完成!")
print("=" * 70)
