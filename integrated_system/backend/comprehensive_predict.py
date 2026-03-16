"""
综合预测系统 - 分场景预测策略
场景A：有完整数据（章节+评论+NLP）→ 增强模型（97特征）
场景B：有基础数据（月票、推荐、收藏）→ 简化模型
场景C：只有基本信息（字数、推荐）→ 保守估算+置信区间
"""
import joblib
import numpy as np
import xgboost as xgb
import pymysql
from datetime import datetime

# 数据库配置
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'qidian_data', 'charset': 'utf8mb4'
}

print("=" * 70)
print("综合预测系统 - 分场景预测")
print("=" * 70)

# ================================================================
#  加载模型
# ================================================================

print("\n【加载模型】")

# 增强模型（97特征）
enhanced_model_path = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/ticket_comments_enhanced_20260315_000101.pkl'
enhanced_model = joblib.load(enhanced_model_path)
print(f"   增强模型: {len(enhanced_model['feature_names'])}特征")

# v7模型（排名评估）
v7_model_path = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/model_j_oracle_v7.pkl'
v7_model = joblib.load(v7_model_path)
print(f"   v7模型: IP评分预测")

# ================================================================
#  预测函数
# ================================================================

def predict_scenario_a(book_data, chapter_features, comment_features):
    """场景A：有完整数据 - 增强模型"""
    print("\n【场景A】完整数据 - 增强模型预测")
    
    feature_names = enhanced_model['feature_names']
    scaler = enhanced_model['scaler']
    model = enhanced_model['model']
    
    # 构建完整特征向量
    features = {f: 0.0 for f in feature_names}
    
    # 填充基础特征
    features.update(book_data)
    
    # 填充NLP特征
    features.update(chapter_features)
    
    # 填充评论特征
    features.update(comment_features)
    
    # 预测
    X = np.array([[features[f] for f in feature_names]])
    X_scaled = scaler.transform(X)
    dtest = xgb.DMatrix(X_scaled)
    y_pred = np.expm1(model.predict(dtest)[0])
    
    return y_pred, "高置信度"

def predict_scenario_b(book_data):
    """场景B：有基础数据 - 简化模型"""
    print("\n【场景B】基础数据 - 简化模型预测")
    
    # 使用v7模型的IP评分预测
    features = np.array([[
        book_data.get('word_count', 0),
        book_data.get('total_recommend', 0)
    ]])
    
    ip_score = v7_model['ip_model'].predict(features)[0]
    
    # 基于IP评分估算月票区间
    # IP评分60 → 月票约500
    # IP评分70 → 月票约2000
    # IP评分80 → 月票约10000
    
    if ip_score >= 90:
        ticket_estimate = 50000
        ticket_range = (30000, 100000)
    elif ip_score >= 80:
        ticket_estimate = 10000
        ticket_range = (5000, 20000)
    elif ip_score >= 70:
        ticket_estimate = 2000
        ticket_range = (1000, 5000)
    elif ip_score >= 60:
        ticket_estimate = 500
        ticket_range = (200, 1000)
    else:
        ticket_estimate = 200
        ticket_range = (50, 500)
    
    return ticket_estimate, ticket_range, ip_score, "中置信度"

def predict_scenario_c(book_data):
    """场景C：只有基本信息 - 保守估算"""
    print("\n【场景C】基本信息 - 保守估算")
    
    word_count = book_data.get('word_count', 0)
    total_recommend = book_data.get('total_recommend', 0)
    weekly_recommend = book_data.get('weekly_recommend', 0)
    category = book_data.get('category', '')
    is_vip = book_data.get('is_vip', 0)
    
    # 基于周推荐估算月票（使用实际转化率）
    # 起点中位转化率约0.002
    base_tickets = weekly_recommend * 0.002 if weekly_recommend > 0 else total_recommend * 0.001
    
    # 字数修正
    if word_count > 1000000:  # 100万字以上
        word_factor = 1.2
    elif word_count > 500000:  # 50万字以上
        word_factor = 1.1
    else:
        word_factor = 1.0
    
    # 题材修正
    hot_genres = ['玄幻', '奇幻', '仙侠', '诸天无限', '都市', '游戏']
    category_factor = 1.2 if any(g in category for g in hot_genres) else 1.0
    
    # VIP修正
    vip_factor = 1.3 if is_vip else 1.0
    
    # 综合估算
    ticket_estimate = base_tickets * word_factor * category_factor * vip_factor
    
    # 置信区间（很宽，因为数据不足）
    ticket_range = (ticket_estimate * 0.3, ticket_estimate * 3.0)
    
    # IP评分估算
    ip_score = 50 + min(30, np.log1p(total_recommend) * 5) + min(10, np.log1p(word_count / 100000) * 3)
    
    return ticket_estimate, ticket_range, ip_score, "低置信度（数据不足）"

# ================================================================
#  主预测函数
# ================================================================

def predict_book(book_info, chapter_data=None, comment_data=None):
    """综合预测入口"""
    
    print(f"\n{'='*70}")
    print(f"预测书籍: 《{book_info.get('title', '未知')}》")
    print(f"{'='*70}")
    
    # 判断场景
    has_chapter = chapter_data is not None and len(chapter_data) > 0
    has_comment = comment_data is not None and len(comment_data) > 0
    has_monthly_ticket = book_info.get('monthly_tickets', 0) > 0
    has_rank = book_info.get('rank', 0) > 0
    
    print(f"\n数据情况:")
    print(f"   章节数据: {'✓' if has_chapter else '✗'}")
    print(f"   评论数据: {'✓' if has_comment else '✗'}")
    print(f"   月票数据: {'✓' if has_monthly_ticket else '✗'}")
    print(f"   排名数据: {'✓' if has_rank else '✗'}")
    
    # 选择场景
    if has_chapter and has_comment:
        # 场景A：完整数据
        ticket_pred, confidence = predict_scenario_a(book_info, chapter_data, comment_data)
        ticket_range = (ticket_pred * 0.8, ticket_pred * 1.2)
        ip_score = 70 + ticket_pred / 1000  # 简化
    elif has_monthly_ticket or has_rank:
        # 场景B：基础数据
        ticket_pred, ticket_range, ip_score, confidence = predict_scenario_b(book_info)
    else:
        # 场景C：基本信息
        ticket_pred, ticket_range, ip_score, confidence = predict_scenario_c(book_info)
    
    # IP等级
    def score_to_grade(score):
        if score >= 90: return 'S'
        elif score >= 80: return 'A'
        elif score >= 70: return 'B'
        elif score >= 60: return 'C'
        else: return 'D'
    
    ip_grade = score_to_grade(ip_score)
    
    # 输出结果
    print(f"\n{'='*70}")
    print(f"预测结果")
    print(f"{'='*70}")
    
    print(f"\n月票预测:")
    print(f"   预测值: {ticket_pred:.0f}")
    print(f"   置信区间: [{ticket_range[0]:.0f}, {ticket_range[1]:.0f}]")
    print(f"   置信度: {confidence}")
    
    print(f"\nIP评估:")
    print(f"   IP评分: {ip_score:.1f}")
    print(f"   IP等级: {ip_grade}")
    
    # 好书判定
    print(f"\n是否好书:")
    if ip_grade in ['S', 'A']:
        verdict = "⭐⭐⭐⭐⭐ 优质好书"
    elif ip_grade == 'B':
        verdict = "⭐⭐⭐⭐ 良好书"
    elif ip_grade == 'C':
        verdict = "⭐⭐⭐ 普通水平"
    else:
        verdict = "⭐⭐ 待观察"
    
    print(f"   {verdict}")
    
    return {
        'ticket_prediction': ticket_pred,
        'ticket_range': ticket_range,
        'ip_score': ip_score,
        'ip_grade': ip_grade,
        'confidence': confidence,
        'verdict': verdict
    }

# ================================================================
#  测试
# ================================================================

# 测试书籍：白手起家，蝙蝠侠干碎我的致富梦
book_info = {
    'title': '白手起家，蝙蝠侠干碎我的致富梦',
    'author': '火星咖啡',
    'platform': 'Qidian',
    'word_count': 1777600,
    'total_recommend': 162000,
    'weekly_recommend': 897,
    'category': '诸天无限',
    'is_vip': 1,
    'is_signed': 1,
    'monthly_tickets': 746,  # 实际值（用于验证）
    'rank': 484              # 实际值（用于验证）
}

result = predict_book(book_info)

# 对比实际值
print(f"\n{'='*70}")
print(f"实际值对比")
print(f"{'='*70}")
print(f"   实际月票: {book_info['monthly_tickets']}")
print(f"   实际排名: 第{book_info['rank']}名")
print(f"   预测偏差: {abs(result['ticket_prediction'] - book_info['monthly_tickets']):.0f}")

print(f"\n{'='*70}")
print(f"预测完成!")
print(f"{'='*70}")
