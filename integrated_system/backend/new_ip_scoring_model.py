"""
新版IP评分模型 - 基于商业价值的综合评估
核心逻辑：
1. 月票是商业价值的核心指标（付费意愿）
2. 排名决定基础等级上限
3. 转化率（月票/推荐）反映读者付费意愿
4. 其他指标作为辅助加成

等级划分（严格）：
- S级：排名前10 + 月票>10000
- A级：排名前50 + 月票>5000
- B级：排名前100 + 月票>2000
- C级：排名前200 + 月票>1000
- D级：排名200后 或 月票<1000
"""
import numpy as np

print("=" * 70)
print("新版IP评分模型 - 商业价值导向")
print("=" * 70)

# ================================================================
#  核心评分函数
# ================================================================

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
        'ip_score': final_score,
        'ip_grade': final_tier,
        'rank_tier': rank_tier,
        'ticket_tier': ticket_tier,
        'conversion_rate': conversion_rate,
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

# ================================================================
#  测试案例
# ================================================================

test_books = [
    {
        'name': '白手起家，蝙蝠侠干碎我的致富梦',
        'rank': 484,
        'monthly_tickets': 746,
        'total_recommend': 162000,
        'word_count': 1777600,
        'total_click': 500000,
        'platform': 'Qidian'
    },
    {
        'name': '纯阳！',
        'rank': 500,
        'monthly_tickets': 728,
        'total_recommend': 73400,
        'word_count': 2609700,
        'total_click': 200000,
        'platform': 'Qidian'
    },
    {
        'name': '众仙俯首',
        'rank': 13,
        'monthly_tickets': 805,
        'total_recommend': 130000,
        'word_count': 2677000,
        'total_click': 6420000,
        'platform': 'Zongheng'
    },
    {
        'name': '星辰之主',
        'rank': 25,
        'monthly_tickets': 463,
        'total_recommend': 3582000,
        'word_count': 8238000,
        'total_click': 17455000,
        'platform': 'Qidian'
    },
    {
        'name': '假设S级好书',
        'rank': 5,
        'monthly_tickets': 15000,
        'total_recommend': 200000,
        'word_count': 3000000,
        'total_click': 10000000,
        'platform': 'Qidian'
    },
    {
        'name': '假设A级好书',
        'rank': 30,
        'monthly_tickets': 6000,
        'total_recommend': 150000,
        'word_count': 2000000,
        'total_click': 5000000,
        'platform': 'Qidian'
    }
]

print(f"\n{'='*70}")
print("测试案例")
print("=" * 70)

for book in test_books:
    result = evaluate_ip(book)
    
    print(f"\n【{book['name']}】")
    print(f"   排名: 第{book['rank']}名 | 月票: {book['monthly_tickets']} | 推荐: {book['total_recommend']}")
    print(f"   排名等级: {result['rank_tier']} | 月票等级: {result['ticket_tier']}")
    print(f"   转化率: {result['conversion_rate']*100:.2f}% ({result['conversion_level']})")
    print(f"   IP评分: {result['ip_score']:.1f} | IP等级: {result['ip_grade']}")
    print(f"   评分明细: 基础{result['details']['base_score']} + 转化{result['details']['conversion_bonus']:+d} + 字数{result['details']['wc_bonus']:+d} + 点击{result['details']['click_bonus']:+d}")
    print(f"   判定: {result['verdict']}")
    print(f"   商业价值: {result['commercial']}")

print(f"\n{'='*70}")
print("评分逻辑说明")
print("=" * 70)
print(f"""
等级判定规则（严格）：
1. 排名决定等级上限：
   - 前10名 → S级候选
   - 前50名 → A级候选
   - 前100名 → B级候选
   - 前200名 → C级候选
   - 200名后 → D级

2. 月票决定等级下限：
   - 月票≥10000 → S级
   - 月票≥5000 → A级
   - 月票≥2000 → B级
   - 月票≥1000 → C级
   - 月票≥500 → D级
   - 月票<500 → E级（极差）

3. 最终等级 = min(排名等级, 月票等级)

4. 转化率影响评分：
   - 转化率≥5% → +5分
   - 转化率≥2% → +3分
   - 转化率≥1% → +1分
   - 转化率<0.5% → -3分

5. 辅助加成：
   - 字数加成：最高+3分
   - 点击加成：最高+2分
""")

print("\n" + "=" * 70)
print("新评分模型完成!")
print("=" * 70)
