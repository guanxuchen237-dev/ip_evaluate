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
# 不使用无头模式
# options.add_argument("--headless")

browser = webdriver.Chrome(options=options)

# 测试第1页
url = 'https://www.qidian.com/rank/yuepiao/'
print(f'访问: {url}')
browser.get(url)

# 等待页面加载
print('等待10秒让JavaScript完全渲染...')
time.sleep(10)

text = browser.page_source

# 检查月票数据
ticket_pattern = r'<span class="FjgiwJie">([^<]+)</span></span>月票'
tickets = re.findall(ticket_pattern, text)
print(f'\n加密月票数据: {len(tickets)} 条')

# 检查书籍
books = re.findall(r'data-bid="(\d+)"[^>]*>.*?<h2><a[^>]*>([^<]+)</a></h2>', text, re.DOTALL)
print(f'书籍: {len(books)} 本')

if tickets:
    print(f'前5个月票: {tickets[:5]}')

browser.quit()
