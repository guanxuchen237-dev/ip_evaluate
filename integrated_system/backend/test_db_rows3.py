import pymysql
import json
from data_manager import ZONGHENG_CONFIG

conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
    cur.execute("SELECT id, title, platform, year, month, overall_score FROM ip_monthly_evaluation WHERE title IN ('无敌天命', '捞尸人')")
    rows = cur.fetchall()
    print(json.dumps(rows, indent=2, default=str))
conn.close()
