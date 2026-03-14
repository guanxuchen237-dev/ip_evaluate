import pymysql
from data_manager import ZONGHENG_CONFIG

def check():
    conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        cur.execute("SELECT title, overall_score, commercial_score, grade FROM ip_ai_evaluation WHERE title LIKE '%云疆养仙蚕%'")
        res = cur.fetchall()
        print("Results for 云疆养仙蚕:")
        for r in res:
            print(r)
    conn.close()

if __name__ == "__main__":
    check()
