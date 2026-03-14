import pymysql
conn = pymysql.connect(host='localhost', port=3306, user='root', password='root', database='zongheng_analysis_v8')
cur = conn.cursor()
cur.execute("SHOW COLUMNS FROM zongheng_book_ranks")
print("zongheng columns:")
for c in cur.fetchall():
    print("  ", c[0])
conn.close()
