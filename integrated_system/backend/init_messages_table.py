"""
留言板数据库初始化脚本
创建 messages 表用于存储用户与管理员之间的留言
"""
import pymysql
from auth import AUTH_DB_CONFIG

def init_messages_table():
    """创建留言板相关表"""
    try:
        conn = pymysql.connect(**AUTH_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cursor:
            # 创建留言表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    username VARCHAR(100) NOT NULL,
                    content TEXT NOT NULL,
                    is_admin_reply BOOLEAN DEFAULT FALSE,
                    admin_id INT NULL,
                    admin_name VARCHAR(100) NULL,
                    parent_id INT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at),
                    INDEX idx_is_read (is_read),
                    FOREIGN KEY (parent_id) REFERENCES messages(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            conn.commit()
            print("[OK] messages 表创建成功或已存在")
            
            # 检查是否需要添加新的列（兼容旧版本）
            try:
                cursor.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_urgent BOOLEAN DEFAULT FALSE")
                conn.commit()
                print("[OK] is_urgent 列已添加")
            except:
                pass
                
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] 创建 messages 表失败: {e}")
        return False

if __name__ == "__main__":
    init_messages_table()
