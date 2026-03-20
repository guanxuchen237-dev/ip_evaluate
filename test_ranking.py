import urllib.request
import json

test_cases = [
    (5, '前5名'),
    (10, '前10名'),
    (20, '前20名'),
    (50, '前50名'),
    (67, '排名67'),
    (100, '前100名'),
    (150, '前150名'),
    (200, '前200名'),
]

for r, desc in test_cases:
    data = {
        'mode': 'ranking',
        'title': f'测试{r}',
        'platform': '起点',
        'ranking': r,
        'monthlyTickets': 3000,
        'wordCount': 500000
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
