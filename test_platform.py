import urllib.request
import json

print("=== 起点平台测试 ===")
# 起点：月票6000票
data1 = {
    'mode': 'basic',
    'title': '起点测试',
    'platform': '起点',
    'monthlyTickets': 6000,
    'wordCount': 1000000,
}
req1 = urllib.request.Request(
    'http://localhost:5000/api/predict/simple',
    json.dumps(data1).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req1, timeout=60) as resp:
        result = json.loads(resp.read())
        print(f"起点6000票: {result.get('score'):.1f}分 - {result.get('grade')}级")
except Exception as e:
    print(f'Error: {e}')

# 起点：月票30000票
data2 = {
    'mode': 'basic',
    'title': '起点测试2',
    'platform': '起点',
    'monthlyTickets': 30000,
    'wordCount': 1000000,
}
req2 = urllib.request.Request(
    'http://localhost:5000/api/predict/simple',
    json.dumps(data2).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req2, timeout=60) as resp:
        result = json.loads(resp.read())
        print(f"起点30000票: {result.get('score'):.1f}分 - {result.get('grade')}级")
except Exception as e:
    print(f'Error: {e}')

print("\n=== 纵横平台测试 ===")
# 纵横：月票500票
data3 = {
    'mode': 'basic',
    'title': '纵横测试',
    'platform': '纵横',
    'monthlyTickets': 500,
    'wordCount': 500000,
}
req3 = urllib.request.Request(
    'http://localhost:5000/api/predict/simple',
    json.dumps(data3).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req3, timeout=60) as resp:
        result = json.loads(resp.read())
        print(f"纵横500票: {result.get('score'):.1f}分 - {result.get('grade')}级")
except Exception as e:
    print(f'Error: {e}')

# 纵横：月票1000票
data4 = {
    'mode': 'basic',
    'title': '纵横测试2',
    'platform': '纵横',
    'monthlyTickets': 1000,
    'wordCount': 500000,
}
req4 = urllib.request.Request(
    'http://localhost:5000/api/predict/simple',
    json.dumps(data4).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req4, timeout=60) as resp:
        result = json.loads(resp.read())
        print(f"纵横1000票: {result.get('score'):.1f}分 - {result.get('grade')}级")
except Exception as e:
    print(f'Error: {e}')

print("\n=== 无月票测试 ===")
# 起点：无月票，只有字数和收藏
data5 = {
    'mode': 'basic',
    'title': '起点无月票',
    'platform': '起点',
    'wordCount': 1000000,
    'collections': 100000,
}
req5 = urllib.request.Request(
    'http://localhost:5000/api/predict/simple',
    json.dumps(data5).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req5, timeout=60) as resp:
        result = json.loads(resp.read())
        print(f"起点100万字+10万收藏: {result.get('score'):.1f}分 - {result.get('grade')}级")
except Exception as e:
    print(f'Error: {e}')

# 纵横：无月票，只有字数和收藏
data6 = {
    'mode': 'basic',
    'title': '纵横无月票',
    'platform': '纵横',
    'wordCount': 500000,
    'collections': 10000,
}
req6 = urllib.request.Request(
    'http://localhost:5000/api/predict/simple',
    json.dumps(data6).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req6, timeout=60) as resp:
        result = json.loads(resp.read())
        print(f"纵横50万字+1万收藏: {result.get('score'):.1f}分 - {result.get('grade')}级")
except Exception as e:
    print(f'Error: {e}')
