"""
预测《纯阳！》- 使用章节内容提取NLP特征
"""
import joblib
import numpy as np
import xgboost as xgb
import jieba
from collections import Counter

print("=" * 70)
print("预测《纯阳！》- 南北宗源")
print("=" * 70)

# ================================================================
#  书籍信息
# ================================================================

book_info = {
    'title': '纯阳！',
    'author': '南北宗源',
    'platform': 'Qidian',
    'category': '玄幻·东方玄幻',
    'status': '连载中',
    'word_count': 2609700,  # 260.97万字
    'total_recommend': 73400,  # 7.34万总推荐
    'weekly_recommend': 488,
    'is_vip': 1,
    'is_signed': 1,
    'chapter_count': 632,
}

# 章节内容（用户提供）
chapter_content = """
江北省，真武山。盘山公路上，观光大巴驱驰而行，隔着玻璃窗便能见到旁边的悬崖绝壁，葱葱古树擦身而过。
我就不信这仙家圣地都洗不净你这颗肮脏不堪的心灵。
笃定的声音从耳边传来，张凡靠着窗户的头稍稍歪了些，看着一脸自信的死党，旋即又死气沉沉地看向车外。
大学四年的感情，最终应了毕业季即是分手季的诅咒，劳燕分飞，曾经最亲密的两人，从此人生再无重合的轨迹。
夕阳下奔跑的身影，彻底沦为逝去的青春……
这样的落差让张凡好一阵子都难以缓过劲来。身为死党，李一山不得不将其拖了出来，登山朝圣，进庙烧香，换一换心情，求一求神佛。
你说……仙人有没有情关？就在此时，张凡头也不回地问了一句。
这可是真武山，灵得很，你别乱说话。李一山双目圆瞪，小声道。
不过老话说，凡人求仙堕红尘，需过两关得道闻……李一山大学研修民俗文化。
哪两关？张凡随口问道。情关和生死关……过了这两关，才会有高人来度化你。
真武山，乃是天下名山。唐朝贞观年间，朝廷便在此地敕建五龙观，祈天求雨，至此开玄宗之山门，为天下七十二福地之一，古往今来，不知多少求仙客登山栖隐，望窥仙道。
炼尽神中阴滓，成就无极纯阳！我叫张凡，凡人的凡！！
"""

# 简介内容
intro = """
【劫是杀身大祸，亦是长生大药】
真武山，道门十大名山，5A级旅游景区，门票280……
祖师爷曾预言：真武传道七十三，因凡应劫后人参。
绝不绝，灭不灭，七十三代有一歇……
真武山传到今日，已有七十三代，难道天命当绝？
因凡应劫，旅游观光的凡俗太多了，涨价吧！
这一日，真武山玉牒传度……
这一日，大学毕业的张凡观光旅游……
炼尽神中阴滓，成就无极纯阳！我叫张凡，凡人的凡！！
"""

print(f"\n书籍信息:")
print(f"   书名: 《{book_info['title']}》")
print(f"   作者: {book_info['author']}")
print(f"   题材: {book_info['category']}")
print(f"   状态: {book_info['status']}")
print(f"   字数: {book_info['word_count']/10000:.2f}万")
print(f"   总推荐: {book_info['total_recommend']/10000:.2f}万")
print(f"   周推荐: {book_info['weekly_recommend']}")
print(f"   章节数: {book_info['chapter_count']}")

# ================================================================
#  NLP特征提取
# ================================================================

print(f"\n【步骤1】提取NLP特征...")

# 停用词
STOPWORDS = set([
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也',
    '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那',
    '啊', '呢', '吧', '吗', '嘛', '哦', '嗯', '哼', '哇', '呀', '第', '章', '节', '正文'
])

# 情感词典
positive_words = set([
    '喜欢', '爱', '棒', '精彩', '优秀', '好', '强', '厉害', '牛', '赞', '神', '无敌',
    '热血', '激动', '爽', '燃', '震撼', '感动', '泪目', '哭', '笑', '开心', '快乐',
    '幸福', '美', '帅', '酷', '霸气', '威武', '英雄', '传奇', '神话', '巅峰', '至尊',
    '绝世', '超神', '逆天', '最强', '第一', '王者', '帝王', '主宰', '推荐', '好看'
])

negative_words = set([
    '讨厌', '恨', '差', '烂', '垃圾', '坏', '弱', '菜', '坑', '毒', '屎', '粪',
    '悲伤', '痛苦', '绝望', '死', '杀', '血', '泪', '伤', '痛', '苦', '难', '惨',
    '悲剧', '失败', '输', '败', '落', '沉', '暗', '黑', '阴', '邪', '魔', '鬼'
])

# 分词
all_text = chapter_content + intro
words = list(jieba.cut(all_text))
words = [w for w in words if len(w) > 1 and w not in STOPWORDS]

# 情感分析
pos_count = sum(1 for w in words if w in positive_words)
neg_count = sum(1 for w in words if w in negative_words)
total_words = len(words)

sentiment_score = (pos_count - neg_count) / total_words if total_words > 0 else 0
sentiment_ratio = pos_count / (neg_count + 1)

print(f"   总词数: {total_words}")
print(f"   正面词: {pos_count}")
print(f"   负面词: {neg_count}")
print(f"   情感得分: {sentiment_score:.4f}")
print(f"   情感比率: {sentiment_ratio:.2f}")

# 词汇丰富度
unique_words = len(set(words))
vocabulary_richness = unique_words / (total_words + 1)

print(f"   独立词数: {unique_words}")
print(f"   词汇丰富度: {vocabulary_richness:.4f}")

# 写作风格
action_words = ['打', '杀', '战', '斗', '冲', '跑', '飞', '跳', '劈', '斩', '修', '炼', '仙', '道']
dialog_words = ['说', '道', '问', '答', '喊', '叫']
scene_words = ['山', '水', '城', '门', '宫', '殿', '林', '海', '天', '地']

action_count = sum(1 for w in words if any(aw in w for aw in action_words))
dialog_count = sum(1 for w in words if any(dw in w for dw in dialog_words))
scene_count = sum(1 for w in words if any(sw in w for sw in scene_words))

action_ratio = action_count / total_words if total_words > 0 else 0
dialog_ratio = dialog_count / total_words if total_words > 0 else 0
scene_ratio = scene_count / total_words if total_words > 0 else 0

print(f"   动作词比例: {action_ratio:.4f}")
print(f"   对话词比例: {dialog_ratio:.4f}")
print(f"   场景词比例: {scene_ratio:.4f}")

# 高频词
word_freq = Counter(words)
top_words = [w for w, _ in word_freq.most_common(20)]
print(f"   高频词: {top_words[:10]}")

# 悬念计数
suspense_words = ['？', '！', '...', '悬念', '惊', '秘', '劫', '命', '绝']
suspense_count = sum(1 for w in words if any(sw in w for sw in suspense_words))
print(f"   悬念词数: {suspense_count}")

# ================================================================
#  构建特征向量
# ================================================================

print(f"\n【步骤2】构建特征向量...")

# 加载增强模型
model_path = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/ticket_comments_enhanced_20260315_000101.pkl'
model_data = joblib.load(model_path)

feature_names = model_data['feature_names']
scaler = model_data['scaler']
model = model_data['model']

# 创建特征字典
features = {f: 0.0 for f in feature_names}

# 基础特征
features['word_count'] = book_info['word_count']
features['total_recommend'] = book_info['total_recommend']
features['weekly_recommend'] = book_info['weekly_recommend']
features['is_vip'] = book_info['is_vip']
features['is_signed'] = book_info['is_signed']

# 派生特征
features['log_word_count'] = np.log1p(book_info['word_count'])
features['log_recommend'] = np.log1p(book_info['total_recommend'])
features['log_collection'] = np.log1p(book_info['total_recommend'] * 0.5)  # 估计收藏
features['log_click'] = np.log1p(book_info['total_recommend'] * 2)

# NLP特征
features['sentiment_score'] = sentiment_score
features['sentiment_ratio'] = sentiment_ratio
features['positive_word_count'] = pos_count
features['negative_word_count'] = neg_count
features['vocabulary_richness'] = vocabulary_richness
features['unique_word_count'] = unique_words
features['total_word_count'] = total_words
features['action_word_ratio'] = action_ratio
features['dialog_word_ratio'] = dialog_ratio
features['scene_word_ratio'] = scene_ratio
features['title_suspense_count'] = suspense_count

# 章节特征
features['chapter_count'] = book_info['chapter_count']
features['avg_chapter_length'] = book_info['word_count'] / book_info['chapter_count']
features['total_content_length'] = len(chapter_content)

# 题材编码（玄幻）
categories = model_data.get('categories', [])
if '玄幻' in categories:
    features['category_code'] = categories.index('玄幻')
else:
    features['category_code'] = 0

# 时间特征
features['quarter'] = 1
features['is_year_end'] = 0
features['is_year_start'] = 1
features['is_summer'] = 0

# 状态特征
features['is_completed'] = 0
features['is_new_book'] = 0
features['is_mature'] = 1  # 260万字
features['is_long_running'] = 1

# 比率特征
features['tickets_per_word'] = 0  # 未知
features['collection_per_word'] = book_info['total_recommend'] * 0.5 / (book_info['word_count'] / 10000 + 1)
features['recommend_per_collection'] = 2.0

# 社区特征
features['has_contribution'] = 1
features['has_fans'] = 1
features['has_posts'] = 1
features['community_score'] = np.log1p(5000)

# 历史特征（未知，用估计值）
estimated_monthly_tickets = book_info['weekly_recommend'] * 3  # 周推荐×3
features['hist_tickets_mean'] = estimated_monthly_tickets
features['hist_tickets_max'] = estimated_monthly_tickets
features['last_month_tickets'] = estimated_monthly_tickets
features['tickets_ma3'] = estimated_monthly_tickets
features['tickets_ma6'] = estimated_monthly_tickets
features['tickets_ma12'] = estimated_monthly_tickets

# 评论特征（未知，用默认值）
# 保持为0

# 转换为特征向量
X = np.array([[features[f] for f in feature_names]])

print(f"   特征向量维度: {X.shape}")

# 统计非零特征
non_zero = np.sum(X != 0)
print(f"   非零特征数: {non_zero}/{len(feature_names)}")

# ================================================================
#  预测
# ================================================================

print(f"\n【步骤3】预测月票...")

X_scaled = scaler.transform(X)
dtest = xgb.DMatrix(X_scaled)
y_pred_log = model.predict(dtest)
y_pred = np.expm1(y_pred_log[0])

print(f"   预测月票: {y_pred:.0f}")

# ================================================================
#  IP评估
# ================================================================

print(f"\n【步骤4】IP评估...")

# 基于预测月票计算IP评分
if y_pred >= 50000:
    ip_score = 90 + min(5, (y_pred - 50000) / 100000)
elif y_pred >= 20000:
    ip_score = 80 + (y_pred - 20000) / 3000
elif y_pred >= 10000:
    ip_score = 70 + (y_pred - 10000) / 1000
elif y_pred >= 5000:
    ip_score = 60 + (y_pred - 5000) / 500
else:
    ip_score = 50 + y_pred / 100

# 字数加成
wc_bonus = min(3.0, np.log1p(book_info['word_count'] / 500000) * 1.5)
ip_score += wc_bonus

# 题材加成（玄幻热门）
cat_bonus = 1.0
ip_score += cat_bonus

# 情感加成
if sentiment_score > 0:
    ip_score += min(2, sentiment_score * 10)

ip_score = np.clip(ip_score, 45.0, 99.5)

def score_to_grade(score):
    if score >= 90: return 'S'
    elif score >= 80: return 'A'
    elif score >= 70: return 'B'
    elif score >= 60: return 'C'
    else: return 'D'

ip_grade = score_to_grade(ip_score)

print(f"   IP评分: {ip_score:.1f}")
print(f"   IP等级: {ip_grade}")

# ================================================================
#  综合评估
# ================================================================

print(f"\n{'='*70}")
print(f"综合评估结果")
print(f"{'='*70}")

print(f"\n【月票预测】")
print(f"   预测月票: {y_pred:.0f}")
print(f"   置信区间: [{y_pred*0.5:.0f}, {y_pred*1.5:.0f}]")
print(f"   置信度: 中（缺少评论数据）")

print(f"\n【IP评估】")
print(f"   IP评分: {ip_score:.1f}")
print(f"   IP等级: {ip_grade}")
print(f"   商业潜力: {'高' if ip_grade in ['S', 'A'] else '中' if ip_grade == 'B' else '低'}")
print(f"   改编潜力: {'高' if book_info['word_count'] > 1000000 else '中'}")

print(f"\n【内容分析】")
print(f"   情感倾向: {'正面' if sentiment_score > 0 else '负面' if sentiment_score < 0 else '中性'}")
print(f"   写作风格: 动作{action_ratio*100:.1f}% / 对话{dialog_ratio*100:.1f}% / 场景{scene_ratio*100:.1f}%")
print(f"   词汇丰富度: {vocabulary_richness:.3f}")
print(f"   题材热度: 玄幻·东方玄幻（热门）")

print(f"\n【是否好书】")
if ip_grade in ['S', 'A']:
    verdict = "⭐⭐⭐⭐⭐ 优质好书"
elif ip_grade == 'B':
    verdict = "⭐⭐⭐⭐ 良好书"
elif ip_grade == 'C':
    verdict = "⭐⭐⭐ 普通水平"
else:
    verdict = "⭐⭐ 待观察"

print(f"   {verdict}")

print(f"\n【投资建议】")
if ip_grade in ['S', 'A']:
    advice = "强烈推荐关注，IP价值高"
elif ip_grade == 'B':
    advice = "推荐关注，IP价值良好"
elif ip_grade == 'C':
    advice = "可关注，IP价值一般"
else:
    advice = "建议观察，IP价值待定"

print(f"   {advice}")

print("\n" + "=" * 70)
print("预测完成!")
print("=" * 70)
