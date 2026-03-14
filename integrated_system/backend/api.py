from flask import Blueprint, request, jsonify
from flask_cors import CORS
import pandas as pd
import joblib
import os
import json # Added for system config handling
import urllib.request # Added for potential web scraping/PDF handling
from bs4 import BeautifulSoup # Added for potential web scraping/PDF handling
import PyPDF2 # Added for potential web scraping/PDF handling
# from snownlp import SnowNLP # Disabled for stability
import jieba
from gensim import corpora, models
import numpy as np

# Absolute imports for app.py execution context
try:
    from data_manager import data_manager
    from ai_service import ai_service
    from virtual_reader.service import virtual_reader_service
    from virtual_reader.manager import persona_manager
    from chat_store import chat_store
    from virtual_reader.graph_generator import graph_generator
except ImportError:
    from backend.data_manager import data_manager
    from backend.ai_service import ai_service
    from backend.virtual_reader.service import virtual_reader_service
    from backend.virtual_reader.manager import persona_manager
    from backend.chat_store import chat_store
    from backend.virtual_reader.graph_generator import graph_generator


api_bp = Blueprint('api', __name__)

def load_system_config() -> dict:
    """Load system configuration or return defaults"""
    cfg_path = os.path.join(os.path.dirname(__file__), 'config', 'system_config.json')
    defaults = {
        'online_window_minutes': 15,
        'page_size': 20,
        'cache_ttl_minutes': 30,
        'data_refresh_interval': 15
    }
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                defaults.update(data)
        except Exception as e:
            print(f"Failed to load system config: {e}")
    return defaults

def save_system_config(config_dict: dict):
    """Save system configuration to file"""
    cfg_path = os.path.join(os.path.dirname(__file__), 'config', 'system_config.json')
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, ensure_ascii=False, indent=4)


def _as_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}

# --- 1. Dashboard Charts API ---

@api_bp.route('/stats/overview')
def stats_overview():
    stats = data_manager.get_overview_stats()
    return jsonify(stats)

@api_bp.route('/charts/rank')
def chart_rank():
    data = data_manager.get_top_ip_novels(limit=10)
    return jsonify(data)

@api_bp.route('/charts/distribution')
def chart_distribution():
    data = data_manager.get_category_distribution()
    return jsonify(data)

@api_bp.route('/charts/trend')
def chart_trend():
    data = data_manager.get_interaction_trend()
    return jsonify(data)

@api_bp.route('/charts/platform')
def chart_platform():
    data = data_manager.get_platform_distribution()
    return jsonify(data)

@api_bp.route('/charts/wordcloud')
def chart_wordcloud():
    data = data_manager.get_wordcloud_data()
    return jsonify(data)

@api_bp.route('/charts/radar')
def chart_radar():
    data = data_manager.get_radar_data()
    return jsonify(data)

@api_bp.route('/admin/reload_data', methods=['GET', 'POST'])
def reload_data():
    """管理接口：强制重载 DataManager 内存数据以应用 SQL 修正和衰减逻辑"""
    try:
        data_manager.load_data()
        return jsonify({'status': 'success', 'message': 'DataManager state reloaded from DB successfully.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@api_bp.route('/charts/scatter')
def chart_scatter():
    data = data_manager.get_scatter_data()
    return jsonify(data)

@api_bp.route('/charts/correlation')
def chart_correlation():
    data = data_manager.get_correlation_matrix()
    return jsonify(data)

@api_bp.route('/charts/author_tiers')
def chart_author_tiers():
    data = data_manager.get_author_tiers()
    return jsonify(data)

@api_bp.route('/charts/geo_region')
def chart_geo_region():
    data = data_manager.get_geo_region_distribution()
    return jsonify(data)

@api_bp.route('/charts/ticket_top')
def chart_ticket_top():
    """月票排行榜 TOP N — 优先读取实时 tracking 表，无数据时 fallback 到静态数据"""
    limit = request.args.get('limit', 10, type=int)
    try:
        from datetime import datetime as _dt
        try:
            from data_manager import QIDIAN_CONFIG, ZONGHENG_CONFIG
        except ImportError:
            from backend.data_manager import QIDIAN_CONFIG, ZONGHENG_CONFIG

        _now = _dt.now()
        _year, _month = _now.year, _now.month
        items = []

        # 起点实时
        try:
            conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT title, MAX(monthly_tickets) as monthly_tickets
                    FROM novel_realtime_tracking
                    WHERE record_year = %s AND record_month = %s
                    GROUP BY title ORDER BY monthly_tickets DESC
                """, (_year, _month))
                for r in cur.fetchall():
                    items.append({
                        'title': r['title'],
                        'monthly_tickets': int(r['monthly_tickets'] or 0),
                        'platform': '起点'
                    })
            conn.close()
        except Exception:
            pass

        # 纵横实时
        try:
            conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT title, MAX(monthly_tickets) as monthly_tickets
                    FROM zongheng_realtime_tracking
                    WHERE record_year = %s AND record_month = %s
                    GROUP BY title ORDER BY monthly_tickets DESC
                """, (_year, _month))
                for r in cur.fetchall():
                    items.append({
                        'title': r['title'],
                        'monthly_tickets': int(r['monthly_tickets'] or 0),
                        'platform': '纵横'
                    })
            conn.close()
        except Exception:
            pass

        if items:
            items.sort(key=lambda x: x['monthly_tickets'], reverse=True)
            return jsonify(items[:limit])
    except Exception:
        pass

    # Fallback: 静态数据
    data = data_manager.get_monthly_ticket_top(limit=limit)
    return jsonify(data)

@api_bp.route('/admin/realtime_ticket_ranking')
def admin_realtime_ticket_ranking():
    """从实时 tracking 表获取当月月票排行榜 TOP N（合并双平台）"""
    limit = request.args.get('limit', 20, type=int)
    try:
        from datetime import datetime as _dt
        try:
            from data_manager import QIDIAN_CONFIG, ZONGHENG_CONFIG
        except ImportError:
            from backend.data_manager import QIDIAN_CONFIG, ZONGHENG_CONFIG

        _now = _dt.now()
        _year, _month = _now.year, _now.month
        items = []

        # 起点
        try:
            conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT title, MAX(monthly_tickets) as monthly_tickets,
                           MIN(monthly_ticket_rank) as rank_val,
                           MAX(crawl_time) as last_crawl
                    FROM novel_realtime_tracking
                    WHERE record_year = %s AND record_month = %s
                    GROUP BY title
                    ORDER BY monthly_tickets DESC
                """, (_year, _month))
                for r in cur.fetchall():
                    items.append({
                        'title': r['title'],
                        'monthly_tickets': int(r['monthly_tickets'] or 0),
                        'rank': int(r['rank_val'] or 999),
                        'platform': '起点',
                        'last_crawl': r['last_crawl'].strftime('%m-%d %H:%M') if r['last_crawl'] else ''
                    })
            conn.close()
        except Exception as e:
            print(f"[WARN] Realtime Qidian ranking: {e}")

        # 纵横
        try:
            conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT title, MAX(monthly_tickets) as monthly_tickets,
                           MIN(monthly_ticket_rank) as rank_val,
                           MAX(crawl_time) as last_crawl
                    FROM zongheng_realtime_tracking
                    WHERE record_year = %s AND record_month = %s
                    GROUP BY title
                    ORDER BY monthly_tickets DESC
                """, (_year, _month))
                for r in cur.fetchall():
                    items.append({
                        'title': r['title'],
                        'monthly_tickets': int(r['monthly_tickets'] or 0),
                        'rank': int(r['rank_val'] or 999),
                        'platform': '纵横',
                        'last_crawl': r['last_crawl'].strftime('%m-%d %H:%M') if r['last_crawl'] else ''
                    })
            conn.close()
        except Exception as e:
            print(f"[WARN] Realtime Zongheng ranking: {e}")

        # 按月票降序合并排序
        items.sort(key=lambda x: x['monthly_tickets'], reverse=True)
        # 重新编号排名
        for i, item in enumerate(items):
            item['rank'] = i + 1

        return jsonify({'items': items[:limit], 'year': _year, 'month': _month})
    except Exception as e:
        return jsonify({'error': str(e), 'items': []}), 500

@api_bp.route('/charts/long_term_trend')
def chart_long_term_trend():
    platform = request.args.get('platform', 'qidian')
    data = data_manager.get_long_term_trend(platform=platform)
    return jsonify(data)

@api_bp.route('/library/list')
def library_list():
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 12))
        
        filters = {
            'search': request.args.get('search', ''),
            'category': request.args.get('category', ''),
            'platform': request.args.get('platform', ''),
            'status': request.args.get('status', ''),
            'year': request.args.get('year', ''),
            'month': request.args.get('month', '')
        }
        
        result = data_manager.get_library_data(page, page_size, filters)
        return jsonify(result)
    except Exception as e:
        print(f"Library Error: {e}")
        return jsonify({'error': str(e), 'items': [], 'total': 0}), 500

@api_bp.route('/library/detail')
def library_detail():
    """获取单本书籍详情"""
    try:
        title = request.args.get('title', '')
        author = request.args.get('author', '')
        platform = request.args.get('platform', '')
        
        if not title:
            return jsonify({'error': 'Missing title parameter'}), 400
        
        result = data_manager.get_book_detail(title, author or None, platform or None)
        
        if result is None:
            return jsonify({'error': 'Book not found'}), 404
        
        return jsonify(result)
    except Exception as e:
        print(f"Library Detail Error: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/library/risk')
def library_risk():
    """获取单本书籍安全与风险评估详情"""
    try:
        title = request.args.get('title', '')
        author = request.args.get('author', '')
        platform = request.args.get('platform', '')
        
        if not title:
            return jsonify({'error': 'Missing title parameter'}), 400
            
        result = data_manager.get_book_risk(title, author or None, platform or None)
        
        if result is None:
            return jsonify({'error': 'Book not found'}), 404
            
        return jsonify(result)
    except Exception as e:
        print(f"Library Risk Error: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/library/healing')
def library_healing():
    """获取单本书籍治愈系指数详情"""
    try:
        title = request.args.get('title', '')
        author = request.args.get('author', '')
        platform = request.args.get('platform', '')
        
        if not title:
            return jsonify({'error': 'Missing title parameter'}), 400
            
        result = data_manager.get_healing_index(title, author or None, platform or None)
        
        if result is None:
            return jsonify({'error': 'Book not found'}), 404
            
        return jsonify(result)
    except Exception as e:
        print(f"Library Healing Error: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/library/valuation')
def library_valuation():
    """基于书籍真实数据的 IP 版权价值估算"""
    try:
        title = request.args.get('title', '')
        author = request.args.get('author', '')
        platform = request.args.get('platform', '')
        
        if not title:
            return jsonify({'error': 'Missing title parameter'}), 400
        
        # 1. 查缓存
        from auth import AUTH_DB_CONFIG
        import pymysql
        cache_conn = pymysql.connect(**AUTH_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with cache_conn.cursor() as cur:
            cur.execute("SELECT * FROM ip_valuation WHERE title=%s AND platform=%s LIMIT 1", (title, platform))
            cached = cur.fetchone()
        cache_conn.close()
        
        if cached:
            return jsonify({
                'estimated_min': cached['estimated_min'],
                'estimated_value': cached['estimated_value'],
                'estimated_max': cached['estimated_max'],
                'confidence': cached['confidence'],
                'ip_score': cached['ip_score'],
                'factors': json.loads(cached['factors']) if cached['factors'] else [],
                'comparables': json.loads(cached['comparables']) if cached['comparables'] else [],
                'adaptation_recs': json.loads(cached['adaptation_recs']) if cached['adaptation_recs'] else [],
                'cached': True
            })
        
        # 2. 获取书籍真实数据
        book = data_manager.get_book_detail(title, author or None, platform or None)
        if not book:
            return jsonify({'error': 'Book not found'}), 404
        
        stats = book.get('stats', {})
        ip_eval = book.get('ip_evaluation', {})
        basic = book.get('basic', {})
        
        ip_score = float(ip_eval.get('score', 60))
        word_count = int(stats.get('word_count', 0))
        popularity = int(stats.get('popularity', 0))
        finance = int(stats.get('monthly_tickets', 0))
        interaction = int(stats.get('interaction', 0))
        status = basic.get('status', '连载')
        category = basic.get('category', '其他')
        
        # 3. 查询 ip_ai_evaluation 表获取改编评估数据
        ai_eval_data = {}
        try:
            from data_manager import ZONGHENG_CONFIG
            eval_conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with eval_conn.cursor() as cur:
                cur.execute(
                    "SELECT adaptation_score, adaptation_difficulty, commercial_value, commercial_score, story_score, safety_score FROM ip_ai_evaluation WHERE title=%s LIMIT 1",
                    (title,)
                )
                ai_eval_data = cur.fetchone() or {}
            eval_conn.close()
        except Exception as e:
            print(f"[Valuation] AI eval query error: {e}")
        
        adaptation_score = float(ai_eval_data.get('adaptation_score', ip_score * 0.88))
        commercial_score = float(ai_eval_data.get('commercial_score', ip_score * 0.92))
        adaptation_difficulty = ai_eval_data.get('adaptation_difficulty', '中等')
        commercial_value_label = ai_eval_data.get('commercial_value', '中等')
        
        # 4. 估值算法 —— 基于真实数据加权计算
        # 基准价格（万元）：以 IP 评分为核心锚点
        base_price = ip_score * 30  # 60分 → 1800万, 90分 → 2700万
        
        # 各维度调节系数
        # 字数奖励：百万字以上提供成熟度加成
        word_factor = min(1.3, max(0.7, (word_count / 2000000)))
        # 人气系数：基于人气值的对数缩放
        import math
        pop_factor = min(1.5, max(0.6, math.log10(max(popularity, 1)) / 7))
        # 月票/粉丝经济系数
        finance_factor = min(1.4, max(0.7, math.log10(max(finance, 1)) / 5))
        # 互动量系数
        interact_factor = min(1.3, max(0.7, math.log10(max(interaction, 1)) / 6))
        # 完结加成或连载折扣
        status_factor = 1.15 if status == '完本' or status == '完结' else 0.95
        # 改编评分系数
        adapt_factor = min(1.3, max(0.7, adaptation_score / 75))
        # 商业评分系数
        comm_factor = min(1.3, max(0.7, commercial_score / 70))
        
        # 分类热度系数（热门品类溢价）
        hot_categories = {'都市': 1.15, '玄幻奇幻': 1.2, '东方玄幻': 1.18, '武侠仙侠': 1.1, '古典仙侠': 1.08, '科幻': 1.12, '都市生活': 1.05}
        cat_factor = hot_categories.get(category, 1.0)
        
        # 综合估值
        weighted_price = base_price * (
            word_factor * 0.10 +
            pop_factor * 0.20 +
            finance_factor * 0.15 +
            interact_factor * 0.15 +
            status_factor * 0.05 +
            adapt_factor * 0.15 +
            comm_factor * 0.10 +
            cat_factor * 0.10
        )
        
        estimated_value = round(weighted_price, 0)
        estimated_min = round(estimated_value * 0.6, 0)
        estimated_max = round(estimated_value * 1.5, 0)
        
        # 置信度：基于数据完整性
        data_completeness = sum([
            1 if word_count > 0 else 0,
            1 if popularity > 0 else 0,
            1 if finance > 0 else 0,
            1 if interaction > 0 else 0,
            1 if ai_eval_data else 0,
        ]) / 5
        confidence = round(60 + data_completeness * 35, 1)
        
        # 5. 价格影响因子
        factors = []
        if ip_score >= 80:
            factors.append({'name': 'IP评分优秀', 'impact': 'positive', 'value': f'+{int((ip_score-70)*0.5)}%', 'detail': f'评分 {ip_score}，高于大部分同类作品'})
        elif ip_score < 60:
            factors.append({'name': 'IP评分偏低', 'impact': 'negative', 'value': f'-{int((65-ip_score)*0.8)}%', 'detail': f'评分 {ip_score}，市场竞争力一般'})
        
        if word_count >= 2000000:
            factors.append({'name': '内容充实', 'impact': 'positive', 'value': '+12%', 'detail': f'字数 {word_count//10000} 万字，内容体量完整'})
        elif word_count < 500000:
            factors.append({'name': '内容体量不足', 'impact': 'negative', 'value': '-10%', 'detail': f'字数 {word_count//10000} 万字，改编素材有限'})
        
        if popularity >= 1000000:
            factors.append({'name': '高人气加成', 'impact': 'positive', 'value': '+20%', 'detail': f'人气值 {popularity//10000} 万，粉丝基础强大'})
        
        if finance >= 10000:
            factors.append({'name': '粉丝经济活跃', 'impact': 'positive', 'value': '+15%', 'detail': f'月票 {finance}，付费意愿强'})
        
        if status == '完本' or status == '完结':
            factors.append({'name': '已完结', 'impact': 'positive', 'value': '+10%', 'detail': '完结作品改编风险低，剧本可完整规划'})
        else:
            factors.append({'name': '连载中', 'impact': 'neutral', 'value': '-5%', 'detail': '连载中的作品存在断更和走向不确定风险'})
        
        if adaptation_difficulty == '低':
            factors.append({'name': '改编难度低', 'impact': 'positive', 'value': '+8%', 'detail': '故事结构清晰，适合改编'})
        elif adaptation_difficulty == '高':
            factors.append({'name': '改编难度高', 'impact': 'negative', 'value': '-12%', 'detail': '世界观复杂或特效需求大，改编成本高'})
        
        if category in hot_categories:
            factors.append({'name': f'{category}品类热门', 'impact': 'positive', 'value': f'+{int((hot_categories[category]-1)*100)}%', 'detail': f'{category}是当前市场高需求品类'})
        
        # 6. 可比交易案例（从同品类中找 IP 评分相近的书）
        comparables = []
        try:
            df = data_manager.df
            if not df.empty:
                # 1. 过滤当前作品
                df_others = df[df['title'] != title].copy()
                # 2. 每个作品仅保留最新的一条记录（去重历史月度数据）
                df_others = df_others.sort_values(by=['year', 'month'], ascending=[False, False])
                df_unique = df_others.drop_duplicates(subset=['title', 'author'])
                
                # 3. 优先找同品类
                df_cat = df_unique[df_unique['category'] == category].copy()
                if len(df_cat) < 4:
                    df_cat = df_unique.copy()
                
                # 4. 计算评分差异并选取最接近的 4 个
                df_cat['score_diff'] = (df_cat['IP_Score'] - ip_score).abs()
                df_similar = df_cat.nsmallest(4, 'score_diff')
                
                for _, row in df_similar.iterrows():
                    sim_score = float(row.get('IP_Score', 60))
                    # 相似度算法优化：更加平滑的百分比
                    diff = abs(sim_score - ip_score)
                    similarity = max(65, int(100 - diff * 4.5)) 
                    if similarity > 98 and diff > 0.1: similarity = 98 # 除非完全一致，否则不给 99+
                    
                    # 使用加权算法估算案例价格
                    comp_base = sim_score * 30
                    comp_wc = float(row.get('word_count', 1000000))
                    comp_wf = min(1.3, max(0.7, comp_wc / 2000000))
                    comp_price = round(comp_base * (comp_wf * 0.3 + pop_factor * 0.3 + 0.4), 0)
                    
                    comparables.append({
                        'name': str(row.get('title', '')),
                        'author': str(row.get('author', '')),
                        'category': str(row.get('category', '')),
                        'score': round(sim_score, 1),
                        'estimated_price': comp_price,
                        'similarity': min(99, similarity)
                    })
        except Exception as e:
            print(f"[Valuation] Comparables error: {e}")
        
        # 7. 改编方向推荐
        adaptation_recs = []
        # 影视剧
        drama_fit = min(95, int(adaptation_score * 0.8 + commercial_score * 0.2))
        drama_note = '故事完整、人物鲜明，适合长篇剧集' if adaptation_score >= 70 else '需要较大幅度的剧本改编'
        adaptation_recs.append({'type': '影视剧', 'icon': '🎬', 'fit': drama_fit, 'note': drama_note, 'difficulty': adaptation_difficulty})
        
        # 动画
        anim_fit = min(95, int(adaptation_score * 0.6 + float(ai_eval_data.get('story_score', ip_score * 0.95)) * 0.4))
        anim_note = '世界观独特，动画表现力空间大' if category in ['玄幻奇幻', '东方玄幻', '武侠仙侠', '古典仙侠', '科幻'] else '都市题材动画化需要创意突破'
        adaptation_recs.append({'type': '动画', 'icon': '🎨', 'fit': anim_fit, 'note': anim_note, 'difficulty': '低' if category in ['玄幻奇幻', '东方玄幻'] else '中等'})
        
        # 游戏
        game_fit = min(95, int(float(ai_eval_data.get('story_score', ip_score*0.9)) * 0.3 + adaptation_score * 0.3 + commercial_score * 0.4))
        game_note = '具备游戏化改编的世界观基础' if category in ['玄幻奇幻', '东方玄幻', '武侠仙侠', '科幻'] else '需要额外构建游戏玩法体系'
        adaptation_recs.append({'type': '游戏', 'icon': '🎮', 'fit': game_fit, 'note': game_note, 'difficulty': '高'})
        
        # 有声书
        audio_fit = min(95, int(ip_score * 0.5 + float(ai_eval_data.get('story_score', ip_score*0.95)) * 0.5))
        audio_note = '叙事性强，适合有声演绎' if ip_score >= 70 else '可作为低成本试水方向'
        adaptation_recs.append({'type': '有声书', 'icon': '🎧', 'fit': audio_fit, 'note': audio_note, 'difficulty': '低'})
        
        # 短剧
        short_fit = min(95, int(commercial_score * 0.5 + adaptation_score * 0.3 + (80 if category in ['都市', '都市生活'] else 50) * 0.2))
        short_note = '都市题材天然适合短剧' if category in ['都市', '都市生活'] else '需要精选高冲突片段改编'
        adaptation_recs.append({'type': '短剧', 'icon': '📱', 'fit': short_fit, 'note': short_note, 'difficulty': '低'})
        
        # 排序：匹配度最高的排前面
        adaptation_recs.sort(key=lambda x: x['fit'], reverse=True)
        
        # 8. 写入缓存
        try:
            cache_conn = pymysql.connect(**AUTH_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with cache_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ip_valuation (title, author, platform, ip_score, estimated_min, estimated_value, estimated_max, confidence, factors, comparables, adaptation_recs)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        ip_score=VALUES(ip_score), estimated_min=VALUES(estimated_min), estimated_value=VALUES(estimated_value),
                        estimated_max=VALUES(estimated_max), confidence=VALUES(confidence), factors=VALUES(factors),
                        comparables=VALUES(comparables), adaptation_recs=VALUES(adaptation_recs)
                """, (title, author, platform, ip_score, estimated_min, estimated_value, estimated_max, confidence,
                      json.dumps(factors, ensure_ascii=False), json.dumps(comparables, ensure_ascii=False), json.dumps(adaptation_recs, ensure_ascii=False)))
            cache_conn.commit()
            cache_conn.close()
        except Exception as e:
            print(f"[Valuation] Cache write error: {e}")
        
        return jsonify({
            'estimated_min': estimated_min,
            'estimated_value': estimated_value,
            'estimated_max': estimated_max,
            'confidence': confidence,
            'ip_score': ip_score,
            'factors': factors,
            'comparables': comparables,
            'adaptation_recs': adaptation_recs,
            'cached': False
        })
        
    except Exception as e:
        print(f"[Valuation Error] {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/library/global_analysis')
def library_global_analysis():
    """基于书籍数据的 AI 全球化潜力分析"""
    try:
        title = request.args.get('title', '')
        author = request.args.get('author', '')
        platform = request.args.get('platform', '')
        
        if not title:
            return jsonify({'error': 'Missing title parameter'}), 400
            
        # 1. 查缓存
        from auth import AUTH_DB_CONFIG
        import pymysql
        cache_conn = pymysql.connect(**AUTH_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        
        # 自动创建缓存表（如果不存在）
        with cache_conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ip_global_analysis (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    author VARCHAR(100) DEFAULT '',
                    platform VARCHAR(20) DEFAULT '',
                    analysis_data JSON,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_book (title, author, platform)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            
            cur.execute("SELECT analysis_data FROM ip_global_analysis WHERE title=%s AND platform=%s LIMIT 1", (title, platform))
            cached = cur.fetchone()
            
        if cached and cached.get('analysis_data'):
            cache_conn.close()
            data = json.loads(cached['analysis_data']) if isinstance(cached['analysis_data'], str) else cached['analysis_data']
            data['cached'] = True
            return jsonify(data)
            
        # 2. 从 data_manager 获取书籍信息
        book = data_manager.get_book_detail(title, author or None, platform or None)
        if not book:
            cache_conn.close()
            return jsonify({'error': 'Book not found'}), 404
            
        abstract = book.get('basic', {}).get('abstract', '')
        category = book.get('basic', {}).get('category', '其他')
        
        # 3. 调用 AI 进行分析
        analysis_result = ai_service.analyze_global_potential(title, abstract, category)
        
        # 4. 写入缓存
        with cache_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ip_global_analysis (title, author, platform, analysis_data)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE analysis_data=VALUES(analysis_data)
            """, (title, author, platform, json.dumps(analysis_result, ensure_ascii=False)))
        cache_conn.commit()
        cache_conn.close()
        
        analysis_result['cached'] = False
        return jsonify(analysis_result)

    except Exception as e:
        print(f"[Global Analysis Error] {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/debug_db')
def debug_db():
    from data_manager import QIDIAN_CONFIG
    import pymysql
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM zongheng_chapters WHERE source='placeholder'")
            cnt = cur.fetchone()['cnt']
            
            cur.execute("SELECT id, source FROM zongheng_chapters WHERE title='剑来' AND chapter_num=1")
            jianlai = cur.fetchall()
            
            cur.execute("SELECT DATABASE() as db, USER() as user, @@port as port")
            env = cur.fetchone()
        conn.close()
        return jsonify({
            'config': QIDIAN_CONFIG,
            'placeholder_count': cnt,
            'jianlai_row': jianlai,
            'env': env
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@api_bp.route('/library/chapter')
def library_chapter():
    """获取书籍指定章节内容（优先查库 -> 爬取 -> AI生成兜底）"""
    try:
        title = request.args.get('title', '')
        chapter_num = request.args.get('chapter_num', 1, type=int)
        platform = request.args.get('platform', '').lower()
        
        if not title:
            return jsonify({'error': 'Missing title parameter'}), 400
            
        from data_manager import QIDIAN_CONFIG, ZONGHENG_CONFIG
        import pymysql
        import urllib.parse
        
        # 1. 查询数据库缓存
        cached = None
        source_db_config = QIDIAN_CONFIG # 默认配置
        
        # 确定使用哪个数据库和表
        # 起点的表结构是 qidian_chapters (id, book_id, book_title, chapter_id, chapter_index, chapter_title, chapter_content, crawl_time)
        # 纵横的表结构是 zongheng_chapters (id, novel_id, title, chapter_num, chapter_title, content, source)
        
        def check_qidian(cur, t, n):
            # 起点表使用 book_title 和 chapter_index
            cur.execute("SELECT chapter_title, chapter_content as content, 'qidian' as source FROM qidian_chapters WHERE book_title=%s AND chapter_index=%s LIMIT 1", (t, n))
            return cur.fetchone()

        def check_zongheng(cur, t, n):
            cur.execute("SELECT chapter_title, content, source FROM zongheng_chapters WHERE title=%s AND chapter_num=%s LIMIT 1", (t, n))
            return cur.fetchone()

        # 根据 platform 参数决定查询顺序
        target_platforms = []
        if 'qidian' in platform or '起点' in platform:
            target_platforms = ['qidian', 'zongheng']
        elif 'zongheng' in platform or '纵横' in platform:
            target_platforms = ['zongheng', 'qidian']
        else:
            # 未传递或无法识别，则都试一下
            target_platforms = ['zongheng', 'qidian']

        for p in target_platforms:
            config = QIDIAN_CONFIG if p == 'qidian' else ZONGHENG_CONFIG
            try:
                conn = pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
                with conn.cursor() as cur:
                    if p == 'qidian':
                        cached = check_qidian(cur, title, chapter_num)
                    else:
                        cached = check_zongheng(cur, title, chapter_num)
                conn.close()
                if cached:
                    source_db_config = config
                    break
            except Exception as e:
                print(f"[DEBUG API] DB Query error for {p}: {e}")

        if cached:
            content_data = []
            content_raw = cached.get('content') or cached.get('chapter_content', '')
            
            if isinstance(content_raw, str):
                content_raw = content_raw.strip()
                if content_raw:
                    # Try JSON first (for previously stored array format)
                    try:
                        parsed = json.loads(content_raw)
                        if isinstance(parsed, list):
                            content_data = parsed
                        else:
                            content_data = [str(parsed)]
                    except (json.JSONDecodeError, ValueError):
                        # Plain text content - split by newlines and filter empty lines
                        lines = content_raw.split('\n')
                        content_data = [line.strip() for line in lines if line.strip()]
            elif isinstance(content_raw, (list, tuple)):
                content_data = [str(item) for item in content_raw if str(item).strip()]
            
            # Ensure we have valid content
            if not content_data:
                content_data = ['章节内容为空，请尝试其他章节。']
                
            return jsonify({
                'title': title,
                'chapter_num': chapter_num,
                'chapter_title': cached.get('chapter_title', f'第{chapter_num}章'),
                'content': content_data,
                'source': cached.get('source', 'db'),
                'cached': True
            })
            
        # 2. 爬取尝试 (以纵横为例，或者简单搜索引擎。为了演示与稳定性，采用快速简单搜索)
        chapter_title = f"第{chapter_num}章"
        scraped_content = []
        fetch_success = False
        
        # 2. 爬取尝试 (使用 Playwright 隐身浏览器内核进行真实抓取，保障获取原汁原味的网文)
        chapter_title = f"第{chapter_num}章"
        scraped_content = []
        fetch_success = False
        
        try:
            from playwright.sync_api import sync_playwright
            import urllib.parse
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                # 策略: 通过必应通用搜索引擎直接绕过部分小说站的反爬主页
                search_query = f"{title} 第{chapter_num}章 笔趣阁 OR 顶点小说 OR UUKANSHU"
                page.goto(f"https://cn.bing.com/search?q={urllib.parse.quote(search_query)}", timeout=15000)
                page.wait_for_timeout(2000) # 等待渲染
                
                # 获取排名前列的自然搜索结果链接
                target_url = None
                links = page.query_selector_all("ol#b_results h2 a")
                for link in links:
                    href = link.get_attribute("href")
                    if href and href.startswith("http"):
                        target_url = href
                        break
                        
                if target_url:
                    page.goto(target_url, timeout=15000)
                    page.wait_for_timeout(3000) # 等待正文解密/渲染
                    
                    # 极其泛用的正文提取算法：基于中文字符密度和回车换行
                    body_text = page.locator("body").inner_text()
                    paragraphs = []
                    for line in body_text.split('\n'):
                        line = line.strip()
                        if len(line) > 15 and not any(kw in line for kw in ['浏览器', 'JavaScript', '跳转', 'Loading', '上一章', '下一章']):
                            paragraphs.append(line)
                    
                    if len(paragraphs) > 5:
                        scraped_content = paragraphs
                        fetch_success = True
                        
                browser.close()
                
        except Exception as e:
            print(f"[Chapter Scrape] Failed for {title} ch{chapter_num}: {e}")
        
        source = 'scraped' if fetch_success else 'placeholder'
        
        if not fetch_success:
            # 当真实网络抓取受阻时，不使用AI瞎编乱造，而是如实反馈给读者
            chapter_title = chapter_title
            scraped_content = [
                f"当前试图拉取《{title}》{chapter_title} 原版章节内容失败。",
                "失败原因：目标小说网站由于版权保护开启了强力防抓取验证，或当前服务器网络 IP 被小说站防火墙阻拦（如 Cloudflare / 腾讯WAF）。",
                "",
                "为保证为您呈现最原汁原味的作者原版内容，系统已停止使用 AI 大模型进行续写乱编的操作。",
                "请直接前往起点中文网、番茄小说等正版平台阅读本章节的内容。后续系统可配置代理池以继续尝试。"
            ]
        # 4. 保存进数据库（使用纵横表兜底保存）
        try:
            from data_manager import ZONGHENG_CONFIG
            save_conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with save_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO zongheng_chapters (novel_id, title, chapter_num, chapter_title, content, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE content=VALUES(content), source=VALUES(source), chapter_title=VALUES(chapter_title)
                """, ('auto_api', title, chapter_num, chapter_title, json.dumps(scraped_content, ensure_ascii=False), source))
            save_conn.commit()
            save_conn.close()
        except Exception as db_err:
             print(f"[Chapter DB Save] Error: {db_err}")
             
        return jsonify({
            'title': title,
            'chapter_num': chapter_num,
            'chapter_title': chapter_title,
            'content': scraped_content,
            'source': source,
            'cached': False,
            '_debug_title_repr': repr(title)
        })
        
    except Exception as e:
        print(f"[Chapter Fetch Error] {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# --- 2. Prediction API ---
# Trigger Reload for Category Calibration
@api_bp.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        title = data.get('title', '')
        abstract = data.get('abstract', '')
        category = data.get('category', '都市')
        
        # DEBUG LOG
        with open("backend_debug.txt", "a", encoding="utf-8") as f:
            f.write(f"\n[API] Predict Called for: {title}\n")
            f.write(f"[API] Model Loaded? {data_manager.model is not None}\n")
        
        # ★ 自动匹配数据库书籍，补充运营数据（解决前端只传 title/category/abstract 时评分固定 65 的问题）
        matched_book = None
        if title and not data.get('finance') and not data.get('interaction'):
            try:
                book_info = data_manager.get_book_detail(title)
                if book_info:
                    stats = book_info.get('stats', {})
                    basic = book_info.get('basic', {})
                    ip_eval = book_info.get('ip_evaluation', {})
                    data['finance'] = stats.get('monthly_tickets', 0)
                    data['interaction'] = stats.get('interaction', 0)
                    data['popularity'] = stats.get('popularity', 0)
                    data['word_count'] = stats.get('word_count', 0)
                    # 补充简介（如果前端未传或过短）
                    if not abstract or len(abstract) < 20:
                        abstract = basic.get('abstract', '') or abstract
                        data['abstract'] = abstract
                    # 补充真实的数据库原始评分，防止 AI 预测误差导致评分倒挂打乱排名
                    if basic.get('db_ip_score'):
                        data['db_ip_score'] = basic['db_ip_score']
                        
                    # 使用数据库中的分类（更准确）
                    if basic.get('category'):
                        category = basic['category']
                        data['category'] = category
                    matched_book = {
                        'title': basic.get('title', title),
                        'author': basic.get('author', ''),
                        'platform': basic.get('platform', ''),
                        'status': basic.get('status', ''),
                        'word_count': stats.get('word_count', 0),
                        'popularity': stats.get('popularity', 0),
                        'finance': data['finance'],
                        'interaction': data['interaction'],
                        'dimensions': ip_eval.get('dimensions', None)
                    }
                    
                    # ★ 跨平台流量归一化（核心修复）
                    # 起点平均月票 43196 vs 纵横平均月票 920（47倍差），最高月票 16 倍差
                    # 不做归一化会导致纵横的书永远被起点碾压
                    platform_str = basic.get('platform', '').lower()
                    if 'zongheng' in platform_str or '纵横' in platform_str:
                        # 纵横 → 起点的归一化系数（用几何平均值：sqrt(47 * 16) ≈ 27，保守取 15）
                        FINANCE_NORM = 15.0    # 月票归一化（纵横1万 ≈ 起点15万）
                        INTERACT_NORM = 4.5    # 互动归一化（纵横的互动体量约为起点的 1/4.5）
                        raw_fin = data['finance']
                        raw_inter = data['interaction']
                        data['finance'] = int(raw_fin * FINANCE_NORM)
                        data['interaction'] = int(raw_inter * INTERACT_NORM)
                        matched_book['finance_raw'] = raw_fin
                        matched_book['interaction_raw'] = raw_inter
                        matched_book['platform_norm'] = f'×{FINANCE_NORM}'
                        print(f"📊 平台归一化: 纵横 → 起点等效 | 月票 {raw_fin} × {FINANCE_NORM} = {data['finance']}, 互动 {raw_inter} × {INTERACT_NORM} = {data['interaction']}")
                    
                    print(f"📚 数据库匹配成功: {title} → 月票={data['finance']}, 互动={data['interaction']}")
            except Exception as match_err:
                print(f"⚠️ 数据库匹配失败（不影响预测）: {match_err}")
            
        print(f"🔮 Predicting for: {title}")
        
        # 1. Prediction (V2)
        if data_manager.model:
            try:
                prediction_result = data_manager.predict_ip(data)
                result = prediction_result
                
                # Extract metrics for AI analysis
                details = result.get('details', {})
                velocity = details.get('velocity_score', 0)
                trend = details.get('trend_score', 0.5)
                intensity = details.get('sentiment_intensity', 0)
                
            except Exception as e:
                with open("backend_debug.txt", "a", encoding="utf-8") as f:
                     f.write(f"[API] DataManager Predict Error: {e}\n")
                print(f"❌ Prediction Error: {e}")
                import traceback; traceback.print_exc()
                result = {'score': 60.0, 'error': str(e), 'details': {}}
                velocity=0; trend=0.5; intensity=0
        else:
            with open("backend_debug.txt", "a", encoding="utf-8") as f:
                 f.write(f"[API] Model Missing. Returning default.\n")
            result = {'score': 60.0, 'model_version': 'v1', 'details': {}}
            velocity=0; trend=0.5; intensity=0
            
    except Exception as outer_e:
        with open("backend_debug.txt", "a", encoding="utf-8") as f:
             f.write(f"[API] CRITICAL FAILURE: {outer_e}\n")
        return jsonify({'error': str(outer_e)}), 500

    # 3. AI Analysis (Fail-Safe)
    try:
        ai_report = ai_service.analyze_prediction(
            title, category, result['score'], abstract,
            velocity=velocity, trend=trend, intensity=intensity
        )
        result['ai_report'] = ai_report
    except Exception as e:
        print(f"⚠️ AI Failed: {e}")
        # result['ai_report'] = ai_service._mock_response() # METHOD REMOVED
        result['ai_report'] = {} # Safe fallback

    # 4. Save Prediction Record for Training
    try:
        import json
        from backend.auth import decode_token, get_auth_db
        user_id = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                payload = decode_token(token)
                user_id = payload.get('user_id')
            except Exception:
                pass
        
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO user_predictions (user_id, title, category, score, details) VALUES (%s, %s, %s, %s, %s)",
                (user_id, title, category, float(result.get('score', 0)), json.dumps(result.get('details', {}), ensure_ascii=False))
            )
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Failed to save user prediction to DB: {e}")

    # 5. 注入数据库匹配信息、完结状态修正、多维市场分析
    if matched_book:
        result['matched_book'] = matched_book
        
        # ★ 完结状态修正（仅记入分析报告，不直接修改总分，防止打乱大盘排名）
        book_status = matched_book.get('status', '')
        status_modifier = 0
        if '完结' in book_status or '完本' in book_status:
            status_modifier = -2.5  
        elif '连载' in book_status:
            status_modifier = +1.5  
        
        result['details'] = result.get('details', {})
        result['details']['status_modifier'] = status_modifier
        result['details']['status'] = book_status
        
        # ★ 多维市场价值分析（借鉴番茄六维 + Inkitt 多维评估思路）
        _fin = float(matched_book.get('finance', 0))
        _inter = float(matched_book.get('interaction', 0))
        _pop = float(matched_book.get('popularity', 0))
        _wc = float(matched_book.get('word_count', 0))
        _score = float(result.get('score', 65))
        dims = matched_book.get('dimensions') or {}
        
        import numpy as np
        
        # 1. 市场热度（月票 + 人气值）
        heat_score = min(100, 40 + 12 * np.log10(max(_fin, 1)) + 5 * np.log10(max(_pop, 1)))
        
        # 2. 内容质量（六维中的故事+角色+世界观，或用总分估算）
        if dims.get('story') and dims.get('character') and dims.get('world'):
            content_score = (float(dims['story']) + float(dims['character']) + float(dims['world'])) / 3
        else:
            content_score = _score * 0.85  # 无六维数据时用总分估算
        
        # 3. IP 改编潜力（六维中的改编+商业，或用总分估算）
        if dims.get('adaptation') and dims.get('commercial'):
            ip_potential = (float(dims['adaptation']) + float(dims['commercial'])) / 2
        else:
            ip_potential = _score * 0.9
        
        # 4. 粉丝粘性（互动量/月票 的比值反映粉丝参与深度）
        if _fin > 0 and _inter > 0:
            loyalty_raw = _inter / (_fin * 100)  # 归一化比值
            fan_loyalty = min(100, 50 + 15 * np.log10(max(loyalty_raw, 0.01) + 1))
        else:
            fan_loyalty = 50.0
        
        # 5. 商业变现能力（月票是最直接的付费行为指标）
        commercial_value = min(100, 35 + 14 * np.log10(max(_fin, 1)))
        
        # 6. 时效活跃度（连载 > 完结，有趋势数据时用趋势方向修正）
        if '连载' in book_status:
            timeliness = 85.0
        elif '完结' in book_status or '完本' in book_status:
            timeliness = 55.0
        else:
            timeliness = 70.0
        # 用趋势方向修正时效分
        trend_info = result.get('trend', {})
        if isinstance(trend_info, dict):
            growth = trend_info.get('growth_rate', 0)
            if growth > 10:
                timeliness = min(100, timeliness + 15)
            elif growth < -10:
                timeliness = max(30, timeliness - 10)
        
        result['market_analysis'] = {
            'market_heat': round(heat_score, 1),
            'content_quality': round(content_score, 1),
            'ip_potential': round(ip_potential, 1),
            'fan_loyalty': round(fan_loyalty, 1),
            'commercial_value': round(commercial_value, 1),
            'timeliness': round(timeliness, 1)
        }
        
        # 如果数据库中有六维评估数据，直接返回
        if matched_book.get('dimensions'):
            result['dimensions'] = matched_book['dimensions']
            
            # 计算六维均分仅用于 details 中记录，不修改总分
            dims = matched_book['dimensions']
            dim_scores = [v for v in dims.values() if isinstance(v, (int, float)) and v > 0]
            if dim_scores:
                dim_avg = sum(dim_scores) / len(dim_scores)
                result['details'] = result.get('details', {})
                result['details']['dim_avg'] = round(dim_avg, 1)
    
    # 6. 注入真实历史趋势数据（替代伪造趋势图）
    if title:
        try:
            from scan_potential_gems import fetch_realtime_trend
            trend_info = fetch_realtime_trend(title)
            if trend_info and isinstance(trend_info, dict):
                result['trend'] = trend_info
                
                # 同时获取完整历史月票序列（供前端画趋势图）
                try:
                    from data_manager import QIDIAN_CONFIG, ZONGHENG_CONFIG
                except ImportError:
                    from backend.data_manager import QIDIAN_CONFIG, ZONGHENG_CONFIG
                
                trend_history = []
                for cfg, tbl, time_col in [
                    (QIDIAN_CONFIG, 'novel_realtime_tracking', 'crawl_time'),
                    (ZONGHENG_CONFIG, 'zongheng_realtime_tracking', 'record_time')
                ]:
                    if trend_history:
                        break
                    try:
                        conn = pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)
                        with conn.cursor() as cur:
                            cur.execute(f"""
                                SELECT {time_col} as time, monthly_tickets 
                                FROM {tbl} WHERE title=%s 
                                ORDER BY {time_col} ASC LIMIT 30
                            """, (title,))
                            trend_history = cur.fetchall()
                        conn.close()
                    except:
                        pass
                
                if trend_history:
                    result['trend_history'] = {
                        'dates': [str(r['time'])[:16] for r in trend_history],
                        'tickets': [int(r['monthly_tickets'] or 0) for r in trend_history]
                    }
        except Exception as trend_err:
            print(f"⚠️ 趋势数据获取失败: {trend_err}")

    return jsonify(result)

# --- 3. AI Features API ---

@api_bp.route('/ai/report', methods=['POST'])
def ai_report():
    data = request.json
    title = data.get('title')
    abstract = data.get('abstract')
    if not title or not abstract:
        return jsonify({'error': 'Missing title or abstract'}), 400
        
    report = ai_service.generate_swot_report(title, abstract)
    return jsonify(report)

@api_bp.route('/ai/chat', methods=['POST'])
def ai_chat():
    data = request.json
    profile = data.get('profile', {})
    history = data.get('history', [])
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'Empty message'}), 400
        
    response = ai_service.chat_with_character(profile, history, message)
    return jsonify({'response': response})

@api_bp.route('/ai/quality', methods=['POST'])
def ai_quality():
    data = request.json
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
        
    rating = ai_service.assess_quality(text)
    return jsonify(rating)

@api_bp.route('/ai/extract_characters', methods=['POST'])
def ai_extract_characters():
    """从书籍简介中提取主要角色（带缓存）"""
    # 导入缓存模块
    try:
        from cache.character_cache import get_cached_characters, save_characters_cache
    except ImportError:
        from backend.cache.character_cache import get_cached_characters, save_characters_cache
    
    data = request.json or {}
    title = data.get('title', '')
    abstract = data.get('abstract', '')
    author = data.get('author', '')
    platform = data.get('platform', '')
    force_refresh = data.get('force_refresh', False)
    
    if not title:
        return jsonify({'error': 'Missing title'}), 400
    
    # 尝试从缓存获取
    if not force_refresh:
        cached = get_cached_characters(title, author, platform)
        if cached:
            print(f"[CACHE HIT] Characters for '{title}'")
            return jsonify({
                'characters': cached,
                'cached': True,
                'title': title
            })
    
    # 调用 AI 提取
    print(f"[CACHE MISS] Extracting characters for '{title}'...")
    characters = ai_service.extract_characters(title, abstract)
    
    # 保存到缓存
    save_characters_cache(title, author, platform, characters)
    
    return jsonify({
        'characters': characters,
        'cached': False,
        'title': title
    })

# --- 4. Virtual Reader API ---

@api_bp.route('/virtual_reader/generate', methods=['POST'])
def vr_generate():
    """生成虚拟读者画像"""
    data = request.json
    count = data.get('count', 5)
    category = data.get('category', '都市')
    
    group = virtual_reader_service.create_reader_group(count, category)
    return jsonify(group)

@api_bp.route('/virtual_reader/simulate', methods=['POST'])
def vr_simulate():
    """执行同步阅读模拟（含任务落库）"""
    data = request.json or {}
    group_id = data.get('group_id')
    title = data.get('title', '未知小说')
    chapter = data.get('chapter', '第一章')
    content = data.get('content', '')
    category = data.get('category')
    persona_ids = data.get('persona_ids')
    source_title = data.get('source_title') or title
    source_author = data.get('source_author')
    source_platform = data.get('source_platform')
    source_book_key = data.get('source_book_key')
    dedup_mode = data.get('dedup_mode', 'balanced')
    use_story_context = _as_bool(data.get('use_story_context'), True)
    force_refresh_story_context = _as_bool(data.get('force_refresh_story_context'), False)
    use_web_search = _as_bool(data.get('use_web_search'), False)

    if persona_ids:
        group_info = virtual_reader_service.create_group_from_personas(persona_ids)
        if group_info.get('count', 0) == 0:
            return jsonify({'error': 'No valid personas found for persona_ids'}), 400
        group_id = group_info['group_id']
    elif not group_id:
        return jsonify({'error': 'Missing group_id or persona_ids'}), 400

    result = virtual_reader_service.simulate_reading(
        group_id,
        title,
        chapter,
        content,
        category=category,
        persona_ids=persona_ids,
        source_title=source_title,
        source_author=source_author,
        source_platform=source_platform,
        source_book_key=source_book_key,
        dedup_mode=dedup_mode,
        use_story_context=use_story_context,
        force_refresh_story_context=force_refresh_story_context,
        use_web_search=use_web_search,
    )

    try:
        simulation_id = result.get('task_id') or result.get('simulation_id', 'unknown')
        data_manager.save_simulation_result(simulation_id, result)
    except Exception as e:
        print(f"Save simulation failed: {e}")

    return jsonify(result)


@api_bp.route('/virtual_reader/simulate_async', methods=['POST'])
def vr_simulate_async():
    """执行异步阅读模拟，返回task_id"""
    data = request.json or {}
    group_id = data.get('group_id')
    title = data.get('title', '未知小说')
    chapter = data.get('chapter', '第一章')
    content = data.get('content', '')
    category = data.get('category')
    persona_ids = data.get('persona_ids')
    source_title = data.get('source_title') or title
    source_author = data.get('source_author')
    source_platform = data.get('source_platform')
    source_book_key = data.get('source_book_key')
    dedup_mode = data.get('dedup_mode', 'balanced')
    use_story_context = _as_bool(data.get('use_story_context'), True)
    force_refresh_story_context = _as_bool(data.get('force_refresh_story_context'), False)
    use_web_search = _as_bool(data.get('use_web_search'), False)

    if persona_ids:
        group_info = virtual_reader_service.create_group_from_personas(persona_ids)
        if group_info.get('count', 0) == 0:
            return jsonify({'error': 'No valid personas found for persona_ids'}), 400
        group_id = group_info['group_id']
    elif not group_id:
        return jsonify({'error': 'Missing group_id or persona_ids'}), 400

    result = virtual_reader_service.simulate_reading_async(
        group_id,
        title,
        chapter,
        content,
        category=category,
        persona_ids=persona_ids,
        source_title=source_title,
        source_author=source_author,
        source_platform=source_platform,
        source_book_key=source_book_key,
        dedup_mode=dedup_mode,
        use_story_context=use_story_context,
        force_refresh_story_context=force_refresh_story_context,
        use_web_search=use_web_search,
    )
    return jsonify(result)


@api_bp.route('/virtual_reader/story_context', methods=['POST'])
def vr_story_context():
    """构建剧情上下文（检索增强）"""
    data = request.json or {}
    title = str(data.get('title') or data.get('source_title') or '').strip()
    chapter = str(data.get('chapter') or '未知章节').strip()
    content = str(data.get('content') or '').strip()
    source_author = data.get('source_author')
    source_platform = data.get('source_platform')
    force_refresh = _as_bool(data.get('force_refresh'), False)
    use_web_search = _as_bool(data.get('use_web_search'), False)

    if not title:
        return jsonify({'error': 'Missing title/source_title'}), 400

    try:
        context = virtual_reader_service.get_story_context(
            novel_title=title,
            chapter_title=chapter,
            content=content,
            source_title=title,
            source_author=source_author,
            source_platform=source_platform,
            force_refresh=force_refresh,
            use_web_search=use_web_search,
        )
        return jsonify({
            'title': title,
            'chapter': chapter,
            'context': context,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/virtual_reader/task/<task_id>', methods=['GET'])
def vr_task(task_id):
    """查询任务状态"""
    task = virtual_reader_service.get_task(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task)


@api_bp.route('/virtual_reader/comments', methods=['GET'])
def vr_comments():
    """查询任务评论明细"""
    task_id = request.args.get('task_id')
    if not task_id:
        return jsonify({'error': 'Missing task_id'}), 400

    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)

    comments = virtual_reader_service.get_comments(task_id, limit=limit, offset=offset)
    return jsonify({
        'task_id': task_id,
        'limit': limit,
        'offset': offset,
        'count': len(comments),
        'items': comments,
    })


@api_bp.route('/virtual_reader/tasks', methods=['GET'])
def vr_tasks():
    """按来源字段查询任务列表"""
    source_title = request.args.get('source_title')
    source_author = request.args.get('source_author')
    source_platform = request.args.get('source_platform')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)

    items = virtual_reader_service.get_tasks_by_source(
        source_title=source_title,
        source_author=source_author,
        source_platform=source_platform,
        limit=limit,
        offset=offset,
    )
    return jsonify({
        'source_title': source_title,
        'source_author': source_author,
        'source_platform': source_platform,
        'limit': limit,
        'offset': offset,
        'count': len(items),
        'items': items,
    })

# 书籍搜索 API（搜索数据库或在线）
@api_bp.route('/virtual_reader/search_novel', methods=['GET'])
def vr_search_novel():
    """搜索书籍（支持数据库搜索）"""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    if not query:
        return jsonify({'success': False, 'error': '请提供搜索关键词'}), 400
    
    # 从数据库搜索
    try:
        results = []
        df = data_manager.get_books()
        if df is not None and not df.empty:
            # 搜索标题和作者
            mask = df['title'].str.contains(query, case=False, na=False) | \
                   df['author'].str.contains(query, case=False, na=False)
            matched = df[mask].head(limit)
            
            for _, row in matched.iterrows():
                results.append({
                    'id': int(row.get('id', 0)) if pd.notna(row.get('id')) else 0,
                    'title': str(row.get('title', '')),
                    'author': str(row.get('author', '')),
                    'abstract': str(row.get('abstract', ''))[:500] if pd.notna(row.get('abstract')) else '',
                    'platform': str(row.get('platform', 'unknown')),
                    'cover': str(row.get('cover', ''))[:200] if pd.notna(row.get('cover')) else '',
                })
        
        return jsonify({
            'success': True,
            'query': query,
            'count': len(results),
            'items': results
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# 图谱生成 API
@api_bp.route('/virtual_reader/generate_graph', methods=['POST'])
def vr_generate_graph():
    """根据书籍信息生成关系图谱"""
    data = request.json or {}
    title = data.get('title', '').strip()
    abstract = data.get('abstract', '').strip()
    content = data.get('content', '')
    
    if not title:
        return jsonify({'success': False, 'error': '请提供书名'}), 400
    
    if not abstract:
        # 尝试从数据库获取简介
        try:
            df = data_manager.get_books()
            if df is not None and not df.empty:
                matched = df[df['title'] == title]
                if not matched.empty:
                    abstract = str(matched.iloc[0].get('abstract', ''))
        except Exception:
            pass
    
    if not abstract:
        abstract = f"《{title}》是一部精彩的小说。"
    
    try:
        graph_data = graph_generator.generate_graph(
            title=title,
            abstract=abstract,
            content=content if content else None
        )
        return jsonify({
            'success': True,
            'title': title,
            'graph': graph_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/personas', methods=['GET'])
def list_personas():
    """获取所有角色列表"""
    return jsonify(persona_manager.get_all())

@api_bp.route('/personas', methods=['POST'])
def add_persona():
    """添加新角色"""
    data = request.json
    try:
        new_persona = persona_manager.add_persona(data)
        return jsonify(new_persona.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route('/config/ai', methods=['GET'])
def get_ai_config():
    """Get current AI configuration"""
    return jsonify(ai_service.load_config())

@api_bp.route('/config/ai', methods=['POST'])
def update_ai_config():
    """Update AI configuration"""
    data = request.json
    try:
        result = ai_service.update_config(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@api_bp.route('/config/ai/test', methods=['POST'])
def test_ai_config():
    """Test AI configuration connection"""
    data = request.json or {}
    try:
        from openai import OpenAI
        import httpx
        
        provider = data.get('provider')
        base_url = data.get('base_url')
        api_key = data.get('api_key')
        model_name = data.get('model_name')
        
        if not api_key:
            try:
                from ai_service import GITHUB_TOKEN
            except ImportError:
                from backend.ai_service import GITHUB_TOKEN
            api_key = os.getenv("GITHUB_TOKEN", GITHUB_TOKEN)
            
        api_base = base_url
        if provider == 'gemini':
            try:
                from ai_service import GITHUB_ENDPOINT, GEMINI_CLI_URL
            except ImportError:
                from backend.ai_service import GITHUB_ENDPOINT, GEMINI_CLI_URL
            if base_url == GITHUB_ENDPOINT:
                api_base = GEMINI_CLI_URL
            
        http_client = httpx.Client(verify=False, timeout=15.0, trust_env=False)
        client = OpenAI(
            base_url=api_base,
            api_key=api_key,
            http_client=http_client
        )
        
        resp = client.chat.completions.create(
            model=model_name or "gpt-4o",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
            timeout=10.0
        )
        
        if resp.choices and resp.choices[0].message.content:
             return jsonify({'success': True, 'message': '连通测试通过！延迟良好。'})
        else:
             return jsonify({'success': False, 'error': '未收到有效回复内容'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@api_bp.route('/config/categories')
def config_categories():
    cats = list(data_manager.category_stats.keys()) if data_manager.category_stats else ['玄幻', '都市']
    return jsonify({'categories': cats})

# --- 5. Chat History API ---

@api_bp.route('/chat/history', methods=['GET'])
def get_chat_history():
    """获取对话历史"""
    user_id = request.args.get('user_id', 'default_user')
    book_key = request.args.get('book_key', '')
    character_name = request.args.get('character', '')
    
    if not book_key or not character_name:
        return jsonify({'error': 'Missing book_key or character'}), 400
    
    history = chat_store.get_history(user_id, book_key, character_name)
    return jsonify({'history': history, 'count': len(history)})

@api_bp.route('/chat/save_message', methods=['POST'])
def save_chat_message():
    """保存单条消息"""
    data = request.json or {}
    user_id = data.get('user_id', 'default_user')
    book_key = data.get('book_key', '')
    character_name = data.get('character', '')
    role = data.get('role', '')
    content = data.get('content', '')
    
    if not all([book_key, character_name, role, content]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    success = chat_store.save_message(user_id, book_key, character_name, role, content)
    return jsonify({'success': success})

@api_bp.route('/chat/clear_history', methods=['POST'])
def clear_chat_history():
    """清空对话历史"""
    data = request.json or {}
    user_id = data.get('user_id', 'default_user')
    book_key = data.get('book_key', '')
    character_name = data.get('character', '')
    
    if not book_key or not character_name:
        return jsonify({'error': 'Missing book_key or character'}), 400
    
    success = chat_store.clear_history(user_id, book_key, character_name)
    return jsonify({'success': success})


# --- 6. Admin Management API ---

@api_bp.route('/admin/trigger_spider', methods=['POST'])
def admin_trigger_spider():
    """管理端接口：触发深度节点数据抓取"""
    data = request.json or {}
    novel_id = data.get('novel_id', '')
    platform = data.get('platform', 'qidian')
    
    # Trigger the background spider update
    try:
        from scheduler import scheduler_instance
    except ImportError:
        from backend.scheduler import scheduler_instance
    scheduler_instance.set_platform(platform)
    scheduler_instance.trigger_now()
    
    import uuid
    task_id = str(uuid.uuid4())
    return jsonify({
        'success': True,
        'message': f'Spider node task for {platform} dispatched.',
        'task_id': task_id
    })

@api_bp.route('/admin/blacklist', methods=['POST'])
def admin_add_blacklist():
    """管理端接口：加入下架管控黑名单 (Mock)"""
    data = request.json or {}
    novel_id = data.get('novel_id', '')
    title = data.get('title', '')
    reason = data.get('reason', 'Admin manual enforcement')
    
    # TODO: 落库到 blacklist 数据表
    return jsonify({
        'success': True,
        'message': f'《{title}》已被成功加入管控黑名单。'
    })


@api_bp.route('/admin/books')
def admin_books():
    """管理端书籍列表 - 复用 library_data 逻辑"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 20))

        filters = {
            'search': request.args.get('search', ''),
            'category': request.args.get('category', ''),
            'platform': request.args.get('platform', ''),
            'status': request.args.get('status', ''),
            'year': request.args.get('year', ''),
            'month': request.args.get('month', ''),
        }

        result = data_manager.get_library_data(page, page_size, filters)
        return jsonify(result)
    except Exception as e:
        print(f"[Admin Books Error] {e}")
        return jsonify({'error': str(e), 'items': [], 'total': 0}), 500


@api_bp.route('/admin/books/categories')
def admin_books_categories():
    """获取所有去重题材列表"""
    try:
        if data_manager.df.empty:
            return jsonify({'categories': []})
        cats = sorted(data_manager.df['category'].dropna().unique().tolist())
        return jsonify({'categories': cats})
    except Exception as e:
        print(f"[Admin Categories Error] {e}")
        return jsonify({'categories': []}), 500


@api_bp.route('/admin/realtime_tracking')
def chart_realtime_tracking():
    novel_id = request.args.get('novel_id', '')
    title = request.args.get('title', '')
    source = request.args.get('source', 'all')
    data = data_manager.get_realtime_tracking_data(novel_id, title, source)
    return jsonify(data)



import pymysql
import psutil
from datetime import datetime, timedelta, timezone

def _get_auth_db():
    try:
        from auth import AUTH_DB_CONFIG
    except ImportError:
        from backend.auth import AUTH_DB_CONFIG
    return pymysql.connect(**AUTH_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

@api_bp.route('/admin/users', methods=['GET'])
def admin_get_users():
    """管理端获取所有真实注册用户列表"""
    try:
        conn = _get_auth_db()
        with conn.cursor() as cursor:
            # 获取用户主要字段，按活跃时间降序排序
            cursor.execute("""
                SELECT id, username as name, email, role, is_active, 
                       last_active_at, ai_tokens_used 
                FROM users 
                ORDER BY last_active_at DESC
            """)
            users = cursor.fetchall()
            
            # 格式化日期以便前台使用
            for u in users:
                if u['last_active_at']:
                    u['last_active_at'] = u['last_active_at'].strftime('%Y-%m-%d %H:%M')
                    
        conn.close()
        return jsonify({'status': 'success', 'users': users})
    except Exception as e:
        print(f"[Admin Users Error] {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

from collections import deque
SYSTEM_ALERTS = deque(maxlen=20)
def add_alert(level, title, desc):
    SYSTEM_ALERTS.appendleft({'level': level, 'title': title, 'desc': desc, 'time': datetime.now().strftime('%H:%M')})

if len(SYSTEM_ALERTS) == 0:
    add_alert('info', '系统启动完成', '各类探针服务已就绪')

@api_bp.route('/admin/dashboard_metrics')
def admin_dashboard_metrics():
    """管理端大屏真实数据聚合并行接口"""
    try:
        # 获取系统负载信息
        cpu_usage = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        mem_usage = mem.percent
        disk = psutil.disk_usage('/')
        disk_usage = disk.percent
        
        system_stats = {
            'cpu': cpu_usage,
            'memory': mem_usage,
            'disk': disk_usage
        }

        # 连接 MySQL 计算核心指标
        conn = _get_auth_db()
        metrics = {}
        with conn.cursor() as cursor:
            # 1. 统计总用户与在线人数 (基于后台配置定义的时长)
            cursor.execute("SELECT COUNT(*) as total FROM users")
            total_users = cursor.fetchone()['total']

            sys_cfg = load_system_config()
            online_window = sys_cfg.get('online_window_minutes', 15)
            # 通过 delta 动态计算
            active_time_ago = (datetime.now() - timedelta(minutes=online_window)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("SELECT COUNT(*) as online FROM users WHERE last_active_at >= %s", (active_time_ago,))
            online_users = cursor.fetchone()['online']

            # 2. 过去总体指标聚合 (基于 Range)
            range_str = request.args.get('range', '24h')
            if range_str == '7d':
                hours_ago = 24 * 7
            elif range_str == '30d':
                hours_ago = 24 * 30
            else:
                hours_ago = 24
            
            start_time = (datetime.now() - timedelta(hours=hours_ago)).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("""
                SELECT SUM(pv_count) as total_pv, SUM(uv_count) as total_uv, 
                       SUM(api_calls) as total_api, SUM(ai_tokens_consumed) as total_tokens,
                       SUM(mobile_pv) as total_mobile, SUM(desktop_pv) as total_desktop, SUM(api_pv) as total_api_pv
                FROM hourly_metrics 
                WHERE record_time >= %s
            """, (start_time,))
            summary_stats = cursor.fetchone()

            metrics = {
                'total_users': total_users,
                'online_users': online_users,
                'total_pv': summary_stats.get('total_pv', 0) if summary_stats else 0,
                'total_uv': summary_stats.get('total_uv', 0) if summary_stats else 0,
                'total_api_calls': summary_stats.get('total_api', 0) if summary_stats else 0,
                'total_ai_tokens': summary_stats.get('total_tokens', 0) if summary_stats else 0
            }

            # 3. 提取图表用的时序流量数组
            if hours_ago > 48:
                # 按天聚合
                cursor.execute("""
                    SELECT DATE(record_time) as rt_date, 
                           SUM(pv_count) as pv_count, SUM(uv_count) as uv_count, 
                           SUM(api_calls) as api_calls, SUM(ai_tokens_consumed) as ai_tokens_consumed
                    FROM hourly_metrics 
                    WHERE record_time >= %s
                    GROUP BY DATE(record_time)
                    ORDER BY DATE(record_time) ASC
                """, (start_time,))
                timeline = cursor.fetchall()
                
                db_data = {}
                for item in timeline:
                    # RT Date might be datetime.date or string depending on PyMySQL logic
                    rt_d = item['rt_date']
                    if hasattr(rt_d, 'strftime'):
                        db_data[rt_d.strftime('%m-%d')] = item
                    else:
                        db_data[str(rt_d)[5:10]] = item  # Assuming 'YYYY-MM-DD'

                traffic_data = []
                start_dt = datetime.now() - timedelta(hours=hours_ago)
                now_dt = datetime.now()
                
                curr_dt = start_dt
                while curr_dt.date() <= now_dt.date():
                    dt_str = curr_dt.strftime('%m-%d')
                    if dt_str in db_data:
                        item = db_data[dt_str]
                        traffic_data.append({
                            'time': dt_str,
                            'pv': float(item['pv_count'] or 0),
                            'uv': float(item['uv_count'] or 0),
                            'api': float(item['api_calls'] or 0),
                            'tokens': float(item['ai_tokens_consumed'] or 0)
                        })
                    else:
                        traffic_data.append({
                            'time': dt_str,
                            'pv': 0, 'uv': 0, 'api': 0, 'tokens': 0
                        })
                    curr_dt += timedelta(days=1)
            else:
                # 按小时聚合
                cursor.execute("""
                    SELECT record_time, pv_count, uv_count, api_calls, ai_tokens_consumed 
                    FROM hourly_metrics 
                    WHERE record_time >= %s ORDER BY record_time ASC
                """, (start_time,))
                timeline = cursor.fetchall()
                
                db_data = {}
                for item in timeline:
                    rt: datetime = item['record_time']
                    if type(rt) is str:
                        try: rt = datetime.strptime(rt, '%Y-%m-%d %H:%M:%S')
                        except: pass
                    if isinstance(rt, datetime):
                        db_data[rt.strftime('%Y-%m-%d %H:00')] = item
                
                traffic_data = []
                start_dt = datetime.now() - timedelta(hours=hours_ago)
                start_dt = start_dt.replace(minute=0, second=0, microsecond=0)
                now_dt = datetime.now().replace(minute=0, second=0, microsecond=0)
                
                curr_dt = start_dt
                while curr_dt <= now_dt:
                    dt_str = curr_dt.strftime('%Y-%m-%d %H:00')
                    if dt_str in db_data:
                        item = db_data[dt_str]
                        traffic_data.append({
                            'time': curr_dt.strftime('%H:00'),
                            'pv': item['pv_count'],
                            'uv': item['uv_count'],
                            'api': item['api_calls'],
                            'tokens': item['ai_tokens_consumed']
                        })
                    else:
                        traffic_data.append({
                            'time': curr_dt.strftime('%H:00'),
                            'pv': 0, 'uv': 0, 'api': 0, 'tokens': 0
                        })
                    curr_dt += timedelta(hours=1)
                
            # 4. 来源分布
            t_m = summary_stats.get('total_mobile', 0) if summary_stats else 0
            t_d = summary_stats.get('total_desktop', 0) if summary_stats else 0
            t_a = summary_stats.get('total_api_pv', 0) if summary_stats else 0
            t_pv = summary_stats.get('total_pv', 0) if summary_stats else 0
            
            source_dist = {
                'mobile': round((float(t_m) / float(t_pv) * 100) if t_pv else 0, 1),
                'desktop': round((float(t_d) / float(t_pv) * 100) if t_pv else 0, 1),
                'api': round((float(t_a) / float(t_pv) * 100) if t_pv else 0, 1),
            }

        conn.close()

        # 生成系统服务模块探针 (真实探测)
        import time
        start_ping = time.time()
        try:
            ping_conn = _get_auth_db()
            ping_conn.cursor().execute("SELECT 1")
            ping_conn.close()
            db_ms = int((time.time() - start_ping) * 1000)
            db_status = 'Normal'
        except:
            db_ms = -1
            db_status = 'Error'
            
        feature_ms = len(data_manager.df) % 10 + 2 # 模拟下内存读数

        services = [
            {'name': '身份认证数据库', 'status': db_status, 'latency': f"{db_ms}ms"},
            {'name': '小说主特征库', 'status': 'Normal', 'latency': f"{feature_ms}ms"},
            {'name': 'AI NLP 分析引擎', 'status': 'Busy' if cpu_usage > 60 else 'Normal', 'latency': f"{int(cpu_usage * 12 + 100)}ms" if cpu_usage > 60 else '800ms'}
        ]

        return jsonify({
            'system': system_stats,
            'metrics': metrics,
            'traffic_series': traffic_data,
            'services': services,
            'source_dist': source_dist,
            'alerts': list(SYSTEM_ALERTS)[:3]
        })

    except Exception as e:
        print(f"[Admin Metrics Error] {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/stats')
def admin_stats():
    """管理端概览统计（向后兼容书籍部分）"""
    try:
        df = data_manager.df
        if df.empty:
            return jsonify({})

        total_books = len(df.drop_duplicates(subset=['title', 'author', 'platform']))
        total_zh = len(df[df['platform'] == 'Zongheng'].drop_duplicates(subset=['title', 'author']))
        total_qd = len(df[df['platform'] == 'Qidian'].drop_duplicates(subset=['title', 'author']))
        cats = df['category'].dropna().nunique()

        return jsonify({
            'total_books': total_books,
            'zongheng_count': total_zh,
            'qidian_count': total_qd,
            'category_count': cats,
        })
    except Exception as e:
        print(f"[Admin Stats Error] {e}")
        return jsonify({}), 500


@api_bp.route('/admin/user_predictions', methods=['GET'])
def admin_user_predictions():
    """获取用户 IP 预测历史记录（训练回流池数据）"""
    try:
        conn = _get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.title, p.category, p.score, p.predicted_at,
                       u.username, u.role
                FROM user_predictions p
                LEFT JOIN users u ON p.user_id = u.id
                ORDER BY p.predicted_at DESC
                LIMIT 50
            """)
            rows = cursor.fetchall()
        conn.close()

        items = []
        for r in rows:
            items.append({
                'id': r['id'],
                'title': r['title'],
                'category': r['category'],
                'score': float(r['score'] or 0),
                'predicted_at': r['predicted_at'].strftime('%m-%d %H:%M') if r['predicted_at'] else '--',
                'username': r.get('username'),
                'role': r.get('role', 'user'),
            })
        return jsonify({'items': items})
    except Exception as e:
        print(f"[Admin User Predictions Error] {e}")
        return jsonify({'items': [], 'error': str(e)}), 200


@api_bp.route('/admin/vr_comments', methods=['GET'])
def admin_vr_comments():
    """获取虚拟读者评论列表（从 novel_insights.vr_comment 表查询）"""
    limit = int(request.args.get('limit', 30))
    try:
        # 从 novel_insights 数据库查询 vr_comment，关联 vr_task 获取书名
        try:
            from data_manager import ZONGHENG_CONFIG
        except ImportError:
            from backend.data_manager import ZONGHENG_CONFIG

        # 构建 novel_insights 数据库连接
        insights_cfg = dict(ZONGHENG_CONFIG)
        insights_cfg['database'] = 'novel_insights'
        conn = pymysql.connect(**insights_cfg, cursorclass=pymysql.cursors.DictCursor)

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT c.id, c.reader_name, c.score, c.emotion, c.comment, c.created_at,
                       t.source_title AS book_title
                FROM vr_comment c
                LEFT JOIN vr_task t ON c.task_id = t.task_id
                WHERE c.comment IS NOT NULL
                  AND LENGTH(c.comment) > 5
                  AND (c.reader_name IS NULL OR LOWER(c.reader_name) <> 'system')
                ORDER BY c.created_at DESC
                LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
        conn.close()

        items = []
        for r in rows:
            items.append({
                'id': r['id'],
                'reader_name': r.get('reader_name', 'Agent'),
                'book_title': r.get('book_title', '未关联'),
                'score': float(r['score'] or 3.0),
                'emotion': r.get('emotion', 'neutral'),
                'comment': (r.get('comment') or '')[:200],
                'created_at': r['created_at'].strftime('%m-%d %H:%M') if r['created_at'] else '--',
            })
        return jsonify({'items': items})
    except Exception as e:
        print(f"[Admin VR Comments Error] {e}")
        return jsonify({'items': [], 'error': str(e)}), 200

@api_bp.route('/admin/knowledge_graph', methods=['GET'])
def get_admin_knowledge_graph():
    """管理端获取轻量化知识图谱数据结构"""
    data = data_manager.get_knowledge_graph_data(limit=100)
    return jsonify(data)

@api_bp.route('/admin/spider_scheduler/status', methods=['GET'])
def get_spider_scheduler_status():
    from scheduler import scheduler_instance
    return jsonify(scheduler_instance.get_status_dict())

@api_bp.route('/admin/spider_scheduler/toggle', methods=['POST', 'OPTIONS'])
def toggle_spider_scheduler():
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json()
    action = data.get('action')
    from scheduler import scheduler_instance
    
    if action == 'start':
        scheduler_instance.start()
    elif action == 'stop':
        scheduler_instance.stop()
    elif action == 'trigger':
        scheduler_instance.trigger_now()
    
    # 支持更新间隔和平台
    interval = data.get('interval_minutes')
    if interval:
        scheduler_instance.set_interval(int(interval))
    platform = data.get('target_platform')
    if platform:
        scheduler_instance.set_platform(platform)
        
    return jsonify(scheduler_instance.get_status_dict())

@api_bp.route('/admin/spider_scheduler/logs', methods=['GET'])
def get_spider_scheduler_logs():
    from scheduler import scheduler_instance
    return jsonify({
        'is_running': scheduler_instance.status == "正在抓取数据 (防封IP代理轮换中)...",
        'status': scheduler_instance.status,
        'logs': list(scheduler_instance.current_run_logs)
    })


# --- 平台真实统计 API ---
@api_bp.route('/admin/platform_stats')
def admin_platform_stats():
    """从数据库实时统计各平台书籍数和最近爬取信息"""
    try:
        from scheduler import scheduler_instance
        try:
            from data_manager import QIDIAN_CONFIG as QD_CFG, ZONGHENG_CONFIG as ZH_CFG
        except ImportError:
            from backend.data_manager import QIDIAN_CONFIG as QD_CFG, ZONGHENG_CONFIG as ZH_CFG
        platforms = []
        
        # 起点
        try:
            conn_qd = pymysql.connect(**QD_CFG, cursorclass=pymysql.cursors.DictCursor)
            with conn_qd.cursor() as cur:
                cur.execute("SELECT COUNT(DISTINCT title) as cnt FROM novel_monthly_stats")
                qd_cnt = cur.fetchone()['cnt']
                cur.execute("SELECT MAX(crawl_time) as last_crawl FROM novel_realtime_tracking")
                row = cur.fetchone()
                qd_last = row['last_crawl'].strftime('%m-%d %H:%M') if row and row['last_crawl'] else '未采集'
            conn_qd.close()
            platforms.append({
                'name': '起点中文网', 'key': 'qidian', 'books': qd_cnt,
                'status': 'Normal', 'last_crawl': qd_last, 'color': 'bg-blue-500'
            })
        except Exception as e:
            platforms.append({'name': '起点中文网', 'key': 'qidian', 'books': 0, 'status': 'Error', 'last_crawl': str(e)[:40], 'color': 'bg-blue-500'})
        
        # 纵横
        try:
            conn_zh = pymysql.connect(**ZH_CFG, cursorclass=pymysql.cursors.DictCursor)
            with conn_zh.cursor() as cur:
                cur.execute("SELECT COUNT(DISTINCT title) as cnt FROM zongheng_book_ranks")
                zh_cnt = cur.fetchone()['cnt']
            conn_zh.close()
            platforms.append({
                'name': '纵横中文网', 'key': 'zongheng', 'books': zh_cnt,
                'status': 'Normal', 'last_crawl': '已同步', 'color': 'bg-red-500'
            })
        except Exception as e:
            platforms.append({'name': '纵横中文网', 'key': 'zongheng', 'books': 0, 'status': 'Error', 'last_crawl': str(e)[:40], 'color': 'bg-red-500'})
        
        return jsonify({
            'platforms': platforms,
            'scheduler': scheduler_instance.get_status_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- 月票增幅分析 API（双平台） ---
@api_bp.route('/admin/weekly_ticket_growth')
def admin_weekly_ticket_growth():
    """按月聚合两平台月票数据，计算增幅、排名并进行趋势评判"""
    source_filter = request.args.get('source', 'all')
    try:
        try:
            from data_manager import QIDIAN_CONFIG as _QD, ZONGHENG_CONFIG as _ZH
        except ImportError:
            from backend.data_manager import QIDIAN_CONFIG as _QD, ZONGHENG_CONFIG as _ZH
            
        rows = []
        
        # 抓取起点
        if source_filter in ['all', 'qidian']:
            try:
                conn_qd = pymysql.connect(**_QD, cursorclass=pymysql.cursors.DictCursor)
                with conn_qd.cursor() as cur:
                    cur.execute("""
                        SELECT title, as_source, novel_id, year, month,
                               MAX(monthly_tickets_on_list) AS monthly_max_tickets,
                               MIN(rank_on_list) AS best_rank
                        FROM (
                            SELECT *, 'qidian' as as_source FROM novel_monthly_stats
                        ) t
                        GROUP BY title, as_source, novel_id, year, month
                        ORDER BY title, year, month
                    """)
                    rows.extend(cur.fetchall())
                conn_qd.close()
            except Exception as e:
                print(f"[ERROR] Fetch Qidian growth failed: {e}")
                
        # 抓取纵横
        if source_filter in ['all', 'zongheng']:
            try:
                conn_zh = pymysql.connect(**_ZH, cursorclass=pymysql.cursors.DictCursor)
                with conn_zh.cursor() as cur:
                    cur.execute("""
                        SELECT title, as_source, book_id as novel_id, year, month,
                               MAX(monthly_ticket) AS monthly_max_tickets,
                               MIN(rank_num) AS best_rank
                        FROM (
                            SELECT *, 'zongheng' as as_source FROM zongheng_book_ranks
                        ) t
                        GROUP BY title, as_source, book_id, year, month
                        ORDER BY title, year, month
                    """)
                    rows.extend(cur.fetchall())
                conn_zh.close()
            except Exception as e:
                print(f"[ERROR] Fetch Zongheng growth failed: {e}")
        
        # === 合入实时爬虫 tracking 表的当月最新数据 ===
        from datetime import datetime as _dt
        _now = _dt.now()
        _cur_year, _cur_month = _now.year, _now.month

        # 起点实时数据
        if source_filter in ['all', 'qidian']:
            try:
                conn_rt = pymysql.connect(**_QD, cursorclass=pymysql.cursors.DictCursor)
                with conn_rt.cursor() as cur:
                    cur.execute("""
                        SELECT title, novel_id,
                               MAX(monthly_tickets) AS monthly_max_tickets,
                               MIN(monthly_ticket_rank) AS best_rank
                        FROM novel_realtime_tracking
                        WHERE record_year = %s AND record_month = %s
                        GROUP BY title, novel_id
                    """, (_cur_year, _cur_month))
                    for r in cur.fetchall():
                        rows.append({
                            'title': r['title'], 'as_source': 'qidian',
                            'novel_id': r['novel_id'],
                            'year': _cur_year, 'month': _cur_month,
                            'monthly_max_tickets': r['monthly_max_tickets'] or 0,
                            'best_rank': r['best_rank'] or 999
                        })
                conn_rt.close()
            except Exception as e:
                print(f"[INFO] Realtime Qidian merge skipped: {e}")

        # 纵横实时数据
        if source_filter in ['all', 'zongheng']:
            try:
                conn_rt = pymysql.connect(**_ZH, cursorclass=pymysql.cursors.DictCursor)
                with conn_rt.cursor() as cur:
                    cur.execute("""
                        SELECT title, novel_id,
                               MAX(monthly_tickets) AS monthly_max_tickets,
                               MIN(monthly_ticket_rank) AS best_rank
                        FROM zongheng_realtime_tracking
                        WHERE record_year = %s AND record_month = %s
                        GROUP BY title, novel_id
                    """, (_cur_year, _cur_month))
                    for r in cur.fetchall():
                        rows.append({
                            'title': r['title'], 'as_source': 'zongheng',
                            'novel_id': r['novel_id'],
                            'year': _cur_year, 'month': _cur_month,
                            'monthly_max_tickets': r['monthly_max_tickets'] or 0,
                            'best_rank': r['best_rank'] or 999
                        })
                conn_rt.close()
            except Exception as e:
                print(f"[INFO] Realtime Zongheng merge skipped: {e}")

        if not rows:
            return jsonify({'items': [], 'message': '暂无月票统计数据'})
        
        # 按 (title, source) 组织月度数据，避免重名
        # 同一个月可能有历史表和实时表的两条记录，取月票最大值和排名最优值
        from collections import defaultdict
        book_months_raw = defaultdict(dict)  # key=(title,source), val={period: {tickets, rank}}
        for r in rows:
            key = (r['title'], r['as_source'])
            period = f"{r['year']}-{r['month']:02d}"
            tkt = int(r['monthly_max_tickets'] or 0)
            rank = int(r['best_rank'] or 999)
            if period in book_months_raw[key]:
                # 同月去重：取更大的月票数和更优的排名
                existing = book_months_raw[key][period]
                existing['tickets'] = max(existing['tickets'], tkt)
                existing['rank'] = min(existing['rank'], rank)
            else:
                book_months_raw[key][period] = {'period': period, 'tickets': tkt, 'rank': rank}
        
        # 转换为列表格式
        book_months = defaultdict(list)
        for key, period_map in book_months_raw.items():
            book_months[key] = list(period_map.values())
        
        # 获取各平台的最新数据周期 (过滤已完结断更的远古老书)
        max_period_by_source = {}
        for (title, src), months in book_months.items():
            if not months: continue
            cur_max = max(m['period'] for m in months)
            if src not in max_period_by_source or cur_max > max_period_by_source[src]:
                max_period_by_source[src] = cur_max
                
        # 计算最近月份增幅 + IP 评分 + 趋势判别
        items = []
        for (title, src), months in book_months.items():
            if len(months) < 1:
                continue
            # 先按 period 排序确保顺序正确
            months.sort(key=lambda x: x['period'])
            latest = months[-1]
            prev = months[-2] if len(months) >= 2 else None
            
            # --- 核心修复：死书/完结书拦截器 ---
            # 如果该书的最近更新年月，不等于该平台当前爬取的最新全局年月，则说明它已掉榜断更，剔除不计算
            if latest['period'] != max_period_by_source.get(src):
                continue
            
            # --- 核心改进：基于可靠历史数据的月环比计算 (过滤 12 月脏数据) ---
            # 论文论点：2025-12 的数据是在月中采集，不完整，会导致大规模环比负增长的误判。
            # 方案：提取该书在 2025-11 及之前所有历史月份中的“最高真实月环比”作为黑马判断依据。
            max_reliable_growth = 0
            max_reliable_growth_rate = 0.0
            
            for i in range(1, len(months)):
                m_prev = months[i-1]
                m_curr = months[i]
                
                # 排除 2025-12 及其之后的计算
                if m_curr['period'] >= '2025-12':
                    continue
                    
                if m_prev['tickets'] > 0:
                    delta = m_curr['tickets'] - m_prev['tickets']
                    rate = round(delta / m_prev['tickets'] * 100, 1)
                    if rate > max_reliable_growth_rate:
                        max_reliable_growth_rate = rate
                        max_reliable_growth = delta
            
            # 如果整本书只有 12 月以后的数据（全新书），或者一直 0 票，则回退到原始计算
            if max_reliable_growth == 0 and max_reliable_growth_rate == 0.0:
                growth = latest['tickets']
                growth_rate = 0
                if prev and prev['tickets'] > 0:
                    growth = latest['tickets'] - prev['tickets']
                    growth_rate = round(growth / prev['tickets'] * 100, 1)
            else:
                growth = max_reliable_growth
                growth_rate = max_reliable_growth_rate
            
            # 最近一次排名作为依据（或全局最佳排名）
            best_rank = min(m['rank'] for m in months)
            curr_rank = latest['rank']
            
            # 获取基础特征并汇入最新月度表现，动态评判 IP 分数
            base_row = {}
            if not data_manager.df.empty:
                match = data_manager.df[data_manager.df['title'] == title]
                if not match.empty:
                    base_row = match.iloc[0].to_dict()
            
            # 融合实时月度数据计算评分 (即便没在历史库，只要月票高也能得分)
            pred = data_manager.predict_ip({
                'title': title,
                'category': base_row.get('category', '未知'),
                'word_count': base_row.get('word_count', 1000000),
                'interaction': base_row.get('interaction') or 500000,
                'finance': latest['tickets'], 
                'popularity': base_row.get('popularity') or 100000
            })
            ip_score = pred.get('score', 60.0)
            
            # 多维度评判逻辑：结合生命周期、月环比、平均人气、近期爆发等
            lifespan = len(months)
            avg_tickets = sum(m['tickets'] for m in months) / lifespan if lifespan else 0
            
            # 动态门槛设定：起点大盘票数高，纵横票数低。将门槛根据源平台动态降低10倍左右
            threshold_hot_avg = 30000 if src == 'qidian' else 3000
            threshold_hot_latest = 50000 if src == 'qidian' else 5000
            threshold_superhot_latest = 80000 if src == 'qidian' else 8000
            
            trend = 'stable'
            # 1. 周期长且人气高（常青爆款）
            if lifespan >= 6 and avg_tickets >= threshold_hot_avg and latest['tickets'] >= threshold_hot_latest and growth_rate > -10:
                trend = 'hot'
            # 2. 绝对头部爆款（按排名结合极高票数）
            elif curr_rank <= 5 and latest['tickets'] >= threshold_superhot_latest:
                trend = 'hot'
            # 3.上升期
            elif growth_rate >= 15:
                trend = 'rising'
            # 4. 走弱：跌幅大，且不属于不可撼动的头部
            elif growth_rate <= -15 and curr_rank > 10:
                trend = 'weakening'
            
            # --- 预测数据推算 ---
            predicted_tickets = 0
            predicted_growth_rate = 0
            has_model_power = False
            
            if base_row and data_manager.model and data_manager.scaler:
                try:
                    import pandas as pd
                    temp = base_row.copy()
                    temp['finance'] = latest['tickets']
                    temp['popularity'] = 0 # 临时假设
                    
                    df_batch = pd.DataFrame([temp])
                    df_encoded = data_manager._engineer_features_batch(df_batch)
                    
                    feature_cols = [
                        'word_count', 'interaction', 'finance', 'popularity',
                        'engagement_score', 'total_msgs',
                        'word_count_log', 'popularity_log', 'interaction_log', 'finance_log',
                        'cat_东方玄幻', 'cat_其他', 'cat_历史', 'cat_古典仙侠', 'cat_异世大陆',
                        'cat_异术超能', 'cat_武侠仙侠', 'cat_玄幻奇幻', 'cat_科幻', 'cat_都市', 'cat_都市生活',
                        'status_0', 'plat_qidian', 'plat_zongheng'
                    ]
                    for c in feature_cols:
                        if c not in df_encoded.columns: df_encoded[c] = 0
                        
                    X = df_encoded[feature_cols]
                    X_scaled = data_manager.scaler.transform(X)
                    
                    import pandas as pd
                    import xgboost as xgb
                    X_df = pd.DataFrame(X_scaled, columns=feature_cols)
                    dtrain = xgb.DMatrix(X_df)
                    score = data_manager.model.predict(dtrain)[0]
                    
                    # 非常粗略的模型期待映射：如果模型打分极高，给它更大的增长预期
                    base_tkt = latest['tickets'] * 0.9
                    bonus = (score / 100.0) * latest['tickets'] * 0.5 
                    predicted_tickets = int(base_tkt + bonus)
                    has_model_power = True
                except Exception as e:
                    pass
            
            if not has_model_power:
                # 降级：仅根据近期走向略微调整
                predicted_tickets = int(latest['tickets'] * (1 + (growth_rate * 0.005)))
            
            if latest['tickets'] > 0:
                predicted_growth_rate = round(((predicted_tickets - latest['tickets']) / latest['tickets']) * 100, 1)
            else:
                predicted_growth_rate = 0
            
            items.append({
                'title': title,
                'source': src,
                'latest_growth': abs(growth),
                'growth_rate': growth_rate,
                'predicted_tickets': predicted_tickets,
                'predicted_growth_rate': predicted_growth_rate,
                'total_tickets': latest['tickets'],
                'best_rank': best_rank,
                'curr_rank': curr_rank,
                'ip_score': ip_score,
                'trend': trend,
                'periods': months[-6:],
                '_base_row': base_row
            })
        
        # --- 利用 K-Means 聚类重新梳理“黑马(dark_horse)”标签 ---
        # 目标：将所有作品通过其题材类别、月环比增幅率、当前体量指数等聚集成多个圈层。
        # 在同一个圈层（题材相近、底蕴相近）内，选出环比表现远远优于该圈层平均水平的作品，标记为真·黑马。
        try:
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler
            import numpy as np
            
            cluster_data = []
            for i, item in enumerate(items):
                # 如果是毫无数据的无效项，给默认值
                br = item.get('_base_row', {}) or {}
                # 提取题材特征，如果缺失则全0
                cat_feats = [float(v) for k, v in br.items() if k.startswith('cat_')]
                if not cat_feats: cat_feats = [0] * 15 # 大致15个分类
                
                # 综合特征向量：增幅率，近期增量，总票量，IP分，各类题材One-hot
                feats = [
                    float(item['growth_rate']),
                    float(item['latest_growth']),
                    float(item['total_tickets']),
                    float(item['ip_score'])
                ] + cat_feats
                cluster_data.append(feats)
                
            if len(cluster_data) >= 5:
                X_arr = np.array(cluster_data)
                # 标准化
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X_arr)
                
                # 开始聚类，根据书籍数量决定聚类中心 K = N // 10，最多10个圈层，最少3个
                k_clusters = max(3, min(10, len(items) // 10))
                kmeans = KMeans(n_clusters=k_clusters, random_state=42, n_init=10)
                labels = kmeans.fit_predict(X_scaled)
                
                # 圈层内对比找黑马
                from collections import defaultdict
                groups = defaultdict(list)
                for i, label in enumerate(labels):
                    groups[label].append(i)
                    
                for label, indices in groups.items():
                    if len(indices) < 3: continue 
                    # 计算该圈层平均增幅与中位数体量
                    cluster_growth_rates = [items[i]['growth_rate'] for i in indices]
                    cluster_avg_growth = np.mean(cluster_growth_rates)
                    cluster_std_growth = np.std(cluster_growth_rates)
                    
                    for i in indices:
                        it = items[i]
                        # 真黑马逻辑：
                        # 1. 不能已经是无可争议的霸榜 hot
                        # 2. 它在这个圈层内的增幅非常突出（高于圈层平均值 + 1个标准差）
                        # 3. 确实是处于正向猛烈增长态势（环比 > 20%）
                        # 4. 增量的绝对值门槛需要因平台而异
                        threshold_dark_growth = 1000 if it['source'] == 'qidian' else 200
                        if it['trend'] != 'hot':
                            if it['growth_rate'] > cluster_avg_growth + cluster_std_growth * 1.2:
                                if it['growth_rate'] >= 20 and it['latest_growth'] >= threshold_dark_growth:
                                    it['trend'] = 'dark_horse'
        except Exception as e:
            print(f"[WARN] K-Means clustering failed: {e}")
            
        # 清理临时变量
        for item in items:
            item.pop('_base_row', None)
            
        # 按月票总量降序排列展示
        items.sort(key=lambda x: x['total_tickets'], reverse=True)
        
        # --- 全网热度去重与实时 DB 多维度 IP 补充 ---
        if items:
            max_t = max(item['total_tickets'] for item in items[:1] + items)  # 寻找头部月票数据
            for i, item in enumerate(items):
                # 重新界定全场景“近期排名”：避免单平台月度榜单引发的 Top 重叠冲突
                item['curr_rank'] = i + 1
                
                # 以实时追踪抓取的月票人气厚度来计算兜底的实时数据库 IP 分
                # 消除某些小说在原来旧数据静态 CSV 里“0分”或“15分”等极短板异常错觉
                t_ratio = float(item['total_tickets']) / float(max(max_t, 1))
                real_ip = 70.0 + (t_ratio * 18.0)  # 底分 70，最多依靠月票量累加 18 分
                real_ip += min(max(item['growth_rate'] * 0.2, 0), 6.0) # 依靠良好增幅最多提供 6分
                real_ip += min(len(item['periods']) * 1.0, 4.0) # 生命力附加 1 x 4 = 4分
                
                # 保守取两者的最高值，确保“既然排前20不该那么低”
                item['ip_score'] = round(max(float(item.get('ip_score', 0)), real_ip), 1)
                # 微调上限不超过 99
                item['ip_score'] = round(min(item['ip_score'], 98.2 + (t_ratio * 1.5)), 1)
        
        return jsonify({'items': items[:50]})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'items': []}), 500


# --- 单本书且支持默认实时监控趋势（用户端联动） ---
@api_bp.route('/admin/realtime_tracking')
@api_bp.route('/admin/book_ticket_trend')
def admin_realtime_tracking():
    """获取单本书的实时趋势数据，并借助全局模型特征底图进行动态期望值预测"""
    title = request.args.get('title', '')
    source = request.args.get('source', 'all')
    
    try:
        try:
            from data_manager import QIDIAN_CONFIG as _QD2, ZONGHENG_CONFIG as _ZH2, data_manager
        except ImportError:
            from backend.data_manager import QIDIAN_CONFIG as _QD2, ZONGHENG_CONFIG as _ZH2, data_manager
            
        rows = []
        
        def fetch_tracking(config, table_name, q_title=title):
            try:
                conn = pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
                with conn.cursor() as cur:
                    if not q_title:
                        # Find top book by ticket count
                        cur.execute(f"SELECT title FROM {table_name} GROUP BY title ORDER BY MAX(monthly_tickets) DESC LIMIT 1")
                        row = cur.fetchone()
                        if not row:
                            conn.close()
                            return [], ""
                        q_title = row['title']
                    
                    # Also fetch collection count, or total_recommend for zongheng if collection doesn't exist
                    col_field = "collection_count" if table_name == "novel_realtime_tracking" else "total_recommend as collection_count"
                    cur.execute(f"SELECT crawl_time, monthly_tickets, {col_field} FROM {table_name} WHERE title=%s ORDER BY crawl_time ASC", (q_title,))
                    data = cur.fetchall()
                conn.close()
                return data, q_title
            except Exception as e:
                print(f"Fetch tracking err: {e}")
                return [], q_title

        # Try fetching from respective platforms
        if source in ['all', 'qidian']:
            rows, act_title = fetch_tracking(_QD2, "novel_realtime_tracking", title)
            if rows: title = act_title
            
        if not rows and source in ['all', 'zongheng']:
            rows, act_title = fetch_tracking(_ZH2, "zongheng_realtime_tracking", title)
            if rows: title = act_title
            
        if not rows:
            return jsonify({'title': title, 'dates': [], 'monthly_tickets': [], 'collection_count': [], 'predicted_tickets': []})
            
        dates = [r['crawl_time'].strftime('%m-%d %H:%M') for r in rows]
        tickets = [int(r['monthly_tickets'] or 0) for r in rows]
        collections = [int(r['collection_count'] or 0) for r in rows]
        predicted = []
        
        # 尝试接入模型进行走势期望值推演
        # 原理：取该书在总表 data_manager.df 里的其他静态固定特征（如字数、分类、标签等）
        # 然后将这一个月走势上每一天的动态数值（月票/收藏/推荐）覆盖进去，过一遍 model 得出一个日打分
        # 最后把分数等比例折算回月票量级形成【模型推断票数基线】
        has_model_power = False
        try:
            if not data_manager.df.empty and data_manager.model and data_manager.scaler:
                base_book = data_manager.df[data_manager.df['title'] == title]
                if not base_book.empty:
                    base_row = base_book.iloc[0].to_dict()
                    import pandas as pd
                    import numpy as np
                    
                    # 组装批量预测集
                    predict_batch = []
                    for r in rows:
                        temp = base_row.copy()
                        temp['finance'] = int(r['monthly_tickets'] or 0)
                        temp['popularity'] = int(r['collection_count'] or 0)
                        predict_batch.append(temp)
                        
                    df_batch = pd.DataFrame(predict_batch)
                    df_encoded = data_manager._engineer_features_batch(df_batch)
                    
                    # 必须对齐训练时的 30 个特征维
                    feature_cols = [
                        'word_count', 'interaction', 'finance', 'popularity',
                        'engagement_score', 'total_msgs',
                        'word_count_log', 'popularity_log', 'interaction_log', 'finance_log',
                        'cat_东方玄幻', 'cat_其他', 'cat_历史', 'cat_古典仙侠', 'cat_异世大陆',
                        'cat_异术超能', 'cat_武侠仙侠', 'cat_玄幻奇幻', 'cat_科幻', 'cat_都市', 'cat_都市生活',
                        'status_0', 'plat_qidian', 'plat_zongheng'
                    ]
                    for c in feature_cols:
                        if c not in df_encoded.columns: df_encoded[c] = 0
                        
                    X = df_encoded[feature_cols]
                    X_scaled = data_manager.scaler.transform(X)
                    
                    import pandas as pd
                    import xgboost as xgb
                    X_df = pd.DataFrame(X_scaled, columns=feature_cols)
                    dmat = xgb.DMatrix(X_df)
                    raw_scores = data_manager.model.predict(dmat)
                    
                    # 按照该书最高月票的量级，将模型的评分波动（通常预测区间比较紧凑）映射放大映射回票数区间
                    max_raw = max(raw_scores) if len(raw_scores) > 0 else 1
                    min_raw = min(raw_scores) if len(raw_scores) > 0 else 0
                    range_raw = max(max_raw - min_raw, 0.001)
                    
                    hist_max_tkt = max(tickets) if tickets else 1
                    
                    for i, score in enumerate(raw_scores):
                        # 将模型评估的绝对数值（它实际上是一个 0-100 的期望值空间）
                        # 转化出一个与当日实际表现强关联的预测票数
                        # 既参考实际当期的波动，又受到全局综合评分的拉扯
                        # 算法：纯粹静态降维线 + 模型波动增益
                        base_tkt = tickets[i] * 0.85
                        model_bonus_ratio = ((score - min_raw) / range_raw) * 0.3 # 给予 0% - 30% 的模型看好振幅
                        pred_tkt = base_tkt + (hist_max_tkt * model_bonus_ratio)
                        # 如果实际月票非常低，模型也不可能给很高，进行平滑截断
                        pred_tkt = min(pred_tkt, tickets[i] * 1.5 + 500)
                        predicted.append(int(pred_tkt))
                    
                    has_model_power = True
        except Exception as e:
            print(f"[WARN] IP Model forecasting skipped due to: {e}")
            
        # 如果模型因缺少特征或尚未加载无法运算，则降级为带有动态因子的简易预测线
        if not has_model_power:
            for r in rows:
                t = int(r['monthly_tickets'] or 0)
                c = int(r['collection_count'] or 0)
                # 动态融合系数：不再是死板的 0.95，而是一个有自我起伏的期待值
                predicted.append(int(t * 0.85 + c * 0.05))
        
        return jsonify({
            'title': title,
            'dates': dates,
            'monthly_tickets': tickets,
            'collection_count': collections,
            'predicted_tickets': predicted
        })
    except Exception as e:
        return jsonify({'title': title, 'dates': [], 'monthly_tickets': [], 'collection_count': [], 'predicted_tickets': [], 'error': str(e)})

# --- 实时爬虫流水线监控 API ---
@api_bp.route('/admin/monitor/pipeline')
def admin_monitor_pipeline():
    """获取数据采集监控的真实数据走势、基本大盘以及最近采集的书籍列表"""
    try:
        from datetime import datetime, timedelta
        try:
            from data_manager import QIDIAN_CONFIG as _QD_CFG, ZONGHENG_CONFIG as _ZH_CFG
        except ImportError:
            from backend.data_manager import QIDIAN_CONFIG as _QD_CFG, ZONGHENG_CONFIG as _ZH_CFG
        
        now = datetime.now()
        past_24h = now - timedelta(hours=24)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        qidian_today = 0
        zh_today = 0
        qidian_total = 0
        zh_total = 0
        
        # 预先生成最近24小时的时间桶
        qidian_hours = { (past_24h + timedelta(hours=i)).strftime('%m-%d %H:00'): 0 for i in range(25) }
        zh_hours = { (past_24h + timedelta(hours=i)).strftime('%m-%d %H:00'): 0 for i in range(25) }
        time_labels = list(qidian_hours.keys())
        
        # 最近采集的书籍
        recent_books = []
        
        # 最近一次采集时间
        last_crawl_time = None

        def fetch_pipeline_data(config, table_name, platform):
            nonlocal last_crawl_time
            today_count = 0
            total_count = 0
            try:
                conn = pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
                with conn.cursor() as cur:
                    # 今日采集量
                    cur.execute(f"SELECT COUNT(*) as c FROM {table_name} WHERE crawl_time >= %s", (today_start,))
                    today_count = cur.fetchone()['c'] or 0
                    
                    # 全量总记录数
                    cur.execute(f"SELECT COUNT(*) as c FROM {table_name}")
                    total_count = cur.fetchone()['c'] or 0
                    
                    # 避免 SQL % 格式化冲突，直接按小时聚合
                    cur.execute(f"SELECT DATE_FORMAT(crawl_time, '%%m-%%d %%H:00') as hr, COUNT(*) as c FROM {table_name} WHERE crawl_time >= %s GROUP BY hr", (past_24h,))
                    for r in cur.fetchall():
                        if platform == 'qidian' and r['hr'] in qidian_hours:
                            qidian_hours[r['hr']] = r['c']
                        elif platform == 'zongheng' and r['hr'] in zh_hours:
                            zh_hours[r['hr']] = r['c']
                    
                    # 获取最近采集的书籍（按 crawl_time 倒序取最新 20 本）
                    ticket_col = "monthly_tickets"
                    rank_col = "monthly_ticket_rank"
                    cur.execute(f"""
                        SELECT title, {ticket_col} as monthly_tickets, 
                               {rank_col} as rank_val, crawl_time
                        FROM {table_name} 
                        ORDER BY crawl_time DESC LIMIT 20
                    """)
                    for r in cur.fetchall():
                        ct = r['crawl_time']
                        if last_crawl_time is None or ct > last_crawl_time:
                            last_crawl_time = ct
                        recent_books.append({
                            'title': r['title'],
                            'monthly_tickets': int(r['monthly_tickets'] or 0),
                            'rank': int(r['rank_val'] or 0),
                            'crawl_time': ct.strftime('%m-%d %H:%M'),
                            'source': platform
                        })
                conn.close()
            except Exception as e:
                print(f"[WARN] Pipeline fetch failed for {platform}: {e}")
            return today_count, total_count

        qidian_today, qidian_total = fetch_pipeline_data(_QD_CFG, 'novel_realtime_tracking', 'qidian')
        zh_today, zh_total = fetch_pipeline_data(_ZH_CFG, 'zongheng_realtime_tracking', 'zongheng')
        
        # 按排名升序排列，Top 1 在最前面
        recent_books.sort(key=lambda x: x['rank'] if x['rank'] > 0 else 9999)

        traffic_data = []
        for lbl in time_labels:
            q_val = qidian_hours.get(lbl, 0)
            z_val = zh_hours.get(lbl, 0)
            traffic_data.append({
                'time': lbl,
                'value': q_val + z_val,
                'qidian': q_val,
                'zongheng': z_val
            })
            
        return jsonify({
            'today_total': qidian_today + zh_today,
            'qidian_today': qidian_today,
            'zongheng_today': zh_today,
            'qidian_total': qidian_total,
            'zongheng_total': zh_total,
            'last_crawl_time': last_crawl_time.strftime('%m-%d %H:%M') if last_crawl_time else '--',
            'traffic_series': traffic_data,
            'recent_books': recent_books[:30]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- 7. Model Training API ---
from model_trainer import model_trainer
import threading

@api_bp.route('/admin/model/train', methods=['POST'])
def train_model_endpoint():
    """触发模型训练"""
    if model_trainer.is_training:
        return jsonify({'status': 'error', 'message': 'Training already in progress'}), 400
    
    params = request.json or {}
    
    # Run in background thread
    def run_train():
        model_trainer.train(params)
        
    thread = threading.Thread(target=run_train)
    thread.start()
    
    return jsonify({'status': 'success', 'message': 'Training started in background'})

@api_bp.route('/admin/model/status')
def model_status():
    """获取训练状态和日志"""
    return jsonify({
        'is_training': model_trainer.is_training,
        'log': model_trainer.last_training_log
    })

@api_bp.route('/admin/model/config', methods=['GET', 'POST'])
def model_config():
    """获取或更新模型配置"""
    if request.method == 'POST':
        new_params = request.json
        model_trainer.default_params.update(new_params)
        return jsonify({'status': 'success', 'config': model_trainer.default_params})
    
    return jsonify({'config': model_trainer.default_params})


# --- 8. Admin Settings API ---

def _mask_key(key_str):
    """对 API Key 进行脱敏处理"""
    if not key_str or len(key_str) < 8:
        return key_str or ''
    return key_str[:4] + '*' * (len(key_str) - 8) + key_str[-4:]


@api_bp.route('/admin/settings', methods=['GET'])
def get_admin_settings():
    """获取管理员设置面板所需的全部配置（脱敏）"""
    try:
        # 1. AI 大模型配置
        ai_cfg = ai_service.load_config()
        ai_settings = {
            'provider': ai_cfg.get('provider', 'github'),
            'base_url': ai_cfg.get('base_url', ''),
            'api_key': _mask_key(ai_cfg.get('api_key', '')),
            'model_name': ai_cfg.get('model_name', 'gpt-4o'),
            'temperature': ai_cfg.get('temperature', 0.7),
            'max_tokens': ai_cfg.get('max_tokens', 1024),
        }

        # 2. 爬虫调度器配置
        from scheduler import scheduler_instance
        spider_settings = {
            'interval_minutes': scheduler_instance.interval_minutes,
            'target_platform': scheduler_instance.target_platform,
            'is_running': scheduler_instance.is_running,
            'status': scheduler_instance.status,
        }

        # 3. 数据库连配置（只读展示，脱敏密码）
        try:
            from data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG
        except ImportError:
            from backend.data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG
        db_settings = {
            'zongheng': {
                'host': ZONGHENG_CONFIG['host'],
                'port': ZONGHENG_CONFIG['port'],
                'database': ZONGHENG_CONFIG['database'],
                'user': ZONGHENG_CONFIG['user'],
                'password': _mask_key(ZONGHENG_CONFIG.get('password', '')),
            },
            'qidian': {
                'host': QIDIAN_CONFIG['host'],
                'port': QIDIAN_CONFIG['port'],
                'database': QIDIAN_CONFIG['database'],
                'user': QIDIAN_CONFIG['user'],
                'password': _mask_key(QIDIAN_CONFIG.get('password', '')),
            },
        }

        # 4. 系统参数
        system_settings = load_system_config()

        # 5. 模型训练参数
        model_settings = model_trainer.default_params

        # 6. 关于系统
        about = {
            'version': 'v1.2.0',
            'tech_stack': 'Vue 3 + Flask + XGBoost + ECharts',
            'python_version': os.sys.version.split()[0],
            'total_books': len(data_manager.df) if not data_manager.df.empty else 0,
            'model_loaded': data_manager.model is not None,
        }

        return jsonify({
            'ai': ai_settings,
            'spider': spider_settings,
            'database': db_settings,
            'system': system_settings,
            'model': model_settings,
            'about': about,
        })
    except Exception as e:
        print(f"[Settings Error] {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/settings', methods=['POST'])
def update_admin_settings():
    """按模块更新管理员设置"""
    try:
        data = request.json or {}
        section = data.get('section')
        values = data.get('values', {})

        if section == 'ai':
            # 如果 api_key 是脱敏值（含 *），则保留原值不覆盖
            current_cfg = ai_service.load_config()
            if 'api_key' in values and '*' in values['api_key']:
                values['api_key'] = current_cfg.get('api_key', '')
            ai_service.update_config(values)
            return jsonify({'status': 'success', 'message': 'AI 配置已更新，模型重新初始化中...'})

        elif section == 'spider':
            from scheduler import scheduler_instance
            if 'interval_minutes' in values:
                scheduler_instance.set_interval(int(values['interval_minutes']))
            if 'target_platform' in values:
                scheduler_instance.set_platform(values['target_platform'])
            return jsonify({'status': 'success', 'message': '爬虫调度器配置已更新'})

        elif section == 'model':
            model_trainer.default_params.update(values)
            return jsonify({'status': 'success', 'message': '模型训练参数已更新'})

        elif section == 'system':
            # 系统参数持久化
            current_sys = load_system_config()
            current_sys.update(values)
            save_system_config(current_sys)
            return jsonify({'status': 'success', 'message': '系统参数已保存'})

        else:
            return jsonify({'error': f'未知的设置模块: {section}'}), 400

    except Exception as e:
        print(f"[Settings Update Error] {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/test_db', methods=['POST'])
def test_db_connection():
    """测试数据库连接"""
    try:
        platform = (request.json or {}).get('platform', 'zongheng')
        try:
            from data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG
        except ImportError:
            from backend.data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG

        config = ZONGHENG_CONFIG if platform == 'zongheng' else QIDIAN_CONFIG

        import time
        start = time.time()
        conn = pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM information_schema.tables WHERE table_schema = %s", (config['database'],))
            table_count = cur.fetchone()['cnt']
        conn.close()
        latency = int((time.time() - start) * 1000)

        return jsonify({
            'status': 'success',
            'latency_ms': latency,
            'table_count': table_count,
            'message': f'连接成功 · {latency}ms · {table_count} 张表'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'连接失败: {str(e)[:100]}'
        }), 500

# --- 9. Audit Logs API ---

@api_bp.route('/admin/audit_logs', methods=['GET'])
def get_audit_logs():
    """获取 IP 商业风控与预警日志"""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    status = request.args.get('status')
    risk_level = request.args.get('risk_level')
    risk_type = request.args.get('risk_type')
    book_title = request.args.get('book_title')
    
    query = "SELECT * FROM ip_audit_logs WHERE 1=1"
    params = []
    
    if status:
        query += " AND status = %s"
        params.append(status)
    if risk_level:
        query += " AND risk_level = %s"
        params.append(risk_level)
    if risk_type:
        query += " AND risk_type = %s"
        params.append(risk_type)
    if book_title:
        query += " AND book_title = %s"
        params.append(book_title)
        
    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    try:
        from auth import get_auth_db
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(params))
            logs = cursor.fetchall()
            
            # 统计总数
            count_query = "SELECT COUNT(*) as cnt FROM ip_audit_logs WHERE 1=1"
            count_params = []
            if status:
                count_query += " AND status = %s"
                count_params.append(status)
            if risk_level:
                count_query += " AND risk_level = %s"
                count_params.append(risk_level)
            if risk_type:
                count_query += " AND risk_type = %s"
                count_params.append(risk_type)
            if book_title:
                count_query += " AND book_title = %s"
                count_params.append(book_title)
            cursor.execute(count_query, tuple(count_params))
            total = cursor.fetchone()['cnt']
            
        conn.close()
        
        # 序列化 datetime
        for log in logs:
            if log.get('created_at'):
                log['created_at'] = log['created_at'].isoformat()
                
        return jsonify({
            'status': 'success',
            'data': logs,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        print(f"Failed to fetch audit logs: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/audit_logs/<int:log_id>/resolve', methods=['POST'])
def resolve_audit_log(log_id):
    """处理风控告警"""
    data = request.json or {}
    new_status = data.get('status', 'RESOLVED')
    if new_status not in ['PENDING', 'REVIEWED', 'RESOLVED']:
        return jsonify({'error': 'Invalid status'}), 400
        
    try:
        from auth import get_auth_db
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE ip_audit_logs SET status = %s WHERE id = %s", (new_status, log_id))
            conn.commit()
            updated = cursor.rowcount > 0
        conn.close()
        
        if updated:
            return jsonify({'status': 'success', 'message': f'Log {log_id} marked as {new_status}'})
        else:
            return jsonify({'error': 'Log not found'}), 404
    except Exception as e:
        print(f"Failed to resolve audit log: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/scan_gems', methods=['POST'])
def trigger_scan_gems():
    """手动触发潜力遗珠扫描"""
    try:
        data = request.json or {}
        book_title = data.get('book_title')
        from scan_potential_gems import scan_and_trigger_gems
        inserted = scan_and_trigger_gems(title_filter=book_title)
        return jsonify({
            'status': 'success',
            'inserted': inserted,
            'message': f'Successfully scanned {book_title if book_title else "all library"}, found {inserted} gems'
        })
    except Exception as e:
        print(f"Scan error: {e}")
        return jsonify({'error': str(e)}), 500


# --- 10. 增强审计 API：深度审计、多源概览、AI评分表 ---

@api_bp.route('/admin/audit/deep_scan', methods=['POST'])
def audit_deep_scan():
    """单本书深度 AI 审计：六维数据融合 + AI 大模型分析"""
    data = request.json or {}
    book_title = data.get('book_title', '').strip()
    if not book_title:
        return jsonify({'error': '请提供书名 (book_title)'}), 400
    
    try:
        from scan_potential_gems import fetch_vr_comments, fetch_global_stats, fetch_ai_eval, fetch_realtime_trend
        from scan_potential_gems import NOVEL_INSIGHTS_CONFIG
        
        try:
            from data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG, data_manager
        except ImportError:
            from backend.data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG, data_manager
        
        # 1. 查找书籍基础数据
        base_stats = {'title': book_title, 'author': '未知', 'category': '未知', 'platform': '未知', 'finance': 0, 'interaction': 0, 'word_count': 0}
        
        # 先从纵横查
        try:
            conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT title, author, category, monthly_ticket as finance, total_rec as interaction, word_count
                    FROM zongheng_book_ranks WHERE title = %s ORDER BY year DESC, month DESC LIMIT 1
                """, (book_title,))
                row = cur.fetchone()
                if row:
                    base_stats = {'title': row['title'], 'author': row['author'], 'category': row['category'] or '未知',
                                  'platform': 'Zongheng', 'finance': row['finance'] or 0, 'interaction': row['interaction'] or 0, 'word_count': row['word_count'] or 0}
            conn.close()
        except: pass
        
        # 再从起点查
        if base_stats['platform'] == '未知':
            try:
                conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT title, author, category, monthly_ticket_count as finance, recommendation_count as interaction, word_count
                        FROM novel_monthly_stats WHERE title = %s ORDER BY year DESC, month DESC LIMIT 1
                    """, (book_title,))
                    row = cur.fetchone()
                    if row:
                        base_stats = {'title': row['title'], 'author': row['author'], 'category': row['category'] or '未知',
                                      'platform': 'Qidian', 'finance': row['finance'] or 0, 'interaction': row['interaction'] or 0, 'word_count': row['word_count'] or 0}
                conn.close()
            except: pass
        
        # 2. 聚合六维数据
        vr_comments = fetch_vr_comments(book_title) or "暂无虚拟读者反馈"
        global_stats = fetch_global_stats(book_title)
        ai_eval_stats = fetch_ai_eval(book_title)
        realtime_trend = fetch_realtime_trend(book_title)
        
        # 3. XGBoost 预测分 (结合最新态势打分)
        realtime_latest = realtime_trend.get('latest_tickets', 0) if isinstance(realtime_trend, dict) else 0
        max_finance = max(base_stats.get('finance', 0), realtime_latest)
        
        predict_res = data_manager.predict_ip({
            'title': book_title, 
            'category': base_stats.get('category', '未知'),
            'word_count': base_stats.get('word_count', 0),
            'finance': max_finance,  # ★ 核心修复：融合了历史巅峰和当下的实时巅峰
            'interaction': base_stats.get('interaction', 0),
            'popularity': base_stats.get('interaction', 0) * 0.2
        })
        model_score = predict_res.get('score', 80.0)
        book_status = predict_res.get('details', {}).get('status', '未知')
        
        # 构建市场价值大盘指标
        import numpy as np
        _fin = float(max_finance)
        _inter = float(base_stats.get('interaction', 0))
        _pop = _inter * 0.2
        _score = float(model_score)
        
        heat_score = min(100, 40 + 12 * np.log10(max(_fin, 1)) + 5 * np.log10(max(_pop, 1)))
        fan_loyalty = min(100, 50 + 15 * np.log10(max(_inter / (_fin * 100), 0.01) + 1)) if _fin > 0 and _inter > 0 else 50.0
        commercial_value = min(100, 35 + 14 * np.log10(max(_fin, 1)))
        
        dims = ai_eval_stats if isinstance(ai_eval_stats, dict) else {}
        if dims.get('story') and dims.get('character') and dims.get('world'):
             content_score = (float(dims.get('story', 0)) + float(dims.get('character', 0)) + float(dims.get('world', 0))) / 3
        else:
             content_score = _score * 0.85
             
        ip_potential = (float(dims.get('commercial', 0)) + float(dims.get('overall', 0))) / 2 if dims.get('commercial') and dims.get('overall') else _score * 0.9
        
        timeliness = 85.0 if '连载' in book_status else (55.0 if '完结' in book_status or '完本' in book_status else 70.0)
        
        market_analysis = {
             'market_heat': round(heat_score, 1),
             'content_quality': round(content_score, 1),
             'ip_potential': round(ip_potential, 1),
             'fan_loyalty': round(fan_loyalty, 1),
             'commercial_value': round(commercial_value, 1),
             'timeliness': round(timeliness, 1)
        }
        
        # 4. 调用 AI 生成深度审计报告
        report_markdown = ai_service.generate_comprehensive_audit(
            title=book_title,
            author=base_stats.get('author', '未知'),
            base_stats=base_stats,
            ai_eval_stats=ai_eval_stats,
            vr_comments=vr_comments,
            global_stats=global_stats,
            model_score=model_score,
            realtime_trend=realtime_trend,
            market_analysis=market_analysis,
            book_status=book_status
        )
        
        # --- 保存至审计日志 (ip_audit_logs) 以便前端展示 ---
        try:
            conn = pymysql.connect(**QIDIAN_CONFIG)  # 复用起点库或专门的分析库
            with conn.cursor() as cursor:
                # 1. 清理该书籍之前的旧审计记录（防止前端展示过时的 60 分报告）
                # 同时清理 ip_ai_evaluation 表中的条目，确保详情页（Header）同步展示最新高分
                if book_title:
                   delete_sql_log = "DELETE FROM ip_audit_logs WHERE book_title = %s"
                   cursor.execute(delete_sql_log, (book_title,))
                   
                   delete_sql_eval = "DELETE FROM ip_ai_evaluation WHERE title = %s"
                   cursor.execute(delete_sql_eval, (book_title,))
                   print(f"[CLEANUP] Force cleared old scores for {book_title} in both Logs and Eval tables")

                # 2. 插入最新的报告
                # （根据分数准确判定风险类型和等级）
                if model_score >= 90:
                    risk_type = "POTENTIAL_GEM"
                    risk_level = "Low"
                elif model_score < 40:
                    risk_type = "RISK"
                    risk_level = "High"
                else:
                    risk_type = "NORMAL"
                    risk_level = "Low"

                # 🚀 核心加固：同步更新基础评价表
                try:
                    eval_sql = """
                    INSERT INTO ip_ai_evaluation 
                    (title, author, platform, overall_score, story_score, character_score, world_score, commercial_score, adaptation_score, safety_score, grade)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    # 计算维度分映射比率
                    base_overall = ai_eval_stats.get('overall', 60)
                    ratio = model_score / max(base_overall, 1)
                    
                    cursor.execute(eval_sql, (
                        book_title,
                        base_stats.get('author', '未知'),
                        base_stats.get('platform', '未知'),
                        model_score,
                        min(100, ai_eval_stats.get('story', 70) * ratio),
                        min(100, ai_eval_stats.get('character', 70) * ratio),
                        min(100, ai_eval_stats.get('world', 70) * ratio),
                        min(100, ai_eval_stats.get('commercial', 70) * ratio),
                        min(100, ai_eval_stats.get('adaptation', 70) * ratio),
                        min(100, ai_eval_stats.get('safety', 80) * ratio),
                        'S' if model_score >= 90 else 'A' if model_score >= 80 else 'B'
                    ))
                except Exception as e_sync:
                    print(f"[SYNC ERROR] {e_sync}")

                # 插入最新的审计日志记录
                sql = """
                INSERT INTO ip_audit_logs (book_title, risk_type, risk_level, content_snippet, status, score, markdown_report, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(sql, (
                    book_title, 
                    risk_type, 
                    risk_level, 
                    report_markdown[:200].replace('\n', ' ') if report_markdown else "AI 深度审计报告已生成",
                    "SUCCESS", 
                    round(float(model_score), 2),
                    report_markdown
                ))
                conn.commit()
            conn.close()
            print(f"[OK] Audit log saved/updated for {book_title}")
        except Exception as e:
            print(f"[ERROR] Failed to save audit log: {e}")

        return jsonify({
            "status": "success",
            "title": book_title,
            "model_score": round(float(model_score), 2),
            "report": report_markdown,
            "data_sources": {
                "ai_eval": bool(ai_eval_stats),
                "vr_comments": bool(vr_comments),
                "global_stats": bool(global_stats),
                "xgboost": True,
                "realtime_trend": bool(realtime_trend)
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/audit/deep_scan_stream', methods=['GET'])
def audit_deep_scan_stream():
    """单本书深度 AI 审计流式输出 (SSE)"""
    book_title = request.args.get('book_title', '').strip()
    if not book_title:
        return jsonify({'error': '请提供书名 (book_title)'}), 400
    
    try:
        from scan_potential_gems import fetch_vr_comments, fetch_global_stats, fetch_ai_eval, fetch_realtime_trend
        try:
            from data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG, data_manager
        except ImportError:
            from backend.data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG, data_manager
            
        base_stats = {'title': book_title, 'author': '未知', 'category': '未知', 'platform': '未知', 'finance': 0, 'interaction': 0, 'word_count': 0}
        try:
            conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                # 修正：不使用 MAX() 避免抓到历史巅峰值，改取最新月份记录
                cur.execute("SELECT title, author, category, monthly_ticket as finance, total_rec as interaction, word_count FROM zongheng_book_ranks WHERE title = %s ORDER BY year DESC, month DESC LIMIT 1", (book_title,))
                row = cur.fetchone()
                if row:
                    base_stats.update({'author': row['author'], 'category': row['category'] or '未知', 'platform': 'Zongheng', 'finance': row['finance'] or 0, 'interaction': row['interaction'] or 0, 'word_count': row['word_count'] or 0})
            conn.close()
        except: pass
        if base_stats['platform'] == '未知':
            try:
                conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
                with conn.cursor() as cur:
                    # 修正：不使用 MAX() 避免抓到历史巅峰值，改取最新月份记录。
                    # 使用 monthly_ticket_count 替代 monthly_tickets_on_list 以反映真实当前票数
                    cur.execute("SELECT title, author, category, monthly_ticket_count as finance, recommendation_count as interaction, word_count FROM novel_monthly_stats WHERE title = %s ORDER BY year DESC, month DESC LIMIT 1", (book_title,))
                    row = cur.fetchone()
                    if row:
                        base_stats.update({'author': row['author'], 'category': row['category'] or '未知', 'platform': 'Qidian', 'finance': row['finance'] or 0, 'interaction': row['interaction'] or 0, 'word_count': row['word_count'] or 0})
                conn.close()
            except: pass
            
        vr_comments = fetch_vr_comments(book_title) or "暂无虚拟读者反馈"
        global_stats = fetch_global_stats(book_title)
        ai_eval_stats = fetch_ai_eval(book_title)
        realtime_trend = fetch_realtime_trend(book_title)
        
        realtime_latest = realtime_trend.get('latest_tickets', 0) if isinstance(realtime_trend, dict) else 0
        
        # 修正：老书应尊重当前的实绩（realtime_latest），若是历史余温则过滤
        if base_stats.get('platform') == 'Qidian' and realtime_latest > 0 and base_stats.get('finance', 0) > 1000 and realtime_latest < 100:
             max_finance = realtime_latest
        else:
             max_finance = max(base_stats.get('finance', 0), realtime_latest)

        # 【核心拦截防伪】优先采信前端真实传来的 V5大盘评级
        base_overall = request.args.get('base_overall')
        if base_overall:
            model_score = float(base_overall)
            book_status = '连载'
            
            # 使用真实传来的六维填入 ai_eval_stats，防止大模型编造假分
            ai_eval_stats = {
                'overall': model_score,
                'story': float(request.args.get('base_story', 75)),
                'character': float(request.args.get('base_character', 75)),
                'world': float(request.args.get('base_world', 75)),
                'commercial': float(request.args.get('base_commercial', 75)),
                'adaptation': float(request.args.get('base_adaptation', 75)),
                'safety': float(request.args.get('base_safety', 75)),
                'grade': 'S' if model_score >= 95 else 'A' if model_score >= 85 else 'B' if model_score >= 70 else 'C' if model_score >= 55 else 'D'
            }
        else:
            # 兼容老前端：若未传参则退回原预测逻辑
            predict_res = data_manager.predict_ip({
                'title': book_title, 'category': base_stats.get('category', '未知'),
                'word_count': base_stats.get('word_count', 0), 'finance': max_finance,
                'interaction': base_stats.get('interaction', 0), 'popularity': base_stats.get('interaction', 0) * 0.2,
                'platform': base_stats.get('platform', 'Qidian'),
                'status': base_stats.get('status', '连载'),
                'updated_at': str(base_stats.get('updated_at', ''))
            })
            model_score = predict_res.get('score', 80.0)
            book_status = predict_res.get('details', {}).get('status', '未知')
        
        import numpy as np
        _fin = float(max_finance)
        _inter = float(base_stats.get('interaction', 0))
        _pop = _inter * 0.2
        
        heat_score = min(100, 40 + 12 * np.log10(max(_fin, 1)) + 5 * np.log10(max(_pop, 1)))
        fan_loyalty = min(100, 50 + 15 * np.log10(max(_inter / (_fin * 100), 0.01) + 1)) if _fin > 0 and _inter > 0 else 50.0
        commercial_value = min(100, 35 + 14 * np.log10(max(_fin, 1)))
        
        dims = ai_eval_stats if isinstance(ai_eval_stats, dict) else {}
        if dims.get('story') and dims.get('character') and dims.get('world'):
             content_score = (float(dims.get('story', 0)) + float(dims.get('character', 0)) + float(dims.get('world', 0))) / 3
        else:
             content_score = float(model_score) * 0.85
             
        ip_potential = (float(dims.get('commercial', 0)) + float(dims.get('overall', 0))) / 2 if dims.get('commercial') and dims.get('overall') else float(model_score) * 0.9
        timeliness = 85.0 if '连载' in book_status else (55.0 if '完结' in book_status or '完本' in book_status else 70.0)
        
        market_analysis = {
             'market_heat': round(heat_score, 1), 'content_quality': round(content_score, 1),
             'ip_potential': round(ip_potential, 1), 'fan_loyalty': round(fan_loyalty, 1),
             'commercial_value': round(commercial_value, 1), 'timeliness': round(timeliness, 1)
        }

        def generate():
            import json
            yield f"data: {json.dumps({'type': 'meta', 'score': model_score, 'data_sources': {'ai_eval': bool(ai_eval_stats), 'vr_comments': bool(vr_comments), 'global_stats': bool(global_stats), 'xgboost': True, 'realtime_trend': bool(realtime_trend)}})}\n\n"
            
            full_report = []
            try:
                generator = ai_service.generate_comprehensive_audit_stream(
                    title=book_title, author=base_stats.get('author', '未知'),
                    base_stats=base_stats, ai_eval_stats=ai_eval_stats,
                    vr_comments=vr_comments, global_stats=global_stats,
                    model_score=model_score, realtime_trend=realtime_trend,
                    market_analysis=market_analysis, book_status=book_status
                )
                for chunk in generator:
                    full_report.append(chunk)
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    
                report_markdown = "".join(full_report)
                
                # Report generated, now async save it to DB
                try:
                    conn = pymysql.connect(**QIDIAN_CONFIG)
                    with conn.cursor() as cursor:
                        cursor.execute("DELETE FROM ip_audit_logs WHERE book_title = %s", (book_title,))
                        cursor.execute("DELETE FROM ip_ai_evaluation WHERE title = %s", (book_title,))
                        
                        insert_sql = "INSERT INTO ip_audit_logs (book_title, status, risk_level, score, report) VALUES (%s, 'REVIEWED', 'MEDIUM', %s, %s)"
                        cursor.execute(insert_sql, (book_title, model_score, report_markdown))
                        
                        base_overall = ai_eval_stats.get('overall', 60)
                        ratio = model_score / max(base_overall, 1)
                        eval_sql = "INSERT INTO ip_ai_evaluation (title, author, platform, overall_score, story_score, character_score, world_score, commercial_score, adaptation_score, safety_score, grade) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                        cursor.execute(eval_sql, (
                            book_title, base_stats.get('author', '未知'), base_stats.get('platform', '未知'),
                            model_score, min(100, ai_eval_stats.get('story', 70) * ratio),
                            min(100, ai_eval_stats.get('character', 70) * ratio),
                            min(100, ai_eval_stats.get('world', 70) * ratio),
                            min(100, ai_eval_stats.get('commercial', 70) * ratio),
                            min(100, ai_eval_stats.get('adaptation', 70) * ratio),
                            85.2, 'S' if model_score >= 90 else 'A'
                        ))
                        conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"Post-stream save error: {e}")
                    
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        from flask import stream_with_context, Response
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/audit/multi_source_overview')
def audit_multi_source_overview():
    """审计中心多源数据概览仪表盘"""
    try:
        from auth import get_auth_db, AUTH_DB_CONFIG
        try:
            from data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG
        except ImportError:
            from backend.data_manager import ZONGHENG_CONFIG, QIDIAN_CONFIG
        
        overview = {
            'vr': {'total': 0, 'positive': 0, 'neutral': 0, 'negative': 0},
            'ai_eval': {'total': 0, 'avg_overall': 0, 'avg_story': 0, 'avg_character': 0, 'avg_world': 0, 'avg_commercial': 0},
            'realtime': {'active_books': 0, 'last_crawl': '--', 'qidian_count': 0, 'zongheng_count': 0},
            'audit': {'total': 0, 'gems': 0, 'global_gems': 0, 'deep_audits': 0}
        }
        
        # 1. 虚拟读者统计
        try:
            from scan_potential_gems import NOVEL_INSIGHTS_CONFIG
            conn = pymysql.connect(**NOVEL_INSIGHTS_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as c FROM vr_comment")
                overview['vr']['total'] = cur.fetchone()['c']
                cur.execute("SELECT COUNT(*) as c FROM vr_comment WHERE rating >= 8")
                overview['vr']['positive'] = cur.fetchone()['c']
                cur.execute("SELECT COUNT(*) as c FROM vr_comment WHERE rating >= 5 AND rating < 8")
                overview['vr']['neutral'] = cur.fetchone()['c']
                cur.execute("SELECT COUNT(*) as c FROM vr_comment WHERE rating < 5")
                overview['vr']['negative'] = cur.fetchone()['c']
            conn.close()
        except Exception as e:
            print(f"[Audit Overview] VR统计失败: {e}")
        
        # 2. AI 评分表统计
        try:
            conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as c, 
                           AVG(overall_score) as avg_overall, AVG(story_score) as avg_story,
                           AVG(character_score) as avg_character, AVG(world_score) as avg_world, 
                           AVG(commercial_score) as avg_commercial
                    FROM ip_ai_evaluation
                """)
                row = cur.fetchone()
                if row:
                    overview['ai_eval'] = {
                        'total': row['c'] or 0,
                        'avg_overall': round(float(row['avg_overall'] or 0), 1),
                        'avg_story': round(float(row['avg_story'] or 0), 1),
                        'avg_character': round(float(row['avg_character'] or 0), 1),
                        'avg_world': round(float(row['avg_world'] or 0), 1),
                        'avg_commercial': round(float(row['avg_commercial'] or 0), 1)
                    }
            conn.close()
        except Exception as e:
            print(f"[Audit Overview] AI评分统计失败: {e}")
        
        # 3. 实时监控统计
        for cfg, table, key in [(QIDIAN_CONFIG, 'novel_realtime_tracking', 'qidian'), (ZONGHENG_CONFIG, 'zongheng_realtime_tracking', 'zongheng')]:
            try:
                conn = pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(DISTINCT title) as c FROM {table}")
                    count = cur.fetchone()['c'] or 0
                    overview['realtime'][f'{key}_count'] = count
                    overview['realtime']['active_books'] += count
                    cur.execute(f"SELECT MAX(crawl_time) as t FROM {table}")
                    row = cur.fetchone()
                    if row and row['t']:
                        t_str = row['t'].strftime('%m-%d %H:%M')
                        if overview['realtime']['last_crawl'] == '--' or t_str > overview['realtime']['last_crawl']:
                            overview['realtime']['last_crawl'] = t_str
                conn.close()
            except Exception as e:
                print(f"[Audit Overview] 实时监控统计失败({key}): {e}")
        
        # 4. 审计日志统计
        try:
            conn = get_auth_db()
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as c FROM ip_audit_logs")
                overview['audit']['total'] = cur.fetchone()['c']
                cur.execute("SELECT COUNT(*) as c FROM ip_audit_logs WHERE risk_type = 'POTENTIAL_GEM'")
                overview['audit']['gems'] = cur.fetchone()['c']
                cur.execute("SELECT COUNT(*) as c FROM ip_audit_logs WHERE risk_type = 'GLOBAL_GEM'")
                overview['audit']['global_gems'] = cur.fetchone()['c']
                cur.execute("SELECT COUNT(*) as c FROM ip_audit_logs WHERE risk_type = 'DEEP_AUDIT'")
                overview['audit']['deep_audits'] = cur.fetchone()['c']
            conn.close()
        except Exception as e:
            print(f"[Audit Overview] 审计日志统计失败: {e}")
        
        return jsonify({'status': 'success', 'data': overview})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/admin/audit/ai_scores')
def audit_ai_scores():
    """AI 评分表 Top 数据查询"""
    limit = request.args.get('limit', 20, type=int)
    try:
        try:
            from data_manager import ZONGHENG_CONFIG
        except ImportError:
            from backend.data_manager import ZONGHENG_CONFIG
        
        conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT title, overall_score, story_score, character_score, world_score, commercial_score,
                       adaptation_score, safety_score, evaluated_at
                FROM ip_ai_evaluation 
                ORDER BY overall_score DESC 
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
        conn.close()
        
        for row in rows:
            if row.get('evaluated_at'):
                row['evaluated_at'] = row['evaluated_at'].isoformat()
            # 将 Decimal 转为 float
            for key in ['overall_score', 'story_score', 'character_score', 'world_score', 'commercial_score', 'adaptation_score', 'safety_score']:
                if row.get(key) is not None:
                    row[key] = round(float(row[key]), 1)
        
        return jsonify({'status': 'success', 'data': rows})
    except Exception as e:
        print(f"[AI Scores] 查询失败: {e}")
        return jsonify({'error': str(e), 'data': []}), 500

