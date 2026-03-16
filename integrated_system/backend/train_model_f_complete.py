"""
Model F - 完整版
融合：Model E的NLP+评论 + 开题报告所有创新点
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
import jieba
import jieba.analyse
from gensim import corpora, models
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
from scipy.stats import entropy
from datetime import datetime
import re
import os

warnings.filterwarnings('ignore')

# 数据库配置
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'qidian_data', 'charset': 'utf8mb4'
}
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

# 停用词
STOPWORDS = set(['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'])

# ================================================================
#  情感词典
# ================================================================
POSITIVE_WORDS = set(['精彩', '优秀', '棒', '好', '喜欢', '爱', '感动', '震撼', '热血', '燃', '爽', '牛', '强', '赞', '推荐', '支持', '加油', '成功', '胜利', '英雄', '强大', '突破', '觉醒', '天才', '神作', '经典', ' masterpiece'])
NEGATIVE_WORDS = set(['差', '烂', '垃圾', '失望', '无聊', '水', '坑', '弃', '毒', '脑残', '弱智', '拖沓', '烂尾', '狗血', '尴尬', '失败', '惨', '死', '悲剧', '垃圾'])
ACTION_WORDS = set(['打', '杀', '战', '斗', '破', '斩', '灭', '冲', '击', '攻', '守', '追', '逃', '怒', '狂', '暴'])
DIALOGUE_WORDS = set(['说', '道', '问', '答', '喊', '叫', '笑', '哭', '骂', '叹', '嗯', '哦', '啊', '呢', '吧', '吗'])

# ================================================================
#  1. 完整数据获取（含NLP、评论、改编标签）
# ================================================================

def fetch_complete_data():
    """获取完整数据，包括改编标签"""
    print("\n" + "="*70)
    print("获取完整数据")
    print("="*70)
    
    # 起点数据
    conn_qd = pymysql.connect(**QIDIAN_CONFIG)
    sql_qd = """
    SELECT year, month, title, author, category, word_count,
           collection_count, monthly_tickets_on_list as monthly_tickets,
           monthly_ticket_count, rank_on_list as monthly_ticket_rank,
           recommendation_count as total_recommend,
           week_recommendation_count as weekly_recommend,
           COALESCE(adaptations, '') as adaptations,
           reward_count, updated_at, synopsis as abstract
    FROM novel_monthly_stats
    WHERE year >= 2020
    """
    df_qd = pd.read_sql(sql_qd, conn_qd)
    df_qd['platform'] = 'Qidian'
    conn_qd.close()
    print(f"起点数据: {len(df_qd)} 条")
    
    # 纵横数据
    conn_zh = pymysql.connect(**ZONGHENG_CONFIG)
    sql_zh = """
    SELECT year, month, title, author, category, word_count,
           total_click as collection_count, monthly_ticket as monthly_tickets,
           total_rec as total_recommend,
           week_rec as weekly_recommend,
           '' as adaptations,
           fan_count as reward_count, updated_at, abstract
    FROM zongheng_book_ranks
    WHERE year >= 2020
    """
    df_zh = pd.read_sql(sql_zh, conn_zh)
    df_zh['platform'] = 'Zongheng'
    conn_zh.close()
    print(f"纵横数据: {len(df_zh)} 条")
    
    # 合并
    df = pd.concat([df_qd, df_zh], ignore_index=True)
    
    # 处理改编标签
    df['has_adaptation'] = df['adaptations'].apply(lambda x: 1 if x and len(str(x)) > 3 else 0)
    df['adaptation_count'] = df['adaptations'].apply(lambda x: len(str(x).split(',')) if x and str(x) != 'nan' else 0)
    
    print(f"总数据: {len(df)} 条")
    print(f"有改编: {df['has_adaptation'].sum()} 本")
    
    return df

def fetch_chapter_data():
    """获取章节NLP数据"""
    print("\n获取章节NLP数据...")
    
    chapters_data = {}
    
    # 起点章节
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT book_title, chapter_content 
                FROM qidian_chapters 
                WHERE chapter_number <= 10
            """)
            for row in cur.fetchall():
                title = row['book_title']
                if title not in chapters_data:
                    chapters_data[title] = {'content': '', 'count': 0}
                chapters_data[title]['content'] += ' ' + str(row['chapter_content'])
                chapters_data[title]['count'] += 1
        conn.close()
        print(f"  起点章节: {len(chapters_data)} 本")
    except Exception as e:
        print(f"  起点章节获取失败: {e}")
    
    # 纵横章节
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT book_title, chapter_content 
                FROM zongheng_chapters 
                WHERE chapter_number <= 10
            """)
            for row in cur.fetchall():
                title = row['book_title']
                if title not in chapters_data:
                    chapters_data[title] = {'content': '', 'count': 0}
                chapters_data[title]['content'] += ' ' + str(row['chapter_content'])
                chapters_data[title]['count'] += 1
        conn.close()
        print(f"  纵横章节: {len(chapters_data)} 本")
    except Exception as e:
        print(f"  纵横章节获取失败: {e}")
    
    return chapters_data

def fetch_comment_data():
    """获取纵横评论数据"""
    print("\n获取评论数据...")
    
    comments_data = {}
    
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT book_title, content, ip_region 
                FROM zongheng_book_comments
            """)
            for row in cur.fetchall():
                title = row['book_title']
                if title not in comments_data:
                    comments_data[title] = {'comments': [], 'regions': []}
                comments_data[title]['comments'].append(str(row['content']))
                if row['ip_region']:
                    comments_data[title]['regions'].append(row['ip_region'])
        conn.close()
        print(f"  评论数据: {len(comments_data)} 本")
    except Exception as e:
        print(f"  评论获取失败: {e}")
    
    return comments_data

# ================================================================
#  2. NLP特征工程
# ================================================================

def extract_nlp_features(df, chapters_data):
    """提取NLP特征"""
    print("\n提取NLP特征...")
    
    nlp_features = []
    
    for _, row in df.iterrows():
        title = row['title']
        features = {}
        
        if title in chapters_data:
            content = chapters_data[title]['content']
            
            # 基础文本统计
            words = list(jieba.cut(content))
            features['word_count'] = len(words)
            unique_words = set(words)
            features['unique_word_count'] = len(unique_words)
            features['vocabulary_richness'] = len(unique_words) / (len(words) + 1)
            
            # 情感分析
            pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
            neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
            features['sentiment_score'] = (pos_count - neg_count) / (len(words) + 1)
            features['positive_word_count'] = pos_count
            features['negative_word_count'] = neg_count
            features['sentiment_ratio'] = pos_count / (neg_count + 1)
            
            # 写作风格
            action_count = sum(1 for w in words if w in ACTION_WORDS)
            dialogue_count = sum(1 for w in words if w in DIALOGUE_WORDS)
            features['action_word_ratio'] = action_count / (len(words) + 1)
            features['dialog_word_ratio'] = dialogue_count / (len(words) + 1)
            features['scene_word_ratio'] = 1 - features['dialog_word_ratio']
            
            # 标题情感
            abstract = str(row.get('abstract', ''))
            abs_words = list(jieba.cut(abstract))
            features['title_sentiment'] = sum(1 for w in abs_words if w in POSITIVE_WORDS) / (len(abs_words) + 1)
            features['title_suspense_count'] = sum(1 for w in abs_words if w in ['谜', '秘', '疑', '悬念', '真相'])
        else:
            # 无章节数据，填充0
            features = {
                'word_count': 0, 'unique_word_count': 0, 'vocabulary_richness': 0,
                'sentiment_score': 0, 'positive_word_count': 0, 'negative_word_count': 0,
                'sentiment_ratio': 1, 'action_word_ratio': 0, 'dialog_word_ratio': 0,
                'scene_word_ratio': 0, 'title_sentiment': 0, 'title_suspense_count': 0
            }
        
        nlp_features.append(features)
    
    df_nlp = pd.DataFrame(nlp_features)
    df = pd.concat([df.reset_index(drop=True), df_nlp], axis=1)
    
    print(f"NLP特征提取完成: {df_nlp.shape[1]} 个特征")
    return df

# ================================================================
#  3. 评论特征工程
# ================================================================

def extract_comment_features(df, comments_data):
    """提取评论特征"""
    print("\n提取评论特征...")
    
    # 一线城市列表
    TIER1_CITIES = ['北京', '上海', '广州', '深圳', '成都', '杭州', '武汉', '西安', '南京', '天津']
    TIER2_CITIES = ['重庆', '苏州', '长沙', '郑州', '东莞', '青岛', '宁波', '佛山', '合肥', '福州']
    
    comment_features = []
    
    for _, row in df.iterrows():
        title = row['title']
        features = {}
        
        if title in comments_data:
            comments = comments_data[title]['comments']
            regions = comments_data[title]['regions']
            
            # 基础统计
            features['comment_count'] = len(comments)
            features['avg_comment_length'] = np.mean([len(c) for c in comments]) if comments else 0
            features['total_comment_length'] = sum([len(c) for c in comments])
            
            # 情感分析
            pos_count = sum(1 for c in comments for w in jieba.cut(c) if w in POSITIVE_WORDS)
            neg_count = sum(1 for c in comments for w in jieba.cut(c) if w in NEGATIVE_WORDS)
            features['comment_sentiment_score'] = (pos_count - neg_count) / (len(comments) + 1)
            features['comment_positive_count'] = pos_count
            features['comment_negative_count'] = neg_count
            features['positive_comment_ratio'] = pos_count / (len(comments) + 1)
            features['negative_comment_ratio'] = neg_count / (len(comments) + 1)
            
            # 地区分布
            tier1_count = sum(1 for r in regions if any(city in r for city in TIER1_CITIES))
            tier2_count = sum(1 for r in regions if any(city in r for city in TIER2_CITIES))
            features['tier1_comment_count'] = tier1_count
            features['tier2_comment_count'] = tier2_count
            features['other_region_comment_count'] = len(regions) - tier1_count - tier2_count
            features['tier1_comment_ratio'] = tier1_count / (len(regions) + 1)
            features['tier2_comment_ratio'] = tier2_count / (len(regions) + 1)
            
            # 地区多样性
            unique_regions = len(set(regions))
            features['region_diversity'] = unique_regions
            if len(regions) > 1:
                region_counts = pd.Series(regions).value_counts()
                probs = region_counts / region_counts.sum()
                features['region_entropy'] = entropy(probs, base=2)
            else:
                features['region_entropy'] = 0
        else:
            # 无评论数据，填充0
            features = {
                'comment_count': 0, 'avg_comment_length': 0, 'total_comment_length': 0,
                'comment_sentiment_score': 0, 'comment_positive_count': 0, 'comment_negative_count': 0,
                'positive_comment_ratio': 0, 'negative_comment_ratio': 0,
                'tier1_comment_count': 0, 'tier2_comment_count': 0, 'other_region_comment_count': 0,
                'tier1_comment_ratio': 0, 'tier2_comment_ratio': 0,
                'region_diversity': 0, 'region_entropy': 0
            }
        
        comment_features.append(features)
    
    df_comment = pd.DataFrame(comment_features)
    df = pd.concat([df.reset_index(drop=True), df_comment], axis=1)
    
    print(f"评论特征提取完成: {df_comment.shape[1]} 个特征")
    return df

# ================================================================
#  4. 更新熵特征（开题报告创新点2）
# ================================================================

def calculate_update_entropy(df):
    """计算更新熵 - 量化作者履约稳定性"""
    print("\n计算更新熵特征...")
    
    def calc_entropy_for_book(group):
        group = group.sort_values(['year', 'month'])
        word_diff = group['word_count'].diff().fillna(0)
        
        update_volumes = word_diff[word_diff > 0].values
        
        if len(update_volumes) > 1:
            total = update_volumes.sum()
            if total > 0:
                probs = update_volumes / total
                update_entropy = entropy(probs, base=2)
            else:
                update_entropy = 0
            
            mean_update = update_volumes.mean()
            std_update = update_volumes.std() if len(update_volumes) > 1 else 0
            update_regularity = std_update / (mean_update + 1)
            
            drop_months = (word_diff == 0).sum()
            
            consecutive = 0
            max_consecutive = 0
            for diff in word_diff:
                if diff > 0:
                    consecutive += 1
                    max_consecutive = max(max_consecutive, consecutive)
                else:
                    consecutive = 0
        else:
            update_entropy = 0
            update_regularity = 0
            drop_months = 0
            max_consecutive = 0
            mean_update = 0
        
        return pd.Series({
            'update_entropy': update_entropy,
            'update_regularity': update_regularity,
            'drop_month_count': drop_months,
            'max_consecutive_months': max_consecutive,
            'avg_monthly_update': mean_update
        })
    
    entropy_features = df.groupby(['title', 'platform']).apply(calc_entropy_for_book).reset_index()
    df = df.merge(entropy_features, on=['title', 'platform'], how='left')
    
    for col in ['update_entropy', 'update_regularity', 'drop_month_count', 
                'max_consecutive_months', 'avg_monthly_update']:
        df[col] = df[col].fillna(0)
    
    print(f"更新熵计算完成: 平均={df['update_entropy'].mean():.2f}")
    return df

# ================================================================
#  5. 粉丝购买力指数（开题报告创新点1补充）
# ================================================================

def calculate_purchasing_power_index(df):
    """计算粉丝购买力指数"""
    print("\n计算购买力指数...")
    
    def calc_ppi(row):
        if row['platform'] == 'Qidian':
            pay_willingness = row['reward_count'] / (row['collection_count'] + 1)
        else:
            pay_willingness = row['reward_count'] / (row['collection_count'] + 1)
        
        quality_ratio = row['total_recommend'] / (row['collection_count'] + 1)
        
        ppi = (np.log1p(pay_willingness * 100) * 30 + 
               np.log1p(quality_ratio) * 20 + 
               min(50, row['monthly_tickets'] / 1000))
        
        return min(100, max(0, ppi))
    
    df['purchasing_power_index'] = df.apply(calc_ppi, axis=1)
    print(f"购买力指数计算完成: 平均={df['purchasing_power_index'].mean():.2f}")
    return df

# ================================================================
#  6. 完整特征工程
# ================================================================

def engineer_all_features(df):
    """完整的特征工程"""
    print("\n" + "="*70)
    print("完整特征工程")
    print("="*70)
    
    # 基础数值特征
    print("1. 基础数值特征...")
    df['log_word_count'] = np.log1p(df['word_count'])
    df['log_collection'] = np.log1p(df['collection_count'])
    df['log_recommend'] = np.log1p(df['total_recommend'])
    df['log_monthly_tickets'] = np.log1p(df['monthly_tickets'])
    df['recommend_per_collection'] = df['total_recommend'] / (df['collection_count'] + 1)
    df['tickets_per_word'] = df['monthly_tickets'] / (df['word_count'] + 1) * 10000
    
    # 时间特征
    print("2. 时间特征...")
    df['year_month'] = df['year'] * 12 + df['month']
    df['quarter'] = df['month'].apply(lambda x: (x-1)//3 + 1)
    df['is_year_end'] = (df['month'] == 12).astype(int)
    df['is_year_start'] = (df['month'] == 1).astype(int)
    
    start_dates = df.groupby(['title', 'platform'])['year_month'].transform('min')
    df['months_since_start'] = df['year_month'] - start_dates
    df['is_new_book'] = (df['months_since_start'] < 6).astype(int)
    df['is_mature'] = ((df['months_since_start'] >= 6) & (df['months_since_start'] < 24)).astype(int)
    df['is_long_running'] = (df['months_since_start'] >= 24).astype(int)
    
    # 时序特征
    print("3. 时序特征...")
    df = df.sort_values(['title', 'platform', 'year', 'month'])
    df['tickets_mom'] = df.groupby(['title', 'platform'])['monthly_tickets'].pct_change().fillna(0).replace([np.inf, -np.inf], 0)
    df['tickets_ma3'] = df.groupby(['title', 'platform'])['monthly_tickets'].transform(lambda x: x.rolling(3, min_periods=1).mean())
    df['tickets_ma6'] = df.groupby(['title', 'platform'])['monthly_tickets'].transform(lambda x: x.rolling(6, min_periods=1).mean())
    
    # 更新熵
    print("4. 更新熵...")
    df = calculate_update_entropy(df)
    
    # 购买力指数
    print("5. 购买力指数...")
    df = calculate_purchasing_power_index(df)
    
    print(f"\n特征工程完成，总特征数: {len(df.columns)}")
    return df

# ================================================================
#  7. IP基因K-Means聚类（开题报告创新点3）
# ================================================================

class IPGeneClustering:
    """IP基因聚类"""
    
    def __init__(self, n_clusters=5):
        self.n_clusters = n_clusters
        self.kmeans = None
        self.scaler = StandardScaler()
        
    def fit(self, df):
        """基于成功作品训练"""
        print("\n训练IP基因聚类...")
        
        success_mask = (df['monthly_tickets'] > 10000) | (df['has_adaptation'] == 1)
        success_books = df[success_mask].copy()
        
        if len(success_books) < self.n_clusters * 2:
            success_mask = df['monthly_tickets'] > 5000
            success_books = df[success_mask].copy()
        
        print(f"成功作品: {len(success_books)} 本")
        
        features = ['word_count', 'monthly_tickets', 'total_recommend',
                   'update_regularity', 'purchasing_power_index', 'has_adaptation']
        available_features = [f for f in features if f in success_books.columns]
        
        X = success_books[available_features].fillna(0)
        X_scaled = self.scaler.fit_transform(X)
        
        self.kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        success_books['ip_gene_cluster'] = self.kmeans.fit_predict(X_scaled)
        
        print(f"聚类分布:\n{success_books['ip_gene_cluster'].value_counts().sort_index()}")
        return self
    
    def predict_similarity(self, df):
        """计算相似度"""
        print("\n计算IP基因相似度...")
        
        features = ['word_count', 'monthly_tickets', 'total_recommend',
                   'update_regularity', 'purchasing_power_index', 'has_adaptation']
        available_features = [f for f in features if f in df.columns]
        
        X = df[available_features].fillna(0)
        X_scaled = self.scaler.transform(X)
        
        cluster_ids = self.kmeans.predict(X_scaled)
        df['ip_gene_cluster'] = cluster_ids
        
        similarities = []
        for i, x in enumerate(X_scaled):
            center = self.kmeans.cluster_centers_[cluster_ids[i]]
            distance = np.linalg.norm(x - center)
            similarity = max(0, 100 - distance * 10)
            similarities.append(similarity)
        
        df['ip_gene_similarity'] = similarities
        print(f"平均相似度: {df['ip_gene_similarity'].mean():.2f}")
        
        return df

# ================================================================
#  8. 双引擎训练（开题报告创新点1核心）
# ================================================================

def train_dual_engine_model(df):
    """
    双引擎训练
    Engine A: XGBoost - 成熟期作品
    Engine B: 简化版 - 孵化期作品（使用轻量级规则）
    """
    print("\n" + "="*70)
    print("双引擎模型训练")
    print("="*70)
    
    # 准备特征列表
    feature_cols = [c for c in df.columns if c not in ['title', 'author', 'category', 'platform',
                                                      'year', 'month', 'year_month', 'adaptations',
                                                      'updated_at', 'abstract']]
    
    # 确保数值类型
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    feature_cols = [c for c in feature_cols if c != 'monthly_tickets']
    
    # 时间切分
    train_mask = df['year'] <= 2023
    val_mask = df['year'] == 2024
    test_mask = df['year'] >= 2025
    
    # 成熟期 vs 孵化期
    mature_mask = df['months_since_start'] >= 6
    immature_mask = df['months_since_start'] < 6
    
    print(f"\n数据分布:")
    print(f"  训练集: {(train_mask).sum()} 条")
    print(f"  验证集: {(val_mask).sum()} 条")
    print(f"  测试集: {(test_mask).sum()} 条")
    print(f"  成熟期: {(mature_mask).sum()} 条")
    print(f"  孵化期: {(immature_mask).sum()} 条")
    
    results = {}
    
    # ===== Engine A: XGBoost for Mature Books =====
    print("\n【Engine A】训练XGBoost模型（成熟期）...")
    
    mature_train = df[train_mask & mature_mask]
    if len(mature_train) > 100:
        X_train_a = mature_train[feature_cols]
        y_train_a = np.log1p(mature_train['monthly_tickets'])
        
        scaler_a = StandardScaler()
        X_train_a_scaled = scaler_a.fit_transform(X_train_a)
        
        dtrain = xgb.DMatrix(X_train_a_scaled, label=y_train_a, feature_names=feature_cols)
        
        params = {
            'objective': 'reg:squarederror',
            'max_depth': 8,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'eval_metric': 'rmse',
            'seed': 42
        }
        
        model_a = xgb.train(params, dtrain, num_boost_round=500)
        
        results['engine_a'] = {
            'model': model_a,
            'scaler': scaler_a,
            'features': feature_cols
        }
        print("Engine A训练完成")
    else:
        print("成熟期样本不足，跳过Engine A")
    
    # ===== Engine B: Rule-based for Immature Books =====
    print("\n【Engine B】配置孵化期评分规则...")
    
    # 孵化期使用加权评分（基于增长率和更新稳定性）
    engine_b_weights = {
        'tickets_mom': 0.3,  # 月票环比增长率
        'update_regularity': 0.25,  # 更新稳定性（越低越好，需要反转）
        'max_consecutive_months': 0.2,  # 连续更新月数
        'purchasing_power_index': 0.15,  # 购买力指数
        'total_recommend': 0.1  # 推荐数
    }
    
    results['engine_b'] = {
        'weights': engine_b_weights
    }
    print("Engine B配置完成")
    
    # 评估
    print("\n【模型评估】")
    
    if val_mask.sum() > 0:
        val_df = df[val_mask].copy()
        
        # 预测
        predictions = []
        for _, row in val_df.iterrows():
            if row['months_since_start'] >= 6 and 'engine_a' in results:
                # Engine A: XGBoost
                X = pd.DataFrame([row[feature_cols].values], columns=feature_cols)
                X_scaled = results['engine_a']['scaler'].transform(X)
                dmatrix = xgb.DMatrix(X_scaled, feature_names=feature_cols)
                pred_log = results['engine_a']['model'].predict(dmatrix)
                pred = np.expm1(pred_log)[0]
            else:
                # Engine B: 加权评分
                score = 0
                for feat, weight in engine_b_weights.items():
                    if feat in row:
                        # 归一化到0-100
                        val = min(100, max(0, row[feat] * 100))
                        score += val * weight
                pred = score * 100  # 缩放到月票量级
            
            predictions.append(pred)
        
        val_df['prediction'] = predictions
        y_true = val_df['monthly_tickets'].values
        y_pred = val_df['prediction'].values
        
        # 计算指标
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1))) * 100
        
        print(f"\n验证集性能:")
        print(f"  RMSE: {rmse:.2f}")
        print(f"  MAE: {mae:.2f}")
        print(f"  R²: {r2:.4f}")
        print(f"  MAPE: {mape:.2f}%")
        
        results['validation_metrics'] = {
            'rmse': rmse, 'mae': mae, 'r2': r2, 'mape': mape
        }
    
    return results

# ================================================================
#  9. 主流程
# ================================================================

def main():
    print("="*70)
    print("Model F - 开题报告完整实现")
    print("="*70)
    
    # 1. 获取数据
    df = fetch_complete_data()
    
    # 2. 获取NLP和评论数据
    chapters_data = fetch_chapter_data()
    comments_data = fetch_comment_data()
    
    # 3. NLP特征
    df = extract_nlp_features(df, chapters_data)
    
    # 4. 评论特征
    df = extract_comment_features(df, comments_data)
    
    # 5. 完整特征工程
    df = engineer_all_features(df)
    
    # 6. IP基因聚类
    ip_clustering = IPGeneClustering(n_clusters=5)
    ip_clustering.fit(df)
    df = ip_clustering.predict_similarity(df)
    
    # 7. 双引擎训练
    model_results = train_dual_engine_model(df)
    
    # 8. 保存完整模型
    print("\n" + "="*70)
    print("保存完整模型")
    print("="*70)
    
    model_package = {
        'ip_clustering': ip_clustering,
        'dual_engine_results': model_results,
        'version': 'Model_F_Complete_v1.0',
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'features': {
            'nlp': ['sentiment_score', 'action_word_ratio', 'dialog_word_ratio'],
            'comment': ['comment_sentiment_score', 'tier1_comment_ratio'],
            'entropy': ['update_entropy', 'update_regularity'],
            'ip_gene': ['ip_gene_similarity'],
            'adaptation': ['has_adaptation', 'adaptation_count']
        }
    }
    
    save_path = 'model_f_complete.pkl'
    joblib.dump(model_package, save_path)
    print(f"完整模型已保存: {save_path}")
    
    # 9. 总结
    print("\n" + "="*70)
    print("Model F 训练完成")
    print("="*70)
    print(f"总样本: {len(df)}")
    print(f"特征数: {len(df.columns)}")
    print(f"有改编: {df['has_adaptation'].sum()} 本")
    print(f"成熟期: {(df['months_since_start'] >= 6).sum()} 本")
    print(f"孵化期: {(df['months_since_start'] < 6).sum()} 本")
    
    if 'validation_metrics' in model_results:
        metrics = model_results['validation_metrics']
        print(f"\n验证性能:")
        print(f"  MAPE: {metrics['mape']:.2f}%")
        print(f"  R²: {metrics['r2']:.4f}")

if __name__ == "__main__":
    main()
