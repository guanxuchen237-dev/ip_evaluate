import urllib.request
import json

# 测试场景1：只有月票，无排名
print("=== 测试场景1：只有月票6181，无排名 ===")
data1 = {
    'mode': 'basic',
    'title': '贫道要考大学',
    'platform': '起点',
    'ranking': 0,  # 无排名
    'monthlyTickets': 6181,
    'wordCount': 1740000,
    'category': '都市'
}

req = urllib.request.Request(
    'http://localhost:5000/api/predict/simple',
    json.dumps(data1).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
        print(f"Score: {result.get('score'):.1f}")
        print(f"Grade: {result.get('grade')}")
except Exception as e:
    print(f'Error: {e}')

# 测试场景2：有排名73
print("\n=== 测试场景2：有排名73 ===")
data2 = {
    'mode': 'ranking',
    'title': '贫道要考大学',
    'platform': '起点',
    'ranking': 73,
    'monthlyTickets': 6181,
    'wordCount': 1740000,
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
        print(f"Score: {result.get('score'):.1f}")
        print(f"Grade: {result.get('grade')}")
except Exception as e:
    print(f'Error: {e}')

# 测试场景3：只有字数和收藏
print("\n=== 测试场景3：只有字数100万+收藏10万 ===")
data3 = {
    'mode': 'basic',
    'title': '测试作品',
    'platform': '起点',
    'ranking': 0,
    'monthlyTickets': 0,
    'wordCount': 1000000,
    'collections': 100000,
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
        print(f"Score: {result.get('score'):.1f}")
        print(f"Grade: {result.get('grade')}")
except Exception as e:
    print(f'Error: {e}')
