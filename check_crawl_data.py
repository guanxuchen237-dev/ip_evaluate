import pymysql

QIDIAN_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'qidian_data',
    'charset': 'utf8mb4'
}

conn = pymysql.connect(**QIDIAN_CONFIG)
cursor = conn.cursor()

# 检查记录时间分布
cursor.execute("""
    SELECT DATE(crawl_time) as crawl_date, COUNT(*) as cnt
    FROM novel_realtime_tracking
    GROUP BY DATE(crawl_time)
    ORDER BY crawl_date DESC
    LIMIT 10
""")
print('=== 按日期统计 ===')
for row in cursor.fetchall():
    print(f'  {row[0]}: {row[1]}条')

# 检查今天的记录
cursor.execute("""
    SELECT title, monthly_tickets, crawl_time
    FROM novel_realtime_tracking
    WHERE DATE(crawl_time) = CURDATE()
    ORDER BY crawl_time DESC
    LIMIT 10
""")
print('\n=== 今天最新记录 ===')
for row in cursor.fetchall():
    print(f'  {row[0][:15]:15} | 月票: {row[1]:6} | {row[2]}')

conn.close()
