from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
from lxml import etree

options = Options()
options.add_argument('--headless=new')
options.add_argument('--disable-gpu')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
options.add_argument('--ignore-certificate-errors')
service = Service(executable_path=r'D:\spider_code\chromedriver.exe')
driver = webdriver.Chrome(service=service, options=options)

driver.get('https://www.qidian.com/')
time.sleep(2)

driver.get('https://book.qidian.com/info/1016572786/')
time.sleep(3)
html = driver.page_source
driver.quit()

with open('debug_book_1016572786_real.html', 'w', encoding='utf-8') as f:
    f.write(html)

tree = etree.HTML(html)
intro = tree.xpath('//p[@id="book-intro-detail"]//text()')
print('Intro length:', len("".join(intro)))

# Try to find words related to updates
import re
nodes = tree.xpath('//*[contains(text(), "最新更") or contains(text(), "最后更") or contains(text(), "连载") or contains(text(), "完本")]')
for n in nodes:
    text = etree.tostring(n, encoding='unicode')
    # strip tags for brevity if it's too long
    if len(text) < 300:
        print('Node:', text.strip())
