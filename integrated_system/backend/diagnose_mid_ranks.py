import pymysql
import json
from data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG

def check():
    conn_eval = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    conn_qidian = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    try:
        results = {}
        # 1. 评估结果
        with conn_eval.cursor() as cur:
            cur.execute("SELECT * FROM ip_ai_evaluation WHERE title = '苟在初圣魔门当人材'")
            results['ai'] = cur.fetchone()
            
            cur.execute("SELECT title, overall_score, commercial_score FROM ip_ai_evaluation WHERE platform='Qidian' ORDER BY overall_score DESC LIMIT 50")
            results['top50'] = cur.fetchall()
            
        # 2. 实时追踪
        with conn_qidian.cursor() as cur:
            cur.execute("SELECT * FROM novel_realtime_tracking WHERE title = '苟在初圣魔门当人材' ORDER BY crawl_time DESC LIMIT 1")
            results['rt'] = cur.fetchone()
            
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    finally:
        conn_eval.close()
        conn_qidian.close()

if __name__ == "__main__":
    check()
