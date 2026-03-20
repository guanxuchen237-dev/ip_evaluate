import urllib.request
import json

print("=== 基于真实数据的评分测试 ===\n")

# 起点测试
print("【起点平台】")
test_cases_qidian = [
    (150000, "15万票（头部TOP5）"),
    (70000, "7万票（TOP10）"),
    (50000, "5万票（TOP20）"),
    (30000, "3万票（TOP50）"),
    (20000, "2万票（TOP100）"),
    (17000, "1.7万票（TOP200）"),
]

for tickets, desc in test_cases_qidian:
    data = {
        'mode': 'basic',
        'title': '测试',
        'platform': '起点',
        'monthlyTickets': tickets,
        'wordCount': 1000000,
    }
    req = urllib.request.Request(
        'http://localhost:5000/api/predict/simple',
        json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            print(f'{desc}: {result.get("score"):.1f}分 - {result.get("grade")}级')
    except Exception as e:
        print(f'{desc}: Error - {e}')

# 纵横测试
print("\n【纵横平台】")
test_cases_zongheng = [
    (64000, "6.4万票（头部TOP5）"),
    (30000, "3万票（头部）"),
    (15000, "1.5万票（TOP10）"),
    (8000, "8000票（TOP20）"),
    (5000, "5000票（TOP50）"),
    (2000, "2000票（TOP100）"),
    (500, "500票（TOP200）"),
]

for tickets, desc in test_cases_zongheng:
    data = {
        'mode': 'basic',
        'title': '测试',
        'platform': '纵横',
        'monthlyTickets': tickets,
        'wordCount': 500000,
    }
    req = urllib.request.Request(
        'http://localhost:5000/api/predict/simple',
        json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            print(f'{desc}: {result.get("score"):.1f}分 - {result.get("grade")}级')
    except Exception as e:
        print(f'{desc}: Error - {e}')
