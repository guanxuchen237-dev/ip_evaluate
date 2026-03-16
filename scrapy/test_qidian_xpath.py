import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from lxml import etree

LOCAL_DRIVER_PATH = r"D:\spider_code\chromedriver.exe"

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

service = Service(executable_path=LOCAL_DRIVER_PATH)
driver = webdriver.Chrome(service=service, options=options)

url = "https://www.qidian.com/book/1013562540/"
print("Testing URL:", url)
driver.get(url)
time.sleep(3)

html = driver.page_source
tree = etree.HTML(html)

cover_xpath = '//a[@id="bookImg"]/img/@src | //div[contains(@class, "book-img")]//img/@src'
intro_xpath = '//div[contains(@class, "book-intro")]/p/text() | //p[@id="book-intro-detail"]/text()'
chapter_xpath = '//a[contains(@class, "up-chapter")]/text() | //a[@id="book-last-chapter"]/text()'
time_xpath = '//span[contains(@class, "time")]/text() | //em[@id="lastUpdate"]/text()'

cover_elem = tree.xpath(cover_xpath)
intro_elem = tree.xpath(intro_xpath)
chapter_elem = tree.xpath(chapter_xpath)
time_elem = tree.xpath(time_xpath)

print(f"Cover: {cover_elem}")
print(f"Intro: {intro_elem}")
print(f"Chapter: {chapter_elem}")
print(f"Time: {time_elem}")

driver.quit()
