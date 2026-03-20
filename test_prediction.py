import urllib.request
import json
from datetime import datetime

print(f"当前日期: {datetime.now().strftime('%Y年%m月')}\n")

# 测试：捞尸人（有历史数据，排除12月不完整数据）
data = {
    'mode': 'basic',
    'title': '捞尸人',
    'platform': '起点',
    'monthlyTickets': 200000,  # 用户输入当前月票
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
        print(f"history length: {len(result.get('history', []))}")
        
        # 显示历史数据（排除12月后）
        if result.get('history'):
            print("\n历史数据（已过滤）:")
            for h in result['history']:
                print(f"  {h['year']}/{h['month']} - 月票: {h['monthly_tickets']}")
        
        # 显示未来预测
        if result.get('future_predictions'):
            print("\n未来3个月预测:")
            for p in result['future_predictions']:
                print(f"  {p['year']}/{p['month']}月 - 预计月票: {p['predicted_tickets']} ({p['trend']})")
except Exception as e:
    print(f'Error: {e}')
