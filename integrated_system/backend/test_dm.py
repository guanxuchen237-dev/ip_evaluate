import sys
sys.path.insert(0, r'd:\ip-lumina-main\integrated_system\backend')
from data_manager import DataManager

dm = DataManager()
res = dm.get_library_data(1, 5)
print("Items returned:")
for item in res['items']:
    print(f"Title: {item['title']}, IP_Score_final: {item['ip_score']}, overall_score: {item.get('overall_score')}")

import pandas as pd
import pymysql
from data_manager import ZONGHENG_CONFIG
eval_conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with eval_conn.cursor() as cur:
    cur.execute("SELECT title, overall_score FROM ip_monthly_evaluation WHERE title = '无敌天命'")
    print("DB:", cur.fetchall())
