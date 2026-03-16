"""
测试Model J Oracle预测单本书籍
"""
import joblib
import numpy as np
import sys
sys.path.insert(0, 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend')

# 导入必要的类
from train_model_j_oracle import ImprovedDualEngine, IPGradingSystem

# 书籍数据
book_info = {
    'title': '离婚后她惊艳了世界',
    'author': '明婳',
    'category': '现代言情',
    'platform': 'Zongheng',
    'status': '连载中',
    'word_count': 8249000,      # 824.9万
    'monthly_tickets': 5546,
    'collection_count': 16419000,  # 总点击 1641.9万
    'total_recommend': 80000,      # 总推荐 8.0万
    'week_recommend': 5131,
    'abstract': '隐婚三年，他突然提出离婚，苏婳忍痛一笑，拿钱走人，从此踏上开挂之路，修宝，鉴宝，轻松玩转古玩界。离婚后的某霸总，看着电视里艳惊四座的前妻，悔不当初。他化身妻奴，满世界追着她跑，"老婆，心给你，命给你，回来吧！"',
    'months_active': 12,  # 假设连载12个月
    'has_adaptation': 0
}

print("=" * 60)
print("Model J Oracle 预测测试")
print("=" * 60)

# 加载模型
model_path = 'resources/models/model_j_oracle.pkl'
try:
    model = joblib.load(model_path)
    print(f"\n✅ 模型加载成功: {model_path}")
    print(f"   版本: {model.get('version', 'Unknown')}")
    print(f"   时间: {model.get('timestamp', 'Unknown')}")
except Exception as e:
    print(f"❌ 模型加载失败: {e}")
    exit(1)

# 获取特征列表
feature_cols = model.get('features', [])
print(f"\n模型特征数: {len(feature_cols)}")
print(f"特征列表: {feature_cols[:10]}...")

# 构建特征向量
# 预言机特征计算
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

# 辅助维度
inter_bonus = min(1.0, np.log1p(book_info['total_recommend'] / 100000) * 0.5)
wc_bonus = min(0.5, np.log1p(book_info['word_count'] / 500000) * 0.3)
cat_bonus = 0.5 if any(k in book_info['category'] for k in ['玄幻', '奇幻', '仙侠']) else 0.0

# 新作爆发补偿
potential = 0.0
if book_info['word_count'] < 300000 and book_info['monthly_tickets'] > 5000:
    potential = min(5.0, 8.0 * (1.0 - book_info['word_count'] / 400000.0))

# 预言机综合评分
oracle_composite = ticket_score + inter_bonus + wc_bonus + cat_bonus + potential

# 完结衰减
if '完' in book_info['status']:
    oracle_composite *= 0.90

oracle_composite = np.clip(oracle_composite, 45.0, 99.5)

# 题材热度
HOT_GENRES = {
    '玄幻': 95, '奇幻': 92, '都市': 90, '仙侠': 88, '游戏': 85,
    '武侠': 85, '历史': 82, '科幻': 80, '悬疑': 78, '轻小说': 75,
    '现代言情': 85, '言情': 82, '灵异': 72
}
genre_hotness = HOT_GENRES.get(book_info['category'].strip(), 70)

# 构建完整特征字典
feature_dict = {
    'monthly_tickets': book_info['monthly_tickets'],
    'word_count': book_info['word_count'],
    'collection_count': book_info['collection_count'],
    'total_recommend': book_info['total_recommend'],
    'week_recommend': book_info.get('week_recommend', 0),
    'has_adaptation': book_info.get('has_adaptation', 0),
    'months_active': book_info.get('months_active', 12),
    'oracle_ticket_score': ticket_score,
    'oracle_inter_bonus': inter_bonus,
    'oracle_wc_bonus': wc_bonus,
    'oracle_cat_bonus': cat_bonus,
    'oracle_potential': potential,
    'oracle_composite': oracle_composite,
    'retention': book_info['collection_count'] / (book_info['total_recommend'] + 1),
    'genre_hotness': genre_hotness,
    'adaptation_potential': min(book_info['word_count'] / 500000, 1) * 50 + genre_hotness * 0.3,
    'base_power': (np.log1p(book_info['monthly_tickets']) * 20 + 
                   np.log1p(book_info['collection_count']) * 15 + 
                   np.log1p(book_info['total_recommend']) * 10),
    'tickets_normalized': adjusted_tickets,
    'update_freq': 0
}

# 构建特征向量
X = np.array([[feature_dict.get(col, 0) for col in feature_cols]])
X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

# 使用双引擎预测
dual_engine = model['dual_engine']
months = np.array([book_info.get('months_active', 12)])

predictions, engines = dual_engine.predict(X, months)
predicted_score = predictions[0]
engine_used = engines[0]

# 等级判定
def score_to_grade(score):
    if score >= 90:
        return 'S'
    elif score >= 80:
        return 'A'
    elif score >= 70:
        return 'B'
    elif score >= 60:
        return 'C'
    else:
        return 'D'

predicted_grade = score_to_grade(predicted_score)

# 输出结果
print("\n" + "=" * 60)
print("📊 预测结果")
print("=" * 60)

print(f"\n📖 书籍信息:")
print(f"   书名: {book_info['title']}")
print(f"   作者: {book_info['author']}")
print(f"   题材: {book_info['category']}")
print(f"   平台: {book_info['platform']}")
print(f"   状态: {book_info['status']}")
print(f"   字数: {book_info['word_count']/10000:.1f}万字")
print(f"   月票: {book_info['monthly_tickets']}")
print(f"   总点击: {book_info['collection_count']/10000:.1f}万")
print(f"   总推荐: {book_info['total_recommend']/10000:.1f}万")

print(f"\n🔮 预言机特征:")
print(f"   月票锚定分: {ticket_score:.2f}")
print(f"   互动加成: +{inter_bonus:.2f}")
print(f"   字数加成: +{wc_bonus:.2f}")
print(f"   题材加成: +{cat_bonus:.2f}")
print(f"   新作爆发: +{potential:.2f}")
print(f"   预言机综合: {oracle_composite:.2f}")

print(f"\n📈 模型预测:")
print(f"   使用引擎: {engine_used}")
print(f"   IP评分: {predicted_score:.1f}")
print(f"   IP等级: {predicted_grade}")

# 等级说明
GRADE_INFO = {
    'S': {'desc': '顶级IP', 'color': '🔴'},
    'A': {'desc': '优质IP', 'color': '🟠'},
    'B': {'desc': '良好IP', 'color': '🟡'},
    'C': {'desc': '普通IP', 'color': '🟢'},
    'D': {'desc': '低价值IP', 'color': '⚪'}
}
grade_info = GRADE_INFO.get(predicted_grade, {})
print(f"   等级说明: {grade_info.get('color', '')} {grade_info.get('desc', '')}")

# 推荐建议
if predicted_grade in ['S', 'A']:
    recommendation = "强烈推荐投资，IP价值极高，适合影视/游戏改编"
elif predicted_grade == 'B':
    recommendation = "推荐关注，IP价值良好，可考虑小规模投资"
elif predicted_grade == 'C':
    recommendation = "观察为主，IP价值一般，需关注后续发展"
else:
    recommendation = "暂不推荐，IP价值较低，建议等待数据积累"

print(f"\n💡 推荐建议: {recommendation}")

# 商业潜力评估
if predicted_score >= 85:
    commercial = "高"
elif predicted_score >= 70:
    commercial = "中"
else:
    commercial = "低"

# 改编潜力
if predicted_score >= 80 and book_info['word_count'] >= 1000000:
    adaptation = "高"
elif predicted_score >= 70 and book_info['word_count'] >= 500000:
    adaptation = "中"
else:
    adaptation = "低"

# 风险等级
if '完' in book_info['status']:
    risk = "低（已完结）"
elif predicted_score < 60:
    risk = "高（评分低）"
else:
    risk = "中（连载中）"

print(f"\n📋 详细评估:")
print(f"   商业潜力: {commercial}")
print(f"   改编潜力: {adaptation}")
print(f"   风险等级: {risk}")

print("\n" + "=" * 60)
print("预测完成!")
print("=" * 60)
