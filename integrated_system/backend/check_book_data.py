"""
检查数据库中是否有该书的章节数据和评论数据
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

print("=" * 70)
print("检查数据库中的章节数据和评论数据")
print("=" * 70)

book_title = '白手起家，蝙蝠侠干碎我的致富梦'

# 1. 检查起点章节数据
print(f"\n【起点章节数据】")
try:
    conn = pymysql.connect(**QIDIAN_CONFIG)
    
    # 检查是否有章节表
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES LIKE '%chapter%'")
    tables = cursor.fetchall()
    print(f"   章节相关表: {tables}")
    
    # 检查qidian_chapters表
    cursor.execute("SELECT COUNT(*) FROM qidian_chapters WHERE book_title LIKE %s", 
                   (f'%白手起家%',))
    count = cursor.fetchone()[0]
    print(f"   包含'白手起家'的章节数: {count}")
    
    if count > 0:
        cursor.execute("""
            SELECT book_title, chapter_index, chapter_title 
            FROM qidian_chapters 
            WHERE book_title LIKE %s 
            LIMIT 5
        """, (f'%白手起家%',))
        rows = cursor.fetchall()
        print(f"   示例章节:")
        for row in rows:
            print(f"      {row[0][:20]} | 第{row[1]}章: {row[2]}")
    
    conn.close()
except Exception as e:
    print(f"   错误: {e}")

# 2. 检查纵横章节数据
print(f"\n【纵横章节数据】")
try:
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES LIKE '%chapter%'")
    tables = cursor.fetchall()
    print(f"   章节相关表: {tables}")
    
    # 检查zongheng_chapters表
    cursor.execute("SELECT COUNT(*) FROM zongheng_chapters WHERE title LIKE %s", 
                   (f'%白手起家%',))
    count = cursor.fetchone()[0]
    print(f"   包含'白手起家'的章节数: {count}")
    
    conn.close()
except Exception as e:
    print(f"   错误: {e}")

# 3. 检查评论数据
print(f"\n【评论数据】")
try:
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES LIKE '%comment%'")
    tables = cursor.fetchall()
    print(f"   评论相关表: {tables}")
    
    # 检查zongheng_book_comments表
    cursor.execute("SELECT COUNT(*) FROM zongheng_book_comments WHERE book_title LIKE %s", 
                   (f'%白手起家%',))
    count = cursor.fetchone()[0]
    print(f"   包含'白手起家'的评论数: {count}")
    
    conn.close()
except Exception as e:
    print(f"   错误: {e}")

# 4. 检查起点月度数据中的简介
print(f"\n【起点月度数据-简介】")
try:
    conn = pymysql.connect(**QIDIAN_CONFIG)
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT title, synopsis 
        FROM novel_monthly_stats 
        WHERE title LIKE %s 
        LIMIT 1
    """, (f'%白手起家%',))
    row = cursor.fetchone()
    
    if row:
        print(f"   书名: {row[0]}")
        synopsis = row[1] if row[1] else '无简介'
        print(f"   简介: {synopsis[:100]}...")
    else:
        print(f"   未找到该书")
    
    conn.close()
except Exception as e:
    print(f"   错误: {e}")

# 5. 检查所有可用的书籍数据
print(f"\n【所有可用数据源】")
try:
    conn = pymysql.connect(**QIDIAN_CONFIG)
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT title, author, category, status, word_count,
               recommendation_count, monthly_ticket_count, collection_count,
               synopsis, is_vip, is_sign
        FROM novel_monthly_stats 
        WHERE title LIKE %s 
        ORDER BY year DESC, month DESC
        LIMIT 1
    """, (f'%白手起家%',))
    row = cursor.fetchone()
    
    if row:
        print(f"   书名: {row[0]}")
        print(f"   作者: {row[1]}")
        print(f"   题材: {row[2]}")
        print(f"   状态: {row[3]}")
        print(f"   字数: {row[4]}")
        print(f"   推荐: {row[5]}")
        print(f"   月票: {row[6]}")
        print(f"   收藏: {row[7]}")
        print(f"   VIP: {row[9]}")
        print(f"   签约: {row[10]}")
        
        synopsis = row[8] if row[8] else '无简介'
        print(f"   简介: {synopsis[:200]}...")
        
        # 可以用简介做情感分析
        print(f"\n   ✓ 有简介数据，可做情感分析")
    
    conn.close()
except Exception as e:
    print(f"   错误: {e}")

print("\n" + "=" * 70)
print("检查完成!")
print("=" * 70)
