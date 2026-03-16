from lxml import etree
import re

with open('debug_selenium.html', 'r', encoding='utf-8') as f:
    html = f.read()

tree = etree.HTML(html)
items = tree.xpath('//div[@id="rank-view-list"]//div[contains(@class, "book-img-text")]//ul/li')
print(f'Original xpath found {len(items)} items')

# Try alternate xpath
if not items:
    items = tree.xpath('//div[@id="rank-view-list"]//li')
    print(f'Fallback xpath found {len(items)} items')

if items:
    for i in range(min(2, len(items))):
        item = items[i]
        title = item.xpath('.//h2/a/text()')
        intro = item.xpath('.//p[contains(@class, "intro")]/text()')
        update = item.xpath('.//p[contains(@class, "update")]/a/text()')
        data_bid_a = item.xpath('.//p[contains(@class, "update")]/a/@data-bid')
        data_bid_li = item.get('data-bid')
        data_rid_li = item.get('data-rid')
        
        print(f'Item {i}:')
        print(f'  Title: {title}')
        print(f'  Intro: {intro}')
        print(f'  Update: {update}')
        print(f'  data-bid (A loop): {data_bid_a}')
        print(f'  data-bid (LI attr): {data_bid_li}')
        print(f'  data-rid (LI attr): {data_rid_li}')
