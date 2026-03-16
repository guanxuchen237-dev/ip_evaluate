"""
预测新书 - 无月票数据时的双模型预测
"""
import numpy as np

# 书籍数据（无月票）
book_info = {
    'title': '白手起家，蝙蝠侠干碎我的致富梦',
    'author': '火星咖啡',
    'category': '诸天无限',
    'platform': 'Qidian',
    'status': '连载中',
    'is_signed': True,
    'is_vip': True,
    'word_count': 1777600,      # 177.76万字
    'total_recommend': 162000,  # 16.2万总推荐
    'week_recommend': 897,      # 周推荐
    'chapters': 847,
    'monthly_tickets': None,    # 未知，需要预测
}

print("=" * 70)
print("双模型预测 - 无月票数据")
print("=" * 70)
print(f"\n书籍信息:")
print(f"   书名: 《{book_info['title']}》")
print(f"   作者: {book_info['author']}")
print(f"   题材: {book_info['category']}")
print(f"   平台: {book_info['platform']}")
print(f"   状态: {'签约VIP' if book_info['is_vip'] else '连载'}")
print(f"   字数: {book_info['word_count']/10000:.2f}万字")
print(f"   章节: {book_info['chapters']}章")
print(f"   总推荐: {book_info['total_recommend']/10000:.1f}万")
print(f"   周推荐: {book_info['week_recommend']}")

# ================================================================
#  Model I - 月票预测（无历史月票时使用推荐数据推算）
# ================================================================

print("\n" + "=" * 70)
print("Model I - 月票预测（基于推荐数据）")
print("=" * 70)

# 起点平台：周推荐与月票的关系
# 通常：月票 ≈ 周推荐 × 4~5（活跃读者转化率）
# 但需要考虑字数、题材等因素

# 1. 基础月票估算（从周推荐推算）
base_monthly_tickets = book_info['week_recommend'] * 4.5  # 平均转化率

# 2. 字数修正因子
# 中篇（100-300万）通常月票较高
word_factor = 1.0
if book_info['word_count'] < 500000:
    word_factor = 0.7  # 短篇，月票较少
elif book_info['word_count'] < 2000000:
    word_factor = 1.1  # 中篇，月票较高
elif book_info['word_count'] < 5000000:
    word_factor = 1.0  # 长篇，稳定
else:
    word_factor = 0.9  # 超长篇，月票分散

# 3. 题材修正因子
# 诸天无限属于热门题材
HOT_GENRES_FACTOR = {
    '玄幻': 1.2, '奇幻': 1.15, '仙侠': 1.1, '都市': 1.0,
    '诸天无限': 1.15, '游戏': 1.0, '历史': 0.9, '科幻': 0.95
}
genre_factor = HOT_GENRES_FACTOR.get(book_info['category'], 1.0)

# 4. 签约/VIP修正
# VIP作品通常有更高的月票转化
vip_factor = 1.2 if book_info['is_vip'] else 1.0

# 5. 总推荐修正
# 总推荐高说明读者基础好
recommend_factor = min(1.3, max(0.8, book_info['total_recommend'] / 200000))

# 综合预测
predicted_monthly_tickets = base_monthly_tickets * word_factor * genre_factor * vip_factor * recommend_factor

# 置信区间（无历史数据，区间较宽）
confidence_low = predicted_monthly_tickets * 0.7
confidence_high = predicted_monthly_tickets * 1.3

# 趋势判断（基于周推荐/总推荐比例）
activity_ratio = book_info['week_recommend'] * 52 / (book_info['total_recommend'] + 1)
if activity_ratio > 0.5:
    trend = "上升"
    trend_reason = "近期活跃度高"
elif activity_ratio > 0.3:
    trend = "稳定"
    trend_reason = "活跃度正常"
else:
    trend = "下降"
    trend_reason = "活跃度偏低"

# 可靠性评估
reliability = "中"  # 无历史月票数据，可靠性中等
reliability_reason = "基于推荐数据推算，无历史月票"

print(f"\n月票预测计算:")
print(f"   基础月票(周推荐×4.5): {base_monthly_tickets:,.0f}")
print(f"   字数修正: ×{word_factor:.2f} ({'中篇' if book_info['word_count'] < 2000000 else '长篇'})")
print(f"   题材修正: ×{genre_factor:.2f} ({book_info['category']})")
print(f"   VIP修正: ×{vip_factor:.2f}")
print(f"   推荐修正: ×{recommend_factor:.2f}")

print(f"\nModel I 预测结果:")
print(f"   预测月票: {predicted_monthly_tickets:,.0f}")
print(f"   置信区间: [{confidence_low:,.0f}, {confidence_high:,.0f}]")
print(f"   趋势: {trend} ({trend_reason})")
print(f"   可靠性: {reliability} ({reliability_reason})")

model_i_result = {
    'predicted_tickets': predicted_monthly_tickets,
    'confidence_low': confidence_low,
    'confidence_high': confidence_high,
    'trend': trend,
    'reliability': reliability
}

# ================================================================
#  Model J Oracle - IP价值评估
# ================================================================

print("\n" + "=" * 70)
print("Model J Oracle - IP价值评估")
print("=" * 70)

# 使用预测的月票进行IP评估
adjusted_tickets = predicted_monthly_tickets  # 起点不缩放

# 分段线性月票锚定
if adjusted_tickets < 100:
    ticket_score = 55.0 + adjusted_tickets * 0.1
elif adjusted_tickets < 1000:
    ticket_score = 65.0 + (adjusted_tickets - 100) * 0.015
elif adjusted_tickets < 10000:
    ticket_score = 78.5 + (adjusted_tickets - 1000) * 0.001
else:
    ticket_score = min(95.0, 87.5 + (adjusted_tickets - 10000) * 0.0001)

# 辅助维度
inter_bonus = min(1.0, np.log1p(book_info['total_recommend'] / 100000) * 0.5)
wc_bonus = min(0.5, np.log1p(book_info['word_count'] / 500000) * 0.3)

# 题材加成（诸天无限属于热门）
cat_bonus = 0.5 if book_info['category'] in ['玄幻', '奇幻', '仙侠', '诸天无限'] else 0.0

oracle_composite = ticket_score + inter_bonus + wc_bonus + cat_bonus

# 完结衰减
if '完' in book_info['status']:
    oracle_composite *= 0.90

oracle_composite = np.clip(oracle_composite, 45.0, 99.5)

# IP等级
def score_to_grade(score):
    if score >= 90: return 'S'
    elif score >= 80: return 'A'
    elif score >= 70: return 'B'
    elif score >= 60: return 'C'
    else: return 'D'

ip_grade = score_to_grade(oracle_composite)

# 详细评估
if oracle_composite >= 85:
    commercial = "高"
    adaptation = "高" if book_info['word_count'] >= 1000000 else "中"
    recommendation = "强烈推荐关注，IP潜力高"
elif oracle_composite >= 70:
    commercial = "中"
    adaptation = "中"
    recommendation = "推荐关注，IP价值良好"
elif oracle_composite >= 60:
    commercial = "中低"
    adaptation = "中"
    recommendation = "可关注，IP价值一般"
else:
    commercial = "低"
    adaptation = "低"
    recommendation = "暂不推荐，需观察后续发展"

risk = "低（已完结）" if '完' in book_info['status'] else "中（连载中）"

# 额外分析
print(f"\nIP评估计算:")
print(f"   月票锚定分: {ticket_score:.2f} (基于预测月票: {predicted_monthly_tickets:,.0f})")
print(f"   互动加成: +{inter_bonus:.2f}")
print(f"   字数加成: +{wc_bonus:.2f}")
print(f"   题材加成: +{cat_bonus:.2f} ({book_info['category']})")

print(f"\nModel J Oracle 评估结果:")
print(f"   IP评分: {oracle_composite:.1f}")
print(f"   IP等级: {ip_grade}")
print(f"   商业潜力: {commercial}")
print(f"   改编潜力: {adaptation} (字数: {book_info['word_count']/10000:.1f}万字)")
print(f"   风险等级: {risk}")

print(f"\n投资建议: {recommendation}")

model_j_result = {
    'ip_score': oracle_composite,
    'ip_grade': ip_grade,
    'commercial': commercial,
    'adaptation': adaptation,
    'recommendation': recommendation
}

# ================================================================
#  综合判断 - 是否是好书
# ================================================================

print("\n" + "=" * 70)
print("综合判断 - 是否是好书?")
print("=" * 70)

# 好书判定标准
good_book_criteria = {
    '月票表现': predicted_monthly_tickets > 3000,
    'IP等级': ip_grade in ['S', 'A', 'B'],
    '商业潜力': commercial in ['高', '中'],
    '题材热度': genre_factor >= 1.0,
    '字数充足': book_info['word_count'] >= 500000,
    '签约状态': book_info['is_signed'],
    '读者活跃': trend in ['上升', '稳定']
}

passed = sum(good_book_criteria.values())
total = len(good_book_criteria)

print(f"\n好书判定标准 (通过 {passed}/{total}):")
for criterion, passed_flag in good_book_criteria.items():
    status = "✓" if passed_flag else "✗"
    print(f"   {status} {criterion}: {'通过' if passed_flag else '未通过'}")

# 最终判定
if passed >= 6:
    final_verdict = "⭐⭐⭐⭐⭐ 优质好书"
    verdict_reason = "多维度表现优秀，强烈推荐阅读"
elif passed >= 5:
    final_verdict = "⭐⭐⭐⭐ 值得一看"
    verdict_reason = "整体表现良好，推荐阅读"
elif passed >= 4:
    final_verdict = "⭐⭐⭐ 值得关注"
    verdict_reason = "有一定亮点，可以尝试"
else:
    final_verdict = "⭐⭐ 一般水平"
    verdict_reason = "表现平平，需观察后续发展"

print(f"\n最终判定: {final_verdict}")
print(f"判定理由: {verdict_reason}")

# ================================================================
#  双模型总结
# ================================================================

print("\n" + "=" * 70)
print("双模型预测总结")
print("=" * 70)

print(f"\n{'维度':<20} {'Model I (月票预测)':<30} {'Model J Oracle (IP评估)':<30}")
print("-" * 80)
print(f"{'核心输出':<20} {f'预测月票 {predicted_monthly_tickets:,.0f}':<30} {f'{oracle_composite:.1f}分 ({ip_grade}级)':<30}")
print(f"{'趋势/潜力':<20} {trend:<30} {commercial:<30}")
print(f"{'可靠性':<20} {reliability:<30} {'中（基于预测月票）':<30}")

print(f"\n综合建议:")
print(f"   1. 月票预测: ~{predicted_monthly_tickets:,.0f} ({trend}趋势)")
print(f"   2. IP价值: {oracle_composite:.1f}分 ({ip_grade}级)")
print(f"   3. 是否好书: {final_verdict}")
print(f"   4. 投资建议: {recommendation}")

if ip_grade in ['S', 'A'] and predicted_monthly_tickets > 5000:
    print(f"\n   结论: 双模型均看好，强烈推荐关注!")
elif ip_grade in ['S', 'A', 'B'] and predicted_monthly_tickets > 3000:
    print(f"\n   结论: IP价值良好，月票表现不错，推荐阅读")
elif ip_grade in ['B', 'C'] and predicted_monthly_tickets > 2000:
    print(f"\n   结论: 中等水平，可以尝试阅读")
else:
    print(f"\n   结论: 建议观察后续发展")

print("\n" + "=" * 70)
print("预测完成!")
print("=" * 70)
