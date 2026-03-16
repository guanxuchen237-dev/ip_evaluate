# -*- coding: utf-8 -*-
import time
import logging
import random
import pymysql
import sys
import os
from lxml import etree

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data', 'charset': 'utf8mb4'
}

LOCAL_DRIVER_PATH = r"D:\spider_code\chromedriver.exe"
CONST_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def update_db(title, intro, latest_chapter, cover_url=None, updated_at=None):
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG)
        cursor = conn.cursor()
        
        # 严格非空判断，避免将爬取失败的空值覆盖数据库真实数据
        updates = []
        params = []
        
        if intro:
            # 只更新 synopsis，避免字段冗余
            updates.append("synopsis = %s")
            params.append(intro)
        
        if latest_chapter:
            updates.append("latest_chapter = %s")
            params.append(latest_chapter)
            
        if cover_url:
            updates.append("cover_url = %s")
            params.append(cover_url)
        
        if updated_at:
            updates.append("updated_at = %s")
            params.append(updated_at)
            
        if not updates:
            conn.close()
            return False
            
        sql = f"UPDATE novel_monthly_stats SET {', '.join(updates)} WHERE title LIKE %s"
        params.append(f"%{title}%")
        
        cursor.execute(sql, tuple(params))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    except Exception as e:
        logging.error(f"DB Update Error for {title}: {e}")
        return False

def sync_qidian_intro():
    print("="*50)
    print("🚀 启动 起点【简介及最新章节更新】爬虫 (Selenium版本)")
    print("说明：使用真实浏览器抓取月票榜动态DOM，获取简介与最新章节并入库。")
    print("="*50)

def setup_driver():
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
        
        # 先访问主页设置Cookie
        driver.get("https://www.qidian.com/")
        time.sleep(2)
        driver.add_cookie({"name": "listStyle", "value": "1", "domain": ".qidian.com"})
        return driver
    except Exception as e:
        logging.error(f"启动 Chrome 失败: {e}")
        return None

def sync_qidian_intro():
    print("="*50)
    print("🚀 启动 起点【简介及最新章节更新】爬虫 (Selenium版本)")
    print("说明：使用真实浏览器抓取月票榜动态DOM，获取简介与最新章节并入库。")
    print("="*50)

    driver = setup_driver()
    if not driver:
        return

    max_pages = 25
    total_updated = 0

    for page in range(1, max_pages + 1):
        logging.info(f"正在扫描当月月票榜 第 {page} 页 ...")
        
        if page == 1:
            url = "https://www.qidian.com/rank/yuepiao/"
        else:
            url = f"https://www.qidian.com/rank/yuepiao/page{page}/"
            
        try:
            driver.get(url)
            # 等待列表容器渲染
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "rank-view-list"))
            )
            time.sleep(2) # 缓冲等待
            
            html = driver.page_source
            tree = etree.HTML(html)
            
            items = tree.xpath('//div[@id="rank-view-list"]//div[contains(@class, "book-img-text")]//ul/li')
            
            if not items:
                # 尝试用另一种选择器（可能少了一层容器）
                items = tree.xpath('//div[@id="rank-view-list"]//ul/li')
                
            if not items:
                logging.warning(f"第 {page} 页没有解析到书籍列表，可能是遇到了反爬或列表格式有变。")
                break
                
            page_updated = 0
            for item in items:
                try:
                    update_a_elem = item.xpath('.//p[contains(@class, "update")]/a')
                    if not update_a_elem:
                        continue
                        
                    novel_id = update_a_elem[0].get('data-bid')
                    if not novel_id:
                        continue
                        
                    title_elem = item.xpath('.//h2/a/text()')
                    title = title_elem[0].strip() if title_elem else "未知"
                    
                    intro_elem = item.xpath('.//p[contains(@class, "intro")]/text()')
                    intro = intro_elem[0].strip() if intro_elem else ""

                    latest_chapter = update_a_elem[0].xpath('./text()')
                    latest_chapter = latest_chapter[0].strip() if latest_chapter else ""
                    
                    # 提取更新时间
                    updated_at_elem = item.xpath('.//p[contains(@class, "update")]/span/text()')
                    updated_at = updated_at_elem[0].strip() if updated_at_elem else ""
                    
                    cover_elem = item.xpath('.//div[@class="book-img-box"]/a/img/@src')
                    if not cover_elem:
                        cover_elem = item.xpath('.//div[contains(@class, "book-img-box")]//img/@src')
                    
                    cover_url = ""
                    if cover_elem:
                        cover_url = cover_elem[0].strip()
                        if cover_url.startswith("//"):
                            cover_url = "https:" + cover_url

                    if intro or latest_chapter or cover_url or updated_at:
                        if update_db(title, intro, latest_chapter, cover_url, updated_at):
                            page_updated += 1
                            print(f"  [√] 已更新: {title} | 封面: {cover_url[:20]}.. | 简介: {intro[:10]}.. | 时间: {updated_at}")
                            
                except Exception as e:
                    logging.error(f"解析书籍数据时发生错误: {e}")
                    continue
                    
            total_updated += page_updated
            logging.info(f"第 {page} 页更新完成，本页更新成功 {page_updated} 本书籍。")
            
            sleep_time = random.uniform(5, 10)
            logging.info(f"--> 安全休眠 {sleep_time:.1f} 秒...")
            time.sleep(sleep_time)
            
        except Exception as e:
            logging.error(f"抓取第 {page} 页发生异常: {e}")
            time.sleep(random.uniform(5, 10))
            
    driver.quit()
    print(f"\n🎉 简介与最新章节 更新完成！共数据库更新了 {total_updated} 条小说记录。")
    
    # --- 最终同步补全：将新抓取的数据覆盖到所有历史月份行 ---
    try:
        print("🔄 正在执行起点历史行全量覆盖...")
        conn = pymysql.connect(**QIDIAN_CONFIG)
        cursor = conn.cursor()
        sql_fix = """
        UPDATE novel_monthly_stats t1 
        JOIN (SELECT title, MAX(cover_url) as cover_url, MAX(abstract) as abstract, MAX(latest_chapter) as latest_chapter, MAX(updated_at) as updated_at FROM novel_monthly_stats WHERE cover_url IS NOT NULL AND cover_url != '' GROUP BY title) t2 ON t1.title = t2.title 
        SET t1.cover_url = t2.cover_url, t1.abstract = t2.abstract, t1.latest_chapter = t2.latest_chapter, t1.updated_at = t2.updated_at 
        WHERE t1.cover_url IS NULL OR t1.cover_url = '';
        """
        cursor.execute(sql_fix)
        conn.commit()
        conn.close()
        print("✅ 起点历史行元数据填充完成。")
    except Exception as e:
        print(f"⚠️ 历史行填充失败: {e}")

def setup_mobile_driver():
    options = Options()
    options.add_argument("--headless=new") 
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=375,812")
    options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1")
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
        
        # 预访问域名以设置 Cookie
        driver.get("https://m.qidian.com/")
        time.sleep(2)
        
        cookie_str = "e2=%7B%22l6%22%3A%221%22%2C%22l7%22%3A%22%22%2C%22pid%22%3A%22qd_P_xiangqing%22%2C%22eid%22%3A%22%22%2C%22l1%22%3A3%7D; e1=%7B%22l6%22%3A%221%22%2C%22l7%22%3A%22%22%2C%22l1%22%3A3%2C%22l3%22%3A%22%22%2C%22pid%22%3A%22qd_P_xiangqing%22%2C%22eid%22%3A%22qd_H_shuyouclass%22%7D; newstatisticUUID=1771662042_962039942; _csrfToken=b7e734fe-3189-4cf5-8fa4-f367fb59691f; supportwebp=true; fu=1414068526; Hm_lvt_f00f67093ce2f38f215010b699629083=1771659325,1771729663,1772799584,1772946520; HMACCOUNT=ECE8954E663BA760; traffic_utm_referer=; e1=%7B%22l6%22%3A%22%22%2C%22l7%22%3A%22%22%2C%22l1%22%3A3%2C%22l3%22%3A%22%22%2C%22pid%22%3A%22qd_p_qidian%22%2C%22eid%22%3A%22qd_A1004%22%7D; e2=%7B%22l6%22%3A%22%22%2C%22l7%22%3A%22%22%2C%22l1%22%3A3%2C%22l3%22%3A%22%22%2C%22pid%22%3A%22qd_p_qidian%22%2C%22eid%22%3A%22qd_A1003%22%7D; Hm_lpvt_f00f67093ce2f38f215010b699629083=1773050362; w_tsfp=ltvuV0MF2utBvS0Q7qnpkUutHjgldz84h0wpEaR0f5thQLErU5mC0oZ/vsj/MHDa4cxnvd7DsZoyJTLYCJI3dwMcF5iScIwYj1+RmtRz3olGB0I2FcjVDwQYcLkm5DdBfHhCNxS00jA8eIUd379yilkMsyN1zap3TO14fstJ019E6KDQmI5uDW3HlFWQRzaLbjcMcuqPr6g18L5a5Tfatg/zLlsgBL4RhkOb0i0fDHAkshK7c+BVPEmqJMv8SqA="
        
        for item in cookie_str.split('; '):
            if '=' in item:
                k, v = item.split('=', 1)
                driver.add_cookie({"name": k, "value": v, "domain": ".qidian.com"})
                
        return driver
    except Exception as e:
        logging.error(f"启动 Mobile Chrome 失败: {e}")
        return None

def deep_sync_qidian():
    print("\n🔍 启动 起点【定向深度补全】...")
    conn = pymysql.connect(**QIDIAN_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT DISTINCT title, novel_id FROM novel_monthly_stats WHERE cover_url IS NULL OR cover_url = '' OR synopsis IS NULL OR synopsis = ''")
    books = cursor.fetchall()
    conn.close()
    
    if not books:
        print("✅ 起点目前没有缺失封面的书籍。")
        return

    print(f"统计：共有 {len(books)} 本起点书籍待补全。")
    
    driver = setup_mobile_driver()
    if not driver:
        return
        
    total_updated = 0
    
    try:
        for book in books:
            try:
                title = book['title']
                novel_id = book['novel_id']
                if not novel_id:
                    continue
                url = f"https://m.qidian.com/book/{novel_id}.html"
                print(f"正在抓取: {title} ({url})")
                
                driver.get(url)
                time.sleep(random.uniform(2, 4))
                
                html = driver.page_source
                tree = etree.HTML(html)
                
                # 移动端 XPath
                cover_elem = tree.xpath('//img[contains(@class, "book-cover")]/@src | //img/@src')
                intro_elem = tree.xpath('//book-intro//text() | //div[contains(@class, "book-summary")]//text() | //book-info//text()')
                chapter_elem = tree.xpath('//a[contains(@class,"chapter")]//text() | //div[contains(@class,"update-info")]//text() | //span[contains(text(),"更新")]/../text()')
                time_elem = tree.xpath('//time//text() | //span[contains(text(),"更新")]/text() | //em[contains(text(),"小时前")]/text()')
                
                cover_url = cover_elem[0].strip() if cover_elem else ""
                if cover_url and cover_url.startswith("//"): 
                    cover_url = "https:" + cover_url
                
                intro = "".join([i.strip() for i in intro_elem]).strip() if intro_elem else ""
                latest_chapter = "".join(chapter_elem).strip() if chapter_elem else ""
                updated_at = "".join(time_elem).strip()[:45] if time_elem else ""
                
                if "更新时间" in updated_at:
                    updated_at = updated_at.replace("更新时间", "").strip()
                
                if update_db(title, intro, latest_chapter, cover_url, updated_at):
                    total_updated += 1
                    print(f"  [√] 同步成功: {title} | 封面: {cover_url[:20]}.. | 简介: {intro[:10]}.. | 时间: {updated_at}")
                else:
                    print(f"  [!] 未能更新数据或已是最新: {title}。")
                
            except Exception as e:
                print(f"  [!] 抓取 {book['title']} 时失败: {e}")
                
        print(f"\n🎉 深度补全完成，共更新 {total_updated} 本书籍。")
    finally:
        driver.quit()

if __name__ == '__main__':
    sync_qidian_intro()
    # 默认也可以跑一下深度同步
    deep_sync_qidian()
