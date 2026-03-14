
import pymysql

ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

def inspect_title(title):
    conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, record_year, record_month, record_day, monthly_tickets FROM zongheng_realtime_tracking WHERE title LIKE %s ORDER BY record_year DESC, record_month DESC, record_day DESC", (f'%{title}%',))
            records = cur.fetchall()
            print(f"Records for '{title}':")
            for r in records:
                print(r)
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_title("无敌天命")
