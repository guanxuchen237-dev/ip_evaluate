import codecs
from lxml import etree

html = codecs.open('qidian_dom.html', 'r', 'utf-8').read()
tree = etree.HTML(html)

print('Cover:', tree.xpath('//a[@id="bookImg"]/img/@src'))
print('Intro:')
for t in tree.xpath('//div[contains(@class, "book-intro")]//text()'):
    if t.strip():
        print(t.strip())
print('Chapter:', tree.xpath('//a[contains(@class, "chapter")]/text()'))
print('Time:', tree.xpath('//span[contains(@class, "time")]/text()'))
