import pymysql
import sys

ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data', 'charset': 'utf8mb4'
}

def init_db():
    try:
        # 1. Qidian Data
        print("Connecting to qidian_data...")
        conn_qd = pymysql.connect(**QIDIAN_CONFIG)
        cursor_qd = conn_qd.cursor()
        
        # 1.1 Create novel_realtime_tracking
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS novel_realtime_tracking (
            id INT AUTO_INCREMENT PRIMARY KEY,
            novel_id VARCHAR(50),
            title VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
            record_year INT,
            record_month INT,
            monthly_tickets INT DEFAULT 0,
            collection_count INT DEFAULT 0,
            monthly_ticket_rank INT DEFAULT 0,
            crawl_time DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        cursor_qd.execute(create_table_sql)
        print("[OK] Created table novel_realtime_tracking")
        
        # 1.2 Add cover_url to novel_monthly_stats
        try:
            cursor_qd.execute("ALTER TABLE novel_monthly_stats ADD COLUMN cover_url VARCHAR(255)")
            print("[OK] Added cover_url to novel_monthly_stats")
        except pymysql.err.OperationalError as e:
            if 'Duplicate column name' in str(e):
                print("[SKIP] Column cover_url already exists in novel_monthly_stats")
            else:
                raise e
                
        conn_qd.commit()
        conn_qd.close()
        
        # 2. Zongheng Data
        print("Connecting to zongheng_analysis_v8...")
        try:
            conn_zh = pymysql.connect(**ZONGHENG_CONFIG)
            cursor_zh = conn_zh.cursor()
            
            # 1.3 Add cover_url to zongheng_book_ranks
            try:
                cursor_zh.execute("ALTER TABLE zongheng_book_ranks ADD COLUMN cover_url VARCHAR(255)")
                print("[OK] Added cover_url to zongheng_book_ranks")
            except pymysql.err.OperationalError as e:
                if 'Duplicate column name' in str(e):
                    print("[SKIP] Column cover_url already exists in zongheng_book_ranks")
                else:
                    raise e
                    
            conn_zh.commit()
            conn_zh.close()
        except pymysql.err.OperationalError as e:
             if 'Unknown database' in str(e):
                 print(f"[SKIP] Unknown Database: zongheng_analysis_v8. Ignoring...")
             else:
                 raise e
        
        print("\n🎉 Database migration finished successfully!")
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        sys.exit(1)

if __name__ == '__main__':
    init_db()
