import pymysql
import json
from data_manager import ZONGHENG_CONFIG

conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
    print("--- zongheng_book_ranks (无敌天命) ---")
    cur.execute("SELECT year, month, monthly_ticket FROM zongheng_book_ranks WHERE title = '无敌天命' ORDER BY year DESC, month DESC")
    print(json.dumps(cur.fetchall(), indent=2))
conn.close()
