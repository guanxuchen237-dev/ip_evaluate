"""
检查章节表结构
"""
import pymysql

QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'qidian_data', 'charset': 'utf8mb4'
}
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

def check_chapter_tables():
    print("="*70)
    print("检查章节表结构")
    print("="*70)
    
    # 起点章节表
    print("\n【起点 - qidian_chapters】")
    conn = pymysql.connect(**QIDIAN_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SHOW COLUMNS FROM qidian_chapters")
    cols = cursor.fetchall()
    for col in cols:
        print(f"  {col[0]}: {col[1]}")
    conn.close()
    
    # 纵横章节表
    print("\n【纵横 - zongheng_chapters】")
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SHOW COLUMNS FROM zongheng_chapters")
    cols = cursor.fetchall()
    for col in cols:
        print(f"  {col[0]}: {col[1]}")
    conn.close()

if __name__ == "__main__":
    check_chapter_tables()
