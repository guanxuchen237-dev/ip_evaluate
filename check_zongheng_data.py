import pymysql
from datetime import datetime

# 检查 novel_monthly_stats 表结构和数据
conn = pymysql.connect(
    host='localhost', port=3306, user='root', password='root',
    database='qidian_data', charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
cur = conn.cursor()

# 表结构
cur.execute("SHOW COLUMNS FROM novel_monthly_stats")
print("=== novel_monthly_stats 表结构 ===")
for c in cur.fetchall():
    print(f"  {c['Field']}: {c['Type']}")

# 查看捞尸人的数据
cur.execute("SELECT * FROM novel_monthly_stats WHERE title LIKE '%捞尸人%' LIMIT 10")
rows = cur.fetchall()
print(f"\n=== 捞尸人数据 ({len(rows)}条) ===")
for r in rows:
    print(f"  {r}")

conn.close()
