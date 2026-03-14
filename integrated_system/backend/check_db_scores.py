import pymysql
import sys

QIDIAN_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '', # replace with actual or let's import it
    'charset': 'utf8mb4'
}

from data_manager import ZONGHENG_CONFIG

conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
    cur.execute("SELECT title, overall_score, year, month FROM ip_monthly_evaluation WHERE title IN ('无敌天命', '捞尸人') ORDER BY overall_score DESC")
    rows = cur.fetchall()
    for r in rows:
        print(r)
conn.close()
