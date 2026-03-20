import pymysql

# 查询起点月票分布
conn1 = pymysql.connect(host='localhost', user='root', password='root', database='qidian_data', cursorclass=pymysql.cursors.DictCursor)
with conn1.cursor() as cur:
    cur.execute('SELECT title, monthly_tickets_on_list FROM novel_monthly_stats WHERE year=2025 AND month=3 ORDER BY monthly_tickets_on_list DESC LIMIT 20')
    qidian_top = cur.fetchall()
    print('=== 起点月票TOP20 ===')
    for i, row in enumerate(qidian_top, 1):
        title = row['title'][:15] if len(row['title']) > 15 else row['title']
        print(f'{i}. {title}... 月票: {row["monthly_tickets_on_list"]}')
    
    cur.execute('SELECT MIN(monthly_tickets_on_list) as min_tkt, MAX(monthly_tickets_on_list) as max_tkt, AVG(monthly_tickets_on_list) as avg_tkt FROM novel_monthly_stats WHERE year=2025 AND month=3')
    stats = cur.fetchone()
    print(f'\n起点月票统计: 最低={stats["min_tkt"]}, 最高={stats["max_tkt"]}, 平均={stats["avg_tkt"]:.0f}')
conn1.close()

# 查询纵横月票分布
conn2 = pymysql.connect(host='localhost', user='root', password='root', database='zongheng_data', cursorclass=pymysql.cursors.DictCursor)
with conn2.cursor() as cur:
    cur.execute('SELECT 书名, 月票数, 月票排名 FROM zongheng_monthly_stats ORDER BY 月票数 DESC LIMIT 20')
    zongheng_top = cur.fetchall()
    print('\n=== 纵横月票TOP20 ===')
    for i, row in enumerate(zongheng_top, 1):
        title = row['书名'][:15] if len(row['书名']) > 15 else row['书名']
        print(f'{i}. {title}... 月票: {row["月票数"]} 排名: {row["月票排名"]}')
    
    cur.execute('SELECT MIN(月票数) as min_tkt, MAX(月票数) as max_tkt, AVG(月票数) as avg_tkt FROM zongheng_monthly_stats')
    stats = cur.fetchone()
    print(f'\n纵横月票统计: 最低={stats["min_tkt"]}, 最高={stats["max_tkt"]}, 平均={stats["avg_tkt"]:.0f}')
conn2.close()
