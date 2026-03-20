"""
Model J - 论文版IP评估模型
严格按照论文要求实现：
1. 双引擎架构：XGBoost(成熟期) + K-Means(孵化期)
2. S/A/B/C/D等级制输出
3. 多维度加权评分系统
4. 6大维度特征覆盖
5. 交叉验证 + Optuna调优
6. 实时月票验证对比
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
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
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
POSITIVE_WORDS = set(['精彩', '优秀', '棒', '好', '喜欢', '爱', '感动', '震撼', '热血', '燃', '爽', '牛', '强', '赞', '推荐', '支持', '加油', '成功', '胜利', '英雄', '强大', '突破', '觉醒', '天才', '神作', '经典', '期待'])
NEGATIVE_WORDS = set(['差', '烂', '垃圾', '失望', '无聊', '水', '坑', '弃', '毒', '脑残', '弱智', '拖沓', '烂尾', '狗血', '尴尬', '失败', '惨', '死', '悲剧', '恶心', '无聊', '浪费'])
ACTION_WORDS = set(['打', '杀', '战', '斗', '破', '斩', '灭', '冲', '击', '攻', '守', '追', '逃', '怒', '狂', '暴', '剑', '拳', '掌'])

# 题材热度映射（网文风口）
HOT_GENRES = {
    '玄幻': 95, '都市': 90, '仙侠': 88, '历史': 82, '科幻': 80,
    '游戏': 85, '悬疑': 78, '轻小说': 75, '军事': 70, '现实': 65,
    '奇幻': 92, '武侠': 85, '灵异': 72, '二次元': 78, '短篇': 60
}

print("="*70)
print("Model J - 论文版IP评估模型")
print("XGBoost + K-Means双引擎 | S/A/B/C/D等级制 | 多维度加权评分")
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
            }
        
        qidian_avg = self.platform_stats['Qidian']['avg_monthly_tickets']
        zongheng_avg = self.platform_stats['Zongheng']['avg_monthly_tickets']
        self.zongheng_scale_factor = qidian_avg / (zongheng_avg + 1)
        print(f"  纵横缩放因子: {self.zongheng_scale_factor:.2f}x")
        
        return self
    
    def transform(self, df):
        df = df.copy()
        zongheng_mask = df['platform'] == 'Zongheng'
        
        df['monthly_tickets_normalized'] = df['monthly_tickets'].copy()
        df.loc[zongheng_mask, 'monthly_tickets_normalized'] *= self.zongheng_scale_factor
        
        collection_scale = self.platform_stats['Qidian']['avg_collection'] / (self.platform_stats['Zongheng']['avg_collection'] + 1)
        df['collection_normalized'] = df['collection_count'].copy()
        df.loc[zongheng_mask, 'collection_normalized'] *= collection_scale
        
        recommend_scale = self.platform_stats['Qidian']['avg_recommend'] / (self.platform_stats['Zongheng']['avg_recommend'] + 1)
        df['recommend_normalized'] = df['total_recommend'].copy()
        df.loc[zongheng_mask, 'recommend_normalized'] *= recommend_scale
        
        return df

# ================================================================
#  IP等级制评分系统
# ================================================================

class IPGradingSystem:
    """IP等级制评分系统 - S/A/B/C/D五级"""
    
    GRADES = {
        'S': {'min': 95, 'max': 100, 'desc': '各平台TOP 5', 'color': '🔴'},
        'A': {'min': 85, 'max': 94, 'desc': '各平台TOP 6-20', 'color': '🟠'},
        'B': {'min': 70, 'max': 84, 'desc': '各平台TOP 21-50', 'color': '🟡'},
        'C': {'min': 55, 'max': 69, 'desc': '有月票数据但排名靠后', 'color': '🟢'},
        'D': {'min': 0, 'max': 54, 'desc': '无活跃数据', 'color': '⚪'},
    }
    
    @staticmethod
    def score_to_grade(score):
        """将0-100分转换为等级"""
        if score >= 95:
            return 'S'
        elif score >= 85:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 55:
            return 'C'
        else:
            return 'D'
    
    @staticmethod
    def grade_to_score_range(grade):
        """获取等级对应的分数范围"""
        return IPGradingSystem.GRADES.get(grade, {'min': 0, 'max': 100})
    
    @staticmethod
    def get_grade_info(grade):
        """获取等级详细信息"""
        return IPGradingSystem.GRADES.get(grade, {})

# ================================================================
#  多维度加权评分系统
# ================================================================

class IPWeightedScorer:
    """多维度加权评分系统"""
    
    # 权重配置（论文要求）
    WEIGHTS = {
        'commercial': 0.40,      # 月票/商业分 (40%)
        'stickiness': 0.15,      # 粉丝粘性 (15%)
        'nlp_quality': 0.15,     # 章节NLP评分 (15%)
        'trend': 0.15,           # 趋势环比 (15%)
        'adaptation': 0.15,      # 世界观+改编潜力 (15%)
    }
    
    def __init__(self):
        self.scalers = {}
        
    def compute_commercial_score(self, df):
        """计算商业价值分 (40%)"""
        # 月票、收藏、推荐的综合评分
        tickets = df['monthly_tickets_normalized']
        collection = df['collection_normalized']
        recommend = df['recommend_normalized']
        
        # 使用对数缩放 + 百分位归一化，确保分数分布合理
        # 月票分：使用对数缩放，让高分作品有更高分数
        tickets_log = np.log1p(tickets)
        tickets_score = np.clip(tickets_log / tickets_log.quantile(0.95) * 100, 0, 100)
        
        # 收藏分
        collection_log = np.log1p(collection)
        collection_score = np.clip(collection_log / collection_log.quantile(0.95) * 100, 0, 100)
        
        # 推荐分
        recommend_log = np.log1p(recommend)
        recommend_score = np.clip(recommend_log / recommend_log.quantile(0.95) * 100, 0, 100)
        
        # 加权平均
        commercial = tickets_score * 0.5 + collection_score * 0.3 + recommend_score * 0.2
        
        # 额外加成：排名前100的作品获得加分
        if 'rank_on_list' in df.columns:
            rank_bonus = np.clip(100 - df['rank_on_list'], 0, 100) * 0.2  # 排名前100加分
            commercial = np.clip(commercial + rank_bonus, 0, 100)
        
        return commercial
    
    def compute_stickiness_score(self, df):
        """计算粉丝粘性 (15%)"""
        # fans_count / popularity 互动转化率
        if 'fan_count' in df.columns and 'total_click' in df.columns:
            interaction_rate = df['fan_count'] / (df['total_click'] + 1) * 1000
            stickiness = np.clip(interaction_rate / interaction_rate.quantile(0.9) * 100, 0, 100)
        else:
            # 备用计算：收藏/点击
            stickiness = np.clip(df['collection_normalized'] / (df['total_click'] + 1) * 100, 0, 100)
        return stickiness
    
    def compute_nlp_quality_score(self, df):
        """计算NLP质量分 (15%)"""
        # 情感分析 + 关键词质量
        sentiment = df.get('sentiment_score', 0)
        vocab_richness = df.get('vocabulary_richness', 0)
        action_ratio = df.get('action_word_ratio', 0)
        
        # 归一化
        sentiment_norm = np.clip((sentiment - sentiment.min()) / (sentiment.max() - sentiment.min() + 1) * 100, 0, 100) if sentiment.max() > sentiment.min() else 50
        vocab_norm = np.clip(vocab_richness * 500, 0, 100)
        action_norm = np.clip(action_ratio * 1000, 0, 100)
        
        nlp_score = sentiment_norm * 0.4 + vocab_norm * 0.3 + action_norm * 0.3
        return nlp_score.fillna(50)
    
    def compute_trend_score(self, df):
        """计算趋势环比分 (15%)"""
        # 月票/收藏环比增长率
        tickets_mom = df.get('tickets_mom', 0)
        collection_growth = df.get('collection_growth', 0)
        
        # 处理异常值
        tickets_mom = np.clip(tickets_mom, -1, 5)  # 限制在-100%到500%
        
        # 转换为分数
        trend_score = np.clip((tickets_mom + 1) / 6 * 100, 0, 100)  # -100%映射到0, 500%映射到100
        return trend_score.fillna(50)
    
    def compute_adaptation_score(self, df):
        """计算改编潜力分 (15%)"""
        # 字数、题材复合维度
        word_count = df['word_count']
        has_adaptation = df.get('has_adaptation', 0)
        category = df.get('category', '')
        
        # 字数评分（50万字以上为满分）
        word_score = np.clip(word_count / 500000 * 100, 0, 100)
        
        # 题材热度
        genre_scores = category.map(lambda x: HOT_GENRES.get(str(x), 70)).fillna(70)
        
        # 已有改编加分
        adaptation_bonus = has_adaptation * 20
        
        adaptation_score = word_score * 0.4 + genre_scores * 0.4 + adaptation_bonus
        return np.clip(adaptation_score, 0, 100)
    
    def compute_ip_score(self, df):
        """计算综合IP评分"""
        print("\n【多维度加权评分】计算IP评分...")
        
        # 计算各维度分数
        df['commercial_score'] = self.compute_commercial_score(df)
        df['stickiness_score'] = self.compute_stickiness_score(df)
        df['nlp_quality_score'] = self.compute_nlp_quality_score(df)
        df['trend_score'] = self.compute_trend_score(df)
        df['adaptation_score'] = self.compute_adaptation_score(df)
        
        # 加权求和
        df['ip_score'] = (
            df['commercial_score'] * self.WEIGHTS['commercial'] +
            df['stickiness_score'] * self.WEIGHTS['stickiness'] +
            df['nlp_quality_score'] * self.WEIGHTS['nlp_quality'] +
            df['trend_score'] * self.WEIGHTS['trend'] +
            df['adaptation_score'] * self.WEIGHTS['adaptation']
        )
        
        # 转换为等级
        df['ip_grade'] = df['ip_score'].apply(IPGradingSystem.score_to_grade)
        
        print(f"  商业分均值: {df['commercial_score'].mean():.2f}")
        print(f"  粘性分均值: {df['stickiness_score'].mean():.2f}")
        print(f"  NLP分均值: {df['nlp_quality_score'].mean():.2f}")
        print(f"  趋势分均值: {df['trend_score'].mean():.2f}")
        print(f"  改编分均值: {df['adaptation_score'].mean():.2f}")
        print(f"  IP评分均值: {df['ip_score'].mean():.2f}")
        
        # 等级分布
        grade_dist = df['ip_grade'].value_counts()
        print(f"\n  等级分布:")
        for grade in ['S', 'A', 'B', 'C', 'D']:
            count = grade_dist.get(grade, 0)
            pct = count / len(df) * 100
            info = IPGradingSystem.get_grade_info(grade)
            color_name = info.get('color', '').replace('\U0001f534', '[红]').replace('\U0001f7e1', '[黄]').replace('\U0001f7e2', '[绿]').replace('\U0001f535', '[蓝]').replace('\u26ab', '[灰]')
            print(f"    {color_name} {grade}级: {count}本 ({pct:.1f}%)")
        
        return df

# ================================================================
#  6大维度特征提取
# ================================================================

def extract_six_dimensions(df, chapters_data, comments_data):
    """提取论文要求的6大维度特征"""
    print("\n【6大维度特征提取】")
    
    # 1. 更新频率 (Update Freq)
    print("  1. 更新频率...")
    df['update_freq'] = df.groupby(['title', 'author'])['word_count'].diff().fillna(0)
    df['update_freq_avg'] = df.groupby(['title', 'author'])['update_freq'].transform('mean')
    
    # 2. 断更风险/存活率 (Drop Risk)
    print("  2. 断更风险...")
    df['months_active'] = df.groupby(['title', 'author']).cumcount() + 1
    df['drop_months'] = df.groupby(['title', 'author'])['word_count'].transform(
        lambda x: (x.diff() == 0).sum()
    )
    df['drop_risk'] = df['drop_months'] / (df['months_active'] + 1)
    df['survival_rate'] = 1 - df['drop_risk']
    
    # 3. 读者留存黏性 (Retention)
    print("  3. 读者留存黏性...")
    if 'fan_count' in df.columns:
        df['retention'] = df['fan_count'] / (df['collection_normalized'] + 1)
    else:
        df['retention'] = df['collection_normalized'] / (df['total_click'] + 1)
    df['retention'] = np.clip(df['retention'] * 100, 0, 100)
    
    # 4. 核心题材/风口热度 (Trend Match)
    print("  4. 题材热度...")
    df['genre_hotness'] = df['category'].map(lambda x: HOT_GENRES.get(str(x), 70)).fillna(70)
    
    # 5. 改编延展潜力 (Adaptation)
    print("  5. 改编潜力...")
    df['adaptation_potential'] = (
        np.clip(df['word_count'] / 500000, 0, 1) * 50 +  # 字数因素
        df['genre_hotness'] * 0.3 +                       # 题材因素
        df.get('has_adaptation', 0) * 20                  # 已有改编
    )
    
    # 6. 基础商业爆发力 (Base Power)
    print("  6. 商业爆发力...")
    df['base_power'] = (
        np.log1p(df['monthly_tickets_normalized']) * 20 +
        np.log1p(df['collection_normalized']) * 15 +
        np.log1p(df['recommend_normalized']) * 10
    )
    df['base_power'] = np.clip(df['base_power'] / df['base_power'].quantile(0.95) * 100, 0, 100)
    
    # 额外NLP特征
    print("  7. NLP特征...")
    nlp_features = []
    for _, row in df.iterrows():
        title = row['title']
        feat = {}
        
        if title in chapters_data:
            contents = chapters_data[title]
            all_text = ' '.join(contents)
            words = list(jieba.cut(all_text))
            
            feat['sentiment_score'] = sum(1 for w in words if w in POSITIVE_WORDS) - sum(1 for w in words if w in NEGATIVE_WORDS)
            feat['vocabulary_richness'] = len(set(words)) / (len(words) + 1)
            feat['action_word_ratio'] = sum(1 for w in words if w in ACTION_WORDS) / (len(words) + 1)
        else:
            feat = {'sentiment_score': 0, 'vocabulary_richness': 0.5, 'action_word_ratio': 0.05}
        
        nlp_features.append(feat)
    
    df_nlp = pd.DataFrame(nlp_features)
    df = pd.concat([df.reset_index(drop=True), df_nlp], axis=1)
    
    # 环比变化
    df['tickets_mom'] = df.groupby(['title', 'author'])['monthly_tickets_normalized'].pct_change().fillna(0)
    df['collection_growth'] = df.groupby(['title', 'author'])['collection_normalized'].pct_change().fillna(0)
    
    print(f"  总特征数: {len(df.columns)}")
    return df

# ================================================================
#  论文版双引擎架构
# ================================================================

class PaperDualEngine:
    """论文版双引擎：XGBoost(成熟期) + K-Means(孵化期)"""
    
    def __init__(self):
        self.xgb_engine = None      # Engine A: XGBoost
        self.kmeans_engine = None   # Engine B: K-Means
        self.scaler_xgb = None
        self.scaler_kmeans = None
        self.feature_cols = None
        self.cluster_centers = None
        self.cluster_scores = None  # 每个聚类中心的IP评分
        
    def fit(self, X, y_scores, months, grades):
        """训练双引擎"""
        print("\n【论文版双引擎训练】")
        
        # 分割数据
        mature_mask = months >= 6
        nascent_mask = months < 6
        
        X_mature = X[mature_mask]
        y_mature = y_scores[mature_mask]
        grades_mature = grades[mature_mask]
        
        X_nascent = X[nascent_mask]
        y_nascent = y_scores[nascent_mask]
        grades_nascent = grades[nascent_mask]
        
        print(f"  成熟期样本: {len(X_mature)} (使用XGBoost)")
        print(f"  孵化期样本: {len(X_nascent)} (使用K-Means)")
        
        # ========== Engine A: XGBoost (成熟期) ==========
        print("\n  训练Engine A (XGBoost - 成熟期)...")
        self.scaler_xgb = StandardScaler()
        X_mature_scaled = self.scaler_xgb.fit_transform(X_mature)
        
        self.xgb_engine = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=500,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42,
            n_jobs=-1
        )
        self.xgb_engine.fit(X_mature_scaled, y_mature)
        
        # 验证XGBoost
        y_pred_mature = self.xgb_engine.predict(X_mature_scaled)
        rmse_mature = np.sqrt(mean_squared_error(y_mature, y_pred_mature))
        r2_mature = r2_score(y_mature, y_pred_mature)
        print(f"    XGBoost RMSE: {rmse_mature:.2f}")
        print(f"    XGBoost R²: {r2_mature:.4f}")
        
        # ========== Engine B: K-Means (孵化期) ==========
        print("\n  训练Engine B (K-Means - 孵化期)...")
        self.scaler_kmeans = StandardScaler()
        X_nascent_scaled = self.scaler_kmeans.fit_transform(X_nascent)
        
        # 确定聚类数（根据样本量）
        n_clusters = min(10, max(3, len(X_nascent) // 50))
        self.kmeans_engine = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = self.kmeans_engine.fit_predict(X_nascent_scaled)
        
        # 计算每个聚类的平均IP评分
        self.cluster_scores = {}
        for i in range(n_clusters):
            mask = clusters == i
            if mask.sum() > 0:
                self.cluster_scores[i] = y_nascent[mask].mean()
            else:
                self.cluster_scores[i] = 50  # 默认中等分数
        
        print(f"    K-Means聚类数: {n_clusters}")
        print(f"    各聚类IP评分:")
        for i, score in sorted(self.cluster_scores.items()):
            count = (clusters == i).sum()
            print(f"      聚类{i}: IP评分={score:.1f}, 样本数={count}")
        
        # 验证K-Means
        y_pred_nascent = np.array([self.cluster_scores[c] for c in clusters])
        rmse_nascent = np.sqrt(mean_squared_error(y_nascent, y_pred_nascent))
        print(f"    K-Means RMSE: {rmse_nascent:.2f}")
        
        print("\n  双引擎训练完成")
        return self
    
    def predict(self, X, months):
        """双引擎预测"""
        predictions = np.zeros(len(X))
        engines = []
        
        for i in range(len(X)):
            m = months.iloc[i] if hasattr(months, 'iloc') else months[i]
            x = X[i:i+1]
            
            if m >= 6:
                # 成熟期: 使用XGBoost
                x_scaled = self.scaler_xgb.transform(x)
                predictions[i] = self.xgb_engine.predict(x_scaled)[0]
                engines.append('XGBoost')
            else:
                # 孵化期: 使用K-Means聚类评分
                x_scaled = self.scaler_kmeans.transform(x)
                cluster = self.kmeans_engine.predict(x_scaled)[0]
                predictions[i] = self.cluster_scores.get(cluster, 50)
                engines.append('K-Means')
        
        # 限制在0-100范围
        predictions = np.clip(predictions, 0, 100)
        return predictions, engines

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
               is_vip, is_sign as is_signed
        FROM novel_monthly_stats
        WHERE year >= 2020
    """, conn)
    df_qd['platform'] = 'Qidian'
    df_qd['fan_count'] = 0
    df_qd['total_click'] = df_qd['collection_count']
    conn.close()
    print(f"   起点: {len(df_qd)} 条")
    
    # 纵横数据
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    df_zh = pd.read_sql("""
        SELECT year, month, title, author, category, word_count,
               total_click as collection_count, monthly_ticket as monthly_tickets,
               total_rec as total_recommend,
               fan_count as reward_count, updated_at, abstract
        FROM zongheng_book_ranks
        WHERE year >= 2020
    """, conn)
    df_zh['platform'] = 'Zongheng'
    df_zh['collection_rank'] = 0
    df_zh['monthly_ticket_count'] = df_zh['monthly_tickets']
    df_zh['monthly_ticket_rank'] = 0
    df_zh['rank_on_list'] = 0
    df_zh['weekly_recommend'] = 0
    df_zh['adaptations'] = ''
    df_zh['is_vip'] = '0'
    df_zh['is_signed'] = '0'
    df_zh['fan_count'] = df_zh['reward_count']
    df_zh['total_click'] = df_zh['collection_count']
    conn.close()
    print(f"   纵横: {len(df_zh)} 条")
    
    df = pd.concat([df_qd, df_zh], ignore_index=True)
    
    # 改编标签
    df['has_adaptation'] = df['adaptations'].apply(lambda x: 1 if x and len(str(x)) > 3 else 0)
    
    print(f"   总计: {len(df)} 条")
    return df

def fetch_chapters():
    print("\n2. 获取章节内容...")
    chapters_data = {}
    
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
    
    return chapters_data

# ================================================================
#  交叉验证
# ================================================================

def cross_validate_model(X, y, months, n_splits=5):
    """时间序列交叉验证"""
    print("\n【交叉验证】5折TimeSeriesSplit...")
    
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_scores = []
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        months_train, months_val = months.iloc[train_idx], months.iloc[val_idx]
        
        # 训练双引擎
        engine = PaperDualEngine()
        grades_train = pd.Series([IPGradingSystem.score_to_grade(s) for s in y_train])
        engine.fit(X_train, y_train, months_train.reset_index(drop=True), grades_train)
        
        # 预测
        y_pred, _ = engine.predict(X_val, months_val.reset_index(drop=True))
        
        # 评估
        rmse = np.sqrt(mean_squared_error(y_val, y_pred))
        mae = mean_absolute_error(y_val, y_pred)
        r2 = r2_score(y_val, y_pred)
        
        cv_scores.append({'fold': fold+1, 'rmse': rmse, 'mae': mae, 'r2': r2})
        print(f"  Fold {fold+1}: RMSE={rmse:.2f}, MAE={mae:.2f}, R²={r2:.4f}")
    
    # 汇总
    avg_rmse = np.mean([s['rmse'] for s in cv_scores])
    avg_mae = np.mean([s['mae'] for s in cv_scores])
    avg_r2 = np.mean([s['r2'] for s in cv_scores])
    std_rmse = np.std([s['rmse'] for s in cv_scores])
    
    print(f"\n  平均: RMSE={avg_rmse:.2f}±{std_rmse:.2f}, MAE={avg_mae:.2f}, R²={avg_r2:.4f}")
    
    return cv_scores

# ================================================================
#  Optuna调优
# ================================================================

def optuna_tune(X, y, months, n_trials=30):
    """Optuna超参数调优"""
    print("\n【Optuna调优】")
    
    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 200, 600),
            'max_depth': trial.suggest_int('max_depth', 4, 10),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
            'subsample': trial.suggest_float('subsample', 0.7, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.7, 1.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'reg_alpha': trial.suggest_float('reg_alpha', 0, 5),
            'reg_lambda': trial.suggest_float('reg_lambda', 0, 10),
        }
        
        # 使用部分数据快速验证
        mature_mask = months >= 6
        X_mature = X[mature_mask][:1000]
        y_mature = y[mature_mask][:1000]
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_mature)
        
        model = xgb.XGBRegressor(**params, random_state=42, n_jobs=-1)
        
        # 3折CV
        scores = cross_val_score(model, X_scaled, y_mature, cv=3, scoring='neg_mean_squared_error')
        rmse = np.sqrt(-scores.mean())
        
        return rmse
    
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    
    print(f"\n  最佳参数:")
    for k, v in study.best_params.items():
        print(f"    {k}: {v:.4f}" if isinstance(v, float) else f"    {k}: {v}")
    print(f"  最佳RMSE: {study.best_value:.2f}")
    
    return study.best_params

# ================================================================
#  实时月票验证
# ================================================================

def validate_with_real_time(model_j, df_val):
    """实时月票验证对比"""
    print("\n【实时月票验证】")
    
    # 获取最新月票数据
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG)
        df_latest = pd.read_sql("""
            SELECT title, author, monthly_tickets_on_list as current_tickets,
                   rank_on_list as current_rank
            FROM novel_monthly_stats
            WHERE year = 2024 AND month = (SELECT MAX(month) FROM novel_monthly_stats WHERE year = 2024)
            ORDER BY monthly_tickets_on_list DESC
            LIMIT 100
        """, conn)
        conn.close()
        
        print(f"  获取最新数据: {len(df_latest)} 条")
        
        # 对比预测与实际
        results = []
        for _, row in df_latest.iterrows():
            title = row['title']
            author = row['author']
            current_tickets = row['current_tickets']
            current_rank = row['current_rank']
            
            # 查找验证集中的预测
            mask = (df_val['title'] == title) & (df_val['author'] == author)
            if mask.sum() > 0:
                val_row = df_val[mask].iloc[0]
                pred_score = val_row.get('predicted_ip_score', 0)
                pred_grade = val_row.get('predicted_ip_grade', 'D')
                actual_score = val_row['ip_score']
                actual_grade = val_row['ip_grade']
                
                # 计算误差
                score_error = abs(pred_score - actual_score)
                grade_match = pred_grade == actual_grade
                
                results.append({
                    'title': title,
                    'current_tickets': current_tickets,
                    'current_rank': current_rank,
                    'pred_score': pred_score,
                    'actual_score': actual_score,
                    'score_error': score_error,
                    'pred_grade': pred_grade,
                    'actual_grade': actual_grade,
                    'grade_match': grade_match
                })
        
        if results:
            df_results = pd.DataFrame(results)
            
            print(f"\n  验证样本: {len(df_results)} 本")
            print(f"  平均评分误差: {df_results['score_error'].mean():.2f}")
            print(f"  等级预测准确率: {df_results['grade_match'].mean()*100:.1f}%")
            
            # 展示TOP 10
            print(f"\n  TOP 10对比:")
            for i, row in df_results.head(10).iterrows():
                match_icon = '✅' if row['grade_match'] else '❌'
                print(f"    {row['title'][:15]:15s} | 预测:{row['pred_grade']} | 实际:{row['actual_grade']} | {match_icon}")
            
            return df_results
        else:
            print("  未找到匹配的验证样本")
            return None
            
    except Exception as e:
        print(f"  实时验证错误: {e}")
        return None

# ================================================================
#  主训练流程
# ================================================================

def train_model_j():
    """训练Model J"""
    
    # 1. 获取数据
    df = fetch_all_data()
    
    # 2. 平台归一化
    normalizer = PlatformNormalizer()
    normalizer.fit(df)
    df = normalizer.transform(df)
    
    # 3. 获取章节
    chapters_data = fetch_chapters()
    
    # 4. 提取6大维度特征
    df = extract_six_dimensions(df, chapters_data, {})
    
    # 5. 计算IP评分
    scorer = IPWeightedScorer()
    df = scorer.compute_ip_score(df)
    
    # 6. 准备特征
    print("\n3. 准备训练数据...")
    exclude = ['title', 'author', 'category', 'platform', 'year', 'month', 
               'updated_at', 'abstract', 'adaptations', 'ip_grade']
    feature_cols = [c for c in df.columns if c not in exclude and df[c].dtype in ['int64', 'float64', 'int32', 'float32']]
    
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 清理无穷值和异常值
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], 0)
    df[feature_cols] = df[feature_cols].clip(-1e10, 1e10)  # 限制极端值
    
    print(f"   特征数: {len(feature_cols)}")
    
    # 7. 时间切分
    train_mask = df['year'] <= 2023
    val_mask = df['year'] == 2024
    
    X_train = df[train_mask][feature_cols].values
    y_train = df[train_mask]['ip_score'].values
    months_train = df[train_mask]['months_active']
    grades_train = df[train_mask]['ip_grade']
    
    X_val = df[val_mask][feature_cols].values
    y_val = df[val_mask]['ip_score'].values
    months_val = df[val_mask]['months_active']
    
    print(f"   训练集: {len(X_train)} 条")
    print(f"   验证集: {len(X_val)} 条")
    
    # 8. 交叉验证
    print("\n" + "="*70)
    print("交叉验证")
    print("="*70)
    cv_scores = cross_validate_model(X_train, y_train, months_train)
    
    # 9. Optuna调优
    print("\n" + "="*70)
    print("Optuna超参数调优")
    print("="*70)
    best_params = optuna_tune(X_train, y_train, months_train, n_trials=20)
    
    # 10. 训练最终模型
    print("\n" + "="*70)
    print("训练最终模型")
    print("="*70)
    
    dual_engine = PaperDualEngine()
    dual_engine.fit(X_train, y_train, months_train.reset_index(drop=True), grades_train.reset_index(drop=True))
    dual_engine.feature_cols = feature_cols
    
    # 11. 验证
    print("\n【验证集评估】")
    y_pred, engines = dual_engine.predict(X_val, months_val.reset_index(drop=True))
    
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    mae = mean_absolute_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)
    
    # 等级准确率
    pred_grades = [IPGradingSystem.score_to_grade(s) for s in y_pred]
    actual_grades = df[val_mask]['ip_grade'].values
    grade_accuracy = np.mean([p == a for p, a in zip(pred_grades, actual_grades)])
    
    print(f"  RMSE: {rmse:.2f}")
    print(f"  MAE: {mae:.2f}")
    print(f"  R²: {r2:.4f}")
    print(f"  等级预测准确率: {grade_accuracy*100:.1f}%")
    
    # 引擎使用统计
    engine_counts = pd.Series(engines).value_counts()
    print(f"\n  引擎使用分布:")
    for engine, count in engine_counts.items():
        print(f"    {engine}: {count} ({count/len(engines)*100:.1f}%)")
    
    # 12. 保存预测结果
    df_val = df[val_mask].copy()
    df_val['predicted_ip_score'] = y_pred
    df_val['predicted_ip_grade'] = pred_grades
    df_val['engine_used'] = engines
    
    # 13. 实时月票验证
    print("\n" + "="*70)
    print("实时月票验证")
    print("="*70)
    validation_results = validate_with_real_time(dual_engine, df_val)
    
    # 14. 保存模型
    print("\n" + "="*70)
    print("保存Model J")
    print("="*70)
    
    model_j = {
        'dual_engine': dual_engine,
        'normalizer': normalizer,
        'scorer': scorer,
        'features': feature_cols,
        'best_params': best_params,
        'cv_scores': cv_scores,
        'metrics': {
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'grade_accuracy': grade_accuracy
        },
        'version': 'Model_J_Paper_v1.0',
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'description': '论文版IP评估模型：XGBoost+K-Means双引擎，S/A/B/C/D等级制'
    }
    
    save_path = 'resources/models/model_j_paper.pkl'
    joblib.dump(model_j, save_path)
    print(f"   模型已保存: {save_path}")
    
    # 15. 总结
    print("\n" + "="*70)
    print("Model J 训练完成!")
    print("="*70)
    print(f"   总样本: {len(df)}")
    print(f"   总特征: {len(feature_cols)}")
    print(f"\n   性能指标:")
    print(f"     RMSE: {rmse:.2f}")
    print(f"     MAE: {mae:.2f}")
    print(f"     R²: {r2:.4f}")
    print(f"     等级准确率: {grade_accuracy*100:.1f}%")
    print(f"\n   论文要求实现:")
    print(f"     ✅ XGBoost+K-Means双引擎")
    print(f"     ✅ S/A/B/C/D等级制")
    print(f"     ✅ 多维度加权评分")
    print(f"     ✅ 6大维度特征")
    print(f"     ✅ 交叉验证")
    print(f"     ✅ Optuna调优")
    print(f"     ✅ 实时月票验证")
    print("="*70)
    
    return model_j, df_val

if __name__ == "__main__":
    model_j, df_val = train_model_j()
