import pymysql
import json
import time
import hashlib
import traceback
import os
import sys

# 确保能导入 backend 下的模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from ai_service import ai_service
except ImportError:
    # 模拟环境处理
    class MockAIService:
        def generate_swot_report(self, title, abstract, stats=None):
            return {"radar_scores": {"innovation": 8, "story": 8, "character": 7, "world": 8, "commercial": 9}, "summary": "AI 评价回退"}
    ai_service = MockAIService()

DB_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

def get_book_context(conn, title, platform):
    """获取书籍的简介和最新统计数据作为 AI 输入"""
    # 逻辑：根据平台去对应的库找简介
    db_name = 'zongheng_analysis_v8' if platform == 'Zongheng' else 'qidian_data'
    table_name = 'zongheng_book_ranks' if platform == 'Zongheng' else 'novel_monthly_stats'
    abstract_col = 'abstract' if platform == 'Zongheng' else 'synopsis'
    
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        # 简单起见，从当前库的 evaluation 辅助信息里拿，或者直接去原库
        try:
            cur.execute(f"USE `{db_name}`")
            sql = f"SELECT {abstract_col} as abstract, MAX(monthly_ticket) as m_ticket, MAX(total_click) as clicks FROM {table_name} WHERE title=%s GROUP BY title LIMIT 1"
            if platform == 'Qidian':
                sql = f"SELECT {abstract_col} as abstract, MAX(monthly_ticket_count) as m_ticket, MAX(collection_count) as clicks FROM {table_name} WHERE title=%s GROUP BY title LIMIT 1"
            
            cur.execute(sql, (title,))
            res = cur.fetchone()
            cur.execute("USE `zongheng_analysis_v8`") # 切换回主库
            return res
        except:
            return None

def batch_audit():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            # 1. 找出需要审计的书籍（例如选取 2024年 8月的前 20 名作为深度示范，或者全量）
            print("[INFO] 正在提取待审计书籍列表...")
            cur.execute("""
                SELECT id, title, platform, author, year, month 
                FROM ip_monthly_evaluation 
                WHERE year=2024 AND month=8
                ORDER BY overall_score DESC LIMIT 50
            """)
            books = cur.fetchall()
            
            print(f"[INFO] 开始对 {len(books)} 本书籍进行 AI 深度审计...")
            
            for b in books:
                title = b['title']
                print(f"--> 正在审计: {title} ({b['platform']})")
                
                # 获取上下文
                context = get_book_context(conn, title, b['platform'])
                abstract = context['abstract'] if context and context['abstract'] else "暂无简介"
                stats = {
                    'finance': context['m_ticket'] if context else 0,
                    'popularity': context['clicks'] if context else 0
                }
                
                try:
                    # 调用 AI 核心审计逻辑
                    report = ai_service.generate_swot_report(title, abstract, stats)
                    
                    # 提取 AI 打分 (radar_scores 0-10)
                    scores = report.get('radar_scores', {})
                    # 将 AI 的 10 分制转换为 100 分制，并保留一位小数
                    story_ai = scores.get('story', 7) * 10
                    char_ai  = scores.get('character', 7) * 10
                    world_ai = scores.get('world', 7) * 10
                    comm_ai  = scores.get('commercial', 7) * 10
                    innov_ai = scores.get('innovation', 7) * 10
                    
                    # 重新计算 Overall Score (AI 权重占 40%，市场锚点占 60%)
                    # 这里复用之前的 m_score 逻辑，但为了脚本独立性，我们简单通过 DB 已有分值反推或直接用 AI 修正
                    # 建议：直接更新对应的细项，并重新加权
                    
                    cur.execute("""
                        UPDATE ip_monthly_evaluation 
                        SET story_score=%s, character_score=%s, world_score=%s, 
                            commercial_score=%s, adaptation_score=%s,
                            overall_score = (story_score*0.2 + character_score*0.1 + world_score*0.1 + commercial_score*0.4 + adaptation_score*0.1 + safety_score*0.1)
                        WHERE id=%s
                    """, (story_ai, char_ai, world_ai, comm_ai, innov_ai * 10, b['id']))
                    
                    print(f"   [OK] {title} 审计完成。新总分: 反映在数据库中")
                    
                    # 适当停顿避免 API 频率限制
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"   [ERR] {title} 审计失败: {e}")
            
            conn.commit()
            print("[SUCCESS] 批量 AI 审计任务执行完毕。")
            
    finally:
        conn.close()

if __name__ == "__main__":
    batch_audit()
