"""
使用新模型v8.1预测《人间太岁神！》
"""
import sys
sys.path.append('d:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend')

from ip_scoring_model_v81 import evaluate_ip
import numpy as np

print("=" * 70)
print("《人间太岁神！》IP评估 - 新模型v8.1")
print("=" * 70)

# 书籍数据
book_data = {
    'title': '人间太岁神！',
    'author': '五方行尽',
    'category': '玄幻·东方玄幻',
    'platform': 'Qidian',  # 起点
    'status': '连载中',
    'word_count': 916900,  # 91.69万字
    'total_recommend': 76300,  # 7.63万
    'weekly_recommend': 1362,
    'monthly_tickets': 741,
}

print(f"\n书籍信息:")
print(f"   书名: 《{book_data['title']}》")
print(f"   作者: {book_data['author']}")
print(f"   题材: {book_data['category']}")
print(f"   平台: {book_data['platform']}")
print(f"   字数: {book_data['word_count']/10000:.2f}万")
print(f"   总推荐: {book_data['total_recommend']/10000:.2f}万")
print(f"   周推荐: {book_data['weekly_recommend']}")
print(f"   月票: {book_data['monthly_tickets']}")

# ================================================================
#  估算排名（基于月票）
# ================================================================

print(f"\n{'='*70}")
print("排名估算")
print("=" * 70)

monthly_tickets = book_data['monthly_tickets']

# 起点平台：月票741票
# 根据起点月票分布：
# - 前10名：月票通常>10000
# - 前50名：月票通常>5000
# - 前100名：月票通常>2000
# - 前200名：月票通常>1000
# - 前500名：月票通常>500

if monthly_tickets >= 10000:
    estimated_rank = 5
elif monthly_tickets >= 5000:
    estimated_rank = 30
elif monthly_tickets >= 2000:
    estimated_rank = 70
elif monthly_tickets >= 1000:
    estimated_rank = 150
elif monthly_tickets >= 500:
    estimated_rank = 350  # 500-1000票，排名约200-500
else:
    estimated_rank = 500

book_data['rank'] = estimated_rank

print(f"\n基于月票{monthly_tickets}票估算:")
print(f"   起点平台月票{monthly_tickets}票 → 排名约第{estimated_rank}名")
print(f"   月票区间参考:")
print(f"      前100名: 月票>2000")
print(f"      前200名: 月票>1000")
print(f"      前500名: 月票>500")
print(f"   本书月票{monthly_tickets}票 → 估算排名第{estimated_rank}名左右")

# ================================================================
#  使用新模型v8.1评估
# ================================================================

print(f"\n{'='*70}")
print("新模型v8.1评估")
print("=" * 70)

result = evaluate_ip(book_data)

print(f"\n【等级判定】")
print(f"   排名等级: {result['rank_tier']}（排名前{estimated_rank}名）")
print(f"   月票等级: {result['ticket_tier']}（月票{monthly_tickets}）")
print(f"   最终等级: {result['ip_grade']}")

print(f"\n【转化率分析】")
print(f"   转化率: {result['conversion_rate']*100:.2f}%")
print(f"   转化评级: {result['conversion_level']}")
print(f"   月票/总推荐 = {monthly_tickets}/{book_data['total_recommend']} = {result['conversion_rate']*100:.2f}%")

print(f"\n【评分明细】")
print(f"   基础分: {result['details']['base_score']}")
print(f"   转化率加成: {result['details']['conversion_bonus']:+d}")
print(f"   字数加成: {result['details']['wc_bonus']:+d}（{book_data['word_count']/10000:.0f}万字）")
print(f"   点击加成: {result['details']['click_bonus']:+d}")
print(f"   IP评分: {result['ip_score']:.1f}")

print(f"\n【综合判定】")
print(f"   IP评分: {result['ip_score']:.1f}")
print(f"   IP等级: {result['ip_grade']}")
print(f"   是否好书: {result['verdict']}")
print(f"   商业价值: {result['commercial']}")

# ================================================================
#  详细分析
# ================================================================

print(f"\n{'='*70}")
print("详细分析")
print("=" * 70)

print(f"\n【数据特点】")
print(f"   字数: {book_data['word_count']/10000:.1f}万（新书，字数较少）")
print(f"   推荐数: {book_data['total_recommend']/10000:.1f}万（中等）")
print(f"   周推荐: {book_data['weekly_recommend']}（活跃）")
print(f"   月票: {monthly_tickets}（较低）")

print(f"\n【转化率分析】")
conversion = monthly_tickets / book_data['total_recommend'] * 100
print(f"   月票/总推荐 = {conversion:.2f}%")
if conversion < 1:
    print(f"   转化率低于1%，付费意愿较弱")
elif conversion < 2:
    print(f"   转化率1-2%，付费意愿一般")
else:
    print(f"   转化率>2%，付费意愿较强")

print(f"\n【新书特点】")
print(f"   ✓ 字数91万，属于新书阶段")
print(f"   ✓ 周推荐1362，更新活跃")
print(f"   △ 月票741，付费读者还在积累")
print(f"   △ 转化率{conversion:.2f}%，有待提升")

print(f"\n【投资建议】")
if result['ip_grade'] in ['S', 'A']:
    print(f"   ⭐⭐⭐⭐⭐ 强烈推荐")
elif result['ip_grade'] == 'B':
    print(f"   ⭐⭐⭐⭐ 推荐")
elif result['ip_grade'] == 'C':
    print(f"   ⭐⭐⭐ 可关注，新书有成长空间")
else:
    print(f"   ⭐⭐ 待观察")
    print(f"   - 新书阶段，数据还在积累")
    print(f"   - 建议观察后续月票增长趋势")
    print(f"   - 若月票突破1000，等级可提升")

print("\n" + "=" * 70)
print("评估完成!")
print("=" * 70)
