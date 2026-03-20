import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--headless")

browser = webdriver.Chrome(options=options)

# 添加cookies
browser.get("https://www.qidian.com/")
time.sleep(1)

cookies = {
    'newstatisticUUID': '1771571093_732138864',
    'supportwebp': 'true',
    'fu': '904052339',
    '_csrfToken': 'WeSWELTs3Ja3n5L1IA6GNn3CXlCMGaUAe1vzAq2z',
    'HMACCOUNT': 'B7469F4EC1F841A3',
}

for name, value in cookies.items():
    browser.add_cookie({'name': name, 'value': value, 'domain': '.qidian.com'})

# 测试第1页和第3页
for page, url in [(1, 'https://www.qidian.com/rank/yuepiao/'), 
                  (3, 'https://www.qidian.com/rank/yuepiao/year2026-month03-page3/')]:
    print(f'\n=== 第{page}页: {url} ===')
    browser.get(url)
    time.sleep(3)
    text = browser.page_source
    
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

browser.quit()
