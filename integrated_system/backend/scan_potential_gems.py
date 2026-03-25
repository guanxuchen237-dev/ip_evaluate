import pymysql
import sys
import os
import joblib
import numpy as np
from datetime import datetime

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

def fetch_book_historical_trend(title, platform='Qidian'):
    """
    从历史数据表分析书籍长期趋势
    返回：历史均值、增长趋势、稳定性评分
    """
    try:
        if platform == 'Qidian':
            config = QIDIAN_CONFIG
            table = 'novel_monthly_stats'
            ticket_col = 'monthly_tickets_on_list'
        else:
            config = ZONGHENG_CONFIG
            table = 'zongheng_book_ranks'
            ticket_col = 'monthly_ticket'
        
        conn = pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT {ticket_col}, year, month 
                FROM {table} 
                WHERE title = %s AND {ticket_col} > 0
                ORDER BY year DESC, month DESC
                LIMIT 6
            """, (title,))
            rows = cur.fetchall()
        conn.close()
        
        if len(rows) < 3:
            return {'historical_avg': 0, 'trend_direction': 'unknown', 'stability': 0, 'months_tracked': len(rows)}
        
        tickets = [r[ticket_col] for r in rows]
        avg_ticket = sum(tickets) / len(tickets)
        
        # 计算趋势方向（最近3个月 vs 前3个月）
        recent_avg = sum(tickets[:3]) / 3 if len(tickets) >= 3 else avg_ticket
        older_avg = sum(tickets[3:6]) / 3 if len(tickets) >= 6 else avg_ticket
        
        if recent_avg > older_avg * 1.15:
            trend = 'rising'
        elif recent_avg < older_avg * 0.85:
            trend = 'declining'
        else:
            trend = 'stable'
        
        # 稳定性评分（变异系数倒数）
        std = np.std(tickets) if len(tickets) > 1 else 0
        stability = max(0, 1 - std / (avg_ticket + 1)) if avg_ticket > 0 else 0
        
        return {
            'historical_avg': round(avg_ticket, 0),
            'trend_direction': trend,
            'stability': round(stability, 2),
            'months_tracked': len(rows),
            'latest_monthly': tickets[0] if tickets else 0
        }
    except Exception as e:
        print(f"Historical Trend Error ({platform}): {e}")
        return {'historical_avg': 0, 'trend_direction': 'error', 'stability': 0, 'months_tracked': 0}


def fetch_realtime_latest(title, platform='Qidian'):
    """
    从实时表获取最新数据
    返回：最新月票、收藏、排名、更新时间
    """
    try:
        if platform == 'Qidian':
            config = QIDIAN_CONFIG
            table = 'novel_realtime_tracking'
            ticket_col = 'monthly_tickets'
            rank_col = 'monthly_ticket_rank'
            extra_col = 'collection_count'
        else:
            config = ZONGHENG_CONFIG
            table = 'zongheng_realtime_tracking'
            ticket_col = 'monthly_tickets'
            rank_col = 'monthly_ticket_rank'
            extra_col = 'total_recommend'
        
        conn = pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT {ticket_col}, {rank_col}, {extra_col}, crawl_time
                FROM {table}
                WHERE title = %s
                ORDER BY crawl_time DESC
                LIMIT 1
            """, (title,))
            row = cur.fetchone()
        conn.close()
        
        if row:
            return {
                'realtime_tickets': row.get(ticket_col, 0) or 0,
                'realtime_rank': row.get(rank_col, 9999) or 9999,
                'extra_metric': row.get(extra_col, 0) or 0,  # 起点是收藏数，纵横是推荐数
                'crawl_time': row.get('crawl_time', ''),
                'has_realtime': True
            }
        return {'realtime_tickets': 0, 'realtime_rank': 9999, 'extra_metric': 0, 'crawl_time': '', 'has_realtime': False}
    except Exception as e:
        print(f"Realtime Fetch Error ({platform}): {e}")
        return {'realtime_tickets': 0, 'realtime_rank': 9999, 'extra_metric': 0, 'crawl_time': '', 'has_realtime': False}


def calculate_combined_score(historical_data, realtime_data, book_info):
    """
    综合历史数据和实时数据计算潜力评分
    """
    # 基础分：历史平均值权重 40%
    hist_avg = historical_data.get('historical_avg', 0)
    hist_weight = 0.4
    
    # 实时分：最新月票权重 35%
    realtime_tickets = realtime_data.get('realtime_tickets', 0)
    realtime_weight = 0.35
    
    # 增长分：趋势加分权重 15%
    trend_bonus = 0
    if historical_data.get('trend_direction') == 'rising':
        trend_bonus = 10  # 上升趋势加分
    elif historical_data.get('trend_direction') == 'declining':
        trend_bonus = -5  # 下降趋势扣分
    trend_weight = 0.15
    
    # 稳定性分：历史稳定性权重 10%
    stability = historical_data.get('stability', 0)
    stability_bonus = stability * 10  # 0-10分
    stability_weight = 0.1
    
    # 排名惩罚：排名太高的不算是遗珠（已经红了）
    rank = realtime_data.get('realtime_rank', 9999)
    rank_penalty = 0
    if rank < 100:
        rank_penalty = (100 - rank) * 0.1  # 前100名每靠前1名扣0.1分
    
    # 计算综合分（假设满分100分对应月票100000）
    base_score = (
        min(hist_avg / 1000, 50) * hist_weight +
        min(realtime_tickets / 1000, 50) * realtime_weight +
        trend_bonus * trend_weight +
        stability_bonus * stability_weight
    )
    
    final_score = max(0, base_score - rank_penalty)
    
    return {
        'score': round(final_score, 1),
        'components': {
            'historical_avg': hist_avg,
            'realtime_tickets': realtime_tickets,
            'trend': historical_data.get('trend_direction'),
            'stability': stability,
            'rank': rank,
            'rank_penalty': round(rank_penalty, 1)
        }
    }


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
                SELECT overall_score, story_score, character_score, world_score, commercial_score, adaptation_score, safety_score, grade, risk_factor, global_potential
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
                    'risk_factor': row['risk_factor'],
                    'global_potential': row['global_potential']  # 【添加】出海标签判定需要
                }
        conn.close()
    except: pass
    return stats

def fetch_realtime_trend(title):
    """获取作品的实时趋势数据"""
    trend = {}
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            # 从月度数据计算趋势
            cur.execute("""
                SELECT monthly_ticket, year, month
                FROM zongheng_book_ranks
                WHERE title = %s
                ORDER BY year DESC, month DESC
                LIMIT 3
            """, (title,))
            rows = cur.fetchall()
            if rows and len(rows) >= 1:
                latest = rows[0]
                trend['latest_tickets'] = latest['monthly_ticket'] or 0
                trend['data_points'] = len(rows)
                
                if len(rows) >= 2:
                    prev = rows[1]
                    current_tickets = latest['monthly_ticket'] or 0
                    prev_tickets = prev['monthly_ticket'] or 1
                    if prev_tickets > 0:
                        growth = ((current_tickets - prev_tickets) / prev_tickets) * 100
                        trend['growth_rate'] = round(growth, 1)
                        trend['direction'] = '上升' if growth > 5 else '下降' if growth < -5 else '稳定'
                    else:
                        trend['growth_rate'] = 0
                        trend['direction'] = '稳定'
                else:
                    trend['growth_rate'] = 0
                    trend['direction'] = '稳定'
        conn.close()
    except Exception as e:
        print(f"Realtime Trend Error: {e}")
    return trend

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
            # 获取有数据的作品 - 使用 zongheng_book_ranks 表（按月度统计），过滤完结和过时数据
            cur.execute("""
                SELECT title, author, category, 
                       total_rec as finance, monthly_ticket as monthly_tickets, word_count,
                       total_click as collection_count, total_click as interaction, 0 as reward_count, 0 as fans_count,
                       status, updated_at
                FROM zongheng_book_ranks
                WHERE (word_count > 50000 OR monthly_ticket > 0)
                  AND status != 'completed' 
                  AND status != '完结'
                  AND updated_at >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
                ORDER BY monthly_ticket DESC
                LIMIT 100
            """)
            rows = cur.fetchall()
            print(f"[Gem Scanner] Zongheng found {len(rows)} books (after filtering completed/outdated)")
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
                    'monthly_tickets': row.get('monthly_tickets', 0) or 0,
                    'status': row.get('status', ''),
                    'updated_at': row.get('updated_at', '')
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
            # 获取有数据的起点作品（扩展字段），包含状态和时间过滤
            cur.execute("""
                SELECT DISTINCT m.title, m.author, m.category,
                       MAX(m.monthly_tickets_on_list) as finance,
                       MAX(m.recommendation_count) as interaction,
                       MAX(m.word_count) as word_count,
                       MAX(m.collection_count) as collection_count,
                       MAX(m.reward_count) as reward_count,
                       MAX(m.collection_rank) as collection_rank,
                       MAX(m.monthly_ticket_rank) as ticket_rank,
                       MAX(m.status) as status,
                       MAX(m.updated_at) as updated_at
                FROM novel_monthly_stats m
                WHERE (m.word_count > 50000 OR m.monthly_tickets_on_list > 0)
                  AND m.status != 'completed' 
                  AND m.status != '完结'
                  AND m.updated_at >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
                GROUP BY m.title, m.author, m.category
                ORDER BY MAX(m.monthly_tickets_on_list) DESC
                LIMIT 100
            """)
            rows = cur.fetchall()
            print(f"[Gem Scanner] Qidian found {len(rows)} books (after filtering completed/outdated)")
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
                        'ticket_rank': row.get('ticket_rank', 9999) or 9999,
                        'status': row.get('status', ''),
                        'updated_at': row.get('updated_at', '')
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
            
            # 获取历史和实时数据
            historical = fetch_book_historical_trend(title, bk.get('platform', 'Qidian'))
            realtime = fetch_realtime_latest(title, bk.get('platform', 'Qidian'))
            
            # 计算综合评分
            combined = calculate_combined_score(historical, realtime, bk)
            final_score = combined['score']
            
            # Oracle模型预测（作为参考）
            oracle_result = predict_with_oracle_model(
                word_count=bk.get('word_count', 0),
                total_recommend=bk.get('interaction', 0),
                platform=bk.get('platform', 'Qidian')
            )
            oracle_score = oracle_result.get('score', 0) if oracle_result else 0
            oracle_grade = oracle_result.get('grade', 'D') if oracle_result else 'D'
            
            # 融合评分（综合评分占70%，Oracle占30%）
            if oracle_score > 0:
                final_score = final_score * 0.7 + (oracle_score / 10) * 0.3  # Oracle满分1000，需要归一化
            
            # ========== 严格判定逻辑：真正的潜力遗珠 ==========
            # 基础门槛
            word_count = int(bk.get('word_count', 0) or 0)
            current_tickets = realtime.get('realtime_tickets', bk['finance'])
            
            # 必须满足基础门槛
            base_qualified = word_count >= 100000 and current_tickets >= 1000
            
            # 评分门槛：必须优秀 (基于新的综合评分，阈值调整为70)
            score_qualified = final_score >= 70
            
            # 排名门槛：真正的遗珠排名应该在100-500之间（不算太冷门也不算太热门）
            rank = realtime.get('realtime_rank', 9999)
            rank_qualified = 50 < rank < 500  # 太靠前的是热门书，太靠后的可能质量不行
            
            # 历史趋势门槛：必须稳定增长或保持稳定
            trend_ok = historical.get('trend_direction') in ['rising', 'stable'] and historical.get('months_tracked', 0) >= 3
            
            # 实时数据门槛：必须有实时数据支持
            has_realtime = realtime.get('has_realtime', False)
            
            # 严格判定：必须同时满足所有条件
            is_gem = base_qualified and score_qualified and rank_qualified and trend_ok and has_realtime
            
            # 出海优选判定（更严格的全球市场标准）
            is_global = (is_gem and 
                        bool(global_stats) and 
                        global_stats.get('overseas_revenue_prediction') in ['S', 'A'])
            
            # 调试打印
            if total_scanned <= 10 or is_gem:
                print(f"[Gem Debug] '{title[:20]}': 综合={final_score:.1f}, Oracle={oracle_grade}, 月票={current_tickets}, 排名={rank}")
                print(f"[Gem Debug]   基础={base_qualified}, 评分={score_qualified}, 排名区间={rank_qualified}, 趋势={historical.get('trend_direction')}, 实时={has_realtime}")
                print(f"[Gem Debug]   历史均值={historical.get('historical_avg')}, 跟踪月数={historical.get('months_tracked')}, 稳定性={historical.get('stability')}")
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
                    reasons.append(f"综合评分{final_score:.1f}")
                    reasons.append(f"历史趋势-{historical.get('trend_direction')}")
                    reasons.append(f"排名{realtime.get('realtime_rank')}")
                    reasons.append(f"Oracle-{oracle_grade}")
                print(f"[Gem Scanner] '{title}' → {risk_type} | 原因: {' | '.join(reasons)}")
            
            # 只记录真正有潜力的作品到审计日志（减少噪音和AI调用）
            if risk_type == 'NORMAL':
                # 普通作品跳过，不记录也不调用AI
                continue
            
            # 生成 snippet 显示
            if risk_type == 'GLOBAL_GEM':
                snippet = f"【出海优选】综合评分: {final_score:.1f} | Oracle评级: {oracle_grade} | 实时月票: {realtime.get('realtime_tickets', 0)} | 排名: {realtime.get('realtime_rank')} | 目标市场: {global_stats.get('target_regions', '待定') if global_stats else '待分析'}"
            elif risk_type == 'POTENTIAL_GEM':
                trend_text = f"历史{historical.get('trend_direction')}" if historical.get('trend_direction') else ""
                snippet = f"【潜力遗珠】综合评分: {final_score:.1f} | Oracle评级: {oracle_grade} | 实时月票: {realtime.get('realtime_tickets', 0)} | 排名: {realtime.get('realtime_rank')} | {trend_text} | 点击查看AI深度分析"
            
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
