import requests
import json
import os

from bs4 import BeautifulSoup

cookie_file = r'd:\ip-lumina-main\scrapy\qidian_cookies_dict.json'
with open(cookie_file, 'r', encoding='utf-8') as f:
    cookies = json.load(f)

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.qidian.com/'
})
session.cookies.update(cookies)
session.cookies.set('listStyle', '2', domain='.qidian.com')

url = "https://www.qidian.com/rank/yuepiao/year2026-month02/"
resp = session.get(url, timeout=10)

print("Status Code:", resp.status_code)
print("Content length:", len(resp.text))

soup = BeautifulSoup(resp.text, 'html.parser')
rows = soup.select("table.rank-table-list tbody tr")
print("Table rows found:", len(rows))

if len(rows) == 0:
    list_items = soup.select("div.book-img-text ul li")
    print("List items found:", len(list_items))
    if len(list_items) == 0:
        print("First 500 chars of HTML:")
        print(resp.text[:500])
        print("Checking for Title:")
        print(soup.title.text if soup.title else "No title")
