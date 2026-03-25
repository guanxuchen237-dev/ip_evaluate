import pymysql
import sys
sys.path.insert(0, 'integrated_system/backend')
from data_manager import QIDIAN_CONFIG, ZONGHENG_CONFIG

# 查询起点实时数据表
conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
cur = conn.cursor()

# 获取月票范围
cur.execute("""
    SELECT MIN(monthly_tickets) as min_t, MAX(monthly_tickets) as max_t, COUNT(*) as cnt
    FROM novel_realtime_tracking 
""")
row = cur.fetchone()
print(f"月票范围: {row['min_t']} ~ {row['max_t']}, 共 {row['cnt']} 条记录")

# 获取月票最低的10本作品
cur.execute("""
    SELECT title, monthly_tickets 
    FROM novel_realtime_tracking 
    ORDER BY monthly_tickets ASC
    LIMIT 10
""")
print("\n=== 月票最低的10本 ===")
for row in cur.fetchall():
    print(f"《{row['title']}》 - 月票: {row['monthly_tickets']}")

# 获取月票最高的10本
cur.execute("""
    SELECT title, monthly_tickets 
    FROM novel_realtime_tracking 
    ORDER BY monthly_tickets DESC
    LIMIT 10
""")
print("\n=== 月票最高的10本 ===")
for row in cur.fetchall():
    print(f"《{row['title']}》 - 月票: {row['monthly_tickets']:,}")

conn.close()
