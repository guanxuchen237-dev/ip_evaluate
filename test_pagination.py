import urllib.request
import re
import json

mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'

# 获取页面并查找API相关内容
url = 'https://m.qidian.com/rank/yuepiao/'
req = urllib.request.Request(url, headers={'User-Agent': mobile_ua})
resp = urllib.request.urlopen(req, timeout=15)
text = resp.read().decode('utf-8')

# 查找可能的API URL
api_patterns = [
    r'https://[^"\']*api[^"\']*rank[^"\']*',
    r'https://[^"\']*rank[^"\']*api[^"\']*',
    r'/api/[^"\']+',
    r'fetch\([^)]+\)',
    r'axios\.[^(]+\([^)]+\)',
]

print('=== 查找API相关内容 ===')
for pattern in api_patterns:
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        print(f'{pattern[:30]}: {matches[:3]}')

# 检查 INITIAL_STATE
initial_state = re.search(r'INITIAL_STATE\s*=\s*({[^;]+});', text)
if initial_state:
    print('\nFound INITIAL_STATE')
    print(f'Content (first 300): {initial_state.group(1)[:300]}')
