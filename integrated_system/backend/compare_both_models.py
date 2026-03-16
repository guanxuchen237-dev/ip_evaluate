"""
双模型预测对比 - 简化版（不依赖pickle加载）
Model I: 基于趋势的月票预测
Model J Oracle: IP价值评估
"""
import numpy as np

# 目标书籍数据
book_info = {
    'title': '离婚后她惊艳了世界',
    'author': '明婳',
    'category': '现代言情',
    'platform': 'Zongheng',
    'status': '连载中',
    'word_count': 8249000,
    'monthly_tickets': 5548,
    'collection_count': 16419000,
    'total_recommend': 80000,
    'months_active': 12,
}

print("=" * 70)
print("双模型预测对比报告")
print("=" * 70)
print(f"\n书籍信息:")
print(f"   书名: 《{book_info['title']}》")
print(f"   作者: {book_info['author']}")
print(f"   题材: {book_info['category']}")
print(f"   平台: {book_info['platform']}")
print(f"   当前月票: {book_info['monthly_tickets']:,}")
print(f"   字数: {book_info['word_count']/10000:.1f}万字")

# Model I - 月票预测
print("\n" + "=" * 70)
print("Model I - 月票预测模型")
print("=" * 70)

current_tickets = book_info['monthly_tickets']
word_factor = min(1.2, max(0.8, book_info['word_count'] / 5000000))
popularity_ratio = book_info['collection_count'] / book_info['word_count']
popularity_factor = min(1.3, max(0.9, popularity_ratio * 10))
interaction_factor = min(1.2, max(0.9, book_info['total_recommend'] / 100000))
trend_multiplier = (word_factor * 0.3 + popularity_factor * 0.4 + interaction_factor * 0.3)

if book_info['word_count'] < 1000000:
    stage_factor = 1.15
elif book_info['word_count'] < 5000000:
    stage_factor = 1.0
else:
    stage_factor = 0.95

predicted_tickets = current_tickets * trend_multiplier * stage_factor
confidence_low = predicted_tickets * 0.88
confidence_high = predicted_tickets * 1.12

if trend_multiplier * stage_factor > 1.05:
    trend = "上升"
elif trend_multiplier * stage_factor < 0.95:
    trend = "下降"
else:
    trend = "稳定"

reliability = "高" if book_info['word_count'] > 3000000 else "中"

print(f"\nModel I 预测结果:")
print(f"   当前月票: {current_tickets:,}")
print(f"   预测下月月票: {predicted_tickets:,.0f}")
print(f"   置信区间: [{confidence_low:,.0f}, {confidence_high:,.0f}]")
print(f"   趋势: {trend}")
print(f"   可靠性: {reliability}")

model_i_result = {
    'predicted_tickets': predicted_tickets,
    'trend': trend,
    'reliability': reliability
}

# Model J Oracle
print("\n" + "=" * 70)
print("Model J Oracle - IP价值评估")
print("=" * 70)

platform_scale = 8.0 if book_info['platform'] == 'Zongheng' else 1.0
adjusted_tickets = book_info['monthly_tickets'] * platform_scale

if adjusted_tickets < 100:
    ticket_score = 55.0 + adjusted_tickets * 0.1
elif adjusted_tickets < 1000:
    ticket_score = 65.0 + (adjusted_tickets - 100) * 0.015
elif adjusted_tickets < 10000:
    ticket_score = 78.5 + (adjusted_tickets - 1000) * 0.001
else:
    ticket_score = min(95.0, 87.5 + (adjusted_tickets - 10000) * 0.0001)

inter_bonus = min(1.0, np.log1p(book_info['total_recommend'] / 100000) * 0.5)
wc_bonus = min(0.5, np.log1p(book_info['word_count'] / 500000) * 0.3)
oracle_composite = ticket_score + inter_bonus + wc_bonus

if '完' in book_info['status']:
    oracle_composite *= 0.90
oracle_composite = np.clip(oracle_composite, 45.0, 99.5)

def score_to_grade(score):
    if score >= 90: return 'S'
    elif score >= 80: return 'A'
    elif score >= 70: return 'B'
    elif score >= 60: return 'C'
    else: return 'D'

ip_grade = score_to_grade(oracle_composite)

if oracle_composite >= 85:
    recommendation = "强烈推荐投资，IP价值极高"
elif oracle_composite >= 70:
    recommendation = "推荐关注，IP价值良好"
else:
    recommendation = "观察为主"

risk = "低（已完结）" if '完' in book_info['status'] else "中（连载中）"

print(f"\nModel J Oracle 评估结果:")
print(f"   月票锚定分: {ticket_score:.2f}")
print(f"   IP评分: {oracle_composite:.1f}")
print(f"   IP等级: {ip_grade}")
print(f"   商业潜力: {'高' if oracle_composite >= 85 else '中' if oracle_composite >= 70 else '低'}")
print(f"   改编潜力: {'高' if book_info['word_count'] >= 1000000 else '中'}")
print(f"   风险等级: {risk}")
print(f"   投资建议: {recommendation}")

model_j_result = {
    'ip_score': oracle_composite,
    'ip_grade': ip_grade,
    'recommendation': recommendation,
    'risk': risk
}

# 双模型对比
print("\n" + "=" * 70)
print("双模型对比总结")
print("=" * 70)

print(f"\n对比表:")
print(f"{'维度':<20} {'Model I':<30} {'Model J Oracle':<30}")
print("-" * 80)
print(f"{'任务':<20} {'月票预测':<30} {'IP价值评估':<30}")
print(f"{'核心输出':<20} {f'{model_i_result[chr(39)+chr(39)]}predicted_tickets{chr(39)+chr(39)]}':,.0f}月票'<30} {f'{model_j_result[chr(39)+chr(39)]}ip_score{chr(39)+chr(39)]}'}:.1f}分({model_j_result[chr(39)+chr(39)]}ip_grade{chr(39)+chr(39)]}'}级)'<30}")
print(f"{'趋势':<20} {model_i_result[chr(39)+chr(39)]}trend{chr(39)+chr(39)]}'}'<30} {'稳定' if model_j_result[chr(39)+chr(39)]}ip_score{chr(39)+chr(39)]}'} > 70 else '需观察'<30}")

print(f"\n大模型决策建议:")
print(f"   1. 预测未来收益走势 -> 使用 Model I")
print(f"      当前月票: {current_tickets:,}, 预测: {model_i_result[chr(39)+chr(39)]}predicted_tickets{chr(39)+chr(39)]}'}:,.0f}, 趋势: {model_i_result[chr(39)+chr(39)]}trend{chr(39)+chr(39)]}'}'")

print(f"\n   2. 评估IP投资价值 -> 使用 Model J Oracle")
print(f"      IP评分: {model_j_result[chr(39)+chr(39)]}ip_score{chr(39)+chr(39)]}'}:.1f}分 ({model_j_result[chr(39)+chr(39)]}ip_grade{chr(39)+chr(39)]}'}级)")
print(f"      {model_j_result[chr(39)+chr(39)]}recommendation{chr(39)+chr(39)]}'}'")

print(f"\n   3. 综合建议:")
print(f"      这本书属于'{model_j_result[chr(39)+chr(39)]}ip_grade{chr(39)+chr(39)]}'}级'优质IP，")
print(f"      {model_j_result[chr(39)+chr(39)]}recommendation{chr(39)+chr(39)]}'}'")

print("\n" + "=" * 70)
print("对比完成!")
print("=" * 70)
