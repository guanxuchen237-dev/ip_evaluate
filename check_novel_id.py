import pymysql

def check_db():
    conn = pymysql.connect(host='localhost', user='root', password='root', database='qidian_data', charset='utf8mb4')
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Check novel_id distribution
    cursor.execute("SELECT novel_id, COUNT(*) as cnt, COUNT(DISTINCT title) as titles FROM novel_monthly_stats GROUP BY novel_id HAVING titles > 1")
    rows = cursor.fetchall()
    print("Novel IDs with multiple titles:")
    for r in rows:
        print(r)

if __name__ == '__main__':
    check_db()
