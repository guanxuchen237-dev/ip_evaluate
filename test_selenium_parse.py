import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from lxml import etree
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
browser.quit()

# 保存HTML到文件
with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'w', encoding='utf-8') as f:
    f.write(text)

print(f'Page saved, length: {len(text)}')

# 检查不同的选择器
tree = etree.HTML(text)

selectors = [
    '//div[contains(@class, "rank-item")]',
    '//tr[contains(@class, "rank-list")]',
    '//div[contains(@class, "book-img-text")]',
    '//div[@class="rank-list"]//div[@class="book-img-text"]',
    '//table//tr',
]

for sel in selectors:
    items = tree.xpath(sel)
    print(f'{sel}: {len(items)} items')

# 检查data-bid
bids = re.findall(r'data-bid="(\d+)"', text)
print(f'\nTotal data-bid: {len(bids)}')
print(f'Unique: {len(set(bids))}')

# 检查书籍链接
book_links = re.findall(r'href="/info/(\d+)"', text)
print(f'Book links: {len(book_links)}')
