import pymysql
import json
from data_manager import QIDIAN_CONFIG

conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
    print("--- novel_monthly_stats (捞尸人) ---")
    cur.execute("SELECT year, month, monthly_ticket FROM novel_monthly_stats WHERE title = '捞尸人' ORDER BY year DESC, month DESC LIMIT 5")
    print(json.dumps(cur.fetchall(), indent=2))
conn.close()
