import pymysql
import json
import time
from playwright.sync_api import sync_playwright

def crawl_zongheng_chapters():
    # 1. 连接数据库获取纵横书籍 ID
    print("Connecting to MySQL to fetch novel_ids from zongheng_analysis_v8...")
    source_conn = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='root',
        database='zongheng_analysis_v8',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with source_conn.cursor() as cursor:
        cursor.execute("""
            SELECT book_id as novel_id, title 
            FROM zongheng_book_ranks 
            GROUP BY book_id, title
            ORDER BY MAX(monthly_ticket) DESC
        """)
        books = cursor.fetchall()
    source_conn.close()

    if not books:
        print("No books found in zongheng_book_ranks.")
        return

    # 2. 准备写入数据库的连接
    dest_conn = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='root',
        database='qidian_data',
        charset='utf8mb4'
    )
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for book in books:
            novel_id = str(book['novel_id'])
            title = book['title']
            catalog_url = f"https://book.zongheng.com/showchapter/{novel_id}.html"
            
            print(f"\nProcessing Book: {title} ({novel_id})")
            try:
                page.goto(catalog_url, timeout=30000)
                page.wait_for_selector('li.col-4 a', timeout=10000)
                
                # 获取章节链接
                links = page.eval_on_selector_all('li.col-4 a', 'nodes => nodes.map(n => n.href)')
                if not links:
                    print(f"No chapter links found for {title}")
                    continue
                
                # 取前 10 章
                target_links = links[:10]
                for idx, link in enumerate(target_links):
                    chapter_num = idx + 1
                    print(f"  Fetching Ch {chapter_num}: {link}")
                    
                    try:
                        page.goto(link, timeout=30000)
                        # 等待正文加载
                        page.wait_for_selector('div.content', timeout=10000)
                        
                        chapter_title = page.locator('div.title_txtbox').inner_text() if page.locator('div.title_txtbox').count() > 0 else f"第{chapter_num}章"
                        paragraphs = page.locator('div.content p').all_inner_texts()
                        content = "\n".join([p.strip() for p in paragraphs if p.strip()])
                        
                        if content:
                            # 插入/更新数据库
                            with dest_conn.cursor() as cur:
                                sql = """
                                    INSERT INTO zongheng_chapters (novel_id, title, chapter_num, chapter_title, content, source)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON DUPLICATE KEY UPDATE 
                                        chapter_title=VALUES(chapter_title),
                                        content=VALUES(content),
                                        source=VALUES(source)
                                """
                                cur.execute(sql, (novel_id, title, chapter_num, chapter_title, content, 'playwright_sync'))
                            dest_conn.commit()
                        else:
                            print(f"    Empty content for {title} Ch {chapter_num}")
                        
                        # 休眠一下避免太快
                        time.sleep(1)
                        
                    except Exception as ce:
                        print(f"    Error fetching chapter {link}: {ce}")
                        
            except Exception as be:
                print(f"  Error processing book {title}: {be}")
                
        browser.close()
    
    dest_conn.close()

if __name__ == "__main__":
    crawl_zongheng_chapters()
