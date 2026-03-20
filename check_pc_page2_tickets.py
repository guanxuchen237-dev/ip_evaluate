import re
import io
import os
import urllib.request
from fontTools.ttLib import TTFont
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# 使用Selenium获取PC端第2页
options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--headless")

browser = webdriver.Chrome(options=options)
browser.get("https://www.qidian.com/rank/yuepiao/year2026-month03-page2/")
browser.maximize_window()
time.sleep(3)

text = browser.page_source
browser.quit()

# 检查月票数据
print('=== PC端第2页月票数据 ===')

# 提取月票数
ticket_pattern = r'<span class="FjgiwJie">([^<]+)</span>\s*月票'
ticket_matches = re.findall(ticket_pattern, text)
print(f'月票数据: {len(ticket_matches)} 条')

# 提取书籍ID和标题
pattern = r'data-bid="(\d+)"[^>]*>.*?<h2><a[^>]*>([^<]+)</a></h2>'
matches = re.findall(pattern, text, re.DOTALL)
print(f'书籍数据: {len(matches)} 本')

# 显示前5本书
print('\n前5本书:')
for i, (bid, title) in enumerate(matches[:5]):
    ticket = ticket_matches[i] if i < len(ticket_matches) else 'N/A'
    print(f'  {i+1}. {title.strip()} - 月票: {ticket}')
