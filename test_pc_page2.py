import re
import io
import os
import urllib.request
from fontTools.ttLib import TTFont

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# 使用Selenium获取PC端第2页
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--headless")

browser = webdriver.Chrome(options=options)
browser.get("https://www.qidian.com/rank/yuepiao/year2026-month03-page2/")
browser.maximize_window()
import time
time.sleep(3)

text = browser.page_source
browser.quit()

# 检查书籍数量
titles = re.findall(r'<h2><a[^>]*>([^<]+)</a></h2>', text)
print(f'Page 2 books: {len(titles)}')
print(f'First 5: {titles[:5]}')

# 检查是否有不同的书籍
page1_titles = ['捞尸人', '玄鉴仙族', '夜无疆', '没钱修什么仙？', '我，枪神！']
if titles[:5] != page1_titles:
    print('\n✅ 分页有效！第2页是不同的书籍')
else:
    print('\n❌ 分页无效！第2页与第1页相同')
