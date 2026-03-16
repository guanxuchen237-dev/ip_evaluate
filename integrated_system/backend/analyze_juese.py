"""
《绝色生骄》实际数据对比分析
"""
import sys
sys.path.append('d:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend')

from ip_scoring_model_v8 import evaluate_ip
import numpy as np

print("=" * 70)
print("《绝色生骄》预测 vs 实际对比")
print("=" * 70)

# 预测结果
predicted = {
    'rank': 10,
    'monthly_tickets': 2525,
    'ip_score': 79.0,
    'ip_grade': 'B'
}

# 实际数据
actual = {
    'jan_rank': 20,  # 1月月票榜第20名
    'feb_rank': 38,  # 2月月票榜第38名
    'current_rank': 33,  # 现在排名第33名
    'monthly_tickets': 345,  # 月票345
}

print(f"\n{'指标':<20} {'预测值':<20} {'实际值':<20} {'差异':<20}")
print("-" * 80)
print(f"{'排名':<20} 第{predicted['rank']}名{'':<14} 第{actual['current_rank']}名{'':<14} 预测偏高")
print(f"{'月票':<20} {predicted['monthly_tickets']:<20} {actual['monthly_tickets']:<20} 预测偏高7倍")

# 排名变化
print(f"\n{'='*70}")
print("排名变化分析")
print("=" * 70)

print(f"\n   1月月票榜: 第{actual['jan_rank']}名")
print(f"   2月月票榜: 第{actual['feb_rank']}名")
print(f"   现在排名: 第{actual['current_rank']}名")

rank_change_jan_to_feb = actual['jan_rank'] - actual['feb_rank']
rank_change_feb_to_now = actual['feb_rank'] - actual['current_rank']

print(f"\n   1月→2月: {'↓' if rank_change_jan_to_feb < 0 else '↑'} {abs(rank_change_jan_to_feb)}名")
print(f"   2月→现在: {'↑' if rank_change_feb_to_now > 0 else '↓'} {abs(rank_change_feb_to_now)}名")
print(f"   趋势: 先降后升，波动中")

# 用实际数据重新评估
print(f"\n{'='*70}")
print("基于实际数据的IP评估")
print("=" * 70)

book_data = {
    'title': '绝色生骄',
    'rank': actual['current_rank'],
    'monthly_tickets': actual['monthly_tickets'],
    'total_recommend': 129000,
    'word_count': 2269000,
    'total_click': 4159000,
    'platform': 'Zongheng'
}

result = evaluate_ip(book_data)

print(f"\n【等级判定】")
print(f"   排名等级: {result['rank_tier']}（排名前{actual['current_rank']}名）")
print(f"   月票等级: {result['ticket_tier']}（月票{actual['monthly_tickets']}）")
print(f"   最终等级: {result['ip_grade']}")

print(f"\n【转化率分析】")
print(f"   转化率: {result['conversion_rate']*100:.2f}%")
print(f"   转化评级: {result['conversion_level']}")
print(f"   月票/总推荐 = {actual['monthly_tickets']}/{129000} = {result['conversion_rate']*100:.2f}%")

print(f"\n【评分明细】")
print(f"   基础分: {result['details']['base_score']}")
print(f"   转化率加成: {result['details']['conversion_bonus']:+d}")
print(f"   字数加成: {result['details']['wc_bonus']:+d}")
print(f"   点击加成: {result['details']['click_bonus']:+d}")
print(f"   IP评分: {result['ip_score']:.1f}")

print(f"\n【综合判定】")
print(f"   IP评分: {result['ip_score']:.1f}")
print(f"   IP等级: {result['ip_grade']}")
print(f"   是否好书: {result['verdict']}")
print(f"   商业价值: {result['commercial']}")

# 问题分析
print(f"\n{'='*70}")
print("问题分析")
print("=" * 70)

print(f"""
预测偏差原因：
1. 周推荐1010 → 估算月票2525，但实际仅345票
2. 纵横平台转化率差异大，周推荐与月票关系不稳定
3. 缺少历史数据参考

实际转化率分析：
- 月票/总推荐 = 345/129000 = 0.27%
- 月票/周推荐 = 345/1010 = 34%
- 转化率极低，付费意愿弱

排名趋势：
- 1月第20 → 2月第38 → 现在第33
- 整体下降，波动中
""")

# 对比总结
print(f"\n{'='*70}")
print("对比总结")
print("=" * 70)

print(f"\n{'模型':<25} {'排名':<15} {'月票':<15} {'IP等级':<10} {'准确性':<20}")
print("-" * 85)
print(f"{'预测(基于周推荐)':<25} {'第10名':<15} {'2525':<15} {'B级':<10} {'❌ 偏高':<20}")
print(f"{'实际数据':<25} 第{actual['current_rank']}名{'':<9} {actual['monthly_tickets']:<15} {result['ip_grade']}级{'':<6} ✓ 正确")

print(f"\n结论:")
print(f"   《绝色生骄》排名第{actual['current_rank']}名，月票{actual['monthly_tickets']}")
print(f"   IP评分{result['ip_score']:.1f}，{result['ip_grade']}级")
print(f"   {result['verdict']}")
print(f"   转化率极低（0.27%），付费意愿弱")

print("\n" + "=" * 70)
print("分析完成!")
print("=" * 70)
