import pymysql
import json
from data_manager import ZONGHENG_CONFIG

def check_book_details(title):
    print(f"--- Deep Diagnostic: {title} ---")
    conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            # 1. 检查各月原始数据（看看月票是不是一直不更新）
            cur.execute(f"SELECT year, month, monthly_ticket, total_click, total_rec FROM zongheng_book_ranks WHERE title = '{title}' ORDER BY year DESC, month DESC")
            ranks = cur.fetchall()
            print("\n[Static Ranks History]:")
            for r in ranks: print(r)
            
            # 2. 检查实时追踪（看看有没有实时数据）
            cur.execute(f"SELECT * FROM zongheng_realtime_tracking WHERE title = '{title}' ORDER BY crawl_time DESC LIMIT 1")
            rt = cur.fetchone()
            print(f"\n[Realtime Tracking]: {rt if rt else 'None (NOT ON RANK)'}")
            
            # 3. 检查当前 AI 评分详情
            cur.execute(f"SELECT * FROM ip_ai_evaluation WHERE title = '{title}'")
            ai = cur.fetchone()
            print(f"\n[AI Evaluation]: {ai if ai else 'None'}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_book_details("修仙：我在云疆养仙蚕")
    print("\n" + "="*50 + "\n")
    check_book_details("齐天")
