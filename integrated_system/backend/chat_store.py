"""
角色扮演对话历史存储模块
Chat history persistence for Roleplay feature (MySQL)
"""
import pymysql
import json
from datetime import datetime
from typing import List, Dict, Optional

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'lumina_roleplay',
    'charset': 'utf8mb4'
}

class ChatStore:
    """对话历史存储类"""
    
    def __init__(self):
        """初始化：确保数据库和表存在"""
        self._ensure_database()
        self._ensure_table()
    
    def _connect(self, use_db: bool = True) -> pymysql.connections.Connection:
        """获取数据库连接"""
        config = DB_CONFIG.copy()
        if not use_db:
            config.pop('database')
        return pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
    
    def _ensure_database(self):
        """确保数据库存在"""
        try:
            conn = self._connect(use_db=False)
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            conn.close()
            print(f"[OK] Database '{DB_CONFIG['database']}' ready")
        except Exception as e:
            print(f"[ERROR] Database creation error: {e}")
    
    def _ensure_table(self):
        """确保表存在"""
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(64) NOT NULL DEFAULT 'default_user',
                        book_key VARCHAR(255) NOT NULL COMMENT 'platform|title|author',
                        character_name VARCHAR(100) NOT NULL,
                        role ENUM('user', 'assistant') NOT NULL,
                        content TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_conversation (user_id, book_key, character_name),
                        INDEX idx_created (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
            conn.commit()
            conn.close()
            print("[OK] Table 'chat_history' ready")
        except Exception as e:
            print(f"[ERROR] Table creation error: {e}")
    
    def save_message(self, user_id: str, book_key: str, character_name: str, 
                     role: str, content: str) -> bool:
        """
        保存单条消息
        
        Args:
            user_id: 用户标识
            book_key: 书籍键 (格式: platform|title|author)
            character_name: 角色名
            role: 'user' 或 'assistant'
            content: 消息内容
        """
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO chat_history (user_id, book_key, character_name, role, content)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, book_key, character_name, role, content))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] Save message error: {e}")
            return False
    
    def get_history(self, user_id: str, book_key: str, character_name: str, 
                    limit: int = 50) -> List[Dict]:
        """
        获取对话历史
        
        Returns:
            对话列表 [{role, content, created_at}, ...]
        """
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT role, content, created_at
                    FROM chat_history
                    WHERE user_id = %s AND book_key = %s AND character_name = %s
                    ORDER BY created_at ASC
                    LIMIT %s
                """, (user_id, book_key, character_name, limit))
                rows = cur.fetchall()
            conn.close()
            
            # 转换 datetime 为字符串
            result = []
            for row in rows:
                result.append({
                    'role': row['role'],
                    'content': row['content'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                })
            return result
        except Exception as e:
            print(f"[ERROR] Get history error: {e}")
            return []
    
    def clear_history(self, user_id: str, book_key: str, character_name: str) -> bool:
        """清空指定对话的历史"""
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM chat_history
                    WHERE user_id = %s AND book_key = %s AND character_name = %s
                """, (user_id, book_key, character_name))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] Clear history error: {e}")
            return False
    
    def get_conversation_count(self, user_id: str, book_key: str, character_name: str) -> int:
        """获取对话消息数量"""
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as cnt
                    FROM chat_history
                    WHERE user_id = %s AND book_key = %s AND character_name = %s
                """, (user_id, book_key, character_name))
                row = cur.fetchone()
            conn.close()
            return row['cnt'] if row else 0
        except Exception as e:
            print(f"[ERROR] Count error: {e}")
            return 0

# 全局实例
chat_store = ChatStore()
