import pymysql
from collections import Counter

conn = pymysql.connect(host='localhost', user='root', password='root', database='qidian_data')
cur = conn.cursor()

# 检查2026-02-23的爬取情况
cur.execute('SELECT title, monthly_tickets, crawl_time FROM novel_realtime_tracking WHERE DATE(crawl_time)="2026-02-23" ORDER BY crawl_time')
rows = cur.fetchall()
print(f'2026-02-23 总数: {len(rows)}本')

# 时间分布
times = Counter([r[2].strftime('%H:%M') for r in rows])
print('\n时间分布:')
for t, c in sorted(times.items())[:10]:
    print(f'  {t}: {c}本')

# 检查月票数据
print('\n前10本书:')
for r in rows[:10]:
    print(f'  {r[0][:20]:20} | {r[1]:6} | {r[2]}')
