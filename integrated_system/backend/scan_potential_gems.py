import pymysql
import sys
import os

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth import AUTH_DB_CONFIG
from data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG, DataManager
from ai_service import ai_service

NOVEL_INSIGHTS_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'novel_insights', 'charset': 'utf8mb4'
}

def fetch_realtime_trend(title):
    """从实时监控表查询书籍最近月票走势，供审计报告使用"""
    trend = {}
    for config_key, table_name in [('qidian', 'novel_realtime_tracking'), ('zongheng', 'zongheng_realtime_tracking')]:
        try:
            db_config = QIDIAN_CONFIG if config_key == 'qidian' else ZONGHENG_CONFIG
            conn = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                time_col = 'crawl_time'
                cur.execute(f"""
                    SELECT monthly_tickets, {time_col} 
                    FROM {table_name} 
                    WHERE title = %s 
                    ORDER BY {time_col} DESC LIMIT 10
                """, (title,))
                rows = cur.fetchall()
                if rows:
                    tickets = [int(r['monthly_tickets'] or 0) for r in rows]
                    latest = tickets[0]
                    oldest = tickets[-1] if len(tickets) > 1 else latest
                    growth = round((latest - oldest) / max(oldest, 1) * 100, 1) if oldest > 0 else 0
                    direction = '上升' if growth > 5 else ('下降' if growth < -5 else '稳定')
                    trend = {
                        'direction': direction,
                        'latest_tickets': latest,
                        'growth_rate': growth,
                        'data_points': len(rows),
                        'source': config_key
                    }
            conn.close()
            if trend:
                break
        except Exception as e:
            print(f"Realtime Trend Error ({config_key}): {e}")
    return trend


def fetch_vr_comments(title):
    comments_text = ""
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT content FROM zongheng_book_comments 
                WHERE book_title = %s 
                ORDER BY create_time DESC LIMIT 5
            """, (title,))
            rows = cur.fetchall()
            if rows:
                comments_text = "\n".join([f"- {r['content']}" for r in rows])
        conn.close()
    except Exception as e:
        print(f"VR Comments Error: {e}")
    return comments_text

def fetch_global_stats(title):
    stats = {}
    try:
        conn = pymysql.connect(**AUTH_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT translation_suitability, cultural_barrier, target_regions, overseas_revenue_prediction
                FROM global_market_potential
                WHERE book_title = %s
            """, (title,))
            row = cur.fetchone()
            if row: stats = row
        conn.close()
    except Exception as e:
        print(f"Global Stats Error: {e}")
    return stats

def fetch_ai_eval(title):
    stats = {}
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT overall_score, story_score, character_score, world_score, commercial_score, adaptation_score, safety_score, grade, risk_factor
                FROM ip_ai_evaluation
                WHERE title = %s LIMIT 1
            """, (title,))
            row = cur.fetchone()
            if row:
                stats = {
                    'overall': row['overall_score'],
                    'story': row['story_score'],
                    'character': row['character_score'],
                    'world': row['world_score'],
                    'commercial': row['commercial_score'],
                    'adaptation': row['adaptation_score'],
                    'safety': row['safety_score'],
                    'grade': row['grade'],
                    'risk_factor': row['risk_factor']
                }
        conn.close()
    except: pass
    return stats

def scan_and_trigger_gems(title_filter=None):
    gems_found = []
    normal_books = []
    
    print("[Gem Scanner] Starting potential gem scan with Deep AI Audit...")
    dm = DataManager()
    
    # 1. Zongheng
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            query = """
                SELECT r.title, r.author, r.category, MAX(r.monthly_ticket) as finance, MAX(r.total_rec) as interaction, MAX(r.word_count) as word_count
                FROM zongheng_book_ranks r
                WHERE 1=1
            """
            params = []
            if title_filter:
                query += " AND r.title = %s"
                params.append(title_filter)
            query += " GROUP BY r.title, r.author, r.category"
            cur.execute(query, tuple(params))
            for row in cur.fetchall():
                book_info = {
                    'title': row['title'],
                    'author': row['author'],
                    'category': row['category'],
                    'platform': 'Zongheng',
                    'finance': row['finance'] or 0,
                    'interaction': row['interaction'] or 0,
                    'word_count': row['word_count'] or 0
                }
                gems_found.append(book_info)
        conn.close()
    except Exception as e:
        print(f"[Gem Scanner] Zongheng scan error: {e}")

    # 2. Qidian (If not filtered out, we append)
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            query = """
                SELECT r.title, r.author, r.category, MAX(r.monthly_tickets_on_list) as finance, MAX(r.recommendation_count) as interaction, MAX(r.word_count) as word_count
                FROM novel_monthly_stats r
                WHERE 1=1
            """
            params = []
            if title_filter:
                query += " AND r.title = %s"
                params.append(title_filter)
            query += " GROUP BY r.title, r.author, r.category"
            cur.execute(query, tuple(params))
            for row in cur.fetchall():
                # Avoid duplicate title across platforms if doing massive scan
                if not any(g['title'] == row['title'] for g in gems_found):
                    book_info = {
                        'title': row['title'],
                        'author': row['author'],
                        'category': row['category'],
                        'platform': 'Qidian',
                        'finance': row['finance'] or 0,
                        'interaction': row['interaction'] or 0,
                        'word_count': row['word_count'] or 0
                    }
                    gems_found.append(book_info)
        conn.close()
    except Exception as e:
        print(f"[Gem Scanner] Qidian scan error: {e}")

    # If nothing found, try injecting just the title
    if not gems_found and title_filter:
        gems_found.append({
            'title': title_filter, 'author': '未知', 'category': '未知', 'platform': '未知',
            'finance': 0, 'interaction': 0, 'word_count': 0
        })

    inserted = 0
    try:
        conn = pymysql.connect(**AUTH_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        
        for bk in gems_found:
            title = bk['title']
            
            # 聚合各种外部数据
            vr_comments = fetch_vr_comments(title) or "暂无虚拟读者反馈"
            global_stats = fetch_global_stats(title)
            ai_eval_stats = fetch_ai_eval(title)
            realtime_trend = fetch_realtime_trend(title)

            # Predict Score
            realtime_latest = realtime_trend.get('latest_tickets', 0) if isinstance(realtime_trend, dict) else 0
            max_finance = max(bk['finance'], realtime_latest)
            
            predict_res = dm.predict_ip({
                'title': title, 
                'category': bk['category'],
                'word_count': bk.get('word_count', 0),
                'finance': max_finance,
                'interaction': bk.get('interaction', 0),
                'popularity': bk.get('interaction', 0) * 0.2
            })
            model_score = predict_res.get('score', 80.0)
            
            # 决定报告类型
            is_global = bool(global_stats) and global_stats.get('overseas_revenue_prediction') in ['S', 'A']
            is_gem = model_score >= 82 and bk['finance'] < 500
            
            risk_type = 'NORMAL'
            if is_global: risk_type = 'GLOBAL_GEM'
            elif is_gem: risk_type = 'POTENTIAL_GEM'
            
            # 只在每天限制一条深度报告以避免打扰
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM ip_audit_logs 
                    WHERE book_title = %s AND DATE(created_at) = CURDATE()
                """, (title,))
                if cur.fetchone():
                    # 已经扫描过
                    continue
            
            # 调用大模型生成深度 Markdown 报告
            report_markdown = ai_service.generate_comprehensive_audit(
                title=title, 
                author=bk['author'], 
                base_stats=bk, 
                ai_eval_stats=ai_eval_stats, 
                vr_comments=vr_comments, 
                global_stats=global_stats, 
                model_score=model_score,
                realtime_trend=realtime_trend
            )
            
            # 生成 snippet 显示
            snippet = f"深度审计已完成。实时预测分 {model_score}。详情参见展开报告。"
            if risk_type == 'GLOBAL_GEM': snippet = f"【出海优选】已通过出海潜力评估。预测分: {model_score}。目标市场: {global_stats.get('target_regions')}"
            
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ip_audit_logs 
                    (book_title, book_author, platform, risk_level, risk_type, content_snippet, score, trigger_source, status, markdown_report) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    title, bk['author'], bk['platform'], 
                    'Positive' if risk_type in ['POTENTIAL_GEM', 'GLOBAL_GEM'] else 'Low', 
                    risk_type, snippet, model_score, 'manual_scan', 'RESOLVED', report_markdown
                ))
            conn.commit()
            inserted += 1
            
        conn.close()
        print(f"[Gem Scanner] Triggered AI Deep audit logs for {inserted} new books.")
    except Exception as e:
        print(f"[Gem Scanner] Audit log insert error: {e}")
        import traceback
        traceback.print_exc()
        
    return inserted

if __name__ == '__main__':
    scan_and_trigger_gems()
