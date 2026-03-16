"""
IP评分模型 v8.1 - 修正版（区分平台）
核心改进：纵横平台月票普遍较低，需要调整阈值
"""
import numpy as np
import joblib
from datetime import datetime

def evaluate_ip(book_data):
    """
    综合评估IP价值（区分平台）
    
    参数:
    - rank: 当前排名
    - monthly_tickets: 月票数（核心指标）
    - total_recommend: 总推荐数
    - word_count: 字数
    - total_click: 总点击
    - platform: 平台（Qidian/Zongheng）
    """
    
    rank = book_data.get('rank', 999)
    monthly_tickets = book_data.get('monthly_tickets', 0)
    total_recommend = book_data.get('total_recommend', 0)
    word_count = book_data.get('word_count', 0)
    total_click = book_data.get('total_click', 0)
    platform = book_data.get('platform', 'Qidian')
    
    # ================================================================
    #  第一步：确定基础等级（基于排名）
    # ================================================================
    
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
    
    # ================================================================
    #  第二步：月票等级（区分平台）
    # ================================================================
    
    # 起点平台月票阈值（高）
    if platform == 'Qidian':
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
            ticket_tier = 'E'
    
    # 纵横平台月票阈值（低，约为起点的30%）
    else:  # Zongheng
        if monthly_tickets >= 3000:
            ticket_tier = 'S'
        elif monthly_tickets >= 1500:
            ticket_tier = 'A'
        elif monthly_tickets >= 800:
            ticket_tier = 'B'
        elif monthly_tickets >= 400:
            ticket_tier = 'C'
        elif monthly_tickets >= 200:
            ticket_tier = 'D'
        else:
            ticket_tier = 'E'
    
    # 综合等级：取排名等级和月票等级的较低者
    tier_order = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1, 'E': 0}
    final_tier = rank_tier if tier_order[rank_tier] <= tier_order[ticket_tier] else ticket_tier
    
    # ================================================================
    #  第三步：计算转化率
    # ================================================================
    
    if total_recommend > 0:
        conversion_rate = monthly_tickets / total_recommend
    else:
        conversion_rate = 0
    
    # 转化率评级（区分平台）
    if platform == 'Qidian':
        if conversion_rate >= 0.05:
            conversion_bonus = 5
            conversion_level = "优秀"
        elif conversion_rate >= 0.02:
            conversion_bonus = 3
            conversion_level = "良好"
        elif conversion_rate >= 0.01:
            conversion_bonus = 1
            conversion_level = "一般"
        elif conversion_rate >= 0.005:
            conversion_bonus = 0
            conversion_level = "较差"
        else:
            conversion_bonus = -3
            conversion_level = "极差"
    else:  # 纵横转化率普遍较低
        if conversion_rate >= 0.03:
            conversion_bonus = 5
            conversion_level = "优秀"
        elif conversion_rate >= 0.01:
            conversion_bonus = 3
            conversion_level = "良好"
        elif conversion_rate >= 0.005:
            conversion_bonus = 1
            conversion_level = "一般"
        elif conversion_rate >= 0.002:
            conversion_bonus = 0
            conversion_level = "较差"
        else:
            conversion_bonus = -2
            conversion_level = "极差"
    
    # ================================================================
    #  第四步：辅助加成
    # ================================================================
    
    # 字数加成
    if word_count >= 3000000:
        wc_bonus = 3
    elif word_count >= 2000000:
        wc_bonus = 2
    elif word_count >= 1000000:
        wc_bonus = 1
    else:
        wc_bonus = 0
    
    # 点击加成
    if total_click >= 10000000:
        click_bonus = 2
    elif total_click >= 5000000:
        click_bonus = 1
    else:
        click_bonus = 0
    
    # ================================================================
    #  第五步：计算最终评分
    # ================================================================
    
    final_score = base_score + conversion_bonus + wc_bonus + click_bonus
    
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
    #  第六步：生成评估报告
    # ================================================================
    
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
        'platform': platform,
        'details': {
            'base_score': base_score,
            'conversion_bonus': conversion_bonus,
            'wc_bonus': wc_bonus,
            'click_bonus': click_bonus
        }
    }

# ================================================================
#  测试
# ================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("IP评分模型 v8.1 - 区分平台")
    print("=" * 70)
    
    test_books = [
        # 起点
        {'name': '起点S级', 'rank': 5, 'monthly_tickets': 15000, 'total_recommend': 200000, 'word_count': 3000000, 'total_click': 10000000, 'platform': 'Qidian'},
        {'name': '起点D级', 'rank': 484, 'monthly_tickets': 746, 'total_recommend': 162000, 'word_count': 1777600, 'total_click': 500000, 'platform': 'Qidian'},
        # 纵横
        {'name': '众仙俯首', 'rank': 13, 'monthly_tickets': 805, 'total_recommend': 130000, 'word_count': 2677000, 'total_click': 6420000, 'platform': 'Zongheng'},
        {'name': '离婚后', 'rank': 5, 'monthly_tickets': 5546, 'total_recommend': 80000, 'word_count': 8249000, 'total_click': 16419000, 'platform': 'Zongheng'},
        {'name': '绝色生骄', 'rank': 33, 'monthly_tickets': 345, 'total_recommend': 129000, 'word_count': 2269000, 'total_click': 4159000, 'platform': 'Zongheng'},
    ]
    
    print(f"\n{'='*70}")
    print("平台月票阈值对比")
    print("=" * 70)
    
    print(f"\n{'等级':<10} {'起点阈值':<15} {'纵横阈值':<15}")
    print("-" * 40)
    print(f"{'S':<10} {'≥10000':<15} {'≥3000':<15}")
    print(f"{'A':<10} {'≥5000':<15} {'≥1500':<15}")
    print(f"{'B':<10} {'≥2000':<15} {'≥800':<15}")
    print(f"{'C':<10} {'≥1000':<15} {'≥400':<15}")
    print(f"{'D':<10} {'≥500':<15} {'≥200':<15}")
    print(f"{'E':<10} {'<500':<15} {'<200':<15}")
    
    print(f"\n{'='*70}")
    print("测试案例")
    print("=" * 70)
    
    for book in test_books:
        result = evaluate_ip(book)
        print(f"\n【{book['name']}】({book['platform']})")
        print(f"   排名: 第{book['rank']}名 | 月票: {book['monthly_tickets']}")
        print(f"   排名等级: {result['rank_tier']} | 月票等级: {result['ticket_tier']}")
        print(f"   IP评分: {result['ip_score']:.1f} | IP等级: {result['ip_grade']}")
        print(f"   转化率: {result['conversion_rate']*100:.2f}% ({result['conversion_level']})")
        print(f"   判定: {result['verdict']}")
    
    # 保存模型
    model_v81 = {
        'model_name': 'IP_Scoring_Model_v81',
        'version': '8.1',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'description': '区分平台的IP评分模型',
        'evaluate_ip': evaluate_ip,
        'config': {
            'qidian_ticket_tiers': {'S': 10000, 'A': 5000, 'B': 2000, 'C': 1000, 'D': 500, 'E': 0},
            'zongheng_ticket_tiers': {'S': 3000, 'A': 1500, 'B': 800, 'C': 400, 'D': 200, 'E': 0}
        }
    }
    
    model_path = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/ip_scoring_model_v81.pkl'
    joblib.dump(model_v81, model_path)
    
    print(f"\n{'='*70}")
    print(f"模型v8.1已保存到: {model_path}")
    print("=" * 70)
