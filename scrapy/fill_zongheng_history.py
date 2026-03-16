import sys
import os
import time
import random
import pymysql

sys.path.append(r'd:\ip-lumina-main\scrapy')
import zongheng_spider_v4

# 替换 proxy manager 使其直连
zongheng_spider_v4.proxy_manager.get_valid_proxy = lambda: None

DB_CONFIG = zongheng_spider_v4.DB_CONFIG

def fill_missing_data():
    conn = pymysql.connect(
        host=DB_CONFIG['host'], port=DB_CONFIG['port'],
        user=DB_CONFIG['user'], password=DB_CONFIG['password'],
        database=DB_CONFIG['database'], charset=DB_CONFIG['charset'],
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()
    
    # 获取 2020 到 2025 之间，且封面或者简介为空的数据
    sql = """
        SELECT book_id, title 
        FROM zongheng_book_ranks 
        WHERE year BETWEEN 2020 AND 2025 
        AND (cover_url IS NULL OR cover_url = '' OR abstract IS NULL OR abstract = '')
        GROUP BY book_id, title
    """
    cursor.execute(sql)
    books = cursor.fetchall()
    
    print(f"🔍 查找到 {len(books)} 本缺失数据的去重历史书籍，准备开始后台增量修补...")
    print("="*50)
    
    success_cnt = 0
    fail_cnt = 0
    
    for idx, b in enumerate(books):
        book_id = b['book_id']
        title = b['title']
        
        # 伪造一个 api_book 体以传给 parse 函数
        api_book = {'bookId': book_id, 'bookName': title}
        
        try:
            # 复用更新后的终极解析函数来抓取页面
            detail = zongheng_spider_v4.parse_book_detail_ultimate(api_book)
            
            c_url = detail.get('cover_url', '')
            abs_text = detail.get('abstract', '')
            l_chap = detail.get('latest_chapter', '')
            freq = detail.get('update_frequency', '')
            interv = detail.get('chapter_interval', '')
            
            if c_url or abs_text:
                up_sql = """
                    UPDATE zongheng_book_ranks 
                    SET cover_url=%s, abstract=%s, latest_chapter=%s, update_frequency=%s, chapter_interval=%s
                    WHERE book_id=%s
                """
                cursor.execute(up_sql, (c_url, abs_text, l_chap, freq, interv, book_id))
                conn.commit()
                print(f"[{idx+1}/{len(books)}] ✅ 修补成功: {title} (ID:{book_id})")
                success_cnt += 1
            else:
                print(f"[{idx+1}/{len(books)}] ⚠️ 解析为空: {title} (可能页面已下架/封禁)")
                fail_cnt += 1
                
        except Exception as e:
            print(f"[{idx+1}/{len(books)}] ❌ 发生异常: {title} - {e}")
            fail_cnt += 1
            
        # 增加随机休眠，防止短时间内高频请求导致直连被封
        time.sleep(random.uniform(0.5, 2.0))
        
    conn.close()
    print("="*50)
    print(f"🎉 历史数据修补执行完毕！成功更新: {success_cnt} 本，失败/空值: {fail_cnt} 本。")

if __name__ == "__main__":
    fill_missing_data()
