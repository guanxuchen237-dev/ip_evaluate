import pymysql

def check_jianlai():
    conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='qidian_data', charset='utf8mb4')
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM zongheng_chapters WHERE title='剑来'")
            count = cur.fetchone()[0]
            print(f"Total chapters for exactly '剑来': {count}")

            cur.execute("SELECT id, title, chapter_num, chapter_title FROM zongheng_chapters WHERE title='剑来' ORDER BY chapter_num LIMIT 5")
            rows = cur.fetchall()
            for r in rows:
                print(r)
    finally:
        conn.close()

if __name__ == "__main__":
    check_jianlai()
