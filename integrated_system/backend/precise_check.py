import pymysql
import json
from data_manager import ZONGHENG_CONFIG

def check():
    conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        # 1. 检查 云疆养仙蚕
        cur.execute("SELECT title, overall_score, commercial_score, eval_method, grade FROM ip_ai_evaluation WHERE title LIKE '%云疆养仙蚕%'")
        jl = cur.fetchall()
        
        # 2. 检查 齐天
        cur.execute("SELECT title, overall_score, commercial_score, eval_method, grade FROM ip_ai_evaluation WHERE title = '齐天'")
        qt = cur.fetchone()
        
        # 3. 统计 100 分
        cur.execute("SELECT COUNT(*) as c100 FROM ip_ai_evaluation WHERE overall_score >= 99.5")
        c100 = cur.fetchone()['c100']
        
        # 4. 前 10 名
        cur.execute("SELECT title, platform, overall_score FROM ip_ai_evaluation ORDER BY overall_score DESC LIMIT 10")
        top10 = cur.fetchall()
        
    conn.close()
    
    res = {
        "yunjiang": jl,
        "qitian": qt,
        "count_100": c100,
        "top10": top10
    }
    print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    print(json.dumps(res, indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    check()
