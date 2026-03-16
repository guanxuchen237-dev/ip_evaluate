"""
检查章节表结构
"""
import pymysql

# 数据库配置
QIDIAN_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'qidian_data',
    'charset': 'utf8mb4'
}

ZONGHENG_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'zongheng_analysis_v8',
    'charset': 'utf8mb4'
}

def check_table_structure(config, table_name):
    """检查表结构"""
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    print(f"\n{'='*60}")
    print(f"Table: {table_name}")
    print(f"{'='*60}")
    
    # 获取列信息
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    
    print(f"{'Column':<30} {'Type':<20} {'Null':<10}")
    print("-" * 60)
    for col in columns:
        print(f"{col[0]:<30} {col[1]:<20} {col[2]:<10}")
    
    # 获取数据量
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"\nTotal records: {count}")
    
    # 查看样本数据
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
    rows = cursor.fetchall()
    print(f"\nSample data (first 2 rows):")
    for i, row in enumerate(rows, 1):
        print(f"Row {i}: {row[:5]}...")  # 只显示前5列
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    # 检查起点章节表
    check_table_structure(QIDIAN_CONFIG, 'qidian_chapters')
    
    # 检查纵横章节表
    check_table_structure(ZONGHENG_CONFIG, 'zongheng_chapters')
