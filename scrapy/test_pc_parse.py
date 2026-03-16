import re
from lxml import etree

with open('zongheng_pc_debug.html', 'r', encoding='utf-8') as f:
    content = f.read()

tree = etree.HTML(content)

# 根据用户截图的 DOM：
# class="book-info-desc" 可能包含简介
desc_node = tree.xpath('//div[contains(@class, "book-info-desc")]//text()')
if desc_node:
    desc = ''.join([d.strip() for d in desc_node])
    print("Abstract extracted:", desc[:100])
else:
    # 尝试从 meta tag 拿
    meta_desc = tree.xpath('//meta[@name="description"]/@content')
    if meta_desc:
        print("Meta Abs:", meta_desc[0][:100])
    print("book-info-desc not found")

# 更新时间和最新章节，用户截图是：
# <div class="book-info-chapter">
# <span>2026-02-23 07:01:00</span>
chap_node = tree.xpath('//div[contains(@class, "book-info-chapter")]//span/text()')
print("Chapters / Dates:", chap_node)

# 从 window.__NUXT__ 尝试找 json (最稳定)
m = re.search(r'window\.__NUXT__=(.*?);</script>', content)
if m:
    print("NUXT JSON found length:", len(m.group(1)))
    # 里面可能有我们要的纯粹数据
