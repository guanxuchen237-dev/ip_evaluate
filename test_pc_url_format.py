import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--headless")

browser = webdriver.Chrome(options=options)

# 测试不同的URL格式
urls = [
    "https://www.qidian.com/rank/yuepiao/",  # 第1页
    "https://www.qidian.com/rank/yuepiao/year2026-month03-page2/",  # 格式1
    "https://www.qidian.com/rank/yuepiao/year2026-month3-page2/",   # 格式2 (月份无前导0)
    "https://www.qidian.com/rank/yuepiao/page2/",  # 格式3 (无年月)
]

for url in urls:
    print(f'\n=== 测试: {url} ===')
    browser.get(url)
    time.sleep(2)
    
    text = browser.page_source
    
    # 检查月票数据
    ticket_pattern = r'<span class="FjgiwJie">([^<]+)</span>\s*月票'
    tickets = re.findall(ticket_pattern, text)
    
    # 检查书籍
    book_pattern = r'data-bid="(\d+)"[^>]*>.*?<h2><a[^>]*>([^<]+)</a></h2>'
    books = re.findall(book_pattern, text, re.DOTALL)
    
    print(f'书籍: {len(books)} 本')
    print(f'月票数据: {len(tickets)} 条')
    if books:
        print(f'前3本: {[b[1].strip() for b in books[:3]]}')

browser.quit()
