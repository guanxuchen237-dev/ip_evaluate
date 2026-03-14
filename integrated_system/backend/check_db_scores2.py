import pymysql
import sys

from data_manager import ZONGHENG_CONFIG

conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
    cur.execute("SELECT title, overall_score, year, month FROM ip_monthly_evaluation WHERE title IN ('无敌天命', '捞尸人') ORDER BY year DESC, month DESC")
    rows = cur.fetchall()
    for r in rows:
        print(r)
conn.close()
