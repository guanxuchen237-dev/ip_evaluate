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

# 测试PC端第1页和第2页
for page, url in [(1, "https://www.qidian.com/rank/yuepiao/"), 
                  (2, "https://www.qidian.com/rank/yuepiao/year2026-month03-page2/")]:
    print(f'\n=== 第{page}页: {url} ===')
    browser.get(url)
    time.sleep(2)
    text = browser.page_source
    
    # 检查月票数据（加密的）
    ticket_pattern = r'<span class="FjgiwJie">([^<]+)</span></span>月票'
    tickets = re.findall(ticket_pattern, text)
    print(f'加密月票数据: {len(tickets)} 条')
    
    # 检查月票相关文本
    all_ticket_text = re.findall(r'月票', text)
    print(f'"月票"文本出现: {len(all_ticket_text)} 次')
    
    # 检查书籍
    books = re.findall(r'data-bid="(\d+)"[^>]*>.*?<h2><a[^>]*>([^<]+)</a></h2>', text, re.DOTALL)
    print(f'书籍: {len(books)} 本')
    
    if tickets:
        print(f'前5个月票: {tickets[:5]}')

browser.quit()
