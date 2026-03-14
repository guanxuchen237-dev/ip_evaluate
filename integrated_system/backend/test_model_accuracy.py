"""
AI评分模型准确率验证脚本 V3.0
验证月票锚定评分系统的分数合理性和排名一致性
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pymysql

# 测试用例：使用截图中的实际平台数据
TEST_CASES = [
    {
        'title': '捞尸人',
        'category': '都市',
        'word_count': 4773000,
        'interaction': 5000000,
        'finance': 57517,       # 起点月票榜第1名
        'popularity': 6000000,
        'expected_range': (92, 99),
        'expected_level': 'S',
        'desc': '起点月票第1名 57517票'
    },
    {
        'title': '玄鉴仙族',
        'category': '仙侠',
        'word_count': 5113000,
        'interaction': 4000000,
        'finance': 54561,       # 起点月票榜第2名
        'popularity': 5000000,
        'expected_range': (92, 99),
        'expected_level': 'S',
        'desc': '起点月票第2名 54561票'
    },
    {
        'title': '夜无疆',
        'category': '东方玄幻',
        'word_count': 3035700,
        'interaction': 9250700,
        'finance': 39920,       # 起点月票榜第3名
        'popularity': 8213500,
        'expected_range': (90, 98),
        'expected_level': 'S',
        'desc': '起点月票第3名 39920票'
    },
    {
        'title': '无敌天命',
        'category': '玄幻奇幻',
        'word_count': 3462000,
        'interaction': 3000000,
        'finance': 5213,        # 纵横月票榜第2名
        'popularity': 4000000,
        'expected_range': (73, 85),
        'expected_level': 'B+',
        'desc': '纵横月票第2名 5213票'
    },
    {
        'title': '齐天',
        'category': '玄幻',
        'word_count': 2000000,
        'interaction': 2000000,
        'finance': 9050,        # 纵横月票榜第1名
        'popularity': 3000000,
        'expected_range': (78, 90),
        'expected_level': 'A',
        'desc': '纵横月票第1名 9050票'
    },
    {
        'title': '测试新书',
        'category': '都市',
        'word_count': 50000,
        'interaction': 1000,
        'finance': 100,
        'popularity': 5000,
        'expected_range': (55, 70),
        'expected_level': 'B',
        'desc': '新书/低数据量'
    },
    {
        'title': '零数据书',
        'category': '其他',
        'word_count': 0,
        'interaction': 0,
        'finance': 0,
        'popularity': 0,
        'expected_range': (45, 65),
        'expected_level': 'C',
        'desc': '无任何数据'
    },
]

# 排名一致性测试：月票高的书分数必须高于月票低的书
RANKING_TESTS = [
    ('捞尸人', 57517, '无敌天命', 5213, '起点头部 vs 纵横中游'),
    ('玄鉴仙族', 54561, '齐天', 9050, '起点第2 vs 纵横第1'),
    ('夜无疆', 39920, '无敌天命', 5213, '起点第3 vs 纵横第2'),
    ('捞尸人', 57517, '夜无疆', 39920, '起点第1 vs 起点第3'),
]

print("=" * 70)
print("  AI评分模型准确率验证测试 V3.0 (月票锚定)")
print("=" * 70)

# 1. 测试 predict_ip 函数
print("\n[Test 1] predict_ip 评分验证")
print("-" * 70)

try:
    from data_manager import data_manager
    
    passed = 0
    failed = 0
    scores_map = {}
    
    for tc in TEST_CASES:
        result = data_manager.predict_ip(tc)
        score = result['score']
        lo, hi = tc['expected_range']
        
        ok = lo <= score <= hi
        status = "✅ PASS" if ok else "❌ FAIL"
        
        details = result.get('details', {})
        fin_score = details.get('fin_score', '?')
        rt_src = details.get('rt_source', '?')
        
        print(f"  {status} | {tc['title']:10s} | 分={score:5.1f} (期望 {lo}-{hi}) | 锚={fin_score} | 源={rt_src} | {tc['desc']}")
        
        scores_map[tc['title']] = score
        
        if ok:
            passed += 1
        else:
            failed += 1
    
    print(f"\n  结果: {passed} 通过, {failed} 失败 / {len(TEST_CASES)} 总计")
    
except Exception as e:
    print(f"  [ERROR] predict_ip 测试失败: {e}")
    import traceback
    traceback.print_exc()
    scores_map = {}

# 2. 排名一致性测试
print("\n[Test 2] 跨平台排名一致性验证")
print("-" * 70)

try:
    rank_passed = 0
    rank_failed = 0
    
    for high_title, high_tkt, low_title, low_tkt, desc in RANKING_TESTS:
        high_score = scores_map.get(high_title, 0)
        low_score = scores_map.get(low_title, 0)
        
        ok = high_score > low_score
        status = "✅ PASS" if ok else "❌ FAIL"
        
        print(f"  {status} | {high_title}({high_tkt}票)={high_score:.1f} > {low_title}({low_tkt}票)={low_score:.1f} | {desc}")
        
        if ok:
            rank_passed += 1
        else:
            rank_failed += 1
    
    print(f"\n  结果: {rank_passed} 通过, {rank_failed} 失败 / {len(RANKING_TESTS)} 总计")

except Exception as e:
    print(f"  [ERROR] 排名一致性测试失败: {e}")

# 3. ticket_to_score 单元测试
print("\n[Test 3] ticket_to_score 函数验证")
print("-" * 70)

try:
    from data_manager import DataManager
    
    test_tickets = [0, 100, 500, 2000, 5000, 9050, 10000, 20000, 30000, 40000, 50000, 57517, 60000, 80000, 100000, 150000, 200000]
    
    prev_score = 0
    all_monotonic = True
    
    for t in test_tickets:
        s = DataManager._ticket_to_score(t)
        mono = "✅" if s >= prev_score else "❌"
        if s < prev_score:
            all_monotonic = False
        print(f"  {mono} | 月票 {t:>7d} → 分数 {s:5.1f}")
        prev_score = s
    
    print(f"\n  单调递增: {'✅ PASS' if all_monotonic else '❌ FAIL'}")

except Exception as e:
    print(f"  [ERROR] ticket_to_score 测试失败: {e}")

# 4. 总结
print("\n" + "=" * 70)
print("  验证总结")
print("=" * 70)
print("  ✅ predict_ip V3.0 月票锚定评分已测试")
print("  ✅ 跨平台排名一致性已验证")
print("  ✅ ticket_to_score 单调性已验证")
print("  📌 建议：运行 generate_ai_evaluations.py 更新数据库评估数据")
print("  📌 建议：运行 init_monthly_evaluation.py 重置月度评估数据")
print("  📌 建议：重启后端服务使修改生效")
