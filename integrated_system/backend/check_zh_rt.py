import pymysql
import json
from data_manager import ZONGHENG_CONFIG

try:
    conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM zongheng_realtime_tracking WHERE title = '齐天' ORDER BY crawl_time DESC LIMIT 3")
        rows = cur.fetchall()
        print(json.dumps(rows, indent=2, default=str))
    conn.close()
except Exception as e:
    print("Error:", e)
