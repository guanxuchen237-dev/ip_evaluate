"""
IP评分模型 v8.1 - 配置版（可序列化）
"""
import numpy as np
import joblib
from datetime import datetime

# 平台配置
PLATFORM_CONFIG = {
    'Qidian': {
        'ticket_tiers': {'S': 10000, 'A': 5000, 'B': 2000, 'C': 1000, 'D': 500, 'E': 0},
        'conversion_thresholds': {'优秀': 0.05, '良好': 0.02, '一般': 0.01, '较差': 0.005, '极差': 0}
    },
    'Zongheng': {
        'ticket_tiers': {'S': 3000, 'A': 1500, 'B': 800, 'C': 400, 'D': 200, 'E': 0},
        'conversion_thresholds': {'优秀': 0.03, '良好': 0.01, '一般': 0.005, '较差': 0.002, '极差': 0}
    }
}

def evaluate_ip(book_data):
    """综合评估IP价值"""
    rank = book_data.get('rank', 999)
    monthly_tickets = book_data.get('monthly_tickets', 0)
    total_recommend = book_data.get('total_recommend', 0)
    word_count = book_data.get('word_count', 0)
    total_click = book_data.get('total_click', 0)
    platform = book_data.get('platform', 'Qidian')
    
    # 获取平台配置
    config = PLATFORM_CONFIG.get(platform, PLATFORM_CONFIG['Qidian'])
    ticket_tiers = config['ticket_tiers']
    conv_thresholds = config['conversion_thresholds']
    
    # 排名等级
    if rank <= 10:
        rank_tier, base_score = 'S', 90
    elif rank <= 50:
        rank_tier, base_score = 'A', 80
    elif rank <= 100:
        rank_tier, base_score = 'B', 70
    elif rank <= 200:
        rank_tier, base_score = 'C', 60
    else:
        rank_tier, base_score = 'D', 50
    
    # 月票等级
    tier_order = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1, 'E': 0}
    for tier, threshold in [('S', ticket_tiers['S']), ('A', ticket_tiers['A']), 
                            ('B', ticket_tiers['B']), ('C', ticket_tiers['C']), 
                            ('D', ticket_tiers['D'])]:
        if monthly_tickets >= threshold:
            ticket_tier = tier
            break
    else:
        ticket_tier = 'E'
    
    # 最终等级
    final_tier = rank_tier if tier_order[rank_tier] <= tier_order[ticket_tier] else ticket_tier
    
    # 转化率
    conversion_rate = monthly_tickets / total_recommend if total_recommend > 0 else 0
    
    if conversion_rate >= conv_thresholds['优秀']:
        conversion_bonus, conversion_level = 5, "优秀"
    elif conversion_rate >= conv_thresholds['良好']:
        conversion_bonus, conversion_level = 3, "良好"
    elif conversion_rate >= conv_thresholds['一般']:
        conversion_bonus, conversion_level = 1, "一般"
    elif conversion_rate >= conv_thresholds['较差']:
        conversion_bonus, conversion_level = 0, "较差"
    else:
        conversion_bonus, conversion_level = -2, "极差"
    
    # 辅助加成
    wc_bonus = 3 if word_count >= 3000000 else (2 if word_count >= 2000000 else (1 if word_count >= 1000000 else 0))
    click_bonus = 2 if total_click >= 10000000 else (1 if total_click >= 5000000 else 0)
    
    # 最终评分
    final_score = np.clip(base_score + conversion_bonus + wc_bonus + click_bonus,
                          {'S': 90, 'A': 80, 'B': 70, 'C': 60, 'D': 50, 'E': 40}[final_tier],
                          {'S': 99, 'A': 89, 'B': 79, 'C': 69, 'D': 59, 'E': 49}[final_tier])
    
    # 判定
    if final_tier in ['S', 'A']:
        verdict, commercial = "⭐⭐⭐⭐⭐ 优质好书", "高商业价值，强烈推荐"
    elif final_tier == 'B':
        verdict, commercial = "⭐⭐⭐⭐ 良好书", "中等商业价值，推荐关注"
    elif final_tier == 'C':
        verdict, commercial = "⭐⭐⭐ 普通水平", "一般商业价值，可关注"
    else:
        verdict, commercial = "⭐⭐ 待观察", "商业价值较低，谨慎投资"
    
    return {
        'ip_score': float(final_score),
        'ip_grade': final_tier,
        'rank_tier': rank_tier,
        'ticket_tier': ticket_tier,
        'conversion_rate': float(conversion_rate),
        'conversion_level': conversion_level,
        'verdict': verdict,
        'commercial': commercial,
        'platform': platform
    }

if __name__ == '__main__':
    # 保存配置（不包含函数）
    model_config = {
        'model_name': 'IP_Scoring_Model_v81',
        'version': '8.1',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'platform_config': PLATFORM_CONFIG
    }
    
    model_path = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/ip_scoring_model_v81_config.pkl'
    joblib.dump(model_config, model_path)
    print(f"[OK] Model config saved to: {model_path}")
    
    # 测试
    test_books = [
        {'name': '离婚后', 'rank': 5, 'monthly_tickets': 5546, 'total_recommend': 80000, 'word_count': 8249000, 'total_click': 16419000, 'platform': 'Zongheng'},
        {'name': '绝色生骄', 'rank': 33, 'monthly_tickets': 345, 'total_recommend': 129000, 'word_count': 2269000, 'total_click': 4159000, 'platform': 'Zongheng'},
    ]
    
    print("\n测试:")
    for book in test_books:
        result = evaluate_ip(book)
        print(f"【{book['name']}】{result['ip_grade']}级 - {result['ip_score']:.1f}分 - {result['verdict']}")
