import pymysql
import sys

ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data', 'charset': 'utf8mb4'
}

def check_db(name, config):
    try:
        conn = pymysql.connect(**config)
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = [row[0] for row in cur.fetchall()]
            print(f"--- {name} Tables ---")
            for t in tables:
                if 'chapter' in t.lower() or 'content' in t.lower():
                    cur.execute(f"SELECT COUNT(*) FROM {t}")
                    count = cur.fetchone()[0]
                    print(f" - {t}: {count} rows")
    except Exception as e:
        print(f"Error connecting to {name}: {e}")

check_db("ZONGHENG (zongheng_analysis_v8)", ZONGHENG_CONFIG)
check_db("QIDIAN (qidian_data)", QIDIAN_CONFIG)

