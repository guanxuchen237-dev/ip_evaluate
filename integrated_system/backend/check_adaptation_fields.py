"""
检查数据库中的改编状态字段
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

def check_adaptation_fields():
    print("="*70)
    print("检查数据库中的改编状态字段")
    print("="*70)
    
    # 1. 检查起点数据库
    print("\n【起点数据库 - qidian_data】")
    conn = pymysql.connect(**QIDIAN_CONFIG)
    cursor = conn.cursor()
    
    # 查看novel_monthly_stats表结构
    cursor.execute("SHOW COLUMNS FROM novel_monthly_stats LIKE '%adapt%'")
    adaptation_cols = cursor.fetchall()
    print(f"novel_monthly_stats 改编相关字段:")
    for col in adaptation_cols:
        print(f"  - {col[0]}: {col[1]}")
    
    # 查看novel_realtime_tracking表结构
    cursor.execute("SHOW COLUMNS FROM novel_realtime_tracking LIKE '%adapt%'")
    adaptation_cols = cursor.fetchall()
    print(f"novel_realtime_tracking 改编相关字段:")
    for col in adaptation_cols:
        print(f"  - {col[0]}: {col[1]}")
    
    # 查看所有表的列表
    cursor.execute("SHOW TABLES")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"\n所有表: {tables}")
    
    # 检查是否有其他可能包含改编信息的字段
    for table in ['novel_monthly_stats', 'novel_realtime_tracking']:
        cursor.execute(f"SHOW COLUMNS FROM {table}")
        all_cols = cursor.fetchall()
        interesting_cols = [c for c in all_cols if any(keyword in c[0].lower() for keyword in 
                          ['adapt', 'film', 'tv', 'movie', 'game', 'anime', 'drama', 'ip', '衍生'])]
        if interesting_cols:
            print(f"\n{table} 可能的改编相关字段:")
            for col in interesting_cols:
                print(f"  - {col[0]}: {col[1]}")
    
    conn.close()
    
    # 2. 检查纵横数据库
    print("\n【纵横数据库 - zongheng_analysis_v8】")
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("SHOW TABLES")
    tables = [t[0] for t in cursor.fetchall()]
    print(f"所有表: {tables}")
    
    for table in ['zongheng_book_ranks', 'zongheng_realtime_tracking']:
        if table in tables:
            cursor.execute(f"SHOW COLUMNS FROM {table}")
            all_cols = cursor.fetchall()
            interesting_cols = [c for c in all_cols if any(keyword in c[0].lower() for keyword in 
                              ['adapt', 'film', 'tv', 'movie', 'game', 'anime', 'drama', 'ip', '衍生', '改编'])]
            if interesting_cols:
                print(f"\n{table} 改编相关字段:")
                for col in interesting_cols:
                    print(f"  - {col[0]}: {col[1]}")
    
    conn.close()
    
    # 3. 检查ip_ai_evaluation表
    print("\n【检查ip_ai_evaluation表】")
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SHOW COLUMNS FROM ip_ai_evaluation LIKE '%adapt%'")
        cols = cursor.fetchall()
        if cols:
            print("ip_ai_evaluation 改编相关字段:")
            for col in cols:
                print(f"  - {col[0]}: {col[1]}")
        else:
            print("ip_ai_evaluation 无改编相关字段")
    except:
        print("ip_ai_evaluation 表不存在或无改编字段")
    
    conn.close()

if __name__ == "__main__":
    check_adaptation_fields()
