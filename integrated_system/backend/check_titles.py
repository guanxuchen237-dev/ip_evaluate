
import pymysql

ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

def check_raw_titles():
    conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT HEX(title) as hex_title, title, monthly_tickets FROM zongheng_realtime_tracking WHERE title LIKE '%无敌天命%'")
            records = cur.fetchall()
            for r in records:
                print(r)
    finally:
        conn.close()

if __name__ == "__main__":
    check_raw_titles()
