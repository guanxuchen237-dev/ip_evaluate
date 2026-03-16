import codecs
from lxml import etree

html = codecs.open('scrapy/qidian_m_dom.html', 'r', 'utf-8').read()
tree = etree.HTML(html)

print('Cover:', tree.xpath('//img[contains(@class, "book-cover")]/@src | //img/@src'))
print('Intro:', ''.join(tree.xpath('//div[contains(@class, "book-intro")]//text() | //div[contains(@id, "bookSummary")]//text() | //div[contains(@class, "book-summary")]//text() | //book-intro//text()')).strip())
print('Chapter:', ''.join(tree.xpath('//div[contains(@class,"book-catalog")]//a//text() | //a[contains(@class,"chapter")]//text() | //div[contains(@class,"update-info")]//text()')).strip())
print('Time:', ''.join(tree.xpath('//span[contains(text(),"更新")]/text() | //em[contains(text(),"小时前")]/text() | //time//text()')).strip())
