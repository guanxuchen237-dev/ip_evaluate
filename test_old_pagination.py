import urllib.request
import re
import json

mobile_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'

# 测试之前使用的分页参数
test_urls = [
    'https://m.qidian.com/rank/yuepiao/',
    'https://m.qidian.com/rank/yuepiao/catid-1/202603/?pageNum=2',
    'https://m.qidian.com/rank/yuepiao/catid-1/202603/?pageNum=3',
    'https://m.qidian.com/rank/yuepiao/?pageNum=2',
]

for url in test_urls:
    print(f'Testing: {url}')
    req = urllib.request.Request(url, headers={'User-Agent': mobile_ua})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        text = resp.read().decode('utf-8')
        json_match = re.search(r'id="vite-plugin-ssr_pageContext"[^>]*>(.*?)</script>', text, re.DOTALL)
        if json_match:
            json_data = json.loads(json_match.group(1))
            page_data = json_data.get('pageContext', {}).get('pageProps', {}).get('pageData', {})
            records = page_data.get('records', [])
            page_num = page_data.get('pageNum', 'N/A')
            is_last = page_data.get('isLast', 'N/A')
            print(f'  Records: {len(records)}, pageNum: {page_num}, isLast: {is_last}')
            if records:
                print(f'  First: {records[0].get("bName")}, Last: {records[-1].get("bName")}')
        else:
            print(f'  No JSON found')
    except Exception as e:
        print(f'  Error: {type(e).__name__}: {str(e)[:60]}')
    print()
