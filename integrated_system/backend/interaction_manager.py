"""
Interaction Manager
负责从对话历史中提取用于模型训练的交互特征
Features:
- Interaction turns (Engagement)
- Average reply length (Depth)
- User sentiment (Approximate)
- Last interaction time (Freshness)
"""
import pandas as pd
import numpy as np
from datetime import datetime
from chat_store import chat_store

class InteractionManager:
    def __init__(self):
        self.store = chat_store

    def get_interaction_features(self) -> pd.DataFrame:
        """
        从 chat_history 表中提取聚合特征
        Returns:
            DataFrame with index 'book_key' (platform|title|author)
            Columns: [interaction_turns, avg_user_len, avg_ai_len, engagement_score]
        """
        try:
            conn = self.store._connect()
            # 聚合查询：按书籍分组统计
            # 1. 总对话轮数
            # 2. 用户平均字数
            # 3. AI 平均字数
            # 4. 最近互动时间
            sql = """
            SELECT 
                book_key,
                COUNT(*) as total_msgs,
                SUM(CASE WHEN role='user' THEN 1 ELSE 0 END) as user_msgs,
                AVG(CASE WHEN role='user' THEN CHAR_LENGTH(content) ELSE 0 END) as avg_user_len,
                AVG(CASE WHEN role='assistant' THEN CHAR_LENGTH(content) ELSE 0 END) as avg_ai_len,
                MAX(created_at) as last_active
            FROM chat_history
            GROUP BY book_key
            """
            
            df = pd.read_sql(sql, conn)
            conn.close()
            
            if df.empty:
                return pd.DataFrame()
            
            # Feature Engineering
            # Engagement Score: 基础分为轮数，但也考虑深度（字数）
            # 简单的启发式公式：轮数 * 1.0 + 用户平均字数 * 0.1
            df['engagement_score'] = df['total_msgs'] * 1.0 + df['avg_user_len'] * 0.05
            
            # Normalize dates if needed (e.g., days since last active) - skipping for MVP
            
            # Set index for easy joining
            df.set_index('book_key', inplace=True)
            
            return df[['total_msgs', 'user_msgs', 'avg_user_len', 'avg_ai_len', 'engagement_score']]
            
        except Exception as e:
            print(f"[InteractionManager] Error extracting features: {e}")
            return pd.DataFrame()

# Global Instance
interaction_manager = InteractionManager()
