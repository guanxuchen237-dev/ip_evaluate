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

driver.get('https://book.qidian.com/info/1016572786/')
time.sleep(3)
html = driver.page_source
driver.quit()

tree = etree.HTML(html)
# 寻找与最新更新有关的文本
nodes = tree.xpath('//*[contains(text(), "最新更新") or contains(text(), "最后更新") or contains(@class,"update")]')
for n in nodes:
    print('Tag:', n.tag, 'Class:', n.get('class', ''), 'Text:', n.text)
    
# 查找所有被标记为 blue 或者是章节的
blues = tree.xpath('//a[contains(@class, "blue")]')
for b in blues:
    print('Blue a text:', ''.join(b.itertext()))
