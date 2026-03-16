import qidian_sync_all
from lxml import etree
import time

def extract_test():
    driver = qidian_sync_all.init_selenium()
    if driver:
        # 必须先访问主页拿 cookie，然后才能进详情页
        driver.get('https://www.qidian.com/')
        time.sleep(2)
        driver.get('https://book.qidian.com/info/1036370336/')
        time.sleep(3)
        html = driver.page_source
        with open("test_dom.html", "w", encoding="utf-8") as f:
            f.write(html)
        driver.quit()
        print("DOM saved to test_dom.html")

if __name__ == "__main__":
    extract_test()
