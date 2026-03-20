import requests
import re
import os

# 禁用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['NO_PROXY'] = '*'

cookies = {
    'e1': '%7B%22l6%22%3A%22%22%2C%22l7%22%3A%22%22%2C%22l1%22%3A5%2C%22l3%22%3A%22%22%2C%22pid%22%3A%22qd_P_rank_19%22%2C%22eid%22%3A%22qd_C44%22%7D',
    'e2': '%7B%22l6%22%3A%22%22%2C%22l7%22%3A%22%22%2C%22l1%22%3A%22%22%2C%22l3%22%3A%22%22%2C%22pid%22%3A%22qd_P_rank_19%22%2C%22eid%22%3A%22%22%7D',
    'newstatisticUUID': '1771571093_732138864',
    'supportwebp': 'true',
    'fu': '904052339',
    'supportWebp': 'true',
    'abPolicies': '%7B%22g17%22%3A1%2C%22g16%22%3A1%2C%22g18%22%3A1%2C%22g19%22%3A0%2C%22g14%22%3A0%7D',
    '_csrfToken': 'WeSWELTs3Ja3n5L1IA6GNn3CXlCMGaUAe1vzAq2z',
    'HMACCOUNT': 'B7469F4EC1F841A3',
}

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Connection': 'keep-alive',
    'Referer': 'https://www.qidian.com/rank/yuepiao/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
}

# 测试第1页和第3页
for page, url in [(1, 'https://www.qidian.com/rank/yuepiao/'), 
                  (3, 'https://www.qidian.com/rank/yuepiao/year2026-month03-page3/')]:
    print(f'\n=== 第{page}页: {url} ===')
    response = requests.get(url, cookies=cookies, headers=headers)
    text = response.text
    
    # 检查月票数据
    ticket_pattern = r'<span class="FjgiwJie">([^<]+)</span></span>月票'
    tickets = re.findall(ticket_pattern, text)
    print(f'加密月票数据: {len(tickets)} 条')
    
    # 检查书籍
    books = re.findall(r'data-bid="(\d+)"[^>]*>.*?<h2><a[^>]*>([^<]+)</a></h2>', text, re.DOTALL)
    print(f'书籍: {len(books)} 本')
    
    if tickets:
        print(f'前5个月票: {tickets[:5]}')
    if books:
        print(f'前3本书: {[b[1].strip() for b in books[:3]]}')
