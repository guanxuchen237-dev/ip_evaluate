import pymysql
conn=pymysql.connect(host='localhost',port=3306,user='root',password='root',database='qidian_data',charset='utf8mb4')
cursor=conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("SELECT novel_id, title FROM novel_monthly_stats WHERE abstract IS NOT NULL AND (latest_chapter IS NULL OR latest_chapter = '') LIMIT 5;")
rows = cursor.fetchall()
conn.close()
for r in rows: print(r)
