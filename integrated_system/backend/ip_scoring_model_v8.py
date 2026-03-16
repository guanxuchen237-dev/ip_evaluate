"""
IP评分模型 v8 - 商业价值导向
核心逻辑：月票是商业价值的核心指标

等级判定规则（严格）：
- S级：排名前10 + 月票≥10000
- A级：排名前50 + 月票≥5000
- B级：排名前100 + 月票≥2000
- C级：排名前200 + 月票≥1000
- D级：排名200后 或 月票<1000
- E级：月票<500（极差）
"""
import numpy as np
import joblib
from datetime import datetime

def evaluate_ip(book_data):
    """
    综合评估IP价值
    
    参数:
    - rank: 当前排名
    - monthly_tickets: 月票数（核心指标）
    - total_recommend: 总推荐数
    - word_count: 字数
    - total_click: 总点击
    - platform: 平台（Qidian/Zongheng）
    
    返回:
    - ip_score: IP评分 (40-99)
    - ip_grade: IP等级 (S/A/B/C/D/E)
    - verdict: 是否好书判定
    - commercial: 商业价值评估
    - details: 评分明细
    """
    
    rank = book_data.get('rank', 999)
    monthly_tickets = book_data.get('monthly_tickets', 0)
    total_recommend = book_data.get('total_recommend', 0)
    word_count = book_data.get('word_count', 0)
    total_click = book_data.get('total_click', 0)
    platform = book_data.get('platform', 'Qidian')
    
    # ================================================================
    #  第一步：确定基础等级（基于排名和月票）
    # ================================================================
    
    # 排名决定等级上限
    if rank <= 10:
        rank_tier = 'S'
        base_score = 90
    elif rank <= 50:
        rank_tier = 'A'
        base_score = 80
    elif rank <= 100:
        rank_tier = 'B'
        base_score = 70
    elif rank <= 200:
        rank_tier = 'C'
        base_score = 60
    else:
        rank_tier = 'D'
        base_score = 50
    
    # 月票决定等级下限（月票太低会降级）
    if monthly_tickets >= 10000:
        ticket_tier = 'S'
    elif monthly_tickets >= 5000:
        ticket_tier = 'A'
    elif monthly_tickets >= 2000:
        ticket_tier = 'B'
    elif monthly_tickets >= 1000:
        ticket_tier = 'C'
    elif monthly_tickets >= 500:
        ticket_tier = 'D'
    else:
        ticket_tier = 'E'  # 极低
    
    # 综合等级：取排名等级和月票等级的较低者
    tier_order = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1, 'E': 0}
    final_tier = rank_tier if tier_order[rank_tier] <= tier_order[ticket_tier] else ticket_tier
    
    # ================================================================
    #  第二步：计算转化率（月票/推荐）
    # ================================================================
    
    if total_recommend > 0:
        conversion_rate = monthly_tickets / total_recommend
    else:
        conversion_rate = 0
    
    # 转化率评级
    if conversion_rate >= 0.05:  # 5%以上，优秀
        conversion_bonus = 5
        conversion_level = "优秀"
    elif conversion_rate >= 0.02:  # 2-5%，良好
        conversion_bonus = 3
        conversion_level = "良好"
    elif conversion_rate >= 0.01:  # 1-2%，一般
        conversion_bonus = 1
        conversion_level = "一般"
    elif conversion_rate >= 0.005:  # 0.5-1%，较差
        conversion_bonus = 0
        conversion_level = "较差"
    else:  # 0.5%以下，极差
        conversion_bonus = -3
        conversion_level = "极差"
    
    # ================================================================
    #  第三步：计算辅助加成
    # ================================================================
    
    # 字数加成（上限+3分）
    if word_count >= 3000000:  # 300万字以上
        wc_bonus = 3
    elif word_count >= 2000000:  # 200万字以上
        wc_bonus = 2
    elif word_count >= 1000000:  # 100万字以上
        wc_bonus = 1
    else:
        wc_bonus = 0
    
    # 点击加成（上限+2分）
    if total_click >= 10000000:  # 1000万点击以上
        click_bonus = 2
    elif total_click >= 5000000:  # 500万点击以上
        click_bonus = 1
    else:
        click_bonus = 0
    
    # ================================================================
    #  第四步：计算最终评分
    # ================================================================
    
    # 基础分 + 转化率加成 + 辅助加成
    final_score = base_score + conversion_bonus + wc_bonus + click_bonus
    
    # 根据最终等级调整分数范围
    tier_score_range = {
        'S': (90, 99),
        'A': (80, 89),
        'B': (70, 79),
        'C': (60, 69),
        'D': (50, 59),
        'E': (40, 49)
    }
    
    min_score, max_score = tier_score_range[final_tier]
    final_score = np.clip(final_score, min_score, max_score)
    
    # ================================================================
    #  第五步：生成评估报告
    # ================================================================
    
    # 是否好书判定
    if final_tier in ['S', 'A']:
        verdict = "⭐⭐⭐⭐⭐ 优质好书"
        commercial = "高商业价值，强烈推荐"
    elif final_tier == 'B':
        verdict = "⭐⭐⭐⭐ 良好书"
        commercial = "中等商业价值，推荐关注"
    elif final_tier == 'C':
        verdict = "⭐⭐⭐ 普通水平"
        commercial = "一般商业价值，可关注"
    else:
        verdict = "⭐⭐ 待观察"
        commercial = "商业价值较低，谨慎投资"
    
    return {
        'ip_score': float(final_score),
        'ip_grade': final_tier,
        'rank_tier': rank_tier,
        'ticket_tier': ticket_tier,
        'conversion_rate': float(conversion_rate),
        'conversion_level': conversion_level,
        'verdict': verdict,
        'commercial': commercial,
        'details': {
            'base_score': base_score,
            'conversion_bonus': conversion_bonus,
            'wc_bonus': wc_bonus,
            'click_bonus': click_bonus
        }
    }

def predict_monthly_tickets(book_data):
    """
    基于排名预测月票区间
    
    参数:
    - rank: 当前排名
    - platform: 平台
    
    返回:
    - ticket_estimate: 月票估计中位数
    - ticket_range: 月票区间 (low, high)
    - confidence: 置信度
    """
    rank = book_data.get('rank', 999)
    platform = book_data.get('platform', 'Qidian')
    
    # 起点平台月票区间
    if platform == 'Qidian':
        if rank <= 10:
            ticket_range = (30000, 100000)
            ticket_estimate = 50000
        elif rank <= 50:
            ticket_range = (10000, 50000)
            ticket_estimate = 20000
        elif rank <= 100:
            ticket_range = (5000, 20000)
            ticket_estimate = 10000
        elif rank <= 200:
            ticket_range = (2000, 10000)
            ticket_estimate = 5000
        else:
            ticket_range = (500, 3000)
            ticket_estimate = 1000
    else:  # 纵横平台月票普遍较低
        if rank <= 10:
            ticket_range = (1000, 5000)
            ticket_estimate = 2000
        elif rank <= 50:
            ticket_range = (500, 3000)
            ticket_estimate = 1000
        elif rank <= 100:
            ticket_range = (200, 1500)
            ticket_estimate = 500
        else:
            ticket_range = (100, 800)
            ticket_estimate = 300
    
    confidence = "高" if rank <= 100 else "中"
    
    return {
        'ticket_estimate': ticket_estimate,
        'ticket_range': ticket_range,
        'confidence': confidence
    }

def analyze_trend(history_data):
    """
    分析排名趋势
    
    参数:
    - history_data: 历史数据列表 [{'rank': x, 'monthly_tickets': y}, ...]
    
    返回:
    - trend: 趋势方向
    - prediction: 下月预测
    """
    if len(history_data) < 2:
        return {'trend': '数据不足', 'prediction': None}
    
    ranks = [d['rank'] for d in history_data]
    tickets = [d.get('monthly_tickets', 0) for d in history_data]
    
    # 排名趋势
    rank_change = ranks[-2] - ranks[-1]  # 正数表示排名上升
    
    if rank_change > 5:
        trend = "↑ 上升"
    elif rank_change < -5:
        trend = "↓ 下降"
    else:
        trend = "→ 稳定"
    
    # 下月预测
    avg_rank = sum(ranks[-3:]) / min(3, len(ranks))
    if rank_change < 0:  # 下降趋势
        predicted_rank = int(ranks[-1] + abs(rank_change) * 0.5)
    else:
        predicted_rank = int(ranks[-1] - abs(rank_change) * 0.5)
    
    predicted_rank = max(1, predicted_rank)
    
    return {
        'trend': trend,
        'rank_change': rank_change,
        'predicted_rank': predicted_rank
    }

# ================================================================
#  保存模型
# ================================================================

if __name__ == '__main__':
    # 创建模型对象
    model_v8 = {
        'model_name': 'IP_Scoring_Model_v8',
        'version': '8.0',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'description': '商业价值导向的IP评分模型',
        'evaluate_ip': evaluate_ip,
        'predict_monthly_tickets': predict_monthly_tickets,
        'analyze_trend': analyze_trend,
        'config': {
            'rank_tiers': {
                'S': (1, 10),
                'A': (11, 50),
                'B': (51, 100),
                'C': (101, 200),
                'D': (201, 9999)
            },
            'ticket_tiers': {
                'S': 10000,
                'A': 5000,
                'B': 2000,
                'C': 1000,
                'D': 500,
                'E': 0
            },
            'conversion_thresholds': {
                '优秀': 0.05,
                '良好': 0.02,
                '一般': 0.01,
                '较差': 0.005,
                '极差': 0
            }
        }
    }
    
    # 保存模型
    model_path = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/ip_scoring_model_v8.pkl'
    joblib.dump(model_v8, model_path)
    
    print(f"模型已保存到: {model_path}")
    print(f"\n模型信息:")
    print(f"   名称: {model_v8['model_name']}")
    print(f"   版本: {model_v8['version']}")
    print(f"   创建时间: {model_v8['created_at']}")
    
    # 测试
    print(f"\n{'='*70}")
    print("测试案例")
    print("=" * 70)
    
    test_books = [
        {'name': '白手起家', 'rank': 484, 'monthly_tickets': 746, 'total_recommend': 162000, 'word_count': 1777600, 'total_click': 500000, 'platform': 'Qidian'},
        {'name': '纯阳！', 'rank': 500, 'monthly_tickets': 728, 'total_recommend': 73400, 'word_count': 2609700, 'total_click': 200000, 'platform': 'Qidian'},
        {'name': '众仙俯首', 'rank': 13, 'monthly_tickets': 805, 'total_recommend': 130000, 'word_count': 2677000, 'total_click': 6420000, 'platform': 'Zongheng'},
        {'name': '星辰之主', 'rank': 25, 'monthly_tickets': 463, 'total_recommend': 3582000, 'word_count': 8238000, 'total_click': 17455000, 'platform': 'Qidian'},
        {'name': '假设S级', 'rank': 5, 'monthly_tickets': 15000, 'total_recommend': 200000, 'word_count': 3000000, 'total_click': 10000000, 'platform': 'Qidian'},
    ]
    
    for book in test_books:
        result = evaluate_ip(book)
        print(f"\n【{book['name']}】排名{book['rank']} 月票{book['monthly_tickets']}")
        print(f"   IP评分: {result['ip_score']:.1f} | IP等级: {result['ip_grade']}")
        print(f"   转化率: {result['conversion_rate']*100:.2f}% ({result['conversion_level']})")
        print(f"   判定: {result['verdict']}")
        print(f"   商业价值: {result['commercial']}")
    
    print(f"\n{'='*70}")
    print("模型v8保存完成!")
    print("=" * 70)
