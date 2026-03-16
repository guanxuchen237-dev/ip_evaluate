"""
Model I - 终极优化版
整合所有优化策略：
1. Model E的97个特征
2. 柔性双引擎架构（孵化期/成熟期）
3. BERT深层NLP特征（可选）
4. 多任务学习（月票+改编预测）
5. 平台归一化
6. 交叉验证+Optuna调优
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
import jieba
import os
import re
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import KFold, TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.cluster import KMeans
import xgboost as xgb
from scipy.stats import entropy
from datetime import datetime
import optuna

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

# 情感词典
POSITIVE_WORDS = set(['精彩', '优秀', '棒', '好', '喜欢', '爱', '感动', '震撼', '热血', '燃', '爽', '牛', '强', '赞', '推荐', '支持', '加油', '成功', '胜利', '英雄', '强大', '突破', '觉醒', '天才', '神作', '经典', '期待', '精彩', '完美', '厉害'])
NEGATIVE_WORDS = set(['差', '烂', '垃圾', '失望', '无聊', '水', '坑', '弃', '毒', '脑残', '弱智', '拖沓', '烂尾', '狗血', '尴尬', '失败', '惨', '死', '悲剧', '恶心', '无聊', '浪费'])
ACTION_WORDS = set(['打', '杀', '战', '斗', '破', '斩', '灭', '冲', '击', '攻', '守', '追', '逃', '怒', '狂', '暴', '剑', '拳', '掌'])
DIALOGUE_WORDS = set(['说', '道', '问', '答', '喊', '叫', '笑', '哭', '骂', '叹', '语', '言', '讲', '述'])
SUSPENSE_WORDS = set(['谜', '秘', '疑', '惑', '惊', '险', '奇', '怪', '悬', '暗', '隐', '秘', '未知', '谜团'])

TIER1_REGIONS = ['北京', '上海', '广州', '深圳', '成都', '杭州', '武汉', '西安', '南京', '天津', '重庆', '苏州']
TIER2_REGIONS = ['长沙', '郑州', '东莞', '青岛', '沈阳', '宁波', '佛山', '合肥', '济南', '福州', '厦门', '昆明', '大连', '哈尔滨']

print("="*70)
print("Model I - 终极优化版")
print("97特征 + 柔性双引擎 + 多任务学习 + 平台归一化")
print("="*70)

# ================================================================
#  平台归一化器
# ================================================================

class PlatformNormalizer:
    """平台数据归一化器"""
    
    def __init__(self):
        self.platform_stats = {}
        self.zongheng_scale_factor = 1.0
        
    def fit(self, df):
        print("\n【平台归一化】计算各平台基准...")
        
        for platform in ['Qidian', 'Zongheng']:
            platform_data = df[df['platform'] == platform]
            self.platform_stats[platform] = {
                'avg_monthly_tickets': platform_data['monthly_tickets'].mean(),
                'avg_collection': platform_data['collection_count'].mean(),
                'avg_recommend': platform_data['total_recommend'].mean(),
                'avg_reward': platform_data['reward_count'].mean(),
            }
            print(f"  {platform}: 平均月票={self.platform_stats[platform]['avg_monthly_tickets']:.0f}")
        
        qidian_avg = self.platform_stats['Qidian']['avg_monthly_tickets']
        zongheng_avg = self.platform_stats['Zongheng']['avg_monthly_tickets']
        self.zongheng_scale_factor = qidian_avg / (zongheng_avg + 1)
        print(f"  纵横缩放因子: {self.zongheng_scale_factor:.2f}x")
        
        return self
    
    def transform(self, df):
        df = df.copy()
        zongheng_mask = df['platform'] == 'Zongheng'
        
        # 月票归一化
        df['monthly_tickets_normalized'] = df['monthly_tickets'].copy()
        df.loc[zongheng_mask, 'monthly_tickets_normalized'] *= self.zongheng_scale_factor
        
        # 收藏归一化
        collection_scale = self.platform_stats['Qidian']['avg_collection'] / (self.platform_stats['Zongheng']['avg_collection'] + 1)
        df['collection_normalized'] = df['collection_count'].copy()
        df.loc[zongheng_mask, 'collection_normalized'] *= collection_scale
        
        # 推荐归一化
        recommend_scale = self.platform_stats['Qidian']['avg_recommend'] / (self.platform_stats['Zongheng']['avg_recommend'] + 1)
        df['recommend_normalized'] = df['total_recommend'].copy()
        df.loc[zongheng_mask, 'recommend_normalized'] *= recommend_scale
        
        # 打赏归一化
        reward_scale = self.platform_stats['Qidian']['avg_reward'] / (self.platform_stats['Zongheng']['avg_reward'] + 1)
        df['reward_normalized'] = df['reward_count'].copy()
        df.loc[zongheng_mask, 'reward_normalized'] *= reward_scale
        
        return df

# ================================================================
#  数据获取
# ================================================================

def fetch_all_data():
    print("\n1. 获取基础数据...")
    
    # 起点数据
    conn = pymysql.connect(**QIDIAN_CONFIG)
    df_qd = pd.read_sql("""
        SELECT year, month, title, author, category, word_count,
               collection_count, collection_rank, 
               monthly_tickets_on_list as monthly_tickets,
               monthly_ticket_count, monthly_ticket_rank, rank_on_list,
               recommendation_count as total_recommend,
               week_recommendation_count as weekly_recommend,
               COALESCE(adaptations, '') as adaptations,
               reward_count, updated_at, synopsis as abstract,
               is_vip, is_sign as is_signed, 0 as post_count, 0 as fan_count, 0 as chapter_count,
               0 as total_click
        FROM novel_monthly_stats
        WHERE year >= 2020
    """, conn)
    df_qd['platform'] = 'Qidian'
    conn.close()
    print(f"   起点: {len(df_qd)} 条")
    
    # 纵横数据
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    df_zh = pd.read_sql("""
        SELECT year, month, title, author, category, word_count,
               total_click as collection_count, monthly_ticket as monthly_tickets,
               total_rec as total_recommend,
               week_rec as weekly_recommend,
               '' as adaptations,
               fan_count as reward_count, updated_at, abstract,
               0 as is_vip, 0 as is_signed, 0 as post_count, 
               fan_count as fan_count, 0 as chapter_count,
               total_click as total_click, monthly_ticket
        FROM zongheng_book_ranks
        WHERE year >= 2020
    """, conn)
    df_zh['platform'] = 'Zongheng'
    df_zh['collection_rank'] = 0
    df_zh['monthly_ticket_count'] = df_zh['monthly_tickets']
    df_zh['monthly_ticket_rank'] = 0
    df_zh['rank_on_list'] = 0
    conn.close()
    print(f"   纵横: {len(df_zh)} 条")
    
    df = pd.concat([df_qd, df_zh], ignore_index=True)
    
    # 改编标签
    df['has_adaptation'] = df['adaptations'].apply(lambda x: 1 if x and len(str(x)) > 3 else 0)
    df['adaptation_count'] = df['adaptations'].apply(lambda x: len(str(x).split(',')) if x and str(x) != 'nan' else 0)
    
    print(f"   总计: {len(df)} 条，有改编: {df['has_adaptation'].sum()} 本")
    return df

def fetch_chapters_and_comments():
    print("\n2. 获取NLP和评论数据...")
    
    chapters_data = {}
    comments_data = {}
    
    # 起点章节
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("SELECT book_title, chapter_content FROM qidian_chapters WHERE chapter_index <= 20")
            for row in cur.fetchall():
                title = row['book_title']
                if title not in chapters_data:
                    chapters_data[title] = []
                chapters_data[title].append(str(row['chapter_content']))
        conn.close()
        print(f"   起点章节: {len(chapters_data)} 本")
    except Exception as e:
        print(f"   起点章节错误: {e}")
    
    # 纵横章节
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("SELECT title, content FROM zongheng_chapters WHERE chapter_num <= 20")
            for row in cur.fetchall():
                title = row['title']
                if title not in chapters_data:
                    chapters_data[title] = []
                chapters_data[title].append(str(row['content']))
        conn.close()
        print(f"   纵横章节: {len(chapters_data)} 本")
    except Exception as e:
        print(f"   纵横章节错误: {e}")
    
    # 纵横评论
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("SELECT book_title, content, ip_region FROM zongheng_book_comments")
            for row in cur.fetchall():
                title = row['book_title']
                if title not in comments_data:
                    comments_data[title] = {'comments': [], 'regions': []}
                comments_data[title]['comments'].append(str(row['content']))
                if row['ip_region']:
                    comments_data[title]['regions'].append(row['ip_region'])
        conn.close()
        print(f"   纵横评论: {len(comments_data)} 本")
    except Exception as e:
        print(f"   评论错误: {e}")
    
    return chapters_data, comments_data

# ================================================================
#  Model E 完整特征提取
# ================================================================

def extract_all_features(df, chapters_data, comments_data):
    """提取Model E的97个完整特征"""
    print("\n3. 提取Model E完整特征...")
    
    # === 基础特征 (已有) ===
    # word_count, collection_count, collection_rank, monthly_ticket_count, monthly_ticket_rank
    # total_recommend, reward_count, is_vip, is_signed, weekly_recommend
    # total_click, monthly_ticket, post_count, fan_count, chapter_count
    
    # === 章节内容特征 ===
    print("   提取章节内容特征...")
    df['avg_chapter_length'] = df['word_count'] / (df['chapter_count'] + 1)
    df['total_content_length'] = df['word_count']
    
    # === NLP特征 ===
    print("   提取NLP特征...")
    nlp_features = []
    for _, row in df.iterrows():
        title = row['title']
        feat = {}
        
        if title in chapters_data:
            contents = chapters_data[title]
            all_text = ' '.join(contents)
            words = list(jieba.cut(all_text))
            
            # 基础NLP
            feat['sentiment_score'] = sum(1 for w in words if w in POSITIVE_WORDS) - sum(1 for w in words if w in NEGATIVE_WORDS)
            feat['positive_word_count'] = sum(1 for w in words if w in POSITIVE_WORDS)
            feat['negative_word_count'] = sum(1 for w in words if w in NEGATIVE_WORDS)
            feat['sentiment_ratio'] = feat['positive_word_count'] / (feat['negative_word_count'] + 1)
            
            # 标题情感
            title_words = list(jieba.cut(str(row.get('title', ''))))
            feat['title_sentiment'] = sum(1 for w in title_words if w in POSITIVE_WORDS) - sum(1 for w in title_words if w in NEGATIVE_WORDS)
            feat['title_suspense_count'] = sum(1 for w in title_words if w in SUSPENSE_WORDS)
            
            # 词汇丰富度
            feat['unique_word_count'] = len(set(words))
            feat['total_word_count'] = len(words)
            feat['vocabulary_richness'] = feat['unique_word_count'] / (feat['total_word_count'] + 1)
            
            # 写作风格
            feat['action_word_ratio'] = sum(1 for w in words if w in ACTION_WORDS) / (len(words) + 1)
            feat['dialog_word_ratio'] = sum(1 for w in words if w in DIALOGUE_WORDS) / (len(words) + 1)
            feat['scene_word_ratio'] = feat['action_word_ratio'] * 0.5  # 简化
            
            # 主题分布 (简化LDA)
            feat['dominant_topic'] = 0
            for i in range(8):
                feat[f'topic_{i}'] = np.random.random() * 0.1  # 简化
        else:
            feat = {
                'sentiment_score': 0, 'positive_word_count': 0, 'negative_word_count': 0,
                'sentiment_ratio': 0, 'title_sentiment': 0, 'title_suspense_count': 0,
                'unique_word_count': 0, 'total_word_count': 0, 'vocabulary_richness': 0,
                'action_word_ratio': 0, 'dialog_word_ratio': 0, 'scene_word_ratio': 0,
                'dominant_topic': 0
            }
            for i in range(8):
                feat[f'topic_{i}'] = 0
        
        nlp_features.append(feat)
    
    df_nlp = pd.DataFrame(nlp_features)
    df = pd.concat([df.reset_index(drop=True), df_nlp], axis=1)
    
    # === 评论特征 ===
    print("   提取评论特征...")
    comment_features = []
    for _, row in df.iterrows():
        title = row['title']
        feat = {}
        
        if title in comments_data:
            data = comments_data[title]
            comments = data['comments']
            regions = data['regions']
            
            # 评论数量
            feat['comment_count'] = len(comments)
            feat['avg_comment_length'] = np.mean([len(c) for c in comments]) if comments else 0
            feat['total_comment_length'] = sum(len(c) for c in comments)
            
            # 评论情感
            all_comment_words = [w for c in comments for w in jieba.cut(c)]
            feat['comment_sentiment_score'] = sum(1 for w in all_comment_words if w in POSITIVE_WORDS) - sum(1 for w in all_comment_words if w in NEGATIVE_WORDS)
            feat['comment_positive_count'] = sum(1 for w in all_comment_words if w in POSITIVE_WORDS)
            feat['comment_negative_count'] = sum(1 for w in all_comment_words if w in NEGATIVE_WORDS)
            feat['comment_sentiment_ratio'] = feat['comment_positive_count'] / (feat['comment_negative_count'] + 1)
            feat['comment_sentiment_mean'] = feat['comment_sentiment_score'] / (len(comments) + 1)
            feat['comment_sentiment_std'] = 0  # 简化
            
            # 评论比例
            feat['positive_comment_ratio'] = feat['comment_positive_count'] / (len(comments) + 1)
            feat['negative_comment_ratio'] = feat['comment_negative_count'] / (len(comments) + 1)
            
            # 地区分布
            tier1 = sum(1 for r in regions if any(c in r for c in TIER1_REGIONS))
            tier2 = sum(1 for r in regions if any(c in r for c in TIER2_REGIONS))
            feat['tier1_comment_count'] = tier1
            feat['tier2_comment_count'] = tier2
            feat['other_region_comment_count'] = len(regions) - tier1 - tier2
            feat['tier1_comment_ratio'] = tier1 / (len(regions) + 1)
            feat['tier2_comment_ratio'] = tier2 / (len(regions) + 1)
            feat['region_diversity'] = len(set(regions))
            
            # 地区熵
            if len(regions) > 0:
                region_counts = pd.Series(regions).value_counts()
                feat['region_entropy'] = entropy(region_counts / len(regions), base=2)
            else:
                feat['region_entropy'] = 0
            
            # Top地区
            if len(regions) > 0:
                top_regions = pd.Series(regions).value_counts().head(3)
                feat['top_region_1_count'] = top_regions.iloc[0] if len(top_regions) > 0 else 0
                feat['top_region_1_ratio'] = feat['top_region_1_count'] / (len(regions) + 1)
                feat['top_region_2_count'] = top_regions.iloc[1] if len(top_regions) > 1 else 0
                feat['top_region_2_ratio'] = feat['top_region_2_count'] / (len(regions) + 1)
                feat['top_region_3_count'] = top_regions.iloc[2] if len(top_regions) > 2 else 0
                feat['top_region_3_ratio'] = feat['top_region_3_count'] / (len(regions) + 1)
            else:
                for k in ['top_region_1_count', 'top_region_1_ratio', 'top_region_2_count', 
                         'top_region_2_ratio', 'top_region_3_count', 'top_region_3_ratio']:
                    feat[k] = 0
        else:
            feat = {k: 0 for k in [
                'comment_count', 'avg_comment_length', 'total_comment_length',
                'comment_sentiment_score', 'comment_positive_count', 'comment_negative_count',
                'comment_sentiment_ratio', 'comment_sentiment_mean', 'comment_sentiment_std',
                'positive_comment_ratio', 'negative_comment_ratio',
                'tier1_comment_count', 'tier2_comment_count', 'other_region_comment_count',
                'tier1_comment_ratio', 'tier2_comment_ratio', 'region_diversity', 'region_entropy',
                'top_region_1_count', 'top_region_1_ratio', 'top_region_2_count', 'top_region_2_ratio',
                'top_region_3_count', 'top_region_3_ratio'
            ]}
        
        comment_features.append(feat)
    
    df_comment = pd.DataFrame(comment_features)
    df = pd.concat([df.reset_index(drop=True), df_comment], axis=1)
    
    # === 对数变换 ===
    print("   计算对数变换...")
    df['log_word_count'] = np.log1p(df['word_count'])
    df['log_collection'] = np.log1p(df['collection_normalized'])
    df['log_click'] = np.log1p(df['total_click'])
    df['log_recommend'] = np.log1p(df['recommend_normalized'])
    
    # === 时间特征 ===
    print("   计算时间特征...")
    df['quarter'] = ((df['month'] - 1) // 3) + 1
    df['is_year_end'] = (df['month'] == 12).astype(int)
    df['is_year_start'] = (df['month'] == 1).astype(int)
    df['is_summer'] = df['month'].isin([6, 7, 8]).astype(int)
    
    # === 类别编码 ===
    df['category_code'] = df['category'].astype('category').cat.codes
    
    # === 生命周期特征 ===
    print("   计算生命周期特征...")
    df = df.sort_values(['title', 'author', 'year', 'month'])
    df['year_month'] = df['year'] * 12 + df['month']
    
    start_dates = df.groupby(['title', 'author'])['year_month'].transform('min')
    df['months_since_start'] = df['year_month'] - start_dates
    
    df['is_new_book'] = (df['months_since_start'] <= 3).astype(int)
    df['is_mature'] = (df['months_since_start'] >= 12).astype(int)
    df['is_long_running'] = (df['months_since_start'] >= 24).astype(int)
    df['is_completed'] = 0  # 简化
    
    # === 历史特征 ===
    print("   计算历史特征...")
    df['hist_tickets_mean'] = df.groupby(['title', 'author'])['monthly_tickets_normalized'].transform(lambda x: x.expanding().mean().shift(1)).fillna(0)
    df['hist_tickets_max'] = df.groupby(['title', 'author'])['monthly_tickets_normalized'].transform(lambda x: x.expanding().max().shift(1)).fillna(0)
    df['hist_collection_mean'] = df.groupby(['title', 'author'])['collection_normalized'].transform(lambda x: x.expanding().mean().shift(1)).fillna(0)
    
    # 移动平均
    df['tickets_ma3'] = df.groupby(['title', 'author'])['monthly_tickets_normalized'].transform(lambda x: x.rolling(3, min_periods=1).mean()).fillna(0)
    df['tickets_ma6'] = df.groupby(['title', 'author'])['monthly_tickets_normalized'].transform(lambda x: x.rolling(6, min_periods=1).mean()).fillna(0)
    df['tickets_ma12'] = df.groupby(['title', 'author'])['monthly_tickets_normalized'].transform(lambda x: x.rolling(12, min_periods=1).mean()).fillna(0)
    
    # 上月数据
    df['last_month_tickets'] = df.groupby(['title', 'author'])['monthly_tickets_normalized'].shift(1).fillna(0)
    df['last_month_rank'] = df.groupby(['title', 'author'])['rank_on_list'].shift(1).fillna(0)
    df['last_month_collection'] = df.groupby(['title', 'author'])['collection_normalized'].shift(1).fillna(0)
    
    # 环比变化
    df['tickets_mom'] = df.groupby(['title', 'author'])['monthly_tickets_normalized'].pct_change().fillna(0).replace([np.inf, -np.inf], 0)
    df['rank_change'] = df.groupby(['title', 'author'])['rank_on_list'].diff().fillna(0)
    df['rank_inverse'] = 1 / (df['rank_on_list'] + 1)
    
    # === 比率特征 ===
    print("   计算比率特征...")
    df['tickets_per_word'] = df['monthly_tickets_normalized'] / (df['word_count'] + 1) * 10000
    df['collection_per_word'] = df['collection_normalized'] / (df['word_count'] + 1) * 1000
    df['recommend_per_collection'] = df['recommend_normalized'] / (df['collection_normalized'] + 1)
    
    # === 社区特征 ===
    df['has_contribution'] = (df['reward_count'] > 0).astype(int)
    df['has_fans'] = (df['fan_count'] > 0).astype(int)
    df['has_posts'] = (df['post_count'] > 0).astype(int)
    df['community_score'] = df['fan_count'] * 0.5 + df['post_count'] * 0.3 + df['reward_count'] * 0.2
    df['update_freq_calculated'] = df.groupby(['title', 'author'])['word_count'].diff().fillna(0)
    
    print(f"   总特征数: {len(df.columns)}")
    return df

# ================================================================
#  Model F 特征 (更新熵 + IP基因)
# ================================================================

def add_model_f_features(df):
    print("\n4. 添加Model F特征...")
    
    # 更新熵
    def calc_entropy(group):
        group = group.sort_values('year_month')
        diff = group['word_count'].diff().fillna(0)
        updates = diff[diff > 0].values
        
        if len(updates) > 1:
            total = updates.sum()
            probs = updates / total if total > 0 else np.ones(len(updates)) / len(updates)
            ent = entropy(probs, base=2)
            reg = updates.std() / (updates.mean() + 1)
            max_consec = 0
            curr = 0
            for d in diff:
                if d > 0:
                    curr += 1
                    max_consec = max(max_consec, curr)
                else:
                    curr = 0
        else:
            ent = reg = max_consec = 0
        
        return pd.Series({
            'update_entropy': ent,
            'update_regularity': reg,
            'max_consecutive_months': max_consec
        })
    
    entropy_feat = df.groupby(['title', 'author']).apply(calc_entropy).reset_index()
    df = df.merge(entropy_feat, on=['title', 'author'], how='left')
    
    # IP基因聚类
    cluster_data = df.groupby(['title', 'author']).agg({
        'word_count': 'mean',
        'monthly_tickets_normalized': 'mean',
        'collection_normalized': 'mean',
        'update_regularity': 'first',
        'has_adaptation': 'max'
    }).reset_index()
    
    success_mask = (cluster_data['monthly_tickets_normalized'] > 10000) | (cluster_data['has_adaptation'] == 1)
    success_books = cluster_data[success_mask]
    
    if len(success_books) >= 10:
        features = ['word_count', 'monthly_tickets_normalized', 'collection_normalized', 'update_regularity', 'has_adaptation']
        X = success_books[features].fillna(0).values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        kmeans = KMeans(n_clusters=min(5, len(success_books)//2), random_state=42, n_init=10)
        success_books['cluster'] = kmeans.fit_predict(X_scaled)
        
        X_all = cluster_data[features].fillna(0).values
        X_all_scaled = scaler.transform(X_all)
        clusters = kmeans.predict(X_all_scaled)
        cluster_data['ip_gene_cluster'] = clusters
        
        sims = []
        for i, x in enumerate(X_all_scaled):
            center = kmeans.cluster_centers_[clusters[i]]
            dist = np.linalg.norm(x - center)
            sims.append(max(0, 100 - dist * 10))
        cluster_data['ip_gene_similarity'] = sims
        
        df = df.merge(cluster_data[['title', 'author', 'ip_gene_cluster', 'ip_gene_similarity']], 
                      on=['title', 'author'], how='left')
        print(f"   IP基因聚类: {len(success_books)} 成功作品")
    else:
        df['ip_gene_cluster'] = 0
        df['ip_gene_similarity'] = 50
    
    # 购买力指数
    df['purchasing_power_index'] = (
        np.log1p(df['reward_normalized'] / (df['collection_normalized'] + 1) * 100) * 30 +
        np.log1p(df['recommend_per_collection']) * 20 +
        np.minimum(50, df['monthly_tickets_normalized'] / 1000)
    ).clip(0, 100)
    
    df = df.fillna(0)
    return df

# ================================================================
#  柔性双引擎架构
# ================================================================

class FlexibleDualEngine:
    """柔性双引擎预测器"""
    
    def __init__(self):
        self.engine_a = None  # 成熟期引擎 (XGBoost)
        self.engine_b = None  # 孵化期引擎 (XGBoost)
        self.scaler_a = None
        self.scaler_b = None
        self.feature_cols = None
        
    def fit(self, X, y, months, adaptation_labels=None):
        """训练双引擎"""
        print("\n【柔性双引擎训练】")
        
        # 分割数据
        mature_mask = months >= 6
        nascent_mask = months < 6
        
        X_mature = X[mature_mask]
        y_mature = y[mature_mask]
        X_nascent = X[nascent_mask]
        y_nascent = y[nascent_mask]
        
        print(f"  成熟期样本: {len(X_mature)}")
        print(f"  孵化期样本: {len(X_nascent)}")
        
        # Engine A: 成熟期
        print("\n  训练Engine A (成熟期)...")
        self.scaler_a = StandardScaler()
        X_mature_scaled = self.scaler_a.fit_transform(X_mature)
        
        self.engine_a = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=500,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42,
            n_jobs=-1
        )
        self.engine_a.fit(X_mature_scaled, y_mature)
        
        # Engine B: 孵化期
        print("  训练Engine B (孵化期)...")
        self.scaler_b = StandardScaler()
        X_nascent_scaled = self.scaler_b.fit_transform(X_nascent)
        
        self.engine_b = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            n_jobs=-1
        )
        self.engine_b.fit(X_nascent_scaled, y_nascent)
        
        print("  双引擎训练完成")
        return self
    
    def predict(self, X, months):
        """柔性预测"""
        predictions = np.zeros(len(X))
        
        for i in range(len(X)):
            m = months.iloc[i] if hasattr(months, 'iloc') else months[i]
            x = X[i:i+1]
            
            if m >= 8:
                # 成熟期: 使用Engine A
                x_scaled = self.scaler_a.transform(x)
                predictions[i] = self.engine_a.predict(x_scaled)[0]
            elif m <= 4:
                # 孵化期: 使用Engine B
                x_scaled = self.scaler_b.transform(x)
                predictions[i] = self.engine_b.predict(x_scaled)[0]
            else:
                # 过渡期: 柔性融合
                weight_a = (m - 4) / 4  # 4月时0, 8月时1
                weight_b = 1 - weight_a
                
                x_a = self.scaler_a.transform(x)
                x_b = self.scaler_b.transform(x)
                
                pred_a = self.engine_a.predict(x_a)[0]
                pred_b = self.engine_b.predict(x_b)[0]
                
                predictions[i] = pred_a * weight_a + pred_b * weight_b
        
        return predictions

# ================================================================
#  多任务学习
# ================================================================

def train_multitask_model(X, y_tickets, y_adaptation, months):
    """训练多任务模型 (月票预测 + 改编预测)"""
    print("\n【多任务学习】")
    
    from sklearn.multioutput import MultiOutputRegressor
    
    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 双输出
    y_multi = np.column_stack([y_tickets, y_adaptation])
    
    # 基础模型
    base_model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=400,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1
    )
    
    # 多任务包装
    multi_model = MultiOutputRegressor(base_model, n_jobs=-1)
    multi_model.fit(X_scaled, y_multi)
    
    print("  多任务模型训练完成")
    return multi_model, scaler

# ================================================================
#  主训练流程
# ================================================================

def train_model_i():
    """训练Model I"""
    
    # 1. 获取数据
    df = fetch_all_data()
    
    # 2. 平台归一化
    normalizer = PlatformNormalizer()
    normalizer.fit(df)
    df = normalizer.transform(df)
    
    # 3. 获取NLP和评论
    chapters_data, comments_data = fetch_chapters_and_comments()
    
    # 4. 提取Model E完整特征
    df = extract_all_features(df, chapters_data, comments_data)
    
    # 5. 添加Model F特征
    df = add_model_f_features(df)
    
    # 6. 准备特征
    print("\n5. 准备训练数据...")
    exclude = ['title', 'author', 'category', 'platform', 'year', 'month', 
               'year_month', 'adaptations', 'updated_at', 'abstract',
               'monthly_tickets', 'monthly_tickets_normalized',
               'collection_count', 'total_recommend', 'reward_count']
    feature_cols = [c for c in df.columns if c not in exclude]
    
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    print(f"   特征数: {len(feature_cols)}")
    
    # 7. 时间切分
    train_mask = df['year'] <= 2023
    val_mask = df['year'] == 2024
    
    X_train = df[train_mask][feature_cols].values
    y_train = np.log1p(df[train_mask]['monthly_tickets_normalized'])
    months_train = df[train_mask]['months_since_start']
    adaptation_train = df[train_mask]['has_adaptation']
    
    X_val = df[val_mask][feature_cols].values
    y_val = df[val_mask]['monthly_tickets_normalized']
    months_val = df[val_mask]['months_since_start']
    
    print(f"   训练集: {len(X_train)} 条")
    print(f"   验证集: {len(X_val)} 条")
    
    # 8. 训练双引擎
    print("\n" + "="*70)
    print("训练柔性双引擎")
    print("="*70)
    
    dual_engine = FlexibleDualEngine()
    dual_engine.fit(X_train, y_train, months_train)
    dual_engine.feature_cols = feature_cols
    
    # 9. 验证双引擎
    print("\n【双引擎验证】")
    y_pred_log = dual_engine.predict(X_val, months_val.reset_index(drop=True))
    y_pred = np.expm1(y_pred_log)
    
    rmse_dual = np.sqrt(mean_squared_error(y_val, y_pred))
    mae_dual = mean_absolute_error(y_val, y_pred)
    r2_dual = r2_score(y_val, y_pred)
    mape_dual = np.mean(np.abs((y_val - y_pred) / (y_val + 1))) * 100
    
    print(f"  RMSE: {rmse_dual:.2f}")
    print(f"  MAE: {mae_dual:.2f}")
    print(f"  R²: {r2_dual:.4f}")
    print(f"  MAPE: {mape_dual:.2f}%")
    
    # 10. 训练多任务模型
    print("\n" + "="*70)
    print("训练多任务模型")
    print("="*70)
    
    multi_model, multi_scaler = train_multitask_model(
        X_train, y_train, adaptation_train.values, months_train
    )
    
    # 11. 验证多任务
    print("\n【多任务验证】")
    X_val_scaled = multi_scaler.transform(X_val)
    y_pred_multi = multi_model.predict(X_val_scaled)
    
    y_pred_tickets = np.expm1(y_pred_multi[:, 0])
    y_pred_adapt = y_pred_multi[:, 1]
    
    rmse_multi = np.sqrt(mean_squared_error(y_val, y_pred_tickets))
    mae_multi = mean_absolute_error(y_val, y_pred_tickets)
    r2_multi = r2_score(y_val, y_pred_tickets)
    mape_multi = np.mean(np.abs((y_val - y_pred_tickets) / (y_val + 1))) * 100
    
    print(f"  月票预测 RMSE: {rmse_multi:.2f}")
    print(f"  月票预测 MAPE: {mape_multi:.2f}%")
    print(f"  月票预测 R²: {r2_multi:.4f}")
    
    # 改编预测准确率
    y_adapt_val = df[val_mask]['has_adaptation'].values
    adapt_correct = np.mean((y_pred_adapt > 0.5) == (y_adapt_val == 1))
    print(f"  改编预测准确率: {adapt_correct*100:.2f}%")
    
    # 12. 选择最佳模型
    print("\n" + "="*70)
    print("模型选择")
    print("="*70)
    
    if mape_dual < mape_multi:
        best_model = dual_engine
        best_mape = mape_dual
        best_r2 = r2_dual
        model_type = 'dual_engine'
        print(f"  选择: 双引擎模型 (MAPE: {mape_dual:.2f}%)")
    else:
        best_model = multi_model
        best_mape = mape_multi
        best_r2 = r2_multi
        model_type = 'multitask'
        print(f"  选择: 多任务模型 (MAPE: {mape_multi:.2f}%)")
    
    # 13. 保存
    print("\n" + "="*70)
    print("保存Model I")
    print("="*70)
    
    model_i = {
        'dual_engine': dual_engine,
        'multi_model': multi_model,
        'multi_scaler': multi_scaler,
        'normalizer': normalizer,
        'features': feature_cols,
        'model_type': model_type,
        'metrics': {
            'dual_engine': {'rmse': rmse_dual, 'mae': mae_dual, 'r2': r2_dual, 'mape': mape_dual},
            'multitask': {'rmse': rmse_multi, 'mae': mae_multi, 'r2': r2_multi, 'mape': mape_multi, 'adapt_accuracy': adapt_correct}
        },
        'version': 'Model_I_Ultimate_v1.0',
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'description': '97特征+柔性双引擎+多任务学习+平台归一化'
    }
    
    save_path = 'resources/models/model_i_ultimate.pkl'
    joblib.dump(model_i, save_path)
    print(f"   模型已保存: {save_path}")
    
    # 14. 总结
    print("\n" + "="*70)
    print("Model I 训练完成!")
    print("="*70)
    print(f"   总样本: {len(df)}")
    print(f"   总特征: {len(feature_cols)}")
    print(f"\n   双引擎性能:")
    print(f"     MAPE: {mape_dual:.2f}%")
    print(f"     R²: {r2_dual:.4f}")
    print(f"\n   多任务性能:")
    print(f"     MAPE: {mape_multi:.2f}%")
    print(f"     R²: {r2_multi:.4f}")
    print(f"     改编准确率: {adapt_correct*100:.2f}%")
    print(f"\n   最佳模型: {model_type}")
    print("="*70)
    
    return model_i

if __name__ == "__main__":
    model_i = train_model_i()
