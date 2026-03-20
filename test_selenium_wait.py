import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--headless")

browser = webdriver.Chrome(options=options)

# 测试第1页
url = 'https://www.qidian.com/rank/yuepiao/'
print(f'访问: {url}')
browser.get(url)

# 等待页面加载完成
print('等待页面加载...')
try:
    # 等待书籍列表出现
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "h2 a"))
    )
    print('书籍列表已加载')
except:
    print('等待超时')

# 额外等待JavaScript渲染
print('额外等待5秒...')
time.sleep(5)

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
if books:
    print(f'前3本书: {[b[1].strip() for b in books[:3]]}')

# 保存HTML用于分析
with open('d:/ip-lumina-main-2/ip-lumina-main/pc_page_new.html', 'w', encoding='utf-8') as f:
    f.write(text)
print('\n已保存HTML到 pc_page_new.html')

browser.quit()
