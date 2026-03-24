import pymysql
import sys
import os
import joblib
import numpy as np

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth import AUTH_DB_CONFIG
from data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG, DataManager
from ai_service import ai_service

NOVEL_INSIGHTS_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'novel_insights', 'charset': 'utf8mb4'
}

# 加载用户的 model_j_oracle_v7 模型
ORACLE_MODEL = None
try:
    model_path = os.path.join(os.path.dirname(__file__), 'resources', 'models', 'model_j_oracle_v7.pkl')
    if os.path.exists(model_path):
        model_data = joblib.load(model_path)
        ORACLE_MODEL = model_data
        print(f"[Gem Scanner] Loaded model_j_oracle_v7.pkl successfully")
except Exception as e:
    print(f"[Gem Scanner] Failed to load model_j_oracle_v7: {e}")

def predict_with_oracle_model(word_count, total_recommend, platform='Qidian'):
    """使用 model_j_oracle_v7 进行预测"""
    if not ORACLE_MODEL:
        return None
    
    try:
        model = ORACLE_MODEL.get('ip_model')
        rank_mapping = ORACLE_MODEL.get('rank_ticket_mapping', {}).get(platform, {})
        
        if not model:
            return None
        
        # 模型只接受2个特征: word_count, total_recommend
        features = np.array([[word_count, total_recommend]])
        predicted_score = model.predict(features)[0]
        
        # 根据预测分数映射等级
        if predicted_score >= 90:
            grade = 'S'
        elif predicted_score >= 80:
            grade = 'A'
        elif predicted_score >= 70:
            grade = 'B'
        elif predicted_score >= 60:
            grade = 'C'
        else:
            grade = 'D'
        
        return {
            'score': predicted_score,
            'grade': grade,
            'model': 'oracle_v7'
        }
    except Exception as e:
        print(f"[Oracle Model] Prediction error: {e}")
        return None

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
    """
    扫描潜力遗珠并触发深度AI审计。
    基于实时数据筛选高分、高潜力的优质作品。
    """
    dm = DataManager()
    gems_found = []
    
    # 从多个数据源获取实时数据
    # 1. Zongheng 数据
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            # 获取有数据的作品 - 使用 zongheng_book_ranks 表（按月度统计）
            cur.execute("""
                SELECT title, author, category, 
                       total_rec as finance, monthly_ticket as monthly_tickets, word_count,
                       total_click as collection_count, total_click as interaction, 0 as reward_count, 0 as fans_count
                FROM zongheng_book_ranks
                WHERE word_count > 50000 OR monthly_ticket > 0
                ORDER BY monthly_ticket DESC
                LIMIT 100
            """)
            rows = cur.fetchall()
            print(f"[Gem Scanner] Zongheng found {len(rows)} books")
            for row in rows:
                book_info = {
                    'title': row['title'],
                    'author': row['author'],
                    'category': row['category'],
                    'platform': 'Zongheng',
                    'finance': row['finance'] or 0,
                    'interaction': row.get('interaction', 0) or 0,
                    'word_count': row['word_count'] or 0,
                    'collection_count': row.get('collection_count', 0) or 0,
                    'reward_count': row.get('reward_count', 0) or 0,
                    'fans_count': row.get('fans_count', 0) or 0,
                    'monthly_tickets': row.get('monthly_tickets', 0) or 0
                }
                gems_found.append(book_info)
        conn.close()
    except Exception as e:
        print(f"[Gem Scanner] Zongheng scan error: {e}")
        import traceback
        traceback.print_exc()

    # 2. Qidian 数据
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            # 获取有数据的起点作品（扩展字段）
            cur.execute("""
                SELECT DISTINCT m.title, m.author, m.category,
                       MAX(m.monthly_tickets_on_list) as finance,
                       MAX(m.recommendation_count) as interaction,
                       MAX(m.word_count) as word_count,
                       MAX(m.collection_count) as collection_count,
                       MAX(m.reward_count) as reward_count,
                       MAX(m.collection_rank) as collection_rank,
                       MAX(m.monthly_ticket_rank) as ticket_rank
                FROM novel_monthly_stats m
                WHERE m.word_count > 50000 OR m.monthly_tickets_on_list > 0
                GROUP BY m.title, m.author, m.category
                ORDER BY MAX(m.monthly_tickets_on_list) DESC
                LIMIT 100
            """)
            rows = cur.fetchall()
            print(f"[Gem Scanner] Qidian found {len(rows)} books")
            for row in rows:
                # 避免跨平台重复
                if not any(g['title'] == row['title'] for g in gems_found):
                    book_info = {
                        'title': row['title'],
                        'author': row['author'],
                        'category': row['category'],
                        'platform': 'Qidian',
                        'finance': row['finance'] or 0,
                        'interaction': row['interaction'] or 0,
                        'word_count': row['word_count'] or 0,
                        'collection_count': row.get('collection_count', 0) or 0,
                        'reward_count': row.get('reward_count', 0) or 0,
                        'collection_rank': row.get('collection_rank', 9999) or 9999,
                        'ticket_rank': row.get('ticket_rank', 9999) or 9999
                    }
                    gems_found.append(book_info)
        conn.close()
    except Exception as e:
        print(f"[Gem Scanner] Qidian scan error: {e}")

    # 如果指定了特定书名，优先处理
    if title_filter:
        # 检查是否已在列表中
        existing = [g for g in gems_found if g['title'] == title_filter]
        if not existing:
            gems_found.insert(0, {
                'title': title_filter, 'author': '未知', 'category': '未知', 'platform': '未知',
                'finance': 0, 'interaction': 0, 'word_count': 0
            })
        else:
            # 将指定的书移到最前面
            gems_found.remove(existing[0])
            gems_found.insert(0, existing[0])

    total_scanned = len(gems_found)
    inserted = 0
    gems_count = 0
    global_gems_count = 0
    
    try:
        conn = pymysql.connect(**AUTH_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        
        for bk in gems_found:
            title = bk['title']
            
            # 当天去重：只检查当天是否已扫描，允许每天重新评估
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, risk_type FROM ip_audit_logs 
                    WHERE book_title = %s AND trigger_source = 'manual_scan'
                    AND DATE(created_at) = CURDATE()
                    ORDER BY created_at DESC LIMIT 1
                """, (title,))
                existing = cur.fetchone()
                if existing:
                    # 当天已扫描过，跳过
                    print(f"[Gem Scanner] Skipping '{title}' - already scanned today")
                    continue
            
            # 聚合各种外部数据
            vr_comments = fetch_vr_comments(title) or "暂无虚拟读者反馈"
            global_stats = fetch_global_stats(title)
            ai_eval_stats = fetch_ai_eval(title)
            realtime_trend = fetch_realtime_trend(title)

            # Predict Score - 结合实时数据
            realtime_latest = realtime_trend.get('latest_tickets', 0) if isinstance(realtime_trend, dict) else 0
            max_finance = max(bk['finance'], realtime_latest)
            
            # 使用现有模型预测
            predict_res = dm.predict_ip({
                'title': title, 
                'category': bk['category'],
                'word_count': bk.get('word_count', 0),
                'finance': max_finance,
                'interaction': bk.get('interaction', 0),
                'popularity': bk.get('interaction', 0) * 0.2
            })
            model_score = predict_res.get('score', 80.0)
            
            # 使用用户的 oracle_v7 模型预测
            oracle_result = predict_with_oracle_model(
                word_count=bk.get('word_count', 0),
                total_recommend=bk.get('interaction', 0),
                platform=bk.get('platform', 'Qidian')
            )
            oracle_score = oracle_result.get('score', 0) if oracle_result else 0
            oracle_grade = oracle_result.get('grade', 'D') if oracle_result else 'D'
            
            # 综合评分：取两者较高值
            final_score = max(model_score, oracle_score) if oracle_score > 0 else model_score
            
            # ========== 严格判定逻辑：真正的潜力遗珠 ==========
            # 必须同时满足：
            # 1. 月票持续增长（不是一次性高分）
            # 2. 数据稳定性（有足够历史数据点）
            # 3. 高评分（综合评分>=85）
            # 4. 基础数据门槛（月票>1000，字数>10万）
            
            # 基础门槛
            word_count = int(bk.get('word_count', 0) or 0)
            current_tickets = max_finance
            
            # 必须满足基础门槛
            base_qualified = word_count >= 100000 and current_tickets >= 1000
            
            # 评分门槛：必须优秀
            score_qualified = final_score >= 85 and oracle_grade in ['S', 'A']
            
            # 实时趋势分析（必须有足够数据点）
            has_realtime_data = bool(realtime_trend) and realtime_trend.get('data_points', 0) >= 3
            is_growing = has_realtime_data and realtime_trend.get('growth_rate', 0) > 5  # 至少5%增长
            is_stable = has_realtime_data and realtime_trend.get('growth_rate', 0) < 200  # 增长不能是异常的
            
            # 增长稳定性（连续增长）
            consistent_growth = is_growing and is_stable and has_realtime_data
            
            # AI评估门槛（如果存在AI评估）
            ai_overall = ai_eval_stats.get('overall_score', 0) if ai_eval_stats else 0
            ai_qualified = ai_overall == 0 or ai_overall >= 75  # 要么没有AI评估，要么AI评分高
            
            # 严格判定：必须同时满足所有条件
            is_gem = base_qualified and score_qualified and consistent_growth and ai_qualified
            
            # 出海优选判定（更严格的全球市场标准）
            is_global = (base_qualified and score_qualified and 
                        bool(global_stats) and global_stats.get('overseas_revenue_prediction') in ['S', 'A'])
            
            # 调试打印
            if total_scanned <= 10 or is_gem:
                print(f"[Gem Debug] '{title[:20]}': 综合={final_score:.1f}, Oracle={oracle_grade}, 月票={current_tickets}")
                print(f"[Gem Debug]   基础门槛={base_qualified}, 评分门槛={score_qualified}, 稳定增长={consistent_growth}")
                print(f"[Gem Debug]   实时数据={has_realtime_data}, 增长率={realtime_trend.get('growth_rate', 0):.1f}% if realtime_trend else 'N/A'")
                print(f"[Gem Debug]   判定={is_gem}, 出海={is_global}")
            
            # 定义risk_type
            risk_type = 'NORMAL'
            if is_global: 
                risk_type = 'GLOBAL_GEM'
                global_gems_count += 1
            elif is_gem: 
                risk_type = 'POTENTIAL_GEM'
                gems_count += 1
            
            # 记录判定依据（用于调试）
            if is_gem or is_global:
                reasons = []
                if is_global: 
                    reasons.append("出海优选")
                if is_gem:
                    reasons.append(f"评分{final_score:.1f}")
                    if has_realtime_data:
                        reasons.append(f"月票增长{realtime_trend.get('growth_rate', 0):.0f}%")
                    reasons.append(f"Oracle-{oracle_grade}")
                print(f"[Gem Scanner] '{title}' → {risk_type} | 原因: {' | '.join(reasons)}")
            
            # 只记录真正有潜力的作品到审计日志（减少噪音和AI调用）
            if risk_type == 'NORMAL':
                # 普通作品跳过，不记录也不调用AI
                continue
            
            # 生成 snippet 显示（不调用AI，节省token）
            if risk_type == 'GLOBAL_GEM':
                snippet = f"【出海优选】模型评分: {final_score:.1f} | Oracle评级: {oracle_grade} | 月票: {max_finance} | 目标市场: {global_stats.get('target_regions', '待定') if global_stats else '待分析'}"
            elif risk_type == 'POTENTIAL_GEM':
                growth_info = f" | 增长{realtime_trend.get('growth_rate', 0):.0f}%" if realtime_trend else ""
                snippet = f"【潜力遗珠】模型评分: {final_score:.1f} | Oracle评级: {oracle_grade} | 月票: {max_finance}{growth_info} | 点击查看AI深度分析"
            
            # 先插入基础记录，不调用AI（大幅加速）
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ip_audit_logs 
                    (book_title, book_author, platform, risk_level, risk_type, content_snippet, score, trigger_source, status, markdown_report) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    title, bk['author'], bk['platform'], 
                    'Positive' if risk_type in ['POTENTIAL_GEM', 'GLOBAL_GEM'] else 'Low', 
                    risk_type, snippet, final_score, 'manual_scan', 'Pending', ''  # 报告留空，按需生成
                ))
            conn.commit()
            inserted += 1
            print(f"[Gem Scanner] ✓ Inserted '{title}' as {risk_type} (score: {final_score:.1f})")
            
        conn.close()
        print(f"[Gem Scanner] Scan complete: {total_scanned} books scanned, {inserted} inserted ({gems_count} gems, {global_gems_count} global)")
        
        # 返回详细的统计信息
        return {
            'inserted': inserted,
            'total_scanned': total_scanned,
            'gems_count': gems_count,
            'global_gems_count': global_gems_count
        }
    except Exception as e:
        print(f"[Gem Scanner] Audit log insert error: {e}")
        import traceback
        traceback.print_exc()
        
    return {'inserted': inserted, 'total_scanned': total_scanned, 'gems_count': gems_count, 'global_gems_count': global_gems_count}

if __name__ == '__main__':
    scan_and_trigger_gems()
