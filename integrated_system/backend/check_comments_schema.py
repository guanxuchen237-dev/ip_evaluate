"""
检查纵横评论表结构
"""
import pymysql

ZONGHENG_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'zongheng_analysis_v8',
    'charset': 'utf8mb4'
}

def check_comments_table():
    """检查评论表结构"""
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    cursor = conn.cursor()
    
    print("="*70)
    print("Table: zongheng_book_comments")
    print("="*70)
    
    # 获取列信息
    cursor.execute("DESCRIBE zongheng_book_comments")
    columns = cursor.fetchall()
    
    print(f"{'Column':<30} {'Type':<25} {'Null':<10}")
    print("-" * 70)
    for col in columns:
        print(f"{col[0]:<30} {col[1]:<25} {col[2]:<10}")
    
    # 获取数据量
    cursor.execute("SELECT COUNT(*) FROM zongheng_book_comments")
    count = cursor.fetchone()[0]
    print(f"\n总记录数: {count:,}")
    
    # 查看样本数据
    cursor.execute("""
        SELECT book_id, book_title, nickname, ip_region, content, comment_date 
        FROM zongheng_book_comments 
        LIMIT 5
    """)
    rows = cursor.fetchall()
    print(f"\n样本数据 (前5条):")
    for i, row in enumerate(rows, 1):
        print(f"{i}. 书籍: {row[1]}")
        print(f"   用户: {row[2]} | 地区: {row[3]}")
        print(f"   评论: {str(row[4])[:100]}...")
        print(f"   时间: {row[5]}")
        print()
    
    # 统计地区分布
    cursor.execute("""
        SELECT ip_region, COUNT(*) as cnt 
        FROM zongheng_book_comments 
        WHERE ip_region IS NOT NULL AND ip_region != ''
        GROUP BY ip_region 
        ORDER BY cnt DESC 
        LIMIT 20
    """)
    regions = cursor.fetchall()
    print("\n地区分布 (Top 20):")
    for region, cnt in regions:
        print(f"  {region}: {cnt:,}条")
    
    # 统计书籍覆盖
    cursor.execute("SELECT COUNT(DISTINCT book_id) FROM zongheng_book_comments")
    book_count = cursor.fetchone()[0]
    print(f"\n覆盖书籍数: {book_count:,}本")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_comments_table()
