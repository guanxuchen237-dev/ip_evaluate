import pymysql
from data_manager import ZONGHENG_CONFIG

conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
with conn.cursor() as cur:
    print("--- Stats Check ---")
    cur.execute("SELECT AVG(overall_score) as avg_score, COUNT(*) as total FROM ip_ai_evaluation")
    res = cur.fetchone()
    print(f"DB IP Score Avg: {res['avg_score']:.2f}")
    print(f"DB Total Books: {res['total']}")
conn.close()
