import pymysql
conn=pymysql.connect(host='localhost',port=3306,user='root',password='root',database='qidian_data',charset='utf8mb4')
cursor=conn.cursor(pymysql.cursors.DictCursor)
cursor.execute('SELECT title, novel_id FROM novel_monthly_stats WHERE title IN ("捞尸人", "星空之上", "玄鉴仙族", "宿命之环")')
rows = cursor.fetchall()
print(f'Found {len(rows)} books in DB:')
for r in rows:
    print(r)
cursor.execute('SELECT title, novel_id FROM novel_monthly_stats LIMIT 5')
print('Random 5 books from stats:')
for r in cursor.fetchall():
    print(r)
conn.close()
