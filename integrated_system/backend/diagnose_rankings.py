import pymysql
import pandas as pd
import numpy as np
import json
from data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG
from scipy.stats import rankdata

def debug_jianlai():
    print("--- Diagnosing 'Jian Lai' Ranking Issue ---")
    conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            # 1. 检查实时表
            cur.execute("SELECT * FROM zongheng_realtime_tracking WHERE title = '剑来' ORDER BY crawl_time DESC LIMIT 1")
            rt = cur.fetchone()
            print(f"Realtime Tickets: {rt['monthly_tickets'] if rt else 'N/A'}")
            
            # 2. 检查静态表最新数据
            cur.execute("SELECT * FROM zongheng_book_ranks WHERE title = '剑来' ORDER BY year DESC, month DESC LIMIT 1")
            st = cur.fetchone()
            print(f"Static Tickets: {st['monthly_ticket'] if st else 'N/A'}, WC: {st['word_count'] if st else 'N/A'}")
            
            # 3. 检查 AI 评估结果
            cur.execute("SELECT * FROM ip_ai_evaluation WHERE title = '剑来'")
            ai = cur.fetchone()
            if ai:
                print(f"AI Overall: {ai['overall_score']}, Comm: {ai['commercial_score']}, Method: {ai['eval_method']}")
            
            # 4. 统计有多少个 100 分
            cur.execute("SELECT COUNT(*) as cnt FROM ip_ai_evaluation WHERE overall_score >= 99.5")
            print(f"Books with Score >= 99.5: {cur.fetchone()['cnt']}")
            
            # 5. 列出前 20 名
            cur.execute("SELECT title, platform, overall_score, commercial_score FROM ip_ai_evaluation ORDER BY overall_score DESC LIMIT 20")
            print("\n--- Current Top 20 ---")
            top20 = cur.fetchall()
            for i, r in enumerate(top20):
                print(f"#{i+1} {r['title']} ({r['platform']}) - Score: {r['overall_score']}, Comm: {r['commercial_score']}")
                
    finally:
        conn.close()

if __name__ == "__main__":
    debug_jianlai()
