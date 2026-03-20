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
    
    spider = QidianSpider(use_proxy=False)
    
    # 策略：PC端获取100本书ID+标题 + 移动端获取前20本月票数据
    logging.info("=== 策略：PC端(100本) + 移动端(月票数据) ===")
    
    # 第一步：从移动端榜单获取前20本的月票数据
    logging.info("步骤1: 从移动端榜单获取前20本月票数据...")
    mobile_books = spider.fetch_rank_page_smart(year, month, 1)
    mobile_data = {}
    if mobile_books:
        for b in mobile_books:
            mobile_data[b['book_id']] = {
                'monthly_tickets_on_list': b.get('monthly_tickets_on_list', 0),
                'rank_on_list': b.get('rank_on_list', 0)
            }
        logging.info(f"移动端获取 {len(mobile_books)} 本月票数据")
    
    # 第二步：使用Selenium爬取PC端获取100本书ID和标题（5页x20本）
    logging.info("步骤2: 使用Selenium爬取PC端获取100本书...")
    pc_books = []
    for page in range(1, 6):  # 爬取5页
        page_books = spider.fetch_rank_page_pc_selenium(year, month, page)
        if page_books:
            pc_books.extend(page_books)
            logging.info(f"PC端第{page}页获取 {len(page_books)} 本")
        else:
            break
    
    if not pc_books:
        logging.warning("PC端爬取失败，使用移动端数据...")
        pc_books = mobile_books
    
    if not pc_books:
        logging.error("未能获取到任何书籍数据")
        return
    
    # 去重
    seen = set()
    unique_books = []
    for b in pc_books:
        if b['book_id'] not in seen:
            seen.add(b['book_id'])
            unique_books.append(b)
    
    logging.info(f"共获取 {len(unique_books)} 本唯一书籍")
    
    # 第三步：合并数据并获取详情
    logging.info(f"步骤3: 获取详情数据...")
    success_count = 0
    
    for i, book_info in enumerate(unique_books):
        # 补充月票数据（如果有）
        if book_info['book_id'] in mobile_data:
            book_info.update(mobile_data[book_info['book_id']])
        
        # 获取详情
        data = spider.parse_book_detail_mobile(book_info, year, month)
        if not data:
            data = spider.parse_book_detail(book_info, year, month)
        
        if data:
            if save_realtime_data(data):
                success_count += 1
                tickets = data.get('monthly_tickets_on_list', 0) or data.get('monthly_ticket_count', 0)
                rank = data.get('rank_on_list', 0) or data.get('monthly_ticket_rank', 0)
                print(f"  [{success_count}] {data['title'][:15]:15} | 月票: {tickets:6} | 排名: {rank}")
        
        time.sleep(random.uniform(0.3, 0.8))
        
        if (i + 1) % 20 == 0:
            logging.info(f"进度: {i+1}/{len(unique_books)}")

    print(f"\n🎉 实时更新完成！共抓取并存入 {success_count} 条最新数据。")

if __name__ == '__main__':
    run_realtime_spider()
