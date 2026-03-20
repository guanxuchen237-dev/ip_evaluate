import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import re

options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--headless")

browser = webdriver.Chrome(options=options)
browser.get("https://www.qidian.com/rank/yuepiao/")
browser.maximize_window()
time.sleep(3)

text = browser.page_source
print(f'Page length: {len(text)}')

# 尝试不同的选择器
patterns = [
    (r'data-bid="(\d+)"', 'data-bid'),
    (r'<h4[^>]*>([^<]+)</h4>', 'h4 tags'),
    (r'class="book-title[^"]*"[^>]*>([^<]+)<', 'book-title'),
    (r'<a[^>]*href="/info/(\d+)"[^>]*>([^<]+)</a>', 'book links'),
]

for pattern, desc in patterns:
    matches = re.findall(pattern, text)
    print(f'{desc}: {len(matches)} items')
    if matches and len(matches) <= 10:
        print(f'  {matches[:5]}')

browser.quit()
