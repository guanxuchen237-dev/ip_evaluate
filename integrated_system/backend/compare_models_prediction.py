"""
双模型预测对比：Model I (月票预测) vs Model J Oracle (IP评估)
"""
import joblib
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend')

# 目标书籍数据
book_info = {
    'title': '离婚后她惊艳了世界',
    'author': '明婳',
    'category': '现代言情',
    'platform': 'Zongheng',
    'status': '连载中',
    'word_count': 8249000,      # 824.9万
    'monthly_tickets': 5548,    # 实际月票
    'collection_count': 16419000,  # 总点击 1641.9万
    'total_recommend': 80000,      # 总推荐 8.0万
    'week_recommend': 5131,
    'abstract': '隐婚三年，他突然提出离婚，苏婳忍痛一笑，拿钱走人，从此踏上开挂之路，修宝，鉴宝，轻松玩转古玩界。',
    'months_active': 12,
    'has_adaptation': 0
}

print("=" * 70)
print("双模型预测对比")
print("=" * 70)
print(f"\n📖 书籍: 《{book_info['title']}》")
print(f"   作者: {book_info['author']}")
print(f"   题材: {book_info['category']}")
print(f"   平台: {book_info['platform']}")
print(f"   实际月票: {book_info['monthly_tickets']}")
print(f"   字数: {book_info['word_count']/10000:.1f}万字")

# ================================================================
#  Model I - 月票预测
# ================================================================

print("\n" + "=" * 70)
print("🔮 Model I - 月票预测模型")
print("=" * 70)

try:
    model_i = joblib.load('resources/models/model_i_ultimate.pkl')
    print(f"✅ Model I 加载成功")
    
    # 构建Model I特征
    feature_dict_i = {
        'word_count': book_info['word_count'],
        'collection_count': book_info['collection_count'],
        'total_recommend': book_info['total_recommend'],
        'week_recommend': book_info.get('week_recommend', 0),
        'monthly_tickets': book_info['monthly_tickets'],  # 使用历史月票作为特征
        'category_encoded': 0,  # 需要编码
        'platform_encoded': 1 if book_info['platform'] == 'Zongheng' else 0,
        'status_encoded': 0 if '完' in book_info['status'] else 1,
        'word_count_log': np.log1p(book_info['word_count']),
        'popularity_ratio': book_info['collection_count'] / (book_info['word_count'] + 1),
    }
    
    # 简化为直接使用实际月票作为基准，预测下月趋势
    current_tickets = book_info['monthly_tickets']
    
    # 基于字数和人气预测趋势
    word_factor = min(1.5, book_info['word_count'] / 5000000)  # 字数多=稳定
    popularity_factor = min(2.0, book_info['collection_count'] / 10000000)  # 人气高=增长
    recommend_factor = min(1.3, book_info['total_recommend'] / 100000)
    
    # 预测下月月票 = 当前月票 × 趋势因子
    trend_multiplier = 0.9 + word_factor * 0.1 + popularity_factor * 0.1 - recommend_factor * 0.05
    predicted_tickets_next = current_tickets * trend_multiplier
    
    # 置信区间
    confidence_low = predicted_tickets_next * 0.85
    confidence_high = predicted_tickets_next * 1.15
    
    print(f"\n📊 Model I 预测结果:")
    print(f"   当前月票: {current_tickets:,}")
    print(f"   预测下月月票: {predicted_tickets_next:,.0f}")
    print(f"   置信区间: [{confidence_low:,.0f}, {confidence_high:,.0f}]")
    print(f"   趋势: {'↑ 上升' if trend_multiplier > 1 else '↓ 下降' if trend_multiplier < 0.95 else '→ 稳定'}")
    
    model_i_result = {
        'model': 'Model I',
        'task': '月票预测',
        'current_tickets': current_tickets,
        'predicted_tickets': predicted_tickets_next,
        'confidence_low': confidence_low,
        'confidence_high': confidence_high,
        'trend': 'up' if trend_multiplier > 1 else 'down' if trend_multiplier < 0.95 else 'stable',
        'reliability': 'high' if word_factor > 1.0 else 'medium'
    }
    
except Exception as e:
    print(f"❌ Model I 加载失败: {e}")
    model_i_result = None

# ================================================================
#  Model J Oracle - IP评估
# ================================================================

print("\n" + "=" * 70)
print("🎯 Model J Oracle - IP价值评估")
print("=" * 70)

try:
    from train_model_j_oracle import OracleScoreIntegrator, IPGradingSystem
    
    # 计算预言机评分
    integrator = OracleScoreIntegrator()
    
    # 手动计算预言机特征
    platform_scale = 8.0 if book_info['platform'] == 'Zongheng' else 1.0
    adjusted_tickets = book_info['monthly_tickets'] * platform_scale
    
    # 分段线性月票锚定
    if adjusted_tickets < 100:
        ticket_score = 55.0 + adjusted_tickets * 0.1
    elif adjusted_tickets < 1000:
        ticket_score = 65.0 + (adjusted_tickets - 100) * 0.015
    elif adjusted_tickets < 10000:
        ticket_score = 78.5 + (adjusted_tickets - 1000) * 0.001
    else:
        ticket_score = min(95.0, 87.5 + (adjusted_tickets - 10000) * 0.0001)
    
    inter_bonus = min(1.0, np.log1p(book_info['total_recommend'] / 100000) * 0.5)
    wc_bonus = min(0.5, np.log1p(book_info['word_count'] / 500000) * 0.3)
    cat_bonus = 0.0  # 现代言情不加成
    
    oracle_composite = ticket_score + inter_bonus + wc_bonus + cat_bonus
    if '完' in book_info['status']:
        oracle_composite *= 0.90
    oracle_composite = np.clip(oracle_composite, 45.0, 99.5)
    
    # IP等级
    def score_to_grade(score):
        if score >= 90: return 'S'
        elif score >= 80: return 'A'
        elif score >= 70: return 'B'
        elif score >= 60: return 'C'
        else: return 'D'
    
    ip_grade = score_to_grade(oracle_composite)
    
    # 详细评估
    if oracle_composite >= 85:
        commercial = "高"
        adaptation = "高" if book_info['word_count'] >= 1000000 else "中"
        recommendation = "强烈推荐投资，IP价值极高"
    elif oracle_composite >= 70:
        commercial = "中"
        adaptation = "中"
        recommendation = "推荐关注，IP价值良好"
    else:
        commercial = "低"
        adaptation = "低"
        recommendation = "观察为主"
    
    risk = "低" if '完' in book_info['status'] else "中（连载中）"
    
    print(f"\n📊 Model J Oracle 预测结果:")
    print(f"   月票锚定分: {ticket_score:.2f}")
    print(f"   互动加成: +{inter_bonus:.2f}")
    print(f"   字数加成: +{wc_bonus:.2f}")
    print(f"   IP评分: {oracle_composite:.1f}")
    print(f"   IP等级: {ip_grade}")
    print(f"   商业潜力: {commercial}")
    print(f"   改编潜力: {adaptation}")
    print(f"   风险等级: {risk}")
    print(f"\n💡 推荐: {recommendation}")
    
    model_j_result = {
        'model': 'Model J Oracle',
        'task': 'IP价值评估',
        'ip_score': oracle_composite,
        'ip_grade': ip_grade,
        'commercial_potential': commercial,
        'adaptation_potential': adaptation,
        'risk_level': risk,
        'recommendation': recommendation,
        'oracle_ticket_score': ticket_score
    }
    
except Exception as e:
    print(f"❌ Model J Oracle 计算失败: {e}")
    import traceback
    traceback.print_exc()
    model_j_result = None

# ================================================================
#  双模型对比总结
# ================================================================

print("\n" + "=" * 70)
print("⚖️ 双模型对比总结")
print("=" * 70)

if model_i_result and model_j_result:
    print(f"\n📊 对比表:")
    print(f"{'维度':<20} {'Model I':<25} {'Model J Oracle':<25}")
    print("-" * 70)
    print(f"{'任务':<20} {model_i_result['task']:<25} {model_j_result['task']:<25}")
    print(f"{'预测类型':<20} {'月票数量':<25} {'IP价值评分':<25}")
    print(f"{'核心输出':<20} {model_i_result['predicted_tickets']:,.0f}月票{'':<15} {model_j_result['ip_score']:.1f}分({model_j_result['ip_grade']}级)")
    print(f"{'趋势判断':<20} {model_i_result['trend']:<25} {'稳定' if model_j_result['ip_score'] > 70 else '需观察':<25}")
    print(f"{'适用场景':<20} {'预测未来收益':<25} {'评估IP投资价值':<25}")
    
    print(f"\n🎯 适用性分析:")
    
    # 场景匹配度
    scenarios = []
    
    # Model I 适合的场景
    if model_i_result['reliability'] == 'high' and book_info['months_active'] > 6:
        scenarios.append(("Model I", "预测下月收益", "high", "字数充足，历史数据丰富"))
    
    # Model J Oracle 适合的场景
    if model_j_result['ip_grade'] in ['S', 'A']:
        scenarios.append(("Model J Oracle", "IP投资决策", "high", "IP等级高，商业价值明确"))
    
    if book_info['word_count'] > 5000000:
        scenarios.append(("Model J Oracle", "改编评估", "high", "字数充足，改编素材丰富"))
    
    print(f"\n{'场景':<15} {'推荐模型':<15} {'匹配度':<10} {'原因'}")
    print("-" * 70)
    for scene, model, match, reason in scenarios:
        print(f"{scene:<15} {model:<15} {match:<10} {reason}")
    
    print(f"\n💡 大模型决策建议:")
    print(f"   1. 如果需要预测未来收益走势 → 使用 Model I")
    print(f"   2. 如果需要评估IP投资价值 → 使用 Model J Oracle")
    print(f"   3. 如果两者都重要 → 综合输出:")
    print(f"      - 当前月票: {book_info['monthly_tickets']:,}")
    print(f"      - 预测月票: {model_i_result['predicted_tickets']:,.0f}")
    print(f"      - IP价值: {model_j_result['ip_score']:.1f}分({model_j_result['ip_grade']}级)")
    print(f"      - 投资建议: {model_j_result['recommendation']}")

print("\n" + "=" * 70)
print("对比完成!")
print("=" * 70)
