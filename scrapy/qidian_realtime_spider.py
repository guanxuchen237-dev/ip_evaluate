import requests
from lxml import etree
import time
import logging
import re
import sys
import os
import json
from datetime import datetime
import pymysql
import random

import sys
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 提取当前根系以兼容 integrated_system 和 scrapy 双环境包导入
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if current_dir not in sys.path:
    sys.path.append(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from qidian_advance import CookieManager, QidianSpider
except ImportError:
    print("❌ 无法导入 QidianSpider, 请检查工作目录")
    sys.exit(1)

QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data', 'charset': 'utf8mb4'
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def save_realtime_data(data):
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG)
        cursor = conn.cursor()
        
        try:
            cursor.execute("ALTER TABLE novel_realtime_tracking ADD COLUMN platform VARCHAR(50) DEFAULT 'qidian'")
        except:
            pass

        # 使用 UPSERT 语法（结合新加的唯一约束应对单日重复入库）
        sql = """
        INSERT INTO novel_realtime_tracking 
        (novel_id, title, record_year, record_month, record_day, monthly_tickets, collection_count, monthly_ticket_rank, platform, crawl_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        monthly_tickets = VALUES(monthly_tickets),
        collection_count = VALUES(collection_count),
        monthly_ticket_rank = VALUES(monthly_ticket_rank),
        platform = VALUES(platform),
        crawl_time = VALUES(crawl_time)
        """
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        monthly_tickets = data.get('monthly_ticket_count', 0) or data.get('monthly_tickets_on_list', 0)
        rank = data.get('monthly_ticket_rank', 0) or data.get('rank_on_list', 0)

        cursor.execute(sql, (
            str(data.get('novel_id', '0')), data.get('title', 'Unknown'), 
            data.get('data_year', now.year), data.get('data_month', now.month), now.day,
            monthly_tickets, data.get('collection_count', 0), 
            rank, data.get('source_site', 'qidian'), now_str
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"DB Save Error: {e}")
        return False

def run_realtime_spider():
    print("="*50)
    print("启动起点中文网【实时抓取】")
    print("-" * 50)
    print("说明：抓取当月Top热书的实时月票、收藏与排名数据，存入 tracking 表")
    print("="*50)

    now = datetime.now()
    year, month = now.year, now.month
    
    # 关闭极其容易失效甚至导致阻塞宕机的代理，开启直连抓取实时榜单
    spider = QidianSpider(use_proxy=False)
    
    # 只需要爬取前 5 页 (前 100 本) 作为实时跟踪样例，避免过度请求
    max_pages = 5
    success_count = 0
    
    for page in range(1, max_pages + 1):
        logging.info(f"正在扫描当月月票榜 第 {page} 页 ...")
        books = spider.fetch_rank_page_smart(year, month, page)
        
        if not books:
            logging.warning("未能获取到书籍列表，可能是被封禁或到达页尾。")
            break
            
        for book_info in books:
            # 抓取详情获取细分数据
            data = spider.parse_book_detail(book_info, year, month)
            if data:
                if save_realtime_data(data):
                    success_count += 1
                    print(f"  [√] 实时记录更新: {data['title']} - 月票: {data['monthly_ticket_count']} 排名: {data['monthly_ticket_rank']}")
            time.sleep(random.uniform(2, 5)) # 扩大防封随机间隔，避免过于频繁触碰封禁阈值
            
        time.sleep(random.uniform(3, 6)) # 页与页之间也加入长间隔

    print(f"\n🎉 实时更新完成！共抓取并存入 {success_count} 条最新数据。")

if __name__ == '__main__':
    run_realtime_spider()
