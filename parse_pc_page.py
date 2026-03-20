import re
from lxml import etree

with open('d:/ip-lumina-main-2/ip-lumina-main/pc_rank_page.html', 'r', encoding='utf-8') as f:
    text = f.read()

print(f'Page length: {len(text)}')

# 使用lxml解析
tree = etree.HTML(text)

# 查找书籍列表项
items = tree.xpath('//div[contains(@class, "book-img-text")]')
print(f'book-img-text items: {len(items)}')

if not items:
    # 尝试其他选择器
    items = tree.xpath('//div[@class="rank-list"]//div[@class="book-img-text"]')
    print(f'rank-list book-img-text: {len(items)}')

if not items:
    # 直接查找包含data-bid的元素
    items = tree.xpath('//*[@data-bid]')
    print(f'elements with data-bid: {len(items)}')

if items:
    print(f'\nFirst item structure:')
    item = items[0]
    print(f'Tag: {item.tag}')
    print(f'Attribs: {item.attrib}')
    
    # 查找标题
    title = item.xpath('.//h4/a/text()')
    if not title:
        title = item.xpath('.//h2/a/text()')
    if not title:
        title = item.xpath('.//a[contains(@href, "/info/")]/text()')
    print(f'Title: {title}')
    
    # 查找data-bid
    bid = item.get('data-bid')
    if not bid:
        bid_elem = item.xpath('.//*[@data-bid]')
        if bid_elem:
            bid = bid_elem[0].get('data-bid')
    print(f'Book ID: {bid}')
