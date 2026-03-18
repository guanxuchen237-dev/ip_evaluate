import pymysql
from datetime import datetime

conn = pymysql.connect(
    host='localhost', port=3306, user='root', password='root',
    database='qidian_data', charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
cur = conn.cursor()

# 查看最近5分钟爬取的记录数和去重书籍数
cur.execute("""
    SELECT COUNT(*) as total, COUNT(DISTINCT title) as unique_books
    FROM novel_realtime_tracking 
    WHERE crawl_time >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
""")
result = cur.fetchone()
print(f"最近5分钟: {result['total']}条记录, {result['unique_books']}本不同书籍")

# 查看所有时间段的书籍总数
cur.execute("SELECT COUNT(DISTINCT title) as total FROM novel_realtime_tracking")
total_books = cur.fetchone()
print(f"数据库中总书籍数: {total_books['total']}")

# 查看最新爬取的书籍
cur.execute("""
    SELECT title, monthly_tickets, crawl_time 
    FROM novel_realtime_tracking 
    ORDER BY crawl_time DESC
    LIMIT 10
""")
rows = cur.fetchall()
print(f"\n最新10条记录:")
for r in rows:
    print(f"  {r['crawl_time']} | {r['title'][:25]:25s} | 月票: {r['monthly_tickets']}")

conn.close()
