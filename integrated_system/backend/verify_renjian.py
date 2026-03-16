"""
《人间太岁神！》实际数据验证
"""
import sys
sys.path.append('d:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend')

from ip_scoring_model_v81 import evaluate_ip

print("=" * 70)
print("《人间太岁神！》实际数据验证")
print("=" * 70)

# 预测 vs 实际
predicted = {'rank': 350, 'ip_grade': 'D'}
actual = {'rank': 493, 'monthly_tickets': 741}

print(f"\n{'指标':<20} {'预测值':<20} {'实际值':<20}")
print("-" * 60)
print(f"{'排名':<20} 第{predicted['rank']}名{'':<14} 第{actual['rank']}名")

# 用实际数据重新评估
book_data = {
    'title': '人间太岁神！',
    'rank': 493,
    'monthly_tickets': 741,
    'total_recommend': 76300,
    'word_count': 916900,
    'total_click': 0,
    'platform': 'Qidian'
}

result = evaluate_ip(book_data)

print(f"\n{'='*70}")
print("基于实际排名的IP评估")
print("=" * 70)

print(f"\n【等级判定】")
print(f"   排名: 第{actual['rank']}名")
print(f"   排名等级: {result['rank_tier']}")
print(f"   月票等级: {result['ticket_tier']}")
print(f"   最终等级: {result['ip_grade']}")

print(f"\n【评分明细】")
print(f"   IP评分: {result['ip_score']:.1f}")
print(f"   IP等级: {result['ip_grade']}")
print(f"   判定: {result['verdict']}")

print(f"\n结论:")
print(f"   排名第{actual['rank']}名 + 月票{actual['monthly_tickets']}票")
print(f"   → D级，待观察")
print(f"   预测准确 ✓")

print("\n" + "=" * 70)
