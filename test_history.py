import urllib.request
import json

# 测试数据库中存在的书籍
data = {
    'mode': 'basic',
    'title': '捞尸人',  # 起点TOP1
    'platform': '起点',
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
        print(f"Score: {result.get('score')}")
        print(f"Grade: {result.get('grade')}")
        print(f"db_matched: {result.get('db_matched')}")
        print(f"db_title: {result.get('db_title')}")
        print(f"history length: {len(result.get('history', []))}")
        if result.get('history'):
            print("\n历史数据:")
            for h in result['history'][:5]:
                print(f"  {h['year']}/{h['month']} - 月票: {h['monthly_tickets']}")
except Exception as e:
    print(f'Error: {e}')
