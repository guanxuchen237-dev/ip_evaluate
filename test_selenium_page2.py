import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import re

options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--headless")

browser = webdriver.Chrome(options=options)

# 测试第2页
browser.get("https://www.qidian.com/rank/yuepiao/year2026-month03-page2/")
browser.maximize_window()
time.sleep(3)

text = browser.page_source
print(f'Page 2 length: {len(text)}')

# 提取data-bid
bids = re.findall(r'data-bid="(\d+)"', text)
print(f'Found {len(bids)} books on page 2')
print(f'First 5 bids: {bids[:5]}')

browser.quit()
