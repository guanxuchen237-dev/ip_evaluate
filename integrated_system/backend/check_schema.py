"""Check database schema for available fields"""
import pymysql

QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'qidian_data', 'charset': 'utf8mb4'
}
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

print("=" * 70)
print("QIDIAN - novel_monthly_stats columns:")
print("=" * 70)
conn = pymysql.connect(**QIDIAN_CONFIG)
cur = conn.cursor()
cur.execute("SHOW COLUMNS FROM novel_monthly_stats")
for col in cur.fetchall():
    print(f"  - {col[0]} ({col[1]})")
conn.close()

print("\n" + "=" * 70)
print("ZONGHENG - zongheng_book_ranks columns:")
print("=" * 70)
conn = pymysql.connect(**ZONGHENG_CONFIG)
cur = conn.cursor()
cur.execute("SHOW COLUMNS FROM zongheng_book_ranks")
for col in cur.fetchall():
    print(f"  - {col[0]} ({col[1]})")
conn.close()
