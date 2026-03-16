import time
import logging
import sys
import os
from datetime import datetime
import pymysql
import random

# 提取当前根系以兼容 integrated_system 和 scrapy 双环境包导入
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if current_dir not in sys.path:
    sys.path.append(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from zongheng_spider_v4 import parse_book_detail_ultimate, safe_request
    import zongheng_spider_v4
except ImportError:
    print("❌ 无法导入 zongheng_spider_v4, 请检查工作目录")
    sys.exit(1)

# Monkey patch safe_request to bypass proxy pool for realtime scraping
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def no_proxy_request(method, url, params=None, data=None, headers=None, timeout=5, max_retries=3):
    if headers is None: headers = zongheng_spider_v4.HEADERS
    for i in range(max_retries):
        try:
            session = requests.Session()
            session.trust_env = False
            if method.upper() == 'GET':
                resp = session.get(url, params=params, headers=headers, proxies={"http": None, "https": None}, timeout=timeout, verify=False)
            else:
                resp = session.post(url, data=data, json=params, headers=headers, proxies={"http": None, "https": None}, timeout=timeout, verify=False)
            if resp.status_code == 200:
                return resp
        except:
            time.sleep(1)
    return None
    
zongheng_spider_v4.safe_request = no_proxy_request

def fetch_monthly_ticket_list(page, limit):
    """获取指定页码的月票榜列表"""
    url = "https://www.zongheng.com/api/rank/details"
    data = {
        "rankNo": "", 
        "rankType": "1", 
        "pageNum": str(page),  
        "pageSize": str(limit), 
        "cateFineId": "0", "cateType": "0"
    }
    resp = no_proxy_request('POST', url, data=data)
    if resp:
        return resp.json().get('result', {}).get('resultList', [])
    return []

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(message)s')
logging.getLogger('gensim').setLevel(logging.ERROR)

ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

# Restore basicConfig for spider logic
logging.getLogger().setLevel(logging.INFO)

# We already set it above, so we can remove this redundant basicConfig line.
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def save_realtime_data(data):
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG)
        cursor = conn.cursor()

        # 如果表不存在则创建
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS zongheng_realtime_tracking (
            id INT AUTO_INCREMENT PRIMARY KEY,
            novel_id VARCHAR(50),
            title VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            record_year INT,
            record_month INT,
            monthly_tickets INT DEFAULT 0,
            total_recommend INT DEFAULT 0,
            monthly_ticket_rank INT DEFAULT 0,
            platform VARCHAR(50) DEFAULT 'zongheng',
            crawl_time DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        cursor.execute(create_table_sql)
        
        try:
            cursor.execute("ALTER TABLE zongheng_realtime_tracking ADD COLUMN platform VARCHAR(50) DEFAULT 'zongheng'")
        except:
            pass

        # 使用 UPSERT 语法（ON DUPLICATE KEY UPDATE）对于同样的书本和时间等，这里直接记录，可能重复书
        # 如果需要保持唯一，可以在 novel_id 上加 UNIQUE，但一般来说 realtime 表是每次爬取记一条流水或者UPSERT。
        # 仿照起点，如果只是保留最新一条：
        
        # 检查是否已存在唯一约束，由于之前没有，我们按 qidian 的逻辑，如果是每天的一条流水或者仅存最新数据？
        # 起点的 realtime_tracking 并没有唯一键，ON DUPLICATE KEY UPDATE 需要唯一键。
        # 这里我们就单纯插入一条新记录作为时间序列
        
        # 使用 UPSERT 语法（结合新加的唯一约束应对单日重复入库）
        sql = """
        INSERT INTO zongheng_realtime_tracking 
        (novel_id, title, record_year, record_month, record_day, monthly_tickets, total_recommend, monthly_ticket_rank, platform, crawl_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        monthly_tickets = VALUES(monthly_tickets),
        total_recommend = VALUES(total_recommend),
        monthly_ticket_rank = VALUES(monthly_ticket_rank),
        platform = VALUES(platform),
        crawl_time = VALUES(crawl_time)
        """
        
        # Zongheng 主要是收藏 (总点击或总推荐), 我们映射一下
        collection = data.get('total_rec', 0) 
        
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(sql, (
            str(data.get('book_id', '0')), data.get('title', 'Unknown'), 
            now.year, now.month, now.day, 
            data.get('monthly_ticket', 0), collection, 
            data.get('rank_num', 0), 'zongheng', now_str
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"DB Save Error: {e}")
        return False

def run_realtime_spider():
    print("="*50)
    print("启动 纵横【实时监测】月票榜爬虫")
    print("说明：抓取本期Top热书的实时月票、推荐与排名数据，存入 tracking 表")
    print("="*50)

    now = datetime.now()
    year, month = now.year, now.month
    
    # 只需要爬取前 5 页 (前 100 本) 
    max_pages = 5
    success_count = 0
    rank_counter = 1
    
    for page in range(1, max_pages + 1):
        logging.info(f"正在扫描当月月票榜 第 {page} 页 ...")
        api_books = fetch_monthly_ticket_list(page, limit=20)
        
        if not api_books:
            logging.warning("未能获取到书籍列表或到达页尾。")
            break
            
        for api_book in api_books:
            data = parse_book_detail_ultimate(api_book)
            data['rank_num'] = rank_counter
            rank_counter += 1
            
            if data and data.get('book_id'):
                if save_realtime_data(data):
                    success_count += 1
                    print(f"  [√] 实时记录更新: {data['title']} - 月票: {data['monthly_ticket']} 排名: {data['rank_num']}")
            
            time.sleep(random.uniform(0.5, 1.5))
            
        time.sleep(random.uniform(2, 4))

    print(f"\\n🎉 实时更新完成！共抓取并存入 {success_count} 条最新数据。")

if __name__ == '__main__':
    run_realtime_spider()
