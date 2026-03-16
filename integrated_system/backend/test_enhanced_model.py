"""
使用已有增强模型预测书籍
"""
import joblib
import numpy as np
import xgboost as xgb

print("=" * 70)
print("增强模型预测测试")
print("=" * 70)

# 加载增强模型
model_path = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/ticket_comments_enhanced_20260315_000101.pkl'
model_data = joblib.load(model_path)

model = model_data['model']
scaler = model_data['scaler']
feature_names = model_data['feature_names']

print(f"\n模型信息:")
print(f"   总特征数: {len(feature_names)}")
print(f"   特征列表: {feature_names}")

# ================================================================
#  测试书籍：白手起家，蝙蝠侠干碎我的致富梦
# ================================================================

print("\n" + "=" * 70)
print("测试: 白手起家，蝙蝠侠干碎我的致富梦")
print("=" * 70)

book = {
    'title': '白手起家，蝙蝠侠干碎我的致富梦',
    'platform': 'Qidian',
    'word_count': 1777600,
    'total_recommend': 162000,
    'weekly_recommend': 897,
    'collection_count': 50000,  # 估计
    'monthly_tickets': 746,     # 实际
    'rank': 484,
    'category': '诸天无限',
    'status': '连载中',
    'is_vip': 1,
    'is_signed': 1,
}

print(f"\n已知信息:")
print(f"   书名: {book['title']}")
print(f"   字数: {book['word_count']/10000:.1f}万")
print(f"   总推荐: {book['total_recommend']/10000:.1f}万")
print(f"   周推荐: {book['weekly_recommend']}")
print(f"   收藏: {book['collection_count']/10000:.1f}万 (估计)")
print(f"   实际月票: {book['monthly_tickets']}")
print(f"   实际排名: 第{book['rank']}名")

# ================================================================
#  构建特征向量
# ================================================================

print(f"\n构建特征向量...")

# 创建特征字典，默认值为0
features = {f: 0.0 for f in feature_names}

# 填充已知特征
features['word_count'] = book['word_count']
features['total_recommend'] = book['total_recommend']
features['weekly_recommend'] = book['weekly_recommend']
features['collection_count'] = book['collection_count']
features['monthly_ticket_count'] = book['monthly_tickets']
features['monthly_ticket_rank'] = book['rank']
features['is_vip'] = book['is_vip']
features['is_signed'] = book['is_signed']

# 计算派生特征
features['log_word_count'] = np.log1p(book['word_count'])
features['log_collection'] = np.log1p(book['collection_count'])
features['log_recommend'] = np.log1p(book['total_recommend'])
features['log_click'] = np.log1p(book['collection_count'])  # 用收藏近似

# 题材编码（诸天无限）
categories = model_data.get('categories', [])
if '诸天无限' in categories:
    features['category_code'] = categories.index('诸天无限')
else:
    features['category_code'] = 0

# 时间特征（假设当前月份）
features['quarter'] = 1
features['is_year_end'] = 0
features['is_year_start'] = 1
features['is_summer'] = 0

# 状态特征
features['is_completed'] = 0  # 连载中
features['is_new_book'] = 0
features['is_mature'] = 1  # 177万字，成熟作品
features['is_long_running'] = 1

# 比率特征
features['tickets_per_word'] = book['monthly_tickets'] / (book['word_count'] / 10000 + 1)
features['collection_per_word'] = book['collection_count'] / (book['word_count'] / 10000 + 1)
features['recommend_per_collection'] = book['total_recommend'] / (book['collection_count'] + 1)

# 社区特征（估计）
features['has_contribution'] = 1
features['has_fans'] = 1
features['has_posts'] = 1
features['community_score'] = np.log1p(5000)  # 估计粉丝数

# 历史特征（用当前值近似）
features['hist_tickets_mean'] = book['monthly_tickets']
features['hist_tickets_max'] = book['monthly_tickets']
features['hist_collection_mean'] = book['collection_count']
features['tickets_ma3'] = book['monthly_tickets']
features['tickets_ma6'] = book['monthly_tickets']
features['tickets_ma12'] = book['monthly_tickets']
features['last_month_tickets'] = book['monthly_tickets']
features['last_month_rank'] = book['rank']
features['last_month_collection'] = book['collection_count']

# 变化特征
features['tickets_mom'] = 0  # 无历史数据
features['rank_change'] = 0
features['rank_inverse'] = 1.0 / (book['rank'] + 1)

# NLP特征（默认值，因为没有章节数据）
# sentiment_score, vocabulary_richness 等保持0

# 评论特征（默认值）
# comment_sentiment_score, tier1_comment_ratio 等保持0

# 转换为特征向量
X = np.array([[features[f] for f in feature_names]])

print(f"   特征向量维度: {X.shape}")

# 标准化
X_scaled = scaler.transform(X)

# 预测
dtest = xgb.DMatrix(X_scaled)
y_pred_log = model.predict(dtest)
y_pred = np.expm1(y_pred_log[0])

print(f"\n预测结果:")
print(f"   预测月票: {y_pred:.0f}")
print(f"   实际月票: {book['monthly_tickets']}")
print(f"   偏差: {abs(y_pred - book['monthly_tickets']):.0f}")

# ================================================================
#  问题分析
# ================================================================

print("\n" + "=" * 70)
print("问题分析")
print("=" * 70)

# 检查哪些特征缺失
missing_features = []
zero_features = []

for f in feature_names:
    if features[f] == 0:
        zero_features.append(f)

print(f"\n特征值为0的特征数: {len(zero_features)}/{len(feature_names)}")

# 分类
nlp_zero = [f for f in zero_features if any(k in f for k in ['sentiment', 'chapter', 'vocabulary', 'action', 'dialog', 'scene', 'title_', 'topic_'])]
comment_zero = [f for f in zero_features if any(k in f for k in ['comment_', 'tier', 'region_', 'positive_', 'negative_', 'top_region'])]

print(f"\n缺失的NLP特征: {len(nlp_zero)}")
print(f"   示例: {nlp_zero[:5]}")

print(f"\n缺失的评论特征: {len(comment_zero)}")
print(f"   示例: {comment_zero[:5]}")

print("\n" + "=" * 70)
print("结论")
print("=" * 70)
print(f"""
增强模型需要97个特征，但当前只有基础数据:
- 已知: 字数、推荐、收藏、月票、排名、题材、状态
- 缺失: 章节NLP特征(22个)、评论特征(26个)

预测结果: {y_pred:.0f} (实际: {book['monthly_tickets']})
偏差: {abs(y_pred - book['monthly_tickets']):.0f}

问题: 缺少章节数据和评论数据，无法提取NLP和评论特征
""")
