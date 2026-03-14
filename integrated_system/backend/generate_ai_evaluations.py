"""
IP Lumina AI 评估引擎 V5.0 — 全面重构版
核心策略：
1. 月票锚定 + 实时数据优先（不使用排名映射）
2. 等级制划分 (S/A/B/C/D)
3. 多维度加权：月票40% + 粉丝粘性15% + NLP15% + 趋势环比15% + 世界观改编15%
4. 12月数据特殊处理（月中爬取不完整）
5. 章节 NLP 分析接入
"""
import sys
import os
import numpy as np
import pandas as pd
import pymysql
import json
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ================================================================
#  数据库配置
# ================================================================
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306,
    'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306,
    'user': 'root', 'password': 'root',
    'database': 'qidian_data', 'charset': 'utf8mb4'
}
EVAL_DB_CONFIG = ZONGHENG_CONFIG


# ================================================================
#  月票锚定映射（核心评分基准）
# ================================================================
def ticket_to_score(tickets, platform='Qidian'):
    """
    月票 → 基础分映射（分段线性）
    起点和纵横使用不同的锚点，因为两平台的月票量级不同
    """
    if platform == 'Zongheng':
        # 纵横月票量级较小，提高中段基础分，确保前20名(500+票)能稳到A级(85+)
        anchors = [
            (0, 40.0), (100, 50.0), (200, 65.0), (500, 85.0),
            (1000, 89.0), (2000, 93.0), (3000, 96.0), (5000, 98.0),
            (10000, 99.0), (15000, 99.5),
        ]
    else:
        # 起点前20(约1.3万票)，大幅拉高中段确保拿到A级(85+)
        anchors = [
            (0, 30.0), (500, 40.0), (1000, 50.0), (2000, 60.0),
            (5000, 75.0), (8000, 80.0), (10000, 85.0), (15000, 88.0),
            (20000, 90.0), (30000, 93.0), (50000, 96.0), (80000, 98.0),
            (100000, 99.0), (150000, 99.5),
        ]
    
    if tickets <= 0:
        return anchors[0][1]
    if tickets >= anchors[-1][0]:
        return anchors[-1][1]
    
    for i in range(len(anchors) - 1):
        t0, s0 = anchors[i]
        t1, s1 = anchors[i + 1]
        if t0 <= tickets < t1:
            return s0 + (tickets - t0) / (t1 - t0) * (s1 - s0)
    return anchors[-1][1]


# ================================================================
#  数据加载
# ================================================================
def load_all_books():
    """加载全平台书籍数据，聚合月度记录"""
    dfs = []
    
    for cfg, sql, plat in [
        (ZONGHENG_CONFIG,
         """SELECT title, author, category, status, word_count,
                   total_click as popularity, total_rec as interaction,
                   monthly_ticket as finance, fan_count as fans_count,
                   week_rec as week_recommend, year, month, abstract,
                   updated_at
            FROM zongheng_book_ranks""", "Zongheng"),
        (QIDIAN_CONFIG,
         """SELECT title, author, category, status, word_count,
                   collection_count as popularity,
                   recommendation_count as interaction,
                   monthly_tickets_on_list as finance,
                   reward_count as fans_count,
                   week_recommendation_count as week_recommend,
                   synopsis as abstract, updated_at, year, month
            FROM novel_monthly_stats""", "Qidian")
    ]:
        try:
            conn = pymysql.connect(**cfg)
            df = pd.read_sql(sql, conn)
            df['platform'] = plat
            if plat == 'Zongheng':
                df['status'] = df['status'].apply(lambda x: '连载' if '连载' in str(x) else '完结')
            dfs.append(df)
            conn.close()
            print(f"[OK] {plat} 加载: {len(df)} 行")
        except Exception as e:
            print(f"[ERR] {plat} 加载失败: {e}")
    
    if not dfs:
        return pd.DataFrame()
    
    df_all = pd.concat(dfs, ignore_index=True)
    
    # 数值类型转换
    for c in ['word_count', 'popularity', 'interaction', 'finance', 'fans_count', 'week_recommend']:
        df_all[c] = pd.to_numeric(df_all.get(c, 0), errors='coerce').fillna(0).astype(float)
    
    df_all['year'] = pd.to_numeric(df_all.get('year', 2024), errors='coerce').fillna(2024).astype(int)
    df_all['month'] = pd.to_numeric(df_all.get('month', 1), errors='coerce').fillna(1).astype(int)
    df_all['ym_order'] = df_all['year'] * 12 + df_all['month']
    
    return df_all


def load_realtime_tickets():
    """加载实时月票数据（最准确的当月数据）"""
    rt_data = {}
    
    for cfg, table, plat in [
        (ZONGHENG_CONFIG, 'zongheng_realtime_tracking', 'Zongheng'),
        (QIDIAN_CONFIG, 'novel_realtime_tracking', 'Qidian')
    ]:
        try:
            conn = pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as cur:
                # 获取每本书的最新月票
                cur.execute(f"""
                    SELECT title, monthly_tickets, crawl_time
                    FROM {table}
                    WHERE (title, crawl_time) IN (
                        SELECT title, MAX(crawl_time) FROM {table} GROUP BY title
                    )
                """)
                for r in cur.fetchall():
                    rt_data[(r['title'], plat)] = {
                        'tickets': int(r['monthly_tickets'] or 0),
                        'crawl_time': r['crawl_time']
                    }
            conn.close()
            print(f"[OK] {plat} 实时月票: {len([k for k in rt_data if k[1] == plat])} 本")
        except Exception as e:
            print(f"[ERR] {plat} 实时月票加载失败: {e}")
    
    return rt_data


def load_nlp_scores():
    """运行章节 NLP 评分"""
    try:
        from chapter_nlp_scorer import batch_score_all_books
        return batch_score_all_books()
    except Exception as e:
        print(f"[WARN] NLP 评分加载失败: {e}")
        return {}


# ================================================================
#  聚合与评分计算
# ================================================================
def aggregate_books(df_all, rt_data):
    """
    聚合多月数据为每本书一条记录
    关键：使用实时数据覆盖静态数据，处理 12 月月中爬取问题
    """
    now = datetime.now()
    current_ym = now.year * 12 + now.month
    
    # 按书名和平台排序并聚合
    df_all = df_all.sort_values(['title', 'platform', 'ym_order'])
    
    # 趋势计算（月票环比）
    def calc_trend(group):
        group = group.sort_values('ym_order')
        finances = group['finance'].values
        months = group['ym_order'].values
        n = len(group)
        
        # 月票环比增长率
        mom_growth = 0.0  # Month-over-Month growth
        if n >= 2:
            # 取最近两个有效月的数据 
            recent = finances[-2:]
            if recent[0] > 0:
                mom_growth = (recent[1] - recent[0]) / recent[0]
        
        # 稳定性（最近3个月标准差/均值）
        stability = 0.5  # 默认中等
        if n >= 3:
            last3 = finances[-3:]
            mean_val = np.mean(last3)
            if mean_val > 0:
                cv = np.std(last3) / mean_val  # 变异系数
                stability = max(0, 1.0 - cv)  # 越稳定越接近1
        
        # 趋势斜率
        trend_slope = 0.0
        if n >= 2:
            x = np.arange(n)
            y = finances / (finances.max() + 1e-6)
            if len(x) > 1:
                trend_slope = float(np.polyfit(x, y, 1)[0])
        
        # 数据新鲜度
        latest_ym = months.max()
        gap_months = current_ym - latest_ym
        
        return pd.Series({
            'mom_growth': round(mom_growth, 4),
            'stability': round(stability, 4),
            'trend_slope': round(trend_slope, 4),
            'gap_months': gap_months,
            'data_months': n
        })
    
    trends = df_all.groupby(['title', 'platform']).apply(calc_trend).reset_index()
    
    # 聚合数据（取最新月记录的值）
    df_books = df_all.groupby(['title', 'platform'], as_index=False).agg({
        'author': 'first', 'category': 'first', 'status': 'last',
        'word_count': 'max', 'popularity': 'max', 'interaction': 'max',
        'finance': 'last', 'fans_count': 'max', 'week_recommend': 'max',
        'abstract': 'last', 'year': 'max', 'month': 'max'
    })
    
    df_books = df_books.merge(trends, on=['title', 'platform'], how='left')
    
    # ★ 用实时数据覆盖静态数据（实时数据最准确）
    for idx, row in df_books.iterrows():
        key = (row['title'], row['platform'])
        if key in rt_data:
            rt = rt_data[key]
            rt_tickets = rt['tickets']
            
            # 12月数据特殊处理：如果是12月数据且月票偏低，可能是月中爬取
            crawl_time = rt.get('crawl_time')
            if crawl_time and hasattr(crawl_time, 'year'):
                if crawl_time.year == 2025 and crawl_time.month == 12:
                    day = crawl_time.day
                    if day < 25:
                        estimated_full = int(rt_tickets * 30 / max(day, 1))
                        rt_tickets = int(rt_tickets * 0.4 + estimated_full * 0.6)
            
            # 【关键】：让最新爬取的实时数据绝对主导当期商业价值，直接覆盖旧成绩
            df_books.at[idx, 'finance'] = rt_tickets
            # 打上标记
            df_books.at[idx, 'is_realtime'] = True
        else:
            # 如果不在实时数据里（说明当期不在活跃期或掉出榜单）
            # 对其历史静态 finance 进行强衰减，防止用历史巅峰压制当期霸榜作品
            gap = row.get('gap_months', 0)
            status = str(row.get('status', ''))
            
            decay = 1.0
            if '完' in status:
                # 完结老书彻底退出月票争夺，商业极度衰减，只保留底色
                decay = 0.05
            else:
                # 连载中的非榜单书按断更月数衰减，惩罚更重
                if gap >= 12: decay = 0.1
                elif gap >= 6: decay = 0.2
                elif gap >= 3: decay = 0.3
                elif gap >= 1: decay = 0.5
                
            df_books.at[idx, 'finance'] = float(row.get('finance', 0)) * decay
            df_books.at[idx, 'is_realtime'] = False
            
    print(f"[DATA] 聚合完成: {len(df_books)} 本书")
    return df_books


def compute_scores(df_books, nlp_scores):
    """
    V5.0 多维度评分
    月票商业分 40% + 粉丝粘性 15% + NLP 15% + 趋势环比 15% + 世界观改编 15%
    """
    n = len(df_books)
    if n == 0:
        return df_books
    
    print(f"\n[SCORING] 开始对 {n} 本书进行多维评分...")
    
    # ================================================================
    # 维度 1: 商业分（月票直接锚定）— 权重 40%
    # ================================================================
    def calc_commercial(row):
        return ticket_to_score(row['finance'], row['platform'])
    
    df_books['commercial_score'] = df_books.apply(calc_commercial, axis=1).round(1)
    
    # ================================================================
    # 维度 2: 粉丝粘性 — 权重 15%
    # ================================================================
    def calc_stickiness(row):
        fans = row['fans_count']
        popularity = row['popularity']
        interaction = row['interaction']
        finance = row['finance']
        
        # 互动转化率（粉丝/点击量）
        interact_rate = interaction / (popularity + 1)
        
        # 付费意愿（月票/粉丝量）
        pay_rate = finance / (fans + 1) if fans > 0 else 0
        
        # 综合粘性分（0-100），大幅提升基准分
        rate_score = min(40, interact_rate * 300)
        fan_score = min(30, np.log1p(fans) / 10 * 30 + 5)
        pay_score = min(30, pay_rate * 150)
        
        return max(50, min(98, 40 + rate_score + fan_score + pay_score))
    
    df_books['stickiness_score'] = df_books.apply(calc_stickiness, axis=1).round(1)
    
    # ================================================================
    # 维度 3: NLP 评分 — 权重 15%
    # ================================================================
    def get_nlp(row):
        key = (row['title'], row['platform'])
        if key in nlp_scores:
            # 放宽 NLP 评分要求，整体往上提分
            return min(98.0, nlp_scores[key]['score'] * 1.1 + 10)
        return 65.0  # 无数据给较高基准分
    
    df_books['nlp_score'] = df_books.apply(get_nlp, axis=1).round(1)
    
    # ================================================================
    # 维度 4: 趋势环比 — 权重 15%
    # ================================================================
    def calc_trend_score(row):
        mom = row.get('mom_growth', 0)
        stability = row.get('stability', 0.5)
        slope = row.get('trend_slope', 0)
        gap = row.get('gap_months', 99)
        
        # 基础趋势分改为 75
        base = 75.0
        
        # 环比增长加成
        if mom > 0:
            base += min(15, mom * 30)
        else:
            base += max(-5, mom * 10)
        
        # 稳定性
        base += (stability - 0.5) * 10
        
        # 趋势斜率加持
        base += slope * 5
        
        # 数据时效性惩罚极大幅度减弱，不作为扣分主因
        if gap >= 6:
            base *= 0.85
        elif gap >= 3:
            base *= 0.90
        elif gap >= 2:
            base *= 0.95
        
        return max(60, min(98, base))
    
    df_books['trend_score'] = df_books.apply(calc_trend_score, axis=1).round(1)
    
    # ================================================================
    # 维度 5: 世界观与改编潜力 — 权重 15%
    # ================================================================
    def calc_world_adapt(row):
        wc = row['word_count']
        cat = str(row.get('category', ''))
        status = str(row.get('status', ''))
        abstract = str(row.get('abstract', ''))
        
        # 字数体量分（长篇IP价值高），提升基础分
        if wc >= 3000000:
            wc_score = 40
        elif wc >= 1000000:
            wc_score = 35
        elif wc >= 500000:
            wc_score = 30
        elif wc >= 200000:
            wc_score = 25
        else:
            wc_score = 20
        
        # 题材改编分（影视化/游戏化适配度）
        adapt_map = {
            '玄幻': 25, '奇幻': 25, '仙侠': 22, '武侠': 20,
            '都市': 18, '科幻': 26, '历史': 20, '游戏': 18,
            '悬疑': 24, '军事': 18, '言情': 15
        }
        adapt_score = 15  # 默认分
        for key, val in adapt_map.items():
            if key in cat:
                adapt_score = val
                break
        
        # 完结加成（完整IP更有改编价值）
        completion_bonus = 10 if '完' in status else 0
        
        # 简介丰富度
        abstract_score = min(20, len(abstract) / 20)
        
        total = 20 + wc_score + adapt_score + completion_bonus + abstract_score
        return max(50, min(98, total))
    
    df_books['world_score'] = df_books.apply(calc_world_adapt, axis=1).round(1)
    
    # ================================================================
    # 综合评分（加权合成）：商业分比重提升至 75%，确立绝对统治力（呼应实时榜单）
    # 辅助分仅作为微调排序锚点
    # ================================================================
    
    # 针对非实时榜单（沉寂）作品进行封顶惩罚，商业分最高只能拿75（清退A级竞争）
    is_realtime = df_books.get('is_realtime', pd.Series([False]*len(df_books))).fillna(False).astype(bool)
    df_books.loc[~is_realtime, 'commercial_score'] = df_books.loc[~is_realtime, 'commercial_score'].clip(upper=75.0)

    df_books['overall_score'] = (
        df_books['commercial_score'] * 0.75 +
        df_books['stickiness_score'] * 0.05 +
        df_books['nlp_score'] * 0.10 +
        df_books['world_score'] * 0.05 +
        df_books['trend_score'] * 0.05
    ).round(1)
    
    # 时间衰减：仅对极度古老断更作品进行微调
    gap = df_books['gap_months'].fillna(99)
    time_decay = np.where(gap >= 12, 0.95, np.where(gap >= 6, 0.98, 1.0))
    df_books['overall_score'] = (df_books['overall_score'] * time_decay).round(1)
    
    # 完结作品轻微降分（活跃度低）
    finished_mask = df_books['status'].astype(str).str.contains('完')
    df_books.loc[finished_mask, 'overall_score'] = (df_books.loc[finished_mask, 'overall_score'] * 0.95).round(1)
    
    # 截断范围
    df_books['overall_score'] = df_books['overall_score'].clip(15, 99.5)
    
    # ================================================================
    # 等级划分
    # ================================================================
    def assign_grade(score):
        if score >= 90: return 'S'
        elif score >= 80: return 'A'
        elif score >= 70: return 'B'
        elif score >= 60: return 'C'
        else: return 'D'
    
    df_books['grade'] = df_books['overall_score'].apply(assign_grade)
    
    # 六维雷达图中的其余维度（为前端兼容）
    df_books['story_score'] = df_books['nlp_score']  # 故事 = NLP
    df_books['character_score'] = df_books['stickiness_score']  # 角色 = 粘性
    df_books['adaptation_score'] = df_books['world_score']  # 改编 = 世界观改编
    df_books['safety_score'] = (  # 安全性 = 稳定性 + 完结度
        df_books['trend_score'] * 0.5 + 
        (finished_mask.astype(float) * 20 + 40)  * 0.5
    ).clip(15, 98).round(1)
    
    # 衍生属性
    df_books['commercial_value'] = df_books['commercial_score'].apply(
        lambda s: '极高' if s >= 85 else '高' if s >= 70 else '中等' if s >= 50 else '一般'
    )
    df_books['adaptation_difficulty'] = df_books['adaptation_score'].apply(
        lambda s: '低' if s >= 70 else '中等' if s >= 50 else '高'
    )
    df_books['risk_factor'] = df_books['safety_score'].apply(
        lambda s: '低' if s >= 70 else '中' if s >= 50 else '高'
    )
    df_books['healing_index'] = (df_books['story_score'] * 0.5 + df_books['safety_score'] * 0.5).astype(int)
    df_books['global_potential'] = (df_books['world_score'] * 0.5 + df_books['commercial_score'] * 0.5).astype(int)
    
    return df_books


# ================================================================
#  数据库写入
# ================================================================
def save_to_db(df_res):
    """保存评分结果到数据库"""
    conn = pymysql.connect(**EVAL_DB_CONFIG)
    try:
        with conn.cursor() as cur:
            sql = """INSERT INTO ip_ai_evaluation 
                     (title, author, platform, story_score, character_score, world_score, 
                      commercial_score, adaptation_score, safety_score, overall_score, grade, 
                      commercial_value, adaptation_difficulty, risk_factor, healing_index, 
                      global_potential, eval_method) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                     ON DUPLICATE KEY UPDATE 
                      story_score=VALUES(story_score), character_score=VALUES(character_score), 
                      world_score=VALUES(world_score), commercial_score=VALUES(commercial_score), 
                      adaptation_score=VALUES(adaptation_score), safety_score=VALUES(safety_score), 
                      overall_score=VALUES(overall_score), grade=VALUES(grade), 
                      commercial_value=VALUES(commercial_value), 
                      adaptation_difficulty=VALUES(adaptation_difficulty), 
                      risk_factor=VALUES(risk_factor), healing_index=VALUES(healing_index), 
                      global_potential=VALUES(global_potential), eval_method=VALUES(eval_method), 
                      evaluated_at=NOW()"""
            
            for _, r in df_res.iterrows():
                cur.execute(sql, (
                    r['title'], r.get('author', ''), r['platform'],
                    r['story_score'], r['character_score'], r['world_score'],
                    r['commercial_score'], r['adaptation_score'], r['safety_score'],
                    r['overall_score'], r['grade'],
                    r['commercial_value'], r['adaptation_difficulty'], r['risk_factor'],
                    r['healing_index'], r['global_potential'], 'v5.0_multi_dim'
                ))
        conn.commit()
        print(f"[DB] 已写入 {len(df_res)} 条评分记录")
    except Exception as e:
        print(f"[ERR] 数据库写入失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


# ================================================================
#  主流程
# ================================================================
def main():
    print("=" * 60)
    print("IP Lumina AI 评估引擎 V5.0 启动")
    print("=" * 60)
    
    # 1. 加载数据
    print("\n[Step 1] 加载全平台书籍数据...")
    df_all = load_all_books()
    if df_all.empty:
        print("[FATAL] 无数据，退出")
        return
    
    # 2. 加载实时月票
    print("\n[Step 2] 加载实时月票数据...")
    rt_data = load_realtime_tickets()
    
    # 3. 加载 NLP 评分
    print("\n[Step 3] 运行章节 NLP 评分...")
    nlp_scores = load_nlp_scores()
    
    # 4. 聚合书籍数据
    print("\n[Step 4] 聚合书籍数据...")
    df_books = aggregate_books(df_all, rt_data)
    
    # 5. 计算评分
    print("\n[Step 5] 计算多维评分...")
    df_res = compute_scores(df_books, nlp_scores)
    
    # 6. 保存结果
    print("\n[Step 6] 保存到数据库...")
    save_to_db(df_res)
    
    # 7. 输出报告
    print("\n" + "=" * 60)
    print("评分完成！结果报告：")
    print("=" * 60)
    
    # 等级分布
    grade_dist = df_res['grade'].value_counts().sort_index()
    print(f"\n=== 等级分布 ===")
    for g, cnt in grade_dist.items():
        print(f"  {g} 级: {cnt} 本")
    
    # 起点 TOP 20
    qd = df_res[df_res['platform'] == 'Qidian'].nlargest(20, 'overall_score')
    print(f"\n=== 起点 TOP 20 ===")
    for i, (_, r) in enumerate(qd.iterrows()):
        print(f"  {i+1:2d}. {r['overall_score']:5.1f} [{r['grade']}] comm={r['commercial_score']:5.1f} nlp={r.get('nlp_score', 50):5.1f} trend={r.get('trend_score', 50):5.1f} stick={r.get('stickiness_score', 50):5.1f}  {r['title']}")
    
    # 纵横 TOP 20
    zh = df_res[df_res['platform'] == 'Zongheng'].nlargest(20, 'overall_score')
    print(f"\n=== 纵横 TOP 20 ===")
    for i, (_, r) in enumerate(zh.iterrows()):
        print(f"  {i+1:2d}. {r['overall_score']:5.1f} [{r['grade']}] comm={r['commercial_score']:5.1f} nlp={r.get('nlp_score', 50):5.1f} trend={r.get('trend_score', 50):5.1f} stick={r.get('stickiness_score', 50):5.1f}  {r['title']}")
    
    # 分数段统计
    print(f"\n=== 分数段统计 ===")
    bins = [0, 40, 50, 60, 70, 80, 90, 100]
    labels = ['<40', '40-49', '50-59', '60-69', '70-79', '80-89', '90+']
    df_res['score_band'] = pd.cut(df_res['overall_score'], bins=bins, labels=labels)
    for band in labels:
        cnt = (df_res['score_band'] == band).sum()
        print(f"  {band:6s} : {cnt}")


if __name__ == '__main__':
    main()
