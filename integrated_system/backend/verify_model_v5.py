"""
验证Model J Oracle v5
"""
import joblib
import numpy as np

print("=" * 70)
print("Model J Oracle v5 验证")
print("=" * 70)

# 加载模型
model = joblib.load('d:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/model_j_oracle_v5.pkl')

print(f"\n模型版本: {model['version']}")
print(f"平台转化率:")
for platform, stats in model['platform_stats'].items():
    print(f"   {platform}: 中位转化率={stats['median_ratio']:.4f}, MAE={stats['mae']:.0f}")

def score_to_grade(score):
    if score >= 90: return 'S'
    elif score >= 80: return 'A'
    elif score >= 70: return 'B'
    elif score >= 60: return 'C'
    else: return 'D'

# ================================================================
#  测试1：白手起家，蝙蝠侠干碎我的致富梦
# ================================================================

print("\n" + "=" * 70)
print("测试1: 白手起家，蝙蝠侠干碎我的致富梦")
print("=" * 70)

book1 = {
    'title': '白手起家，蝙蝠侠干碎我的致富梦',
    'platform': 'Qidian',
    'word_count': 1777600,
    'total_recommend': 162000,
    'monthly_tickets': 746,  # 实际
    'rank': 484
}

# 使用起点模型预测月票
qd_model = model['ticket_models'].get('Qidian')
if qd_model:
    # 使用中位转化率估算
    estimated_ratio = qd_model['median_ratio']
    estimated_tickets = book1['total_recommend'] * estimated_ratio
    
    # 使用模型预测
    X_ticket = np.array([[book1['word_count'], book1['total_recommend'], estimated_ratio]])
    tickets_pred = qd_model['model'].predict(X_ticket)[0]
    
    print(f"\n月票预测:")
    print(f"   总推荐: {book1['total_recommend']:,}")
    print(f"   中位转化率: {estimated_ratio:.4f}")
    print(f"   估算月票: {estimated_tickets:.0f}")
    print(f"   模型预测: {tickets_pred:.0f}")
    print(f"   实际月票: {book1['monthly_tickets']}")
    print(f"   偏差: {abs(tickets_pred - book1['monthly_tickets']):.0f}")

# IP评分预测
ticket_ratio = book1['monthly_tickets'] / (book1['total_recommend'] + 1)
X_ip = np.array([[book1['word_count'], book1['total_recommend'], ticket_ratio]])
ip_score = model['ip_model'].predict(X_ip)[0]
ip_grade = score_to_grade(ip_score)

print(f"\nIP评估:")
print(f"   实际转化率: {ticket_ratio:.4f}")
print(f"   IP评分: {ip_score:.1f}")
print(f"   IP等级: {ip_grade}")
print(f"   实际排名: 第{book1['rank']}名")

# ================================================================
#  测试2：离婚后她惊艳了世界
# ================================================================

print("\n" + "=" * 70)
print("测试2: 离婚后她惊艳了世界")
print("=" * 70)

book2 = {
    'title': '离婚后她惊艳了世界',
    'platform': 'Zongheng',
    'word_count': 8249000,
    'total_recommend': 80000,
    'monthly_tickets': 5548,
}

# 使用纵横模型预测
zh_model = model['ticket_models'].get('Zongheng')
if zh_model:
    estimated_ratio = zh_model['median_ratio']
    estimated_tickets = book2['total_recommend'] * estimated_ratio
    
    X_ticket = np.array([[book2['word_count'], book2['total_recommend'], estimated_ratio]])
    tickets_pred = zh_model['model'].predict(X_ticket)[0]
    
    print(f"\n月票预测:")
    print(f"   总推荐: {book2['total_recommend']:,}")
    print(f"   中位转化率: {estimated_ratio:.4f}")
    print(f"   估算月票: {estimated_tickets:.0f}")
    print(f"   模型预测: {tickets_pred:.0f}")
    print(f"   实际月票: {book2['monthly_tickets']}")
    print(f"   偏差: {abs(tickets_pred - book2['monthly_tickets']):.0f}")

# IP评分
ticket_ratio2 = book2['monthly_tickets'] / (book2['total_recommend'] + 1)
X_ip2 = np.array([[book2['word_count'], book2['total_recommend'], ticket_ratio2]])
ip_score2 = model['ip_model'].predict(X_ip2)[0]
ip_grade2 = score_to_grade(ip_score2)

print(f"\nIP评估:")
print(f"   实际转化率: {ticket_ratio2:.4f}")
print(f"   IP评分: {ip_score2:.1f}")
print(f"   IP等级: {ip_grade2}")

# ================================================================
#  对比总结
# ================================================================

print("\n" + "=" * 70)
print("新旧模型对比总结")
print("=" * 70)

print(f"\n{'书籍':<25} {'旧模型':<20} {'v5模型':<20} {'实际':<15}")
print("-" * 80)
print(f"{'白手起家 月票':<25} {'4,963 (×6.6)':<20} {f'{tickets_pred:.0f}':<20} {'746':<15}")
print(f"{'白手起家 IP等级':<25} {'A级 (偏高)':<20} {f'{ip_grade}级':<20} {'C/D级':<15}")
print(f"{'离婚后 月票':<25} {'~6,000':<20} {f'{tickets_pred:.0f}':<20} {'5,548':<15}")
print(f"{'离婚后 IP等级':<25} {'S级 (偏高)':<20} {f'{ip_grade2}级':<20} {'B/C级':<15}")

print(f"\n等级分布:")
for grade, count in sorted(model['grade_distribution'].items()):
    print(f"   {grade}级: {count} 本")

print("\n" + "=" * 70)
print("验证完成!")
print("=" * 70)
