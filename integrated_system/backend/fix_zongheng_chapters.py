import pymysql

def fix_zongheng_chapters():
    conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='qidian_data', charset='utf8mb4')
    try:
        with conn.cursor() as cur:
            # 1. 优先删除 placeholder 占位符失效数据
            print("Removing 'placeholder' and low-quality data...")
            cur.execute("DELETE FROM zongheng_chapters WHERE source = 'placeholder'")
            print(f"Deleted {cur.rowcount} placeholder rows.")

            # 对于残留的内容（例如 scraped 和 playwright_sync 共存），优先保留字数更多的真实文本
            cur.execute("""
            DELETE t1 FROM zongheng_chapters t1
            INNER JOIN zongheng_chapters t2 
            WHERE 
                t1.id != t2.id AND 
                t1.title = t2.title AND 
                t1.chapter_num = t2.chapter_num AND
                LENGTH(t1.content) < LENGTH(t2.content);
            """)
            print(f"Deleted {cur.rowcount} shorter duplicate rows.")
            
            # 再处理字数完全一样的冗余，保留最大的 ID
            cur.execute("""
            DELETE t1 FROM zongheng_chapters t1
            INNER JOIN zongheng_chapters t2 
            WHERE 
                t1.id < t2.id AND 
                t1.title = t2.title AND 
                t1.chapter_num = t2.chapter_num;
            """)
            print(f"Deleted {cur.rowcount} identical duplicate rows.")

            # 对于残留的可能同一 title 和 chapter_num 仍然存在的情况（安全起见再次核查）
            
            # 2. 为 title 和 chapter_num 增加联合 UNIQUE 索引
            print("Adding UNIQUE constraint to (title, chapter_num)...")
            try:
                cur.execute("ALTER TABLE zongheng_chapters ADD UNIQUE KEY unique_title_chap (title(100), chapter_num)")
                print("UNIQUE index added successfully.")
            except pymysql.MySQLError as e:
                print(f"Index might already exist or error: {e}")

        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_zongheng_chapters()
