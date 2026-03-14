import pymysql
import json
from data_manager import ZONGHENG_CONFIG

conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
    print("--- zongheng_book_ranks ---")
    cur.execute("SELECT * FROM zongheng_book_ranks WHERE title = '齐天' ORDER BY year DESC, month DESC LIMIT 3")
    print(json.dumps(cur.fetchall(), indent=2, default=str))

    print("\n--- ip_ai_evaluation ---")
    cur.execute("SELECT * FROM ip_ai_evaluation WHERE title = '齐天'")
    print(json.dumps(cur.fetchall(), indent=2, default=str))

from data_manager import QIDIAN_CONFIG
try:
    conn2 = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    with conn2.cursor() as cur2:
         print("\n--- qidian novel_monthly_stats ---")
         cur2.execute("SELECT * FROM novel_monthly_stats WHERE title = '齐天' ORDER BY year DESC, month DESC LIMIT 3")
         print(json.dumps(cur2.fetchall(), indent=2, default=str))
    conn2.close()
except:
    pass

conn.close()
