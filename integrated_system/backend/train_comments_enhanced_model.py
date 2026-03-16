"""
融合评论特征的月票预测模型训练脚本 (v4.0)
整合：章节NLP + 读者评论情感 + 地区分布特征
"""
import pandas as pd
import numpy as np
import pymysql
import xgboost as xgb
import jieba
import re
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import warnings
from datetime import datetime
from collections import Counter
import os

warnings.filterwarnings('ignore')

# 数据库配置
QIDIAN_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'qidian_data',
    'charset': 'utf8mb4'
}

ZONGHENG_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'zongheng_analysis_v8',
    'charset': 'utf8mb4'
}

# 添加中文停用词
STOPWORDS = set([
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也',
    '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那',
    '啊', '呢', '吧', '吗', '嘛', '哦', '嗯', '哼', '哇', '呀', '第', '章', '节', '正文',
    '简介', '作者', '本书', '小说', '读者', '点击', '推荐', '收藏', '月票', '订阅'
])

# 一线城市定义
TIER1_CITIES = {'北京', '上海', '广东'}  # 广东包含广州、深圳
TIER2_CITIES = {'江苏', '浙江', '山东', '四川', '河南', '湖北', '湖南', '安徽', '辽宁', '陕西', '天津', '重庆', '福建'}


def get_sentiment_dict():
    """加载情感词典"""
    positive_words = set([
        '喜欢', '爱', '棒', '精彩', '优秀', '好', '强', '厉害', '牛', '赞', '神', '无敌',
        '热血', '激动', '爽', '燃', '震撼', '感动', '泪目', '哭', '笑', '开心', '快乐',
        '幸福', '美', '帅', '酷', '霸气', '威武', '英雄', '传奇', '神话', '巅峰', '至尊',
        '绝世', '超神', '逆天', '最强', '第一', '王者', '帝王', '主宰', '至尊', '推荐',
        '好看', '不错', '支持', '加油', '期待', '追更', '订阅', '打赏', '催更', '过瘾'
    ])
    
    negative_words = set([
        '讨厌', '恨', '差', '烂', '垃圾', '坏', '弱', '菜', '坑', '毒', '屎', '粪',
        '悲伤', '痛苦', '绝望', '死', '杀', '血', '泪', '伤', '痛', '苦', '难', '惨',
        '悲剧', '失败', '输', '败', '落', '沉', '暗', '黑', '阴', '邪', '魔', '鬼',
        '妖', '怪', '恐', '怕', '惊', '吓', '慌', '急', '怒', '气', '愤', '怨', '弃书',
        '太监', '断更', '水', '无聊', '失望', '弃坑'
    ])
    
    return positive_words, negative_words


def analyze_sentiment(text):
    """分析文本情感得分 (-1 到 1)"""
    if not text or pd.isna(text):
        return 0.0, 0, 0
    
    positive_words, negative_words = get_sentiment_dict()
    
    words = list(jieba.cut(str(text)))
    
    pos_count = sum(1 for w in words if w in positive_words)
    neg_count = sum(1 for w in words if w in negative_words)
    total = len(words)
    
    if total == 0:
        return 0.0, 0, 0
    
    sentiment_score = (pos_count - neg_count) / total
    
    return sentiment_score, pos_count, neg_count


def fetch_qidian_full_data():
    """获取起点完整数据"""
    conn = pymysql.connect(**QIDIAN_CONFIG)
    
    query = """
    SELECT 
        year, month, title, author, category, status,
        word_count, collection_count, collection_rank,
        monthly_tickets_on_list as monthly_tickets,
        monthly_ticket_count, rank_on_list as monthly_ticket_rank,
        recommendation_count, reward_count as bang_count,
        is_vip, is_sign as is_signed, synopsis as intro,
        latest_chapter, updated_at as latest_update_time,
        week_recommendation_count as weekly_recommend,
        adaptations as adaptation_info
    FROM novel_monthly_stats
    WHERE year >= 2020 AND year <= 2025
    ORDER BY year, month, title
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"[INFO] 起点: 获取 {len(df)} 条记录")
    return df


def fetch_zongheng_full_data():
    """获取纵横完整数据"""
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    
    query = """
    SELECT 
        year, month, title, author, category, word_count,
        monthly_ticket, rank_num as monthly_ticket_rank,
        month_donate as contribution_value, total_click,
        total_rec as total_recommend, week_rec as weekly_recommend,
        post_count, fan_count, is_signed, status as completion_status,
        abstract as intro, latest_chapter, updated_at as latest_update_time,
        update_frequency, chapter_interval as chapter_frequency
    FROM zongheng_book_ranks
    WHERE year >= 2020 AND year <= 2025
    ORDER BY year, month, title
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"[INFO] 纵横: 获取 {len(df)} 条记录")
    return df


def fetch_qidian_chapters():
    """获取起点章节数据"""
    conn = pymysql.connect(**QIDIAN_CONFIG)
    
    query = """
    SELECT 
        book_title as title,
        chapter_index,
        chapter_title,
        chapter_content
    FROM qidian_chapters
    WHERE chapter_index <= 10
    ORDER BY book_title, chapter_index
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"[INFO] 起点章节: 获取 {len(df)} 条记录")
    return df


def fetch_zongheng_chapters():
    """获取纵横章节数据"""
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    
    query = """
    SELECT 
        title,
        chapter_num as chapter_index,
        chapter_title,
        content as chapter_content
    FROM zongheng_chapters
    WHERE chapter_num <= 10
    ORDER BY title, chapter_num
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"[INFO] 纵横章节: 获取 {len(df)} 条记录")
    return df


def fetch_zongheng_comments():
    """获取纵横评论数据（11万条）"""
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    
    query = """
    SELECT 
        book_id,
        book_title as title,
        content as comment_content,
        ip_region,
        content_length,
        comment_date
    FROM zongheng_book_comments
    WHERE content IS NOT NULL AND content != ''
    ORDER BY book_title, comment_date
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"[INFO] 纵横评论: 获取 {len(df)} 条记录")
    print(f"[INFO] 覆盖书籍: {df['title'].nunique()} 本")
    return df


def extract_chapter_features(chapters_df, book_title):
    """提取章节文本特征"""
    book_chapters = chapters_df[chapters_df['title'] == book_title]
    
    if len(book_chapters) == 0:
        return None
    
    all_content = ' '.join(book_chapters['chapter_content'].fillna('').astype(str))
    all_titles = ' '.join(book_chapters['chapter_title'].fillna('').astype(str))
    
    if not all_content.strip():
        return None
    
    features = {}
    
    # 基础统计
    features['chapter_count'] = len(book_chapters)
    features['avg_chapter_length'] = book_chapters['chapter_content'].str.len().mean()
    features['total_content_length'] = len(all_content)
    
    # 情感分析
    sentiment_score, pos_count, neg_count = analyze_sentiment(all_content)
    features['sentiment_score'] = sentiment_score
    features['positive_word_count'] = pos_count
    features['negative_word_count'] = neg_count
    features['sentiment_ratio'] = pos_count / (neg_count + 1)
    
    # 标题特征
    title_sentiment, title_pos, title_neg = analyze_sentiment(all_titles)
    features['title_sentiment'] = title_sentiment
    features['title_suspense_count'] = sum(1 for t in book_chapters['chapter_title'].fillna('') 
                                           if any(w in str(t) for w in ['？', '！', '...', '悬念', '惊', '秘']))
    
    # 分词统计
    words = list(jieba.cut(all_content))
    words = [w for w in words if len(w) > 1 and w not in STOPWORDS]
    
    features['unique_word_count'] = len(set(words))
    features['total_word_count'] = len(words)
    features['vocabulary_richness'] = features['unique_word_count'] / (features['total_word_count'] + 1)
    
    # 写作风格
    action_words = ['打', '杀', '战', '斗', '冲', '跑', '飞', '跳', '劈', '斩']
    dialog_words = ['说', '道', '问', '答', '喊', '叫']
    scene_words = ['山', '水', '城', '门', '宫', '殿', '林', '海', '天', '地']
    
    features['action_word_ratio'] = sum(1 for w in words if any(aw in w for aw in action_words)) / len(words) if words else 0
    features['dialog_word_ratio'] = sum(1 for w in words if any(dw in w for dw in dialog_words)) / len(words) if words else 0
    features['scene_word_ratio'] = sum(1 for w in words if any(sw in w for sw in scene_words)) / len(words) if words else 0
    
    # 高频词
    word_freq = Counter(words)
    features['top_words'] = [w for w, _ in word_freq.most_common(20)]
    
    return features


def extract_comment_features(comments_df, book_title):
    """提取评论特征（情感和地区）"""
    book_comments = comments_df[comments_df['title'] == book_title]
    
    if len(book_comments) == 0:
        return None
    
    features = {}
    
    # 基础统计
    features['comment_count'] = len(book_comments)
    features['avg_comment_length'] = book_comments['comment_content'].str.len().mean()
    features['total_comment_length'] = book_comments['comment_content'].str.len().sum()
    
    # 合并所有评论内容进行情感分析
    all_comments = ' '.join(book_comments['comment_content'].fillna('').astype(str))
    
    sentiment_score, pos_count, neg_count = analyze_sentiment(all_comments)
    features['comment_sentiment_score'] = sentiment_score
    features['comment_positive_count'] = pos_count
    features['comment_negative_count'] = neg_count
    features['comment_sentiment_ratio'] = pos_count / (neg_count + 1)
    
    # 情感分布（每条评论单独分析）
    individual_sentiments = []
    for _, row in book_comments.iterrows():
        s, _, _ = analyze_sentiment(row['comment_content'])
        individual_sentiments.append(s)
    
    features['comment_sentiment_mean'] = np.mean(individual_sentiments)
    features['comment_sentiment_std'] = np.std(individual_sentiments)
    features['positive_comment_ratio'] = sum(1 for s in individual_sentiments if s > 0.1) / len(individual_sentiments)
    features['negative_comment_ratio'] = sum(1 for s in individual_sentiments if s < -0.1) / len(individual_sentiments)
    
    # 地区分布特征
    regions = book_comments['ip_region'].fillna('未知').tolist()
    region_counts = Counter(regions)
    
    # 一线城市评论数
    tier1_count = sum(region_counts.get(city, 0) for city in TIER1_CITIES)
    # 二线城市评论数
    tier2_count = sum(region_counts.get(city, 0) for city in TIER2_CITIES)
    
    features['tier1_comment_count'] = tier1_count
    features['tier2_comment_count'] = tier2_count
    features['other_region_comment_count'] = len(book_comments) - tier1_count - tier2_count
    
    features['tier1_comment_ratio'] = tier1_count / len(book_comments)
    features['tier2_comment_ratio'] = tier2_count / len(book_comments)
    
    # 地区多样性
    features['region_diversity'] = len(region_counts)
    features['region_entropy'] = -sum((c/len(regions)) * np.log(c/len(regions)) for c in region_counts.values() if c > 0)
    
    # 热门地区Top3
    top_regions = region_counts.most_common(3)
    for i, (region, count) in enumerate(top_regions):
        features[f'top_region_{i+1}'] = region
        features[f'top_region_{i+1}_count'] = count
        features[f'top_region_{i+1}_ratio'] = count / len(book_comments)
    
    return features


def apply_lda_topic_model(all_books_features, n_topics=8):
    """应用LDA主题模型"""
    print(f"[INFO] 开始LDA主题建模 (K={n_topics})...")
    
    documents = []
    book_list = []
    
    for title, features in all_books_features.items():
        if features and 'top_words' in features:
            doc = ' '.join(features['top_words'])
            if doc.strip():
                documents.append(doc)
                book_list.append(title)
    
    if len(documents) < n_topics:
        print(f"[WARN] 文档数量({len(documents)})少于主题数({n_topics})，跳过LDA")
        return {}
    
    vectorizer = TfidfVectorizer(max_features=1000, min_df=2)
    tfidf_matrix = vectorizer.fit_transform(documents)
    
    lda = LatentDirichletAllocation(
        n_components=n_topics,
        random_state=42,
        max_iter=20,
        learning_method='online'
    )
    
    lda_matrix = lda.fit_transform(tfidf_matrix)
    
    topic_features = {}
    for i, title in enumerate(book_list):
        topic_features[title] = {f'topic_{j}': lda_matrix[i][j] for j in range(n_topics)}
        topic_features[title]['dominant_topic'] = np.argmax(lda_matrix[i])
    
    print(f"[INFO] LDA主题建模完成，共{len(topic_features)}本书")
    return topic_features


def engineer_features_with_nlp_and_comments(qidian_df, zongheng_df, 
                                            qidian_chapters, zongheng_chapters,
                                            zongheng_comments):
    """工程化所有特征：数值+NLP+评论"""
    print("[INFO] 开始特征工程（数值+NLP+评论）...")
    
    # 提取章节NLP特征
    print("[INFO] 提取起点章节NLP特征...")
    qidian_text_features = {}
    for book in qidian_chapters['title'].unique():
        features = extract_chapter_features(qidian_chapters, book)
        if features:
            qidian_text_features[book] = features
    print(f"[INFO] 起点: {len(qidian_text_features)}本书提取了NLP特征")
    
    print("[INFO] 提取纵横章节NLP特征...")
    zongheng_text_features = {}
    for book in zongheng_chapters['title'].unique():
        features = extract_chapter_features(zongheng_chapters, book)
        if features:
            zongheng_text_features[book] = features
    print(f"[INFO] 纵横: {len(zongheng_text_features)}本书提取了NLP特征")
    
    # 提取纵横评论特征
    print("[INFO] 提取纵横评论特征（11万条评论）...")
    zongheng_comment_features = {}
    comment_covered_books = zongheng_comments['title'].nunique()
    for book in zongheng_comments['title'].unique():
        features = extract_comment_features(zongheng_comments, book)
        if features:
            zongheng_comment_features[book] = features
    print(f"[INFO] 纵横评论: {len(zongheng_comment_features)}本书提取了评论特征")
    print(f"[INFO] 评论覆盖: {comment_covered_books}本，覆盖率: {len(zongheng_comment_features)/comment_covered_books*100:.1f}%")
    
    # 合并所有文本特征用于LDA
    all_text_features = {**qidian_text_features, **zongheng_text_features}
    
    # 应用LDA主题模型
    topic_features = apply_lda_topic_model(all_text_features, n_topics=8)
    
    # 合并LDA特征
    for book, features in all_text_features.items():
        if book in topic_features:
            features.update(topic_features[book])
    
    # 合并评论特征到纵横书籍
    for book, features in zongheng_comment_features.items():
        if book in zongheng_text_features:
            zongheng_text_features[book].update(features)
        else:
            zongheng_text_features[book] = features
    
    # 标记平台并合并
    qidian_df['is_qidian'] = 1
    zongheng_df['is_qidian'] = 0
    
    # 统一列名
    qidian_df = qidian_df.rename(columns={
        'recommendation_count': 'total_recommend',
        'bang_count': 'reward_count'
    })
    
    zongheng_df = zongheng_df.rename(columns={
        'contribution_value': 'reward_count',
        'total_recommend': 'total_recommend'
    })
    
    for col in ['collection_count', 'total_click', 'total_recommend', 'weekly_recommend',
                'reward_count', 'is_signed', 'intro', 'completion_status']:
        if col not in qidian_df.columns:
            qidian_df[col] = 0 if col != 'intro' else ''
        if col not in zongheng_df.columns:
            zongheng_df[col] = 0 if col != 'intro' else ''
    
    df = pd.concat([qidian_df, zongheng_df], ignore_index=True)
    
    print(f"[INFO] 合并后数据: {len(df)}条记录")
    
    # 添加NLP特征列
    nlp_feature_cols = [
        'chapter_count', 'avg_chapter_length', 'total_content_length',
        'sentiment_score', 'positive_word_count', 'negative_word_count', 'sentiment_ratio',
        'title_sentiment', 'title_suspense_count',
        'unique_word_count', 'total_word_count', 'vocabulary_richness',
        'action_word_ratio', 'dialog_word_ratio', 'scene_word_ratio',
        'dominant_topic', 'topic_0', 'topic_1', 'topic_2', 'topic_3',
        'topic_4', 'topic_5', 'topic_6', 'topic_7'
    ]
    
    # 添加评论特征列
    comment_feature_cols = [
        'comment_count', 'avg_comment_length', 'total_comment_length',
        'comment_sentiment_score', 'comment_positive_count', 'comment_negative_count',
        'comment_sentiment_ratio', 'comment_sentiment_mean', 'comment_sentiment_std',
        'positive_comment_ratio', 'negative_comment_ratio',
        'tier1_comment_count', 'tier2_comment_count', 'other_region_comment_count',
        'tier1_comment_ratio', 'tier2_comment_ratio',
        'region_diversity', 'region_entropy',
        'top_region_1_count', 'top_region_1_ratio',
        'top_region_2_count', 'top_region_2_ratio',
        'top_region_3_count', 'top_region_3_ratio'
    ]
    
    all_new_cols = nlp_feature_cols + comment_feature_cols
    for col in all_new_cols:
        df[col] = 0.0
    
    # 填充起点NLP特征
    for book, features in qidian_text_features.items():
        mask = (df['title'] == book) & (df['is_qidian'] == 1)
        for col in nlp_feature_cols:
            if col in features:
                df.loc[mask, col] = features[col]
    
    # 填充纵横NLP+评论特征
    for book, features in zongheng_text_features.items():
        mask = (df['title'] == book) & (df['is_qidian'] == 0)
        for col in all_new_cols:
            if col in features:
                df.loc[mask, col] = features[col]
    
    # 原有的41个数值特征
    print("[INFO] 应用原有41个数值特征...")
    
    df['log_word_count'] = np.log1p(df['word_count'].fillna(0))
    df['log_collection'] = np.log1p(df.get('collection_count', pd.Series([0]*len(df))).fillna(0))
    df['log_click'] = np.log1p(df.get('total_click', pd.Series([0]*len(df))).fillna(0))
    df['log_recommend'] = np.log1p(df['total_recommend'].fillna(0))
    
    df['quarter'] = ((df['month'] - 1) // 3 + 1).astype(int)
    df['is_year_end'] = (df['month'].isin([11, 12])).astype(int)
    df['is_year_start'] = (df['month'].isin([1, 2])).astype(int)
    df['is_summer'] = (df['month'].isin([7, 8])).astype(int)
    
    df['is_vip'] = df.get('is_vip', pd.Series(['0']*len(df))).apply(
        lambda x: 1 if str(x).upper() in ['VIP', '1', 'TRUE', 'YES'] else 0
    )
    df['is_signed'] = df.get('is_signed', pd.Series(['0']*len(df))).apply(
        lambda x: 1 if str(x).upper() in ['已签约', '1', 'TRUE', 'YES', 'SIGNED'] else 0
    )
    
    le_category = LabelEncoder()
    df['category_code'] = le_category.fit_transform(df['category'].fillna('未知'))
    
    df['is_completed'] = df.get('completion_status', df.get('status', pd.Series(['']*len(df)))).apply(
        lambda x: 1 if isinstance(x, str) and '完结' in x else 0
    )
    
    df = df.sort_values(['title', 'year', 'month'])
    df['months_since_start'] = df.groupby('title').cumcount()
    df['is_new_book'] = (df['months_since_start'] <= 3).astype(int)
    df['is_mature'] = (df['months_since_start'] >= 12).astype(int)
    df['is_long_running'] = (df['months_since_start'] >= 24).astype(int)
    
    df['hist_tickets_mean'] = df.groupby('title')['monthly_tickets'].transform(
        lambda x: x.shift(1).expanding().mean()
    ).fillna(df['monthly_tickets'].mean())
    
    df['hist_tickets_max'] = df.groupby('title')['monthly_tickets'].transform(
        lambda x: x.shift(1).expanding().max()
    ).fillna(df['monthly_tickets'].max())
    
    df['hist_collection_mean'] = df.groupby('title')['collection_count'].transform(
        lambda x: x.shift(1).expanding().mean()
    ).fillna(0)
    
    df['tickets_ma3'] = df.groupby('title')['monthly_tickets'].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    ).fillna(df['hist_tickets_mean'])
    
    df['tickets_ma6'] = df.groupby('title')['monthly_tickets'].transform(
        lambda x: x.shift(1).rolling(6, min_periods=1).mean()
    ).fillna(df['hist_tickets_mean'])
    
    df['tickets_ma12'] = df.groupby('title')['monthly_tickets'].transform(
        lambda x: x.shift(1).rolling(12, min_periods=1).mean()
    ).fillna(df['hist_tickets_mean'])
    
    df['last_month_tickets'] = df.groupby('title')['monthly_tickets'].shift(1).fillna(df['hist_tickets_mean'])
    df['last_month_rank'] = df.groupby('title')['monthly_ticket_rank'].shift(1).fillna(999)
    df['last_month_collection'] = df.groupby('title')['collection_count'].shift(1).fillna(0)
    
    df['tickets_mom'] = (df['monthly_tickets'] - df['last_month_tickets']) / (df['last_month_tickets'] + 1)
    df['rank_change'] = df['last_month_rank'] - df['monthly_ticket_rank']
    df['rank_inverse'] = 1.0 / (df['monthly_ticket_rank'] + 1)
    
    df['tickets_per_word'] = df['monthly_tickets'] / (df['word_count'] / 10000 + 1)
    df['collection_per_word'] = df['collection_count'] / (df['word_count'] / 10000 + 1)
    df['recommend_per_collection'] = df['total_recommend'] / (df['collection_count'] + 1)
    
    df['has_contribution'] = (df.get('reward_count', pd.Series([0]*len(df))) > 0).astype(int)
    df['has_fans'] = (df.get('fan_count', pd.Series([0]*len(df))) > 0).astype(int)
    df['has_posts'] = (df.get('post_count', pd.Series([0]*len(df))) > 0).astype(int)
    df['community_score'] = np.log1p(df.get('fan_count', pd.Series([0]*len(df)))) + np.log1p(df.get('post_count', pd.Series([0]*len(df))))
    
    df['update_freq_calculated'] = 1.0
    df['has_adaptation'] = df.get('adaptation_info', pd.Series(['']*len(df))).apply(
        lambda x: 0 if pd.isna(x) or str(x).strip() == '' or str(x) == 'nan' else 1
    )
    
    print(f"[INFO] 特征工程完成，总特征数: {len([c for c in df.columns if c not in ['title', 'author', 'category', 'intro']])}")
    
    return df, list(le_category.classes_)


def train_model_with_comments():
    """训练融合评论特征的模型"""
    print("\n" + "="*70)
    print("融合评论特征的月票预测模型训练 (v4.0)")
    print("="*70)
    
    # 1. 获取数据
    print("\n[Step 1] 获取月度统计数据...")
    qidian_df = fetch_qidian_full_data()
    zongheng_df = fetch_zongheng_full_data()
    
    print("\n[Step 2] 获取章节文本数据...")
    qidian_chapters = fetch_qidian_chapters()
    zongheng_chapters = fetch_zongheng_chapters()
    
    print("\n[Step 3] 获取纵横评论数据...")
    zongheng_comments = fetch_zongheng_comments()
    
    # 2. 特征工程
    print("\n[Step 4] 特征工程（数值+NLP+评论）...")
    df, categories = engineer_features_with_nlp_and_comments(
        qidian_df, zongheng_df, 
        qidian_chapters, zongheng_chapters,
        zongheng_comments
    )
    
    # 3. 数据划分
    print("\n[Step 5] 时间序列数据划分...")
    train_df = df[(df['year'] >= 2020) & (df['year'] <= 2023)]
    test_df = df[df['year'] == 2024]
    predict_df = df[df['year'] >= 2025]
    
    print(f"  训练集 (2020-2023): {len(train_df)} 条")
    print(f"  测试集 (2024): {len(test_df)} 条")
    print(f"  预测集 (2025+): {len(predict_df)} 条")
    
    # 4. 准备特征
    exclude_cols = ['title', 'author', 'category', 'intro', 'monthly_tickets', 
                    'year', 'month', 'status', 'completion_status', 'latest_chapter',
                    'latest_update_time', 'adaptation_info', 'update_frequency',
                    'chapter_frequency', 'is_qidian', 'top_region_1', 'top_region_2', 'top_region_3']
    
    feature_cols = [c for c in train_df.columns if c not in exclude_cols 
                    and train_df[c].dtype in ['int64', 'float64', 'int32', 'float32']]
    
    for col in feature_cols:
        train_df[col] = train_df[col].fillna(0)
        test_df[col] = test_df[col].fillna(0)
    
    X_train = train_df[feature_cols].values
    y_train = train_df['monthly_tickets'].values
    X_test = test_df[feature_cols].values
    y_test = test_df['monthly_tickets'].values
    
    # 清理无效值
    train_valid_mask = np.isfinite(y_train) & (y_train >= 0)
    test_valid_mask = np.isfinite(y_test) & (y_test >= 0)
    
    X_train = X_train[train_valid_mask]
    y_train = y_train[train_valid_mask]
    X_test = X_test[test_valid_mask]
    y_test = y_test[test_valid_mask]
    
    print(f"  清理后训练集: {len(y_train)} 条")
    print(f"  清理后测试集: {len(y_test)} 条")
    
    # 特征统计
    nlp_count = len([c for c in feature_cols if c.startswith(('topic_', 'sentiment', 'chapter', 'vocabulary', 'action', 'dialog', 'scene', 'title_'))])
    comment_count = len([c for c in feature_cols if c.startswith(('comment_', 'tier', 'region_', 'positive_', 'negative_', 'top_region_'))])
    numeric_count = len(feature_cols) - nlp_count - comment_count
    
    print(f"\n[Step 6] 特征矩阵: {X_train.shape}")
    print(f"  数值特征: {numeric_count}")
    print(f"  NLP特征: {nlp_count}")
    print(f"  评论特征: {comment_count}")
    
    # 5. 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 6. 训练XGBoost
    print("\n[Step 7] 训练XGBoost模型...")
    
    dtrain = xgb.DMatrix(X_train_scaled, label=np.log1p(y_train))
    dtest = xgb.DMatrix(X_test_scaled, label=np.log1p(y_test))
    
    params = {
        'objective': 'reg:squarederror',
        'eval_metric': 'rmse',
        'max_depth': 12,
        'learning_rate': 0.02,
        'subsample': 0.9,
        'colsample_bytree': 0.9,
        'colsample_bylevel': 0.85,
        'min_child_weight': 3,
        'gamma': 0.05,
        'reg_alpha': 0.05,
        'reg_lambda': 0.5,
        'seed': 42
    }
    
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=1000,
        evals=[(dtrain, 'train'), (dtest, 'eval')],
        early_stopping_rounds=50,
        verbose_eval=50
    )
    
    # 7. 评估
    print("\n[Step 8] 模型评估...")
    y_pred_log = model.predict(dtest)
    y_pred = np.expm1(y_pred_log)
    
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    mape = np.mean(np.abs((y_test - y_pred) / (y_test + 1))) * 100
    
    print(f"\n测试结果:")
    print(f"  RMSE: {rmse:.2f}")
    print(f"  MAE: {mae:.2f}")
    print(f"  R²: {r2:.4f}")
    print(f"  MAPE: {mape:.2f}%")
    
    # 8. 特征重要性
    importance = model.get_score(importance_type='gain')
    importance_df = pd.DataFrame([
        {'feature': k, 'importance': v} 
        for k, v in importance.items()
    ]).sort_values('importance', ascending=False)
    
    print("\n[Step 9] Top 30 特征重要性:")
    for i, row in importance_df.head(30).iterrows():
        feature_idx = int(row['feature'][1:]) if row['feature'].startswith('f') else -1
        feature_name = feature_cols[feature_idx] if feature_idx >= 0 else row['feature']
        print(f"  {i+1}. {feature_name}: {row['importance']:.2f}")
    
    # 9. 保存模型
    print("\n[Step 10] 保存模型...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = "resources/models"
    os.makedirs(model_dir, exist_ok=True)
    
    model_file = f"{model_dir}/ticket_comments_enhanced_{timestamp}.pkl"
    joblib.dump({
        'model': model,
        'scaler': scaler,
        'feature_names': feature_cols,
        'categories': categories
    }, model_file)
    
    joblib.dump({
        'model': model,
        'scaler': scaler,
        'feature_names': feature_cols,
        'categories': categories
    }, f"{model_dir}/xgboost_model.pkl")
    
    print(f"  模型保存: {model_file}")
    print(f"  默认模型: {model_dir}/xgboost_model.pkl")
    
    print("\n" + "="*70)
    print("训练完成!")
    print("="*70)
    print(f"总特征数: {len(feature_cols)} (数值+NLP+评论)")
    print(f"测试MAPE: {mape:.2f}%")
    print(f"测试R²: {r2:.4f}")
    
    return model, scaler, feature_cols, importance_df


if __name__ == "__main__":
    train_model_with_comments()
