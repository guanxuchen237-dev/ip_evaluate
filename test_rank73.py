import urllib.request
import json

data = {
    'mode': 'ranking',
    'title': '贫道要考大学',
    'platform': '起点',
    'ranking': 73,
    'monthlyTickets': 6181,
    'wordCount': 1740000,
    'category': '都市'
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
        print(f"Dimensions: {result.get('dimensions')}")
except Exception as e:
    print(f'Error: {e}')
