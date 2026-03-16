# -*- coding: utf-8 -*-
import time
import logging
import random
import pymysql
import sys
import os
from datetime import datetime

# 导入纵横爬虫的核心逻辑
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from zongheng_spider_v4 import parse_book_detail_ultimate, safe_request
except ImportError:
    print("❌ 无法导入 zongheng_spider_v4, 请检查工作目录")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

def update_db(book_id, data):
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG)
        cursor = conn.cursor()
        
        sql = """
        UPDATE zongheng_book_ranks 
        SET abstract = %s, cover_url = %s, latest_chapter = %s, updated_at = %s, chapter_interval = %s
        WHERE book_id = %s
        """
        cursor.execute(sql, (
            data.get('abstract', ''), 
            data.get('cover_url', ''), 
            data.get('latest_chapter', ''),
            data.get('updated_at', ''),
            data.get('chapter_interval', ''),
            book_id
        ))
        # 注意：这里会影响多行（所有年份和月份），所以 rowcount 可能大于 1
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    except Exception as e:
        logging.error(f"DB Update Error for {book_id}: {e}")
        return False

def sync_zongheng_meta():
    print("="*50)
    print("🚀 启动 纵横【元数据同步】爬虫")
    print("说明：针对库中已有书籍，重新爬取封面、简介及更新时间。")
    print("="*50)

    conn = pymysql.connect(**ZONGHENG_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # 移除 LIMIT，全量扫描待同步书籍
    cursor.execute("SELECT DISTINCT book_id, title FROM zongheng_book_ranks WHERE abstract IS NULL OR abstract = '' OR cover_url IS NULL")
    books_to_sync = cursor.fetchall()
    conn.close()

    if not books_to_sync:
        print("✅ 没有发现需要同步的纵横书籍。")
        return

    print(f"统计：共有 {len(books_to_sync)} 本书籍待同步。")
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    success_count = 0
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for book in books_to_sync:
            book_id = book['book_id']
            title = book['title']
            futures.append(executor.submit(sync_one_book, book_id, title))
            
        for future in as_completed(futures):
            if future.result():
                success_count += 1

    print(f"\n🎉 纵横元数据同步完成！共更新 {success_count} 本书籍（及其对应的所有历史月份行）。")

def sync_one_book(book_id, title):
    try:
        # 增加更明显的序号或标识
        logging.info(f"👉 正在同步: {title} ({book_id})...")
        
        api_book = {'bookId': book_id, 'bookName': title}
        data = parse_book_detail_ultimate(api_book)
        
        if not data or (not data.get('abstract') and not data.get('cover_url')):
            print(f"  [!] 无法获取到有效数据（确认 ID 可能已下架）: {title}")
            return False
            
        if update_db(book_id, data):
            print(f"  [√] 更新成功: {title} | 封面: {data.get('cover_url', '')[:30]}...")
            return True
        else:
            print(f"  [?] 未能同步到数据库，请检查表结构: {title}")
            return False
            
        time.sleep(random.uniform(3, 8))
    except Exception as e:
        logging.error(f"同步书籍 {title} 时发生异常: {e}")
    return False

if __name__ == '__main__':
    sync_zongheng_meta()
