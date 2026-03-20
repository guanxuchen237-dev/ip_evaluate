"""测试 ip_scoring_model_v81"""
import sys
sys.path.insert(0, '.')
from ip_scoring_model_v81 import evaluate_ip

print('=== ip_scoring_model_v81 测试 ===')

cases = [
    ('顶级(第1)', 1, 50000, 30000, 3000000, 10000000),
    ('优秀(第10)', 10, 30000, 20000, 1000000, 5000000),
    ('良好(第50)', 50, 10000, 10000, 500000, 2000000),
    ('中等(第100)', 100, 5000, 5000, 300000, 1000000),
    ('普通(第200)', 200, 1000, 2000, 100000, 500000),
    ('新作(无排名)', 999, 100, 500, 30000, 10000),
]

for name, rank, tickets, recommend, words, clicks in cases:
    result = evaluate_ip({
        'rank': rank,
        'monthly_tickets': tickets,
        'total_recommend': recommend,
        'word_count': words,
        'total_click': clicks,
        'platform': 'Qidian'
    })
    score = result['ip_score']
    grade = result['ip_grade']
    print(f'{name}: 排名={rank}, 月票={tickets} -> IP={score:.1f} ({grade}级)')
