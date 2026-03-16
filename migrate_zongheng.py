"""
迁移脚本：将 zongheng_chapters 表从 qidian_data 移动到 zongheng_analysis_v8
"""
import pymysql

# 数据库配置
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data', 'charset': 'utf8mb4'
}

ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

def migrate_table():
    print("开始迁移 zongheng_chapters 表...")
    
    # 连接到 zongheng_analysis_v8 创建表
    conn_target = pymysql.connect(**ZONGHENG_CONFIG)
    cursor_target = conn_target.cursor()
    
    # 创建数据库（如果不存在）
    cursor_target.execute("CREATE DATABASE IF NOT EXISTS zongheng_analysis_v8 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor_target.execute("USE zongheng_analysis_v8")
    
    # 创建表结构（匹配源表）
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS zongheng_chapters (
        id INT AUTO_INCREMENT PRIMARY KEY,
        novel_id VARCHAR(50) DEFAULT NULL,
        title VARCHAR(255) NOT NULL,
        chapter_num INT NOT NULL,
        chapter_title VARCHAR(255) DEFAULT NULL,
        content MEDIUMTEXT,
        source VARCHAR(50) DEFAULT 'scrapy',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_title_chapter (title, chapter_num),
        INDEX idx_novel_id (novel_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    cursor_target.execute(create_table_sql)
    conn_target.commit()
    print("✓ 目标表结构创建完成")
    
    # 确保 created_at 列存在
    try:
        cursor_target.execute("ALTER TABLE zongheng_chapters ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
        conn_target.commit()
    except:
        pass  # 列已存在或表已创建时忽略
    
    # 连接到 qidian_data 读取数据
    conn_source = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    cursor_source = conn_source.cursor()
    
    # 获取数据
    cursor_source.execute("SELECT id, novel_id, title, chapter_num, chapter_title, content, source, created_at FROM zongheng_chapters")
    rows = cursor_source.fetchall()
    print(f"✓ 从 qidian_data 读取到 {len(rows)} 条记录")
    
    if len(rows) == 0:
        print("⚠ 没有数据需要迁移")
        return
    
    # 插入数据到目标库
    insert_sql = """
    INSERT INTO zongheng_chapters 
        (id, novel_id, title, chapter_num, chapter_title, content, source, created_at)
    VALUES 
        (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        novel_id = VALUES(novel_id),
        chapter_title = VALUES(chapter_title),
        content = VALUES(content),
        source = VALUES(source),
        created_at = VALUES(created_at)
    """
    
    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        data = [(r['id'], r['novel_id'], r['title'], r['chapter_num'], r['chapter_title'], r['content'], r['source'], r['created_at']) for r in batch]
        cursor_target.executemany(insert_sql, data)
        conn_target.commit()
        print(f"✓ 已迁移 {min(i+batch_size, len(rows))}/{len(rows)} 条记录")
    
    # 验证结果
    cursor_target.execute("SELECT COUNT(*) as cnt FROM zongheng_chapters")
    result = cursor_target.fetchone()
    print(f"\n迁移完成！zongheng_analysis_v8.zongheng_chapters 现有 {result[0]} 条记录")
    
    cursor_source.close()
    conn_source.close()
    cursor_target.close()
    conn_target.close()
    
    print("\n现在可以重启后端服务了！")

if __name__ == '__main__':
    try:
        migrate_table()
    except Exception as e:
        print(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
