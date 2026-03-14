import pymysql

QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data', 'charset': 'utf8mb4'
}

ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

def fix_table(config, table_name, platform):
    print(f"[{platform}] Fixing table {table_name}...")
    conn = pymysql.connect(**config)
    try:
        with conn.cursor() as cur:
            # 1. Add record_day column
            try:
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN record_day INT")
                print(f"[{platform}] Added record_day column.")
            except pymysql.err.OperationalError as e:
                print(f"[{platform}] record_day column might already exist: {e}")
            
            # 2. Update record_day using crawl_time where NULL
            cur.execute(f"UPDATE {table_name} SET record_day = DAY(crawl_time) WHERE record_day IS NULL")
            print(f"[{platform}] Updated record_day values.")
            
            # 3. Handle NULLs just in case
            cur.execute(f"UPDATE {table_name} SET record_day = 1 WHERE record_day IS NULL")

            # 4. Deduplicate: keep the row with max id for each (novel_id, record_year, record_month, record_day)
            print(f"[{platform}] Finding and removing duplicates...")
            cur.execute(f"""
                CREATE TEMPORARY TABLE __temp_keep AS
                SELECT MAX(id) as max_id
                FROM {table_name}
                GROUP BY novel_id, record_year, record_month, record_day
            """)
            
            cur.execute(f"""
                DELETE FROM {table_name}
                WHERE id NOT IN (SELECT max_id FROM __temp_keep)
            """)
            print(f"[{platform}] Deleted duplicate rows.")
            
            # 5. Add unique index
            try:
                cur.execute(f"ALTER TABLE {table_name} ADD UNIQUE INDEX uk_novel_date (novel_id, record_year, record_month, record_day)")
                print(f"[{platform}] Added unique constraint uk_novel_date.")
            except pymysql.err.OperationalError as e:
                print(f"[{platform}] Unique constraint might already exist: {e}")
                
        conn.commit()
        print(f"[{platform}] Successfully fixed {table_name}.")
    except Exception as e:
        print(f"[{platform}] Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_table(QIDIAN_CONFIG, "novel_realtime_tracking", "Qidian")
    fix_table(ZONGHENG_CONFIG, "zongheng_realtime_tracking", "Zongheng")
