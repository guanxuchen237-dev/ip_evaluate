"""
融合NLP特征的月票预测模型训练脚本
整合章节情感分析、LDA主题模型、TF-IDF文本特征
"""
import pandas as pd
import numpy as np
import pymysql
import xgboost as xgb
import jieba
import re
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
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


def get_sentiment_dict():
    """加载情感词典"""
    # 正面情感词
    positive_words = set([
        '喜欢', '爱', '棒', '精彩', '优秀', '好', '强', '厉害', '牛', '赞', '神', '无敌',
        '热血', '激动', '爽', '燃', '震撼', '感动', '泪目', '哭', '笑', '开心', '快乐',
        '幸福', '美', '帅', '酷', '霸气', '威武', '英雄', '传奇', '神话', '巅峰', '至尊',
        '绝世', '超神', '逆天', '无敌', '最强', '第一', '王者', '帝王', '主宰', '至尊'
    ])
    
    # 负面情感词
    negative_words = set([
        '讨厌', '恨', '差', '烂', '垃圾', '坏', '弱', '菜', '坑', '毒', '屎', '粪',
        '悲伤', '痛苦', '绝望', '死', '杀', '血', '泪', '伤', '痛', '苦', '难', '惨',
        '悲剧', '失败', '输', '败', '落', '沉', '暗', '黑', '阴', '邪', '魔', '鬼',
        '妖', '怪', '恐', '怕', '惊', '吓', '慌', '急', '怒', '气', '愤', '怨'
    ])
    
    return positive_words, negative_words


def analyze_sentiment(text):
    """分析文本情感得分 (-1 到 1)"""
    if not text or pd.isna(text):
        return 0.0, 0, 0
    
    positive_words, negative_words = get_sentiment_dict()
    
    # 分词
    words = list(jieba.cut(str(text)))
    
    pos_count = sum(1 for w in words if w in positive_words)
    neg_count = sum(1 for w in words if w in negative_words)
    total = len(words)
    
    if total == 0:
        return 0.0, 0, 0
    
    # 计算情感得分
    sentiment_score = (pos_count - neg_count) / total
    
    return sentiment_score, pos_count, neg_count


def fetch_qidian_full_data():
    """获取起点完整数据（含所有字段）"""
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
    """获取纵横完整数据（含所有字段）"""
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
    """获取起点章节内容数据"""
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
    """获取纵横章节内容数据"""
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


def extract_text_features_for_book(chapters_df, book_title):
    """为一本书提取文本特征"""
    book_chapters = chapters_df[chapters_df['title'] == book_title]
    
    if len(book_chapters) == 0:
        return None
    
    # 合并所有章节内容
    all_content = ' '.join(book_chapters['chapter_content'].fillna('').astype(str))
    all_titles = ' '.join(book_chapters['chapter_title'].fillna('').astype(str))
    
    if not all_content.strip():
        return None
    
    features = {}
    
    # 1. 基础统计特征
    features['chapter_count'] = len(book_chapters)
    features['avg_chapter_length'] = book_chapters['chapter_content'].str.len().mean()
    features['total_content_length'] = len(all_content)
    
    # 2. 情感分析特征
    sentiment_score, pos_count, neg_count = analyze_sentiment(all_content)
    features['sentiment_score'] = sentiment_score
    features['positive_word_count'] = pos_count
    features['negative_word_count'] = neg_count
    features['sentiment_ratio'] = pos_count / (neg_count + 1)
    
    # 3. 章节标题特征
    title_sentiment, title_pos, title_neg = analyze_sentiment(all_titles)
    features['title_sentiment'] = title_sentiment
    features['title_suspense_count'] = sum(1 for t in book_chapters['chapter_title'].fillna('') 
                                           if any(w in str(t) for w in ['？', '！', '...', '悬念']))
    
    # 4. 分词和词频
    words = list(jieba.cut(all_content))
    words = [w for w in words if len(w) > 1 and w not in STOPWORDS]
    
    features['unique_word_count'] = len(set(words))
    features['total_word_count'] = len(words)
    features['vocabulary_richness'] = features['unique_word_count'] / (features['total_word_count'] + 1)
    
    # 5. 高频词统计（用于后续LDA）
    word_freq = Counter(words)
    features['top_words'] = [w for w, _ in word_freq.most_common(20)]
    
    # 6. 动作/对话/场景词识别
    action_words = ['打', '杀', '战', '斗', '冲', '跑', '飞', '跳', '劈', '斩']
    dialog_words = ['说', '道', '问', '答', '喊', '叫']
    scene_words = ['山', '水', '城', '门', '宫', '殿', '林', '海', '天', '地']
    
    features['action_word_ratio'] = sum(1 for w in words if any(aw in w for aw in action_words)) / len(words) if words else 0
    features['dialog_word_ratio'] = sum(1 for w in words if any(dw in w for dw in dialog_words)) / len(words) if words else 0
    features['scene_word_ratio'] = sum(1 for w in words if any(sw in w for sw in scene_words)) / len(words) if words else 0
    
    return features


def apply_lda_topic_model(all_books_features, n_topics=8):
    """对所有书籍应用LDA主题模型"""
    print(f"[INFO] 开始LDA主题建模 (K={n_topics})...")
    
    # 准备文档集合
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
    
    # TF-IDF向量化
    vectorizer = TfidfVectorizer(max_features=1000, min_df=2)
    tfidf_matrix = vectorizer.fit_transform(documents)
    
    # LDA主题模型
    lda = LatentDirichletAllocation(
        n_components=n_topics,
        random_state=42,
        max_iter=20,
        learning_method='online'
    )
    
    lda_matrix = lda.fit_transform(tfidf_matrix)
    
    # 为每本书添加主题分布特征
    topic_features = {}
    for i, title in enumerate(book_list):
        topic_features[title] = {f'topic_{j}': lda_matrix[i][j] for j in range(n_topics)}
        topic_features[title]['dominant_topic'] = np.argmax(lda_matrix[i])
    
    print(f"[INFO] LDA主题建模完成，共{len(topic_features)}本书")
    return topic_features


def engineer_features_with_nlp(qidian_df, zongheng_df, qidian_chapters, zongheng_chapters):
    """工程化所有特征，包括NLP特征"""
    print("[INFO] 开始特征工程（含NLP）...")
    
    # 为起点提取文本特征
    print("[INFO] 提取起点章节NLP特征...")
    qidian_text_features = {}
    qidian_books = qidian_chapters['title'].unique()
    for book in qidian_books:
        features = extract_text_features_for_book(qidian_chapters, book)
        if features:
            qidian_text_features[book] = features
    print(f"[INFO] 起点: {len(qidian_text_features)}本书提取了NLP特征")
    
    # 为纵横提取文本特征
    print("[INFO] 提取纵横章节NLP特征...")
    zongheng_text_features = {}
    zongheng_books = zongheng_chapters['title'].unique()
    for book in zongheng_books:
        features = extract_text_features_for_book(zongheng_chapters, book)
        if features:
            zongheng_text_features[book] = features
    print(f"[INFO] 纵横: {len(zongheng_text_features)}本书提取了NLP特征")
    
    # 合并所有文本特征用于LDA
    all_text_features = {**qidian_text_features, **zongheng_text_features}
    
    # 应用LDA主题模型
    topic_features = apply_lda_topic_model(all_text_features, n_topics=8)
    
    # 合并LDA特征到各平台
    for book, features in all_text_features.items():
        if book in topic_features:
            features.update(topic_features[book])
    
    # 标记平台并合并
    qidian_df['is_qidian'] = 1
    zongheng_df['is_qidian'] = 0
    
    # 统一列名
    common_cols = ['year', 'month', 'title', 'author', 'category', 'word_count', 
                   'monthly_tickets', 'monthly_ticket_rank', 'is_qidian']
    
    qidian_df = qidian_df.rename(columns={
        'recommendation_count': 'total_recommend',
        'bang_count': 'reward_count'
    })
    
    zongheng_df = zongheng_df.rename(columns={
        'contribution_value': 'reward_count',
        'total_recommend': 'total_recommend'
    })
    
    # 确保两表有相同列
    for col in ['collection_count', 'total_click', 'total_recommend', 'weekly_recommend',
                'reward_count', 'is_signed', 'intro', 'completion_status']:
        if col not in qidian_df.columns:
            qidian_df[col] = 0 if col != 'intro' else ''
        if col not in zongheng_df.columns:
            zongheng_df[col] = 0 if col != 'intro' else ''
    
    df = pd.concat([qidian_df, zongheng_df], ignore_index=True)
    
    print(f"[INFO] 合并后数据: {len(df)}条记录")
    
    # 添加NLP特征
    print("[INFO] 合并NLP特征到主数据集...")
    
    nlp_feature_cols = [
        'chapter_count', 'avg_chapter_length', 'total_content_length',
        'sentiment_score', 'positive_word_count', 'negative_word_count', 'sentiment_ratio',
        'title_sentiment', 'title_suspense_count',
        'unique_word_count', 'total_word_count', 'vocabulary_richness',
        'action_word_ratio', 'dialog_word_ratio', 'scene_word_ratio',
        'dominant_topic', 'topic_0', 'topic_1', 'topic_2', 'topic_3',
        'topic_4', 'topic_5', 'topic_6', 'topic_7'
    ]
    
    for col in nlp_feature_cols:
        df[col] = 0.0
    
    # 填充起点NLP特征
    for book, features in qidian_text_features.items():
        mask = (df['title'] == book) & (df['is_qidian'] == 1)
        for col in nlp_feature_cols:
            if col in features:
                df.loc[mask, col] = features[col]
    
    # 填充纵横NLP特征
    for book, features in zongheng_text_features.items():
        mask = (df['title'] == book) & (df['is_qidian'] == 0)
        for col in nlp_feature_cols:
            if col in features:
                df.loc[mask, col] = features[col]
    
    # 原有的41个特征工程
    print("[INFO] 应用原有41个数值特征...")
    
    # 对数变换
    df['log_word_count'] = np.log1p(df['word_count'].fillna(0))
    df['log_collection'] = np.log1p(df.get('collection_count', pd.Series([0]*len(df))).fillna(0))
    df['log_click'] = np.log1p(df.get('total_click', pd.Series([0]*len(df))).fillna(0))
    df['log_recommend'] = np.log1p(df['total_recommend'].fillna(0))
    
    # 时间特征
    df['quarter'] = ((df['month'] - 1) // 3 + 1).astype(int)
    df['is_year_end'] = (df['month'].isin([11, 12])).astype(int)
    df['is_year_start'] = (df['month'].isin([1, 2])).astype(int)
    df['is_summer'] = (df['month'].isin([7, 8])).astype(int)
    
    # 处理VIP和签约
    df['is_vip'] = df.get('is_vip', pd.Series(['0']*len(df))).apply(
        lambda x: 1 if str(x).upper() in ['VIP', '1', 'TRUE', 'YES'] else 0
    )
    df['is_signed'] = df.get('is_signed', pd.Series(['0']*len(df))).apply(
        lambda x: 1 if str(x).upper() in ['已签约', '1', 'TRUE', 'YES', 'SIGNED'] else 0
    )
    
    # 类别编码
    le_category = LabelEncoder()
    df['category_code'] = le_category.fit_transform(df['category'].fillna('未知'))
    
    # 完结状态
    df['is_completed'] = df.get('completion_status', df.get('status', pd.Series(['']*len(df)))).apply(
        lambda x: 1 if isinstance(x, str) and '完结' in x else 0
    )
    
    # 书籍生命周期（按分组计算）
    df = df.sort_values(['title', 'year', 'month'])
    df['months_since_start'] = df.groupby('title').cumcount()
    df['is_new_book'] = (df['months_since_start'] <= 3).astype(int)
    df['is_mature'] = (df['months_since_start'] >= 12).astype(int)
    df['is_long_running'] = (df['months_since_start'] >= 24).astype(int)
    
    # 历史统计特征
    df['hist_tickets_mean'] = df.groupby('title')['monthly_tickets'].transform(
        lambda x: x.shift(1).expanding().mean()
    ).fillna(df['monthly_tickets'].mean())
    
    df['hist_tickets_max'] = df.groupby('title')['monthly_tickets'].transform(
        lambda x: x.shift(1).expanding().max()
    ).fillna(df['monthly_tickets'].max())
    
    df['hist_collection_mean'] = df.groupby('title')['collection_count'].transform(
        lambda x: x.shift(1).expanding().mean()
    ).fillna(0)
    
    # 移动平均
    df['tickets_ma3'] = df.groupby('title')['monthly_tickets'].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    ).fillna(df['hist_tickets_mean'])
    
    df['tickets_ma6'] = df.groupby('title')['monthly_tickets'].transform(
        lambda x: x.shift(1).rolling(6, min_periods=1).mean()
    ).fillna(df['hist_tickets_mean'])
    
    df['tickets_ma12'] = df.groupby('title')['monthly_tickets'].transform(
        lambda x: x.shift(1).rolling(12, min_periods=1).mean()
    ).fillna(df['hist_tickets_mean'])
    
    # 近期趋势
    df['last_month_tickets'] = df.groupby('title')['monthly_tickets'].shift(1).fillna(df['hist_tickets_mean'])
    df['last_month_rank'] = df.groupby('title')['monthly_ticket_rank'].shift(1).fillna(999)
    df['last_month_collection'] = df.groupby('title')['collection_count'].shift(1).fillna(0)
    
    df['tickets_mom'] = (df['monthly_tickets'] - df['last_month_tickets']) / (df['last_month_tickets'] + 1)
    df['rank_change'] = df['last_month_rank'] - df['monthly_ticket_rank']
    df['rank_inverse'] = 1.0 / (df['monthly_ticket_rank'] + 1)
    
    # 比率特征
    df['tickets_per_word'] = df['monthly_tickets'] / (df['word_count'] / 10000 + 1)
    df['collection_per_word'] = df['collection_count'] / (df['word_count'] / 10000 + 1)
    df['recommend_per_collection'] = df['total_recommend'] / (df['collection_count'] + 1)
    
    # 平台特有
    df['has_contribution'] = (df.get('reward_count', pd.Series([0]*len(df))) > 0).astype(int)
    df['has_fans'] = (df.get('fan_count', pd.Series([0]*len(df))) > 0).astype(int)
    df['has_posts'] = (df.get('post_count', pd.Series([0]*len(df))) > 0).astype(int)
    df['community_score'] = np.log1p(df.get('fan_count', pd.Series([0]*len(df)))) + np.log1p(df.get('post_count', pd.Series([0]*len(df))))
    
    # 更新与改编
    df['update_freq_calculated'] = 1.0  # 简化处理
    df['has_adaptation'] = df.get('adaptation_info', pd.Series(['']*len(df))).apply(
        lambda x: 0 if pd.isna(x) or str(x).strip() == '' or str(x) == 'nan' else 1
    )
    
    print(f"[INFO] 特征工程完成，总特征数: {len([c for c in df.columns if c not in ['title', 'author', 'category', 'intro']])}")
    
    return df, list(le_category.classes_)


def train_model_with_nlp():
    """训练融合NLP特征的模型"""
    print("\n" + "="*60)
    print("融合NLP特征的月票预测模型训练")
    print("="*60)
    
    # 1. 获取数据
    print("\n[Step 1] 获取月度统计数据...")
    qidian_df = fetch_qidian_full_data()
    zongheng_df = fetch_zongheng_full_data()
    
    print("\n[Step 2] 获取章节文本数据...")
    qidian_chapters = fetch_qidian_chapters()
    zongheng_chapters = fetch_zongheng_chapters()
    
    # 2. 特征工程
    print("\n[Step 3] 特征工程（数值+NLP）...")
    df, categories = engineer_features_with_nlp(qidian_df, zongheng_df, qidian_chapters, zongheng_chapters)
    
    # 3. 数据划分
    print("\n[Step 4] 时间序列数据划分...")
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
                    'chapter_frequency', 'is_qidian']
    
    feature_cols = [c for c in train_df.columns if c not in exclude_cols 
                    and train_df[c].dtype in ['int64', 'float64', 'int32', 'float32']]
    
    # 填充缺失值
    for col in feature_cols:
        train_df[col] = train_df[col].fillna(0)
        test_df[col] = test_df[col].fillna(0)
    
    X_train = train_df[feature_cols].values
    y_train = train_df['monthly_tickets'].values
    X_test = test_df[feature_cols].values
    y_test = test_df['monthly_tickets'].values
    
    # 清理目标变量中的NaN和无穷大值
    train_valid_mask = np.isfinite(y_train) & (y_train >= 0)
    test_valid_mask = np.isfinite(y_test) & (y_test >= 0)
    
    X_train = X_train[train_valid_mask]
    y_train = y_train[train_valid_mask]
    X_test = X_test[test_valid_mask]
    y_test = y_test[test_valid_mask]
    
    print(f"  清理后训练集: {len(y_train)} 条 (去除{sum(~train_valid_mask)}条无效)")
    print(f"  清理后测试集: {len(y_test)} 条 (去除{sum(~test_valid_mask)}条无效)")
    
    print(f"\n[Step 5] 特征矩阵: {X_train.shape}")
    print(f"  数值特征: {len([c for c in feature_cols if not c.startswith(('topic_', 'sentiment', 'chapter', 'vocabulary', 'action', 'dialog', 'scene', 'title_'))])}")
    print(f"  NLP特征: {len([c for c in feature_cols if c.startswith(('topic_', 'sentiment', 'chapter', 'vocabulary', 'action', 'dialog', 'scene', 'title_'))])}")
    
    # 5. 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 6. 训练XGBoost
    print("\n[Step 6] 训练XGBoost模型...")
    
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
    print("\n[Step 7] 模型评估...")
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
    
    print("\n[Step 8] Top 20 特征重要性:")
    for i, row in importance_df.head(20).iterrows():
        feature_idx = int(row['feature'][1:]) if row['feature'].startswith('f') else -1
        feature_name = feature_cols[feature_idx] if feature_idx >= 0 else row['feature']
        print(f"  {feature_name}: {row['importance']:.2f}")
    
    # 9. 保存模型
    print("\n[Step 9] 保存模型...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = "resources/models"
    os.makedirs(model_dir, exist_ok=True)
    
    model_file = f"{model_dir}/ticket_nlp_enhanced_{timestamp}.pkl"
    joblib.dump({
        'model': model,
        'scaler': scaler,
        'feature_names': feature_cols,
        'categories': categories
    }, model_file)
    
    # 同时保存为默认模型
    joblib.dump({
        'model': model,
        'scaler': scaler,
        'feature_names': feature_cols,
        'categories': categories
    }, f"{model_dir}/xgboost_model.pkl")
    
    print(f"  模型保存: {model_file}")
    print(f"  默认模型: {model_dir}/xgboost_model.pkl")
    
    print("\n" + "="*60)
    print("训练完成!")
    print("="*60)
    print(f"总特征数: {len(feature_cols)} (数值+NLP)")
    print(f"测试MAPE: {mape:.2f}%")
    print(f"测试R²: {r2:.4f}")
    
    return model, scaler, feature_cols, importance_df


if __name__ == "__main__":
    train_model_with_nlp()
