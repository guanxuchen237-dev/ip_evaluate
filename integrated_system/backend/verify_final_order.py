import pymysql
import json
from data_manager import ZONGHENG_CONFIG

conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
    print("--- ip_ai_evaluation (Latest Scores) ---")
    cur.execute("SELECT title, platform, commercial_score, overall_score, eval_method FROM ip_ai_evaluation WHERE title IN ('无敌天命', '捞尸人', '剑来', '齐天') ORDER BY overall_score DESC")
    print(json.dumps(cur.fetchall(), indent=2))
conn.close()
