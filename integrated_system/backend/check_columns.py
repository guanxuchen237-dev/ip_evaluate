import pymysql
try:
    conn = pymysql.connect(host='localhost', user='root', password='root', database='qidian_data')
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM novel_monthly_stats")
    cols = cur.fetchall()
    print("--- Columns ---")
    for c in cols:
        print(c[0])
except Exception as e:
    print(e)
