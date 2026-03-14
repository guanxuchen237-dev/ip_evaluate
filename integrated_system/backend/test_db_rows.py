import pymysql
import sys

from data_manager import ZONGHENG_CONFIG
eval_conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with eval_conn.cursor() as cur:
    cur.execute("SELECT * FROM ip_monthly_evaluation WHERE title = '无敌天命'")
    rows = cur.fetchall()
    for r in rows:
        print(r)
