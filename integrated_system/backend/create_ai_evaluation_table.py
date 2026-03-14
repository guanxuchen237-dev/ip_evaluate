"""
建表脚本：创建 ip_ai_evaluation 表
存储每本书的六维 AI 评估数据
"""
import pymysql

# 使用与 data_manager.py 一致的数据库配置
DB_CONFIG = {
    'host': 'localhost', 'port': 3306,
    'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

SQL = """
CREATE TABLE IF NOT EXISTS ip_ai_evaluation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    author VARCHAR(100) DEFAULT '',
    platform VARCHAR(20) NOT NULL COMMENT 'Qidian / Zongheng',
    
    -- 六维评估分数 (0-100)
    story_score FLOAT DEFAULT 0 COMMENT '故事性',
    character_score FLOAT DEFAULT 0 COMMENT '人物塑造',
    world_score FLOAT DEFAULT 0 COMMENT '世界观',
    commercial_score FLOAT DEFAULT 0 COMMENT '商业价值',
    adaptation_score FLOAT DEFAULT 0 COMMENT '改编潜力',
    safety_score FLOAT DEFAULT 0 COMMENT '安全性',
    
    -- 综合评估
    overall_score FLOAT DEFAULT 0 COMMENT '综合 IP 分数',
    grade VARCHAR(5) DEFAULT '' COMMENT 'A+ / A / B+ / B / C / D',
    commercial_value VARCHAR(10) DEFAULT '' COMMENT '极高/高/中等/低',
    adaptation_difficulty VARCHAR(10) DEFAULT '' COMMENT '低/中等/高',
    risk_factor VARCHAR(10) DEFAULT '' COMMENT '低/中/高',
    healing_index INT DEFAULT 0 COMMENT '治愈指数 (0-100)',
    global_potential INT DEFAULT 0 COMMENT '全球化潜力 %',
    
    -- 评估方法标记
    eval_method VARCHAR(20) DEFAULT 'xgboost' COMMENT 'xgboost / kmeans / hybrid',
    
    evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_book (title, author, platform)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 六维评估数据表';
"""

if __name__ == '__main__':
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()
        print("[OK] ip_ai_evaluation 表创建成功")
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        conn.close()
