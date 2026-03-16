"""
验证Model J Oracle v6
"""
import joblib
import numpy as np

print("=" * 70)
print("Model J Oracle v6 验证")
print("=" * 70)

# 加载模型
model = joblib.load('d:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/model_j_oracle_v6.pkl')

print(f"\n模型版本: {model['version']}")
print(f"特征: {model['features']}")

def score_to_grade(score):
    if score >= 90: return 'S'
    elif score >= 80: return 'A'
    elif score >= 70: return 'B'
    elif score >= 60: return 'C'
    else: return 'D'

# ================================================================
#  测试：白手起家，蝙蝠侠干碎我的致富梦
# ================================================================

print("\n" + "=" * 70)
print("测试: 白手起家，蝙蝠侠干碎我的致富梦")
print("=" * 70)

# 实际数据
book = {
    'title': '白手起家，蝙蝠侠干碎我的致富梦',
    'platform': 'Qidian',
    'word_count': 1777600,
    'total_recommend': 162000,
    'collection_count': 50000,  # 估计
    'fan_count': 5000,          # 估计
    'monthly_tickets': 746,     # 实际
    'rank': 484
}

# 计算特征
log_word = np.log1p(book['word_count'])
log_rec = np.log1p(book['total_recommend'])
log_col = np.log1p(book['collection_count'])

# 热度指数（不包含月票）
heat_index = log_rec * 0.5 + log_col * 0.5

# 人气效率
interaction_per_10k = (book['total_recommend'] + book['collection_count']) / (book['word_count'] / 10000 + 1)

# 特征向量
features = np.array([[
    book['word_count'],
    book['total_recommend'],
    book['collection_count'],
    book['fan_count'],
    log_word,
    log_rec,
    log_col,
    heat_index,
    interaction_per_10k
]])

print(f"\n输入特征:")
print(f"   字数: {book['word_count']/10000:.1f}万")
print(f"   总推荐: {book['total_recommend']/10000:.1f}万")
print(f"   收藏数: {book['collection_count']/10000:.1f}万 (估计)")
print(f"   粉丝数: {book['fan_count']} (估计)")
print(f"   热度指数: {heat_index:.2f}")

# 预测
ticket_pred = model['ticket_model'].predict(features)[0]
ip_score = model['ip_model'].predict(features)[0]
ip_grade = score_to_grade(ip_score)

# 置信区间
error_50 = model['metrics']['error_50']
ticket_lower = max(0, ticket_pred - error_50)
ticket_upper = ticket_pred + error_50

print(f"\n预测结果:")
print(f"   月票预测: {ticket_pred:.0f}")
print(f"   50%置信区间: [{ticket_lower:.0f}, {ticket_upper:.0f}]")
print(f"   实际月票: {book['monthly_tickets']}")
print(f"   偏差: {abs(ticket_pred - book['monthly_tickets']):.0f}")

print(f"\n   IP评分: {ip_score:.1f}")
print(f"   IP等级: {ip_grade}")
print(f"   实际排名: 第{book['rank']}名")

# ================================================================
#  对比旧模型
# ================================================================

print("\n" + "=" * 70)
print("模型演进对比")
print("=" * 70)

print(f"\n{'版本':<15} {'月票预测':<20} {'IP等级':<15} {'实际':<20}")
print("-" * 70)
print(f"{'旧模型':<15} {'4,963 (×6.6)':<20} {'A级':<15} {'月票746, C级':<20}")
print(f"{'v4':<15} {'6,036 (×8)':<20} {'D级':<15} {'月票746, C级':<20}")
print(f"{'v5':<15} {'305-462':<20} {'D级':<15} {'月票746, C级':<20}")
print(f"{'v6':<15} {f'{ticket_pred:.0f} [{ticket_lower:.0f}, {ticket_upper:.0f}]':<20} {f'{ip_grade}级':<15} {'月票746, C级':<20}")

print(f"\n等级分布:")
for grade, count in sorted(model['grade_distribution'].items()):
    pct = count / sum(model['grade_distribution'].values()) * 100
    print(f"   {grade}级: {count} ({pct:.1f}%)")

print("\n" + "=" * 70)
print("验证完成!")
print("=" * 70)
