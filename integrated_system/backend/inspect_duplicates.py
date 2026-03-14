
import pymysql
import json

ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

def inspect_data():
    conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("SHOW COLUMNS FROM zongheng_realtime_tracking")
            columns = cur.fetchall()
            print("Columns in zongheng_realtime_tracking:")
            for col in columns:
                print(f" - {col['Field']} ({col['Type']})")
            
            # Check duplicates for "无敌天命"
            print("\nRecords for '无敌天命':")
            cur.execute("SELECT * FROM zongheng_realtime_tracking WHERE title LIKE '%无敌天命%'")
            records = cur.fetchall()
            for r in records:
                print(r)
                
            # Check for general duplicates (same title)
            print("\nPotential duplicates (Title, Platform) with counts > 1:")
            cur.execute("""
                SELECT title, COUNT(*) as count 
                FROM zongheng_realtime_tracking 
                GROUP BY title 
                HAVING count > 1
                ORDER BY count DESC
                LIMIT 10
            """)
            dups = cur.fetchall()
            for d in dups:
                print(d)
                
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_data()
