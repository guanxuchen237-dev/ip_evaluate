import pymysql
import json
from data_manager import ZONGHENG_CONFIG

def check():
    conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    titles = ['苟在初圣魔门当人材', '大乾武圣!', '真实历史游戏：只有我知道剧情']
    results = []
    with conn.cursor() as cur:
        for t in titles:
            cur.execute("SELECT title, overall_score, commercial_score, eval_method, grade FROM ip_ai_evaluation WHERE title = %s", (t,))
            results.append(cur.fetchone())
            
        # 再看一眼齐天
        cur.execute("SELECT title, overall_score FROM ip_ai_evaluation WHERE title = '齐天'")
        results.append(cur.fetchone())
        
    conn.close()
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    check()
