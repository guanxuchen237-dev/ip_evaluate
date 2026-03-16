"""验证新的三级优先策略能否正确提取最新章节"""
from lxml import etree
import re

def extract_latest(html):
    tree = etree.HTML(html)
    latest_chapter = ""
    
    # 策略1: <a class="book-latest-chapter">
    blc = tree.xpath('//a[contains(@class, "book-latest-chapter")]')
    if blc:
        raw = ''.join(blc[0].itertext()).strip()
        if '最新章节' in raw:
            raw = raw.split('最新章节')[-1].lstrip(':： ').strip()
        if raw:
            latest_chapter = raw
            return latest_chapter, "策略1: book-latest-chapter"
    
    # 策略2: "已更新至"
    upd_p = tree.xpath('//*[contains(text(), "已更新至")]')
    for p in upd_p:
        raw = ''.join(p.itertext()).strip()
        if '已更新至' in raw:
            raw = raw.split('已更新至')[-1].strip()
            raw = re.split(r'\d{4}-\d{2}-\d{2}', raw)[0].strip()
            if raw:
                return raw, "策略2: 已更新至"
    
    # 策略3: book-catalog 最后章节
    catalog_a = tree.xpath('//div[contains(@class, "book-catalog")]//ul[contains(@class, "volume-chapters")]//a/text()')
    if catalog_a:
        for txt in reversed(catalog_a):
            txt = txt.strip()
            if txt:
                return txt, "策略3: catalog最后章节"
    
    return "", "无匹配"

for novel_id, title in [('1016572786', '我师兄实在太稳健了'), ('1013432302', '九星毒奶'), ('1015609210', '明天下')]:
    fname = f"debug_detail_{novel_id}.html"
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            html = f.read()
        chapter, strategy = extract_latest(html)
        print(f"✅ {title}: [{strategy}] => {chapter[:60]}")
    except Exception as e:
        print(f"❌ {title}: {e}")
