import urllib.request
import re
import json

pc_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# 测试PC端分页格式
test_urls = [
    'https://www.qidian.com/rank/yuepiao/',
    'https://www.qidian.com/rank/yuepiao/year2026-month03-page2/',
    'https://www.qidian.com/rank/yuepiao/year2026-month03-page3/',
]

for url in test_urls:
    print(f'Testing: {url}')
    req = urllib.request.Request(url, headers={'User-Agent': pc_ua})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        text = resp.read().decode('utf-8')
        print(f'  Status: 200, Length: {len(text)}')
        
        # 检查是否有数据
        if 'rank-list' in text or 'book-name' in text:
            print(f'  Found rank data')
        if '验证' in text or '登录' in text:
            print(f'  May require login')
    except Exception as e:
        print(f'  Error: {type(e).__name__}: {str(e)[:60]}')
    print()
