import qidian_sync_all
from lxml import etree
import time

def extract_test():
    driver = qidian_sync_all.init_selenium()
    if driver:
        driver.get('https://www.qidian.com/')
        time.sleep(2)
        driver.get('https://book.qidian.com/info/1016572786/')
        time.sleep(3)
        html = driver.page_source
        driver.quit()
        tree = etree.HTML(html)
        
        # Output any potential chapter tags
        a_nodes = tree.xpath('//a/text()')
        for a in a_nodes:
            a = a.strip()
            if a and ('章' in a or '更' in a or '感言' in a or '完' in a or '结' in a):
                print('Found A tag text:', a)
        
        # also checking if there's any text regarding latest update
        ps = tree.xpath('//*[contains(text(), "更新") or contains(text(), "连载")]//text()')
        for p in set(ps):
            if len(p.strip()) > 0 and len(p.strip()) < 50:
                 print('Text node:', p.strip())

if __name__ == "__main__":
    extract_test()
