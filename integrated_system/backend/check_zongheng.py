import pymysql

conn = pymysql.connect(host='localhost', port=3306, user='root', password='root', database='zongheng_analysis_v8', charset='utf8mb4')
cur = conn.cursor()

# 检查year字段的分布
cur.execute("SELECT DISTINCT year FROM zongheng_book_ranks ORDER BY year")
years = cur.fetchall()
print(f'数据库中的年份: {[y[0] for y in years]}')

# 检查无敌天命的所有year/month数据
cur.execute("SELECT title, year, month, monthly_ticket FROM zongheng_book_ranks WHERE title LIKE '%无敌天命%' ORDER BY year, month")
results = cur.fetchall()
print(f'\n无敌天命数据条数: {len(results)}')
for r in results:
    print(f'  {r[1]}/{r[2]} - 月票{r[3]}')

# 检查是否有2024年的数据
cur.execute("SELECT COUNT(*) FROM zongheng_book_ranks WHERE year = 2024")
cnt_2024 = cur.fetchone()[0]
print(f'\n2024年数据条数: {cnt_2024}')

conn.close()
