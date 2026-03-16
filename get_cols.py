import pymysql
conn = pymysql.connect(host='localhost',user='root',password='root')
cursor = conn.cursor()
cursor.execute('DESCRIBE zongheng_analysis_v8.zongheng_book_ranks')
v8 = [r[0] for r in cursor.fetchall()]
cursor.execute('DESCRIBE zh_backup.zongheng_book_ranks')
bk = [r[0] for r in cursor.fetchall()]
print("---V8 COLUMNS---")
for c in v8: print(c)
print("---BACKUP COLUMNS---")
for c in bk: print(c)
