import pymysql
import sys
import os

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from auth import AUTH_DB_CONFIG
from data_manager import QIDIAN_CONFIG

def init_global_db():
    print("Connecting to Auth DB to create global_market_potential table...")
    try:
        conn = pymysql.connect(**AUTH_DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS global_market_potential (
                id INT AUTO_INCREMENT PRIMARY KEY,
                book_title VARCHAR(200) NOT NULL,
                translation_suitability FLOAT DEFAULT 50.0 COMMENT '翻译适配度(0-100)',
                cultural_barrier FLOAT DEFAULT 50.0 COMMENT '文化壁垒指数(0-100，越低越好)',
                target_regions VARCHAR(255) DEFAULT '东南亚,北美' COMMENT '主要推荐出海区域',
                overseas_revenue_prediction VARCHAR(100) DEFAULT '低' COMMENT '海外预期营收评级(S/A/B/C/低)',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY `uk_title` (`book_title`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            print("Table global_market_potential created/ensured.")
            
            # Insert some mock data for top books from Qidian to have something to show
            mock_data = [
                ("1979黄金时代", 60.5, 80.0, "东南亚,日韩", "B"),
                ("无敌天命", 95.0, 10.0, "全球,北美,欧洲", "S"),
                ("苟在妖武乱世修仙", 88.0, 30.0, "东南亚,北美", "A"),
                ("深海余烬", 90.0, 20.0, "欧洲,北美", "S"),
                ("灵境行者", 85.0, 40.0, "东南亚,日韩", "A"),
                ("光阴之外", 82.0, 45.0, "东南亚", "B"),
                ("赤心巡天", 75.0, 60.0, "东南亚华语区", "B")
            ]
            
            for d in mock_data:
                cur.execute("""
                    INSERT IGNORE INTO global_market_potential 
                    (book_title, translation_suitability, cultural_barrier, target_regions, overseas_revenue_prediction)
                    VALUES (%s, %s, %s, %s, %s)
                """, d)
            
        conn.commit()
        conn.close()
        print("Initialization of global market DB complete. Mock data inserted.")
    except Exception as e:
        print(f"Error initializing DB: {e}")

if __name__ == "__main__":
    init_global_db()
