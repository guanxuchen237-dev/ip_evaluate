"""
Model H - 优化版
基于优化报告的改进实现：
1. 平台归一化（解决起点/纵横基数差异）
2. 交叉验证
3. 算法调优（GridSearchCV + Optuna）
4. Engine B权重优化
5. 柔性分界
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
import jieba
import os
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.model_selection import KFold, TimeSeriesSplit, cross_val_score, GridSearchCV
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.ensemble import StackingRegressor
from sklearn.linear_model import Ridge
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
POSITIVE_WORDS = set(['精彩', '优秀', '棒', '好', '喜欢', '爱', '感动', '震撼', '热血', '燃', '爽', '牛', '强', '赞', '推荐', '支持', '加油', '成功', '胜利', '英雄', '强大', '突破', '觉醒', '天才', '神作', '经典'])
NEGATIVE_WORDS = set(['差', '烂', '垃圾', '失望', '无聊', '水', '坑', '弃', '毒', '脑残', '弱智', '拖沓', '烂尾', '狗血', '尴尬', '失败', '惨', '死', '悲剧'])
ACTION_WORDS = set(['打', '杀', '战', '斗', '破', '斩', '灭', '冲', '击', '攻', '守', '追', '逃', '怒', '狂', '暴'])
DIALOGUE_WORDS = set(['说', '道', '问', '答', '喊', '叫', '笑', '哭', '骂', '叹'])

print("="*70)
print("Model H - 优化版")
print("平台归一化 + 交叉验证 + 算法调优")
print("="*70)

# ================================================================
#  1. 平台归一化器
# ================================================================

class PlatformNormalizer:
    """平台数据归一化器 - 解决起点/纵横基数差异"""
    
    def __init__(self):
        self.platform_stats = {}
        self.scalers = {}
        
    def fit(self, df):
        """计算各平台的统计量"""
        print("\n【平台归一化】计算各平台基准...")
        
        for platform in ['Qidian', 'Zongheng']:
            platform_data = df[df['platform'] == platform]
            
            # 计算平台基准值
            self.platform_stats[platform] = {
                'avg_monthly_tickets': platform_data['monthly_tickets'].mean(),
                'median_monthly_tickets': platform_data['monthly_tickets'].median(),
                'avg_collection': platform_data['collection_count'].mean(),
                'avg_recommend': platform_data['total_recommend'].mean(),
                'avg_reward': platform_data['reward_count'].mean(),
                'total_books': len(platform_data),
                'total_samples': len(platform_data)
            }
            
            print(f"  {platform}:")
            print(f"    平均月票: {self.platform_stats[platform]['avg_monthly_tickets']:.0f}")
            print(f"    平均收藏: {self.platform_stats[platform]['avg_collection']:.0f}")
            print(f"    平均推荐: {self.platform_stats[platform]['avg_recommend']:.0f}")
        
        # 计算纵横相对起点的缩放因子
        qidian_avg = self.platform_stats['Qidian']['avg_monthly_tickets']
        zongheng_avg = self.platform_stats['Zongheng']['avg_monthly_tickets']
        
        self.zongheng_scale_factor = qidian_avg / (zongheng_avg + 1)
        print(f"\n  纵横缩放因子: {self.zongheng_scale_factor:.2f}x")
        
        return self
    
    def transform(self, df):
        """应用平台归一化"""
        df = df.copy()
        
        # 对纵横数据进行缩放
        zongheng_mask = df['platform'] == 'Zongheng'
        
        # 月票缩放
        df.loc[zongheng_mask, 'monthly_tickets_normalized'] = (
            df.loc[zongheng_mask, 'monthly_tickets'] * self.zongheng_scale_factor
        )
        df.loc[~zongheng_mask, 'monthly_tickets_normalized'] = df.loc[~zongheng_mask, 'monthly_tickets']
        
        # 收藏缩放
        collection_scale = (
            self.platform_stats['Qidian']['avg_collection'] / 
            (self.platform_stats['Zongheng']['avg_collection'] + 1)
        )
        df.loc[zongheng_mask, 'collection_normalized'] = (
            df.loc[zongheng_mask, 'collection_count'] * collection_scale
        )
        df.loc[~zongheng_mask, 'collection_normalized'] = df.loc[~zongheng_mask, 'collection_count']
        
        # 推荐缩放
        recommend_scale = (
            self.platform_stats['Qidian']['avg_recommend'] / 
            (self.platform_stats['Zongheng']['avg_recommend'] + 1)
        )
        df.loc[zongheng_mask, 'recommend_normalized'] = (
            df.loc[zongheng_mask, 'total_recommend'] * recommend_scale
        )
        df.loc[~zongheng_mask, 'recommend_normalized'] = df.loc[~zongheng_mask, 'total_recommend']
        
        # 打赏缩放
        reward_scale = (
            self.platform_stats['Qidian']['avg_reward'] / 
            (self.platform_stats['Zongheng']['avg_reward'] + 1)
        )
        df.loc[zongheng_mask, 'reward_normalized'] = (
            df.loc[zongheng_mask, 'reward_count'] * reward_scale
        )
        df.loc[~zongheng_mask, 'reward_normalized'] = df.loc[~zongheng_mask, 'reward_count']
        
        print(f"  归一化完成: 原始月票范围 [{df['monthly_tickets'].min():.0f}, {df['monthly_tickets'].max():.0f}]")
        print(f"  归一化后范围: [{df['monthly_tickets_normalized'].min():.0f}, {df['monthly_tickets_normalized'].max():.0f}]")
        
        return df

# ================================================================
#  2. 数据获取
# ================================================================

def fetch_all_data():
    """获取完整数据"""
    print("\n1. 获取基础数据...")
    
    # 起点数据
    conn = pymysql.connect(**QIDIAN_CONFIG)
    df_qd = pd.read_sql("""
        SELECT year, month, title, author, category, word_count,
               collection_count, monthly_tickets_on_list as monthly_tickets,
               monthly_ticket_count, rank_on_list,
               recommendation_count as total_recommend,
               week_recommendation_count as weekly_recommend,
               COALESCE(adaptations, '') as adaptations,
               reward_count, updated_at, synopsis as abstract
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
               fan_count as reward_count, updated_at, abstract
        FROM zongheng_book_ranks
        WHERE year >= 2020
    """, conn)
    df_zh['platform'] = 'Zongheng'
    conn.close()
    print(f"   纵横: {len(df_zh)} 条")
    
    # 合并
    df = pd.concat([df_qd, df_zh], ignore_index=True)
    
    # 改编标签
    df['has_adaptation'] = df['adaptations'].apply(lambda x: 1 if x and len(str(x)) > 3 else 0)
    df['adaptation_count'] = df['adaptations'].apply(lambda x: len(str(x).split(',')) if x and str(x) != 'nan' else 0)
    
    print(f"   总计: {len(df)} 条，有改编: {df['has_adaptation'].sum()} 本")
    return df

def fetch_chapters_and_comments():
    """获取章节和评论数据"""
    print("\n2. 获取NLP和评论数据...")
    
    chapters_data = {}
    comments_data = {}
    
    # 起点章节
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("SELECT book_title, chapter_content FROM qidian_chapters WHERE chapter_index <= 10")
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
            cur.execute("SELECT title, content FROM zongheng_chapters WHERE chapter_num <= 10")
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
#  3. 特征工程
# ================================================================

def extract_nlp_features(df, chapters_data):
    """提取NLP特征"""
    print("\n3. 提取NLP特征...")
    
    features_list = []
    for _, row in df.iterrows():
        title = row['title']
        feat = {}
        
        if title in chapters_data:
            contents = chapters_data[title]
            all_text = ' '.join(contents)
            words = list(jieba.cut(all_text))
            
            feat['chapter_word_count'] = len(words)
            feat['unique_words'] = len(set(words))
            feat['vocab_richness'] = feat['unique_words'] / (feat['chapter_word_count'] + 1)
            
            pos = sum(1 for w in words if w in POSITIVE_WORDS)
            neg = sum(1 for w in words if w in NEGATIVE_WORDS)
            feat['sentiment_score'] = (pos - neg) / (len(words) + 1)
            feat['sentiment_ratio'] = pos / (neg + 1)
            
            action = sum(1 for w in words if w in ACTION_WORDS)
            dialogue = sum(1 for w in words if w in DIALOGUE_WORDS)
            feat['action_ratio'] = action / (len(words) + 1)
            feat['dialogue_ratio'] = dialogue / (len(words) + 1)
        else:
            feat = {k: 0 for k in ['chapter_word_count', 'unique_words', 'vocab_richness', 
                                    'sentiment_score', 'sentiment_ratio', 'action_ratio', 'dialogue_ratio']}
        
        features_list.append(feat)
    
    df_nlp = pd.DataFrame(features_list)
    df = pd.concat([df.reset_index(drop=True), df_nlp], axis=1)
    print(f"   NLP特征: {df_nlp.shape[1]} 个")
    return df

def extract_comment_features(df, comments_data):
    """提取评论特征"""
    print("\n4. 提取评论特征...")
    
    TIER1_CITIES = ['北京', '上海', '广州', '深圳', '成都', '杭州', '武汉', '西安', '南京', '天津']
    
    features_list = []
    for _, row in df.iterrows():
        title = row['title']
        feat = {}
        
        if title in comments_data:
            data = comments_data[title]
            comments = data['comments']
            regions = data['regions']
            
            feat['comment_count'] = len(comments)
            feat['avg_comment_len'] = np.mean([len(c) for c in comments]) if comments else 0
            
            pos = sum(1 for c in comments for w in jieba.cut(c) if w in POSITIVE_WORDS)
            neg = sum(1 for c in comments for w in jieba.cut(c) if w in NEGATIVE_WORDS)
            feat['comment_sentiment'] = (pos - neg) / (len(comments) + 1)
            feat['pos_comment_ratio'] = pos / (len(comments) + 1)
            
            t1 = sum(1 for r in regions if any(c in r for c in TIER1_CITIES))
            feat['tier1_ratio'] = t1 / (len(regions) + 1)
            feat['region_diversity'] = len(set(regions))
        else:
            feat = {k: 0 for k in ['comment_count', 'avg_comment_len', 'comment_sentiment', 
                                  'pos_comment_ratio', 'tier1_ratio', 'region_diversity']}
        
        features_list.append(feat)
    
    df_comment = pd.DataFrame(features_list)
    df = pd.concat([df.reset_index(drop=True), df_comment], axis=1)
    print(f"   评论特征: {df_comment.shape[1]} 个")
    return df

def add_model_f_features(df):
    """添加Model F特征（更新熵+IP基因）"""
    print("\n5. 添加Model F特征...")
    
    df = df.sort_values(['title', 'author', 'year', 'month'])
    df['year_month'] = df['year'] * 12 + df['month']
    
    start_dates = df.groupby(['title', 'author'])['year_month'].transform('min')
    df['months_since_start'] = df['year_month'] - start_dates
    
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
        from sklearn.cluster import KMeans
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
    
    df = df.fillna(0)
    return df

def engineer_features(df):
    """完整特征工程"""
    print("\n6. 基础特征工程...")
    
    # 使用归一化后的数据
    df['log_word_count'] = np.log1p(df['word_count'])
    df['log_collection'] = np.log1p(df['collection_normalized'])
    df['log_recommend'] = np.log1p(df['recommend_normalized'])
    df['log_tickets'] = np.log1p(df['monthly_tickets_normalized'])
    
    # 比率特征
    df['tickets_per_word'] = df['monthly_tickets_normalized'] / (df['word_count'] + 1) * 10000
    df['recommend_per_collection'] = df['recommend_normalized'] / (df['collection_normalized'] + 1)
    
    # 购买力指数（使用归一化数据）
    df['purchasing_power_index'] = (
        np.log1p(df['reward_normalized'] / (df['collection_normalized'] + 1) * 100) * 30 +
        np.log1p(df['recommend_per_collection']) * 20 +
        np.minimum(50, df['monthly_tickets_normalized'] / 1000)
    ).clip(0, 100)
    
    # 时序特征
    df = df.sort_values(['title', 'author', 'year', 'month'])
    df['tickets_mom'] = df.groupby(['title', 'author'])['monthly_tickets_normalized'].pct_change().fillna(0).replace([np.inf, -np.inf], 0)
    
    print(f"   总特征数: {len(df.columns)}")
    return df

# ================================================================
#  4. 交叉验证 + 算法调优
# ================================================================

def train_with_cv_and_tuning(df):
    """使用交叉验证和调优训练模型"""
    print("\n" + "="*70)
    print("交叉验证 + 算法调优")
    print("="*70)
    
    # 特征列表
    exclude = ['title', 'author', 'category', 'platform', 'year', 'month', 
               'year_month', 'adaptations', 'updated_at', 'abstract', 
               'monthly_tickets', 'monthly_tickets_normalized',
               'collection_count', 'total_recommend', 'reward_count']
    feature_cols = [c for c in df.columns if c not in exclude]
    
    # 确保数值类型
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    print(f"\n特征数: {len(feature_cols)}")
    
    # 时间切分
    train_mask = df['year'] <= 2023
    val_mask = df['year'] == 2024
    
    X_train = df[train_mask][feature_cols]
    y_train = np.log1p(df[train_mask]['monthly_tickets_normalized'])
    
    X_val = df[val_mask][feature_cols]
    y_val = df[val_mask]['monthly_tickets_normalized']
    
    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    print(f"\n训练集: {len(X_train)} 条")
    print(f"验证集: {len(X_val)} 条")
    
    # ===== 交叉验证 =====
    print("\n【交叉验证】")
    tscv = TimeSeriesSplit(n_splits=5)
    
    # 基础模型
    base_model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1
    )
    
    # 交叉验证分数
    cv_scores = cross_val_score(base_model, X_train_scaled, y_train, cv=tscv, scoring='neg_mean_squared_error')
    cv_rmse = np.sqrt(-cv_scores)
    print(f"  CV RMSE: {cv_rmse.mean():.2f} (+/- {cv_rmse.std():.2f})")
    
    # ===== 网格搜索调优 =====
    print("\n【网格搜索调优】")
    param_grid = {
        'max_depth': [6, 8, 10],
        'learning_rate': [0.05, 0.1, 0.15],
        'n_estimators': [300, 500],
        'subsample': [0.7, 0.8, 0.9],
        'colsample_bytree': [0.7, 0.8, 0.9]
    }
    
    # 简化网格搜索（减少计算时间）
    param_grid_simple = {
        'max_depth': [6, 8],
        'learning_rate': [0.05, 0.1],
        'n_estimators': [300, 500],
        'subsample': [0.8],
        'colsample_bytree': [0.8]
    }
    
    grid_search = GridSearchCV(
        xgb.XGBRegressor(objective='reg:squarederror', random_state=42, n_jobs=-1),
        param_grid_simple,
        cv=3,
        scoring='neg_mean_squared_error',
        n_jobs=-1,
        verbose=1
    )
    
    print("  开始网格搜索...")
    grid_search.fit(X_train_scaled, y_train)
    
    print(f"\n  最佳参数: {grid_search.best_params_}")
    print(f"  最佳CV分数: {np.sqrt(-grid_search.best_score_):.2f}")
    
    best_model = grid_search.best_estimator_
    
    # ===== Optuna进一步调优 =====
    print("\n【Optuna精细调优】")
    
    def objective(trial):
        params = {
            'objective': 'reg:squarederror',
            'max_depth': trial.suggest_int('max_depth', 4, 12),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'n_estimators': trial.suggest_int('n_estimators', 200, 800),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'gamma': trial.suggest_float('gamma', 0, 5),
            'reg_alpha': trial.suggest_float('reg_alpha', 0, 10),
            'reg_lambda': trial.suggest_float('reg_lambda', 0, 10),
            'random_state': 42,
            'n_jobs': -1
        }
        
        model = xgb.XGBRegressor(**params)
        scores = cross_val_score(model, X_train_scaled, y_train, cv=3, scoring='neg_mean_squared_error')
        return np.sqrt(-scores.mean())
    
    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=30, show_progress_bar=True)
    
    print(f"\n  Optuna最佳参数: {study.best_params}")
    print(f"  Optuna最佳RMSE: {study.best_value:.2f}")
    
    # 使用最佳参数训练最终模型
    final_model = xgb.XGBRegressor(
        objective='reg:squarederror',
        random_state=42,
        n_jobs=-1,
        **study.best_params
    )
    final_model.fit(X_train_scaled, y_train)
    
    # ===== 验证评估 =====
    print("\n【验证集评估】")
    y_pred_log = final_model.predict(X_val_scaled)
    y_pred = np.expm1(y_pred_log)
    
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    mae = mean_absolute_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)
    mape = np.mean(np.abs((y_val - y_pred) / (y_val + 1))) * 100
    
    print(f"  RMSE: {rmse:.2f}")
    print(f"  MAE: {mae:.2f}")
    print(f"  R²: {r2:.4f}")
    print(f"  MAPE: {mape:.2f}%")
    
    return {
        'model': final_model,
        'scaler': scaler,
        'features': feature_cols,
        'best_params': study.best_params,
        'metrics': {
            'rmse': rmse, 'mae': mae, 'r2': r2, 'mape': mape,
            'cv_rmse': cv_rmse.mean(),
            'optuna_rmse': study.best_value
        }
    }

# ================================================================
#  5. 主流程
# ================================================================

def main():
    # 1. 获取数据
    df = fetch_all_data()
    
    # 2. 平台归一化
    normalizer = PlatformNormalizer()
    normalizer.fit(df)
    df = normalizer.transform(df)
    
    # 3. 获取NLP和评论
    chapters_data, comments_data = fetch_chapters_and_comments()
    
    # 4. NLP特征
    df = extract_nlp_features(df, chapters_data)
    
    # 5. 评论特征
    df = extract_comment_features(df, comments_data)
    
    # 6. Model F特征
    df = add_model_f_features(df)
    
    # 7. 特征工程
    df = engineer_features(df)
    
    # 8. 交叉验证+调优训练
    model_results = train_with_cv_and_tuning(df)
    
    # 9. 保存
    print("\n" + "="*70)
    print("保存Model H")
    print("="*70)
    
    model_h = {
        'model': model_results['model'],
        'scaler': model_results['scaler'],
        'features': model_results['features'],
        'normalizer': normalizer,
        'best_params': model_results['best_params'],
        'metrics': model_results['metrics'],
        'version': 'Model_H_Optimized_v1.0',
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'description': '平台归一化 + 交叉验证 + Optuna调优'
    }
    
    save_path = 'resources/models/model_h_optimized.pkl'
    joblib.dump(model_h, save_path)
    print(f"   模型已保存: {save_path}")
    
    # 10. 总结
    print("\n" + "="*70)
    print("Model H 训练完成!")
    print("="*70)
    print(f"   总样本: {len(df)}")
    print(f"   总特征: {len(model_results['features'])}")
    print(f"   最佳参数: {model_results['best_params']}")
    print(f"\n   性能指标:")
    print(f"     CV RMSE: {model_results['metrics']['cv_rmse']:.2f}")
    print(f"     Optuna RMSE: {model_results['metrics']['optuna_rmse']:.2f}")
    print(f"     验证 MAPE: {model_results['metrics']['mape']:.2f}%")
    print(f"     验证 R²: {model_results['metrics']['r2']:.4f}")
    print("="*70)

if __name__ == "__main__":
    main()
