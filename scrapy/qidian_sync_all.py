# -*- coding: utf-8 -*-
import requests
from lxml import etree
import time
import logging
import random
import pymysql
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data', 'charset': 'utf8mb4'
}

CONST_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def get_db_connection():
    return pymysql.connect(**QIDIAN_CONFIG)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

LOCAL_DRIVER_PATH = r"D:\spider_code\chromedriver.exe"

def init_selenium():
    options = Options()
    options.add_argument("--headless=new") 
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"user-agent={CONST_USER_AGENT}")
    options.add_argument("--ignore-certificate-errors")

    try:
        if os.path.exists(LOCAL_DRIVER_PATH):
            service = Service(executable_path=LOCAL_DRIVER_PATH)
        else:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        return driver
    except Exception as e:
        logging.error(f"启动 Chrome 失败: {e}")
        return None

def fetch_book_detail(driver, novel_id):
    url = f"https://book.qidian.com/info/{novel_id}/"
    try:
        driver.get(url)
        # 等待关键元素加载（如简介或书名节点）
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "book-intro-detail"))
            )
            # 关键：起点的连载信息是 React 组件异步 Ajax 拉取的，必须强制等待 DOM 渲染完毕
            time.sleep(1.5)
        except:
            pass # 有的书可能没有简介或已被删除
            
        html = driver.page_source
        tree = etree.HTML(html)
        
        # 简介
        intro_nodes = tree.xpath('//p[@id="book-intro-detail"]//text()')
        intro = "".join([n.strip() for n in intro_nodes if n.strip()])
        
        # 最新章节提取：三级优先策略
        latest_chapter = ""
        
        # 策略1（最优）: 起点详情页专属的 <a class="book-latest-chapter"> 标签
        # 文本格式: "最新章节: xxx" 或直接就是章节名
        blc_nodes = tree.xpath('//a[contains(@class, "book-latest-chapter")]')
        if blc_nodes:
            raw = ''.join(blc_nodes[0].itertext()).strip()
            # 去掉 "最新章节:" 前缀
            if '最新章节' in raw:
                raw = raw.split('最新章节')[-1].lstrip(':： ').strip()
            if raw:
                latest_chapter = raw
        
        # 策略2: 含 "已更新至" 的 <p> 标签中的文本
        if not latest_chapter:
            upd_p = tree.xpath('//*[contains(text(), "已更新至")]')
            for p in upd_p:
                raw = ''.join(p.itertext()).strip()
                if '已更新至' in raw:
                    raw = raw.split('已更新至')[-1].strip()
                    # 去掉后面可能的时间戳
                    import re
                    raw = re.split(r'\d{4}-\d{2}-\d{2}', raw)[0].strip()
                    if raw:
                        latest_chapter = raw
                        break
        
        # 策略3: book-catalog 下最后一个Volume的最后一个 <a> 章节链接
        if not latest_chapter:
            catalog_a = tree.xpath('//div[contains(@class, "book-catalog")]//ul[contains(@class, "volume-chapters")]//a/text()')
            if catalog_a:
                # 取最后一个非空章节名
                for txt in reversed(catalog_a):
                    txt = txt.strip()
                    if txt:
                        latest_chapter = txt
                        break
                 
        return intro, latest_chapter
    except Exception as e:
        logging.error(f"抓取 {novel_id} 发生异常: {e}")
        return None, None

def update_db(novel_id, intro, latest_chapter):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
        UPDATE novel_monthly_stats 
        SET synopsis = %s, abstract = %s, latest_chapter = %s 
        WHERE novel_id = %s
        """
        cursor.execute(sql, (intro, intro, latest_chapter, novel_id))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    except Exception as e:
        logging.error(f"DB Update Error for {novel_id}: {e}")
        return False

def sync_all_books():
    print("="*50)
    print("🚀 启动 起点【全库查漏补缺】爬虫")
    print("说明：读取数据库所有缺失简介的书籍进行详情页抓取填补。")
    print("="*50)
    
    driver = init_selenium()
    if not driver:
        return
        
    # 先访问主页设置Cookie环境，避开第一次的风控
    driver.get("https://www.qidian.com/")
    time.sleep(2)

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    # 取出所有 latest_chapter 为 NULL / 空，但是拥有 abstract 的 novel_id （因为上一波刚更新过 abstract）
    cursor.execute("SELECT DISTINCT novel_id, title FROM novel_monthly_stats WHERE (latest_chapter IS NULL OR latest_chapter = '') AND abstract IS NOT NULL AND abstract != ''")
    books = cursor.fetchall()
    conn.close()
    
    total_missing = len(books)
    if total_missing == 0:
        print("🎉 恭喜！数据库内所有书籍的简介都已经提取完成！")
        return
        
    print(f"📊 查找到有 {total_missing} 本书籍存在信息空缺，开始依次爬取补全：")

    updated_count = 0
    for idx, book in enumerate(books, 1):
        novel_id = book['novel_id']
        title = book['title']
        
        # 排除脏数据或空ID
        if not novel_id or len(str(novel_id)) < 4:
            continue
            
        logging.info(f"({idx}/{total_missing}) 正在抓取: {title} (ID: {novel_id})")
        
        intro, latest = fetch_book_detail(driver, novel_id)
        
        if intro or latest:
            if update_db(novel_id, intro, latest):
                 updated_count += 1
                 print(f"  [√] 已更新: 最新章节=> {latest} | 简介=> {intro[:15]}...")
        else:
            logging.warning(f"  [x] 未抓取到 {title} 的内容，可能是已被封或页面不存在。")
            
        # 防止被封，每本详情抓取后随机休眠 4-8 秒
        time.sleep(random.uniform(4, 8))
        
    driver.quit()
    print(f"\n🎉 全库空缺补齐任务完成！共更新 {updated_count} 条书籍记录。")

if __name__ == '__main__':
    sync_all_books()
