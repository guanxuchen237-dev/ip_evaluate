import requests
import re
import json

mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
session = requests.Session()
session.headers.update({'User-Agent': mobile_ua})

# 测试分页
for page in range(1, 4):
    if page == 1:
        url = 'https://m.qidian.com/rank/yuepiao/'
    else:
        url = f'https://m.qidian.com/rank/yuepiao/catid-1/202603/?pageNum={page}'
    
    print(f'Page {page}: {url}')
    try:
        resp = session.get(url, timeout=15)
        print(f'  Status: {resp.status_code}')
        
        json_match = re.search(r'id="vite-plugin-ssr_pageContext"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
        if json_match:
            json_data = json.loads(json_match.group(1))
            records = json_data.get('pageContext', {}).get('pageProps', {}).get('pageData', {}).get('records', [])
            print(f'  Records: {len(records)}')
        else:
            print('  No JSON found')
    except Exception as e:
        print(f'  Error: {e}')
    print()
