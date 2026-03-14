import pymysql
import pandas as pd
import json
from data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG

def get_platform_top10(platform, db_config):
    conn = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            if platform == "Qidian":
                table = "novel_monthly_stats"
                ticket_col = "monthly_tickets_on_list"
                pop_col = "collection_count"
                ir_col = "recommendation_count"
            else:
                table = "zongheng_book_ranks"
                ticket_col = "monthly_ticket"
                pop_col = "total_click"
                ir_col = "total_rec"
            
            cur.execute(f"""
                SELECT title, author, {ticket_col} as tickets, word_count, {pop_col} as popularity, {ir_col} as interaction
                FROM {table}
                WHERE (title, year, month) IN (
                    SELECT title, MAX(year), MAX(month) FROM {table} GROUP BY title
                )
                ORDER BY tickets DESC LIMIT 10
            """)
            rows = cur.fetchall()
            if not rows: return []
            
            titles = [r['title'] for r in rows]
            
            # Use ZONGHENG_CONFIG for ip_ai_evaluation if that's where it is
            cur.execute(f"SELECT * FROM ip_ai_evaluation WHERE title IN ({','.join(['%s']*len(titles))}) AND platform = %s", titles + [platform])
            evals = {r['title']: r for r in cur.fetchall()}
            
            best_rows = []
            for r in rows:
                ai = evals.get(r['title'], {})
                best_rows.append({
                    'title': r['title'],
                    'tickets': int(r['tickets']),
                    'wc': int(r['word_count']),
                    'pop': int(r['popularity']),
                    'ir': int(r['interaction']),
                    'ai_score': ai.get('overall_score', '--'),
                    'comm_score': ai.get('commercial_score', '--'),
                    'story_score': ai.get('story_score', '--'),
                    'method': ai.get('eval_method', '--')
                })
        return best_rows
    finally:
        conn.close()

results = {}
try:
    results["qidian"] = get_platform_top10("Qidian", QIDIAN_CONFIG)
except Exception as e: results["qidian_err"] = str(e)

try:
    results["zongheng"] = get_platform_top10("Zongheng", ZONGHENG_CONFIG)
except Exception as e: results["zongheng_err"] = str(e)

with open("analysis_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n[DONE] Results saved to analysis_results.json")
