import pymysql
conn=pymysql.connect(host='localhost',port=3306,user='root',password='root',database='qidian_data',charset='utf8mb4')
cursor=conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("SELECT title, latest_chapter, synopsis, novel_id FROM novel_monthly_stats WHERE title LIKE '%仙道尽头%' OR title LIKE '%捞尸人%' LIMIT 5;")
rows = cursor.fetchall()
for r in rows:
    print(r)
print(f'Total {len(rows)}')
conn.close()
