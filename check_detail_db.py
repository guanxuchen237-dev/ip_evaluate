import pymysql
conn=pymysql.connect(host='localhost',port=3306,user='root',password='root',database='qidian_data',charset='utf8mb4')
cursor=conn.cursor(pymysql.cursors.DictCursor)
cursor.execute("SELECT title, latest_chapter, abstract FROM novel_monthly_stats WHERE title='我师兄实在太稳健了' or title='第一序列'")
rows = cursor.fetchall()
for r in rows:
    print(dict(r).get('title'), 'latest:', dict(r).get('latest_chapter'), 'abstract_len:', len(str(dict(r).get('abstract'))))
conn.close()
