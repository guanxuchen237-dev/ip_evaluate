"""
使用新模型v8预测《绝色生骄》
"""
import sys
sys.path.append('d:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend')

from ip_scoring_model_v8 import evaluate_ip, predict_monthly_tickets
import numpy as np

print("=" * 70)
print("《绝色生骄》IP评估 - 新模型v8")
print("=" * 70)

# 书籍数据
book_data = {
    'title': '绝色生骄',
    'category': '历史热血悬疑剑道争霸师徒恋',
    'platform': 'Zongheng',  # 纵横
    'status': '连载中',
    'word_count': 2269000,  # 226.9万字
    'total_recommend': 129000,  # 12.9万
    'total_click': 4159000,  # 415.9万
    'weekly_recommend': 1010,
}

print(f"\n书籍信息:")
print(f"   书名: 《{book_data['title']}》")
print(f"   题材: {book_data['category']}")
print(f"   平台: {book_data['platform']}")
print(f"   字数: {book_data['word_count']/10000:.1f}万")
print(f"   总点击: {book_data['total_click']/10000:.1f}万")
print(f"   总推荐: {book_data['total_recommend']/10000:.1f}万")
print(f"   周推荐: {book_data['weekly_recommend']}")

# ================================================================
#  估算月票和排名（缺少关键数据）
# ================================================================

print(f"\n{'='*70}")
print("数据估算（缺少月票和排名）")
print("=" * 70)

# 基于周推荐估算月票
# 纵横平台：周推荐1010 → 月票约周推荐×2-3
estimated_monthly_tickets = book_data['weekly_recommend'] * 2.5

print(f"\n基于周推荐估算:")
print(f"   周推荐: {book_data['weekly_recommend']}")
print(f"   估算月票: {estimated_monthly_tickets:.0f}（周推荐×2.5）")

# 基于月票估算排名
if estimated_monthly_tickets >= 3000:
    estimated_rank = 5
elif estimated_monthly_tickets >= 2000:
    estimated_rank = 10
elif estimated_monthly_tickets >= 1000:
    estimated_rank = 20
elif estimated_monthly_tickets >= 500:
    estimated_rank = 50
else:
    estimated_rank = 100

book_data['monthly_tickets'] = int(estimated_monthly_tickets)
book_data['rank'] = estimated_rank

print(f"   估算排名: 第{estimated_rank}名")

# ================================================================
#  使用新模型v8评估
# ================================================================

print(f"\n{'='*70}")
print("新模型v8评估")
print("=" * 70)

result = evaluate_ip(book_data)

print(f"\n【等级判定】")
print(f"   排名等级: {result['rank_tier']}（排名前{book_data['rank']}名）")
print(f"   月票等级: {result['ticket_tier']}（月票{book_data['monthly_tickets']}）")
print(f"   最终等级: {result['ip_grade']}")

print(f"\n【转化率分析】")
print(f"   转化率: {result['conversion_rate']*100:.2f}%")
print(f"   转化评级: {result['conversion_level']}")
print(f"   月票/总推荐 = {book_data['monthly_tickets']}/{book_data['total_recommend']} = {result['conversion_rate']*100:.2f}%")

print(f"\n【评分明细】")
print(f"   基础分: {result['details']['base_score']}")
print(f"   转化率加成: {result['details']['conversion_bonus']:+d}")
print(f"   字数加成: {result['details']['wc_bonus']:+d}（{book_data['word_count']/10000:.0f}万字）")
print(f"   点击加成: {result['details']['click_bonus']:+d}（{book_data['total_click']/10000:.0f}万点击）")
print(f"   IP评分: {result['ip_score']:.1f}")

print(f"\n【综合判定】")
print(f"   IP评分: {result['ip_score']:.1f}")
print(f"   IP等级: {result['ip_grade']}")
print(f"   是否好书: {result['verdict']}")
print(f"   商业价值: {result['commercial']}")

# ================================================================
#  月票区间预测
# ================================================================

print(f"\n{'='*70}")
print("月票区间预测")
print("=" * 70)

ticket_result = predict_monthly_tickets(book_data)

print(f"   排名第{book_data['rank']}名对应月票区间: {ticket_result['ticket_range']}")
print(f"   估算月票: {book_data['monthly_tickets']}")
print(f"   是否在区间内: {'✓ 是' if ticket_result['ticket_range'][0] <= book_data['monthly_tickets'] <= ticket_result['ticket_range'][1] else '✗ 否'}")
print(f"   置信度: {ticket_result['confidence']}")

# ================================================================
#  商业价值分析
# ================================================================

print(f"\n{'='*70}")
print("商业价值分析")
print("=" * 70)

print(f"\n【题材分析】")
print(f"   历史热血：男性向题材，适合游戏、动漫改编")
print(f"   悬疑元素：增加剧情张力，改编潜力高")
print(f"   剑道争霸：热血战斗，适合影视化")

print(f"\n【数据评估】")
if result['ip_grade'] in ['S', 'A']:
    print(f"   ✓ IP价值高")
elif result['ip_grade'] == 'B':
    print(f"   ✓ IP价值良好")
elif result['ip_grade'] == 'C':
    print(f"   △ IP价值一般")
else:
    print(f"   △ IP价值待观察")

print(f"\n【注意事项】")
print(f"   ⚠️ 缺少实际月票数据，评估为估算")
print(f"   ⚠️ 建议获取实际月票和排名数据后重新评估")

print(f"\n【投资建议】")
if result['ip_grade'] in ['S', 'A']:
    print(f"   ⭐⭐⭐⭐⭐ 强烈推荐")
elif result['ip_grade'] == 'B':
    print(f"   ⭐⭐⭐⭐ 推荐")
elif result['ip_grade'] == 'C':
    print(f"   ⭐⭐⭐ 可关注")
else:
    print(f"   ⭐⭐ 待观察")

print("\n" + "=" * 70)
print("评估完成!")
print("=" * 70)
