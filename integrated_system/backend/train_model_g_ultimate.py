"""
Model G - 终极融合版
整合：Model E的完整NLP+评论 + Model F的双引擎+更新熵+IP基因聚类
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
import jieba
import os
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
from scipy.stats import entropy
from datetime import datetime
import re

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
print("Model G - 终极融合版")
print("Model E (NLP+评论) + Model F (双引擎+更新熵+IP基因)")
print("="*70)

# ================================================================
#  1. 获取完整数据（含章节和评论）
# ================================================================

def fetch_all_data():
    """获取完整数据"""
    print("\n1. 获取基础数据...")
    
    # 起点数据（含改编标签）
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
#  2. NLP特征提取
# ================================================================

def extract_nlp_features(df, chapters_data):
    """提取NLP特征"""
    print("\n3. 提取NLP特征...")
    
    TIER1_CITIES = ['北京', '上海', '广州', '深圳', '成都', '杭州', '武汉', '西安', '南京', '天津']
    
    features_list = []
    for _, row in df.iterrows():
        title = row['title']
        feat = {}
        
        if title in chapters_data:
            contents = chapters_data[title]
            all_text = ' '.join(contents)
            words = list(jieba.cut(all_text))
            
            # 基础统计
            feat['chapter_word_count'] = len(words)
            feat['unique_words'] = len(set(words))
            feat['vocab_richness'] = feat['unique_words'] / (feat['chapter_word_count'] + 1)
            
            # 情感
            pos = sum(1 for w in words if w in POSITIVE_WORDS)
            neg = sum(1 for w in words if w in NEGATIVE_WORDS)
            feat['sentiment_score'] = (pos - neg) / (len(words) + 1)
            feat['sentiment_ratio'] = pos / (neg + 1)
            
            # 风格
            action = sum(1 for w in words if w in ACTION_WORDS)
            dialogue = sum(1 for w in words if w in DIALOGUE_WORDS)
            feat['action_ratio'] = action / (len(words) + 1)
            feat['dialogue_ratio'] = dialogue / (len(words) + 1)
            
            # 标题情感
            abstract = str(row.get('abstract', ''))
            abs_words = list(jieba.cut(abstract))
            feat['title_sentiment'] = sum(1 for w in abs_words if w in POSITIVE_WORDS) / (len(abs_words) + 1)
        else:
            feat = {k: 0 for k in ['chapter_word_count', 'unique_words', 'vocab_richness', 
                                    'sentiment_score', 'sentiment_ratio', 'action_ratio', 
                                    'dialogue_ratio', 'title_sentiment']}
        
        features_list.append(feat)
    
    df_nlp = pd.DataFrame(features_list)
    df = pd.concat([df.reset_index(drop=True), df_nlp], axis=1)
    print(f"   NLP特征: {df_nlp.shape[1]} 个")
    return df

# ================================================================
#  3. 评论特征提取
# ================================================================

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
            
            # 情感
            pos = sum(1 for c in comments for w in jieba.cut(c) if w in POSITIVE_WORDS)
            neg = sum(1 for c in comments for w in jieba.cut(c) if w in NEGATIVE_WORDS)
            feat['comment_sentiment'] = (pos - neg) / (len(comments) + 1)
            feat['pos_comment_ratio'] = pos / (len(comments) + 1)
            
            # 地区
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

# ================================================================
#  4. 更新熵 + IP基因聚类（Model F创新点）
# ================================================================

def add_model_f_features(df):
    """添加Model F的特征"""
    print("\n5. 添加Model F特征（更新熵 + IP基因）...")
    
    # 时间排序
    df = df.sort_values(['title', 'author', 'year', 'month'])
    df['year_month'] = df['year'] * 12 + df['month']
    
    # 连载月数
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
        'monthly_tickets': 'mean',
        'collection_count': 'mean',
        'update_regularity': 'first',
        'has_adaptation': 'max'
    }).reset_index()
    
    success_mask = (cluster_data['monthly_tickets'] > 10000) | (cluster_data['has_adaptation'] == 1)
    success_books = cluster_data[success_mask]
    
    if len(success_books) >= 10:
        features = ['word_count', 'monthly_tickets', 'collection_count', 'update_regularity', 'has_adaptation']
        X = success_books[features].fillna(0).values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        kmeans = KMeans(n_clusters=min(5, len(success_books)//2), random_state=42, n_init=10)
        success_books['cluster'] = kmeans.fit_predict(X_scaled)
        
        # 为所有书计算相似度
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
        print(f"   IP基因聚类: {len(success_books)} 成功作品, 平均相似度 {np.mean(sims):.1f}")
    else:
        df['ip_gene_cluster'] = 0
        df['ip_gene_similarity'] = 50
        print(f"   成功作品样本不足 ({len(success_books)}), 跳过聚类")
    
    df = df.fillna(0)
    return df

# ================================================================
#  5. 基础特征工程
# ================================================================

def engineer_base_features(df):
    """基础特征工程"""
    print("\n6. 基础特征工程...")
    
    # 对数变换
    df['log_word_count'] = np.log1p(df['word_count'])
    df['log_collection'] = np.log1p(df['collection_count'])
    df['log_recommend'] = np.log1p(df['total_recommend'])
    
    # 比率
    df['tickets_per_word'] = df['monthly_tickets'] / (df['word_count'] + 1) * 10000
    df['recommend_per_collection'] = df['total_recommend'] / (df['collection_count'] + 1)
    
    # 购买力指数
    df['purchasing_power_index'] = (
        np.log1p(df['reward_count'] / (df['collection_count'] + 1) * 100) * 30 +
        np.log1p(df['recommend_per_collection']) * 20 +
        np.minimum(50, df['monthly_tickets'] / 1000)
    ).clip(0, 100)
    
    # 时序特征
    df = df.sort_values(['title', 'author', 'year', 'month'])
    df['tickets_mom'] = df.groupby(['title', 'author'])['monthly_tickets'].pct_change().fillna(0).replace([np.inf, -np.inf], 0)
    
    print(f"   总特征数: {len(df.columns)}")
    return df

# ================================================================
#  6. 双引擎训练
# ================================================================

def train_dual_engine(df):
    """双引擎训练"""
    print("\n" + "="*70)
    print("双引擎训练")
    print("="*70)
    
    # 特征列表
    exclude = ['title', 'author', 'category', 'platform', 'year', 'month', 
               'year_month', 'adaptations', 'updated_at', 'abstract', 'monthly_tickets']
    feature_cols = [c for c in df.columns if c not in exclude]
    
    # 确保数值类型
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    print(f"   特征数: {len(feature_cols)}")
    print(f"   特征: {feature_cols[:10]}...")
    
    # 时间切分
    train_mask = df['year'] <= 2023
    val_mask = df['year'] == 2024
    
    # 成熟期 vs 孵化期
    mature_mask = df['months_since_start'] >= 6
    immature_mask = df['months_since_start'] < 6
    
    print(f"\n   数据分布:")
    print(f"     训练集: {(train_mask).sum()} 条")
    print(f"     验证集: {(val_mask).sum()} 条")
    print(f"     成熟期(≥6月): {(mature_mask).sum()} 条")
    print(f"     孵化期(<6月): {(immature_mask).sum()} 条")
    
    # Engine A: XGBoost for Mature
    print("\n   【Engine A】XGBoost (成熟期)...")
    mature_train = df[train_mask & mature_mask]
    
    if len(mature_train) > 50:
        X_train = mature_train[feature_cols]
        y_train = np.log1p(mature_train['monthly_tickets'])
        
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        
        dtrain = xgb.DMatrix(X_train_scaled, label=y_train, feature_names=feature_cols)
        
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
        print("   ✓ Engine A训练完成")
    else:
        model_a = None
        scaler = None
        print("   ✗ 成熟期样本不足")
    
    # Engine B: Rule-based for Immature
    print("\n   【Engine B】孵化期评分...")
    engine_b_weights = {
        'tickets_mom': 0.25,
        'update_regularity': 0.20,
        'max_consecutive_months': 0.20,
        'purchasing_power_index': 0.15,
        'ip_gene_similarity': 0.10,
        'sentiment_score': 0.05,
        'comment_sentiment': 0.05
    }
    print(f"   权重: {engine_b_weights}")
    
    # 验证
    print("\n   模型验证...")
    if val_mask.sum() > 0 and model_a is not None:
        val_df = df[val_mask].copy()
        
        preds = []
        for _, row in val_df.iterrows():
            if row['months_since_start'] >= 6:
                X = pd.DataFrame([row[feature_cols].values], columns=feature_cols)
                X_scaled = scaler.transform(X)
                dmatrix = xgb.DMatrix(X_scaled, feature_names=feature_cols)
                pred = np.expm1(model_a.predict(dmatrix))[0]
            else:
                score = sum(row.get(feat, 0) * weight * 100 for feat, weight in engine_b_weights.items())
                pred = score
            preds.append(pred)
        
        val_df['prediction'] = preds
        y_true = val_df['monthly_tickets'].values
        y_pred = val_df['prediction'].values
        
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1))) * 100
        
        print(f"\n   验证集性能:")
        print(f"     RMSE: {rmse:.2f}")
        print(f"     MAE: {mae:.2f}")
        print(f"     R²: {r2:.4f}")
        print(f"     MAPE: {mape:.2f}%")
        
        metrics = {'rmse': rmse, 'mae': mae, 'r2': r2, 'mape': mape}
    else:
        metrics = None
        print("   验证集为空或Engine A未训练")
    
    return {
        'engine_a': {'model': model_a, 'scaler': scaler, 'features': feature_cols},
        'engine_b': {'weights': engine_b_weights},
        'metrics': metrics
    }

# ================================================================
#  7. 主流程
# ================================================================

def main():
    # 1. 获取数据
    df = fetch_all_data()
    
    # 2. 获取NLP和评论
    chapters_data, comments_data = fetch_chapters_and_comments()
    
    # 3. NLP特征
    df = extract_nlp_features(df, chapters_data)
    
    # 4. 评论特征
    df = extract_comment_features(df, comments_data)
    
    # 5. Model F特征
    df = add_model_f_features(df)
    
    # 6. 基础特征
    df = engineer_base_features(df)
    
    # 7. 双引擎训练
    model_results = train_dual_engine(df)
    
    # 8. 保存
    print("\n" + "="*70)
    print("保存Model G")
    print("="*70)
    
    model_g = {
        'engine_a': model_results['engine_a'],
        'engine_b': model_results['engine_b'],
        'metrics': model_results['metrics'],
        'version': 'Model_G_Ultimate_v1.0',
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'description': 'Model E (NLP+评论) + Model F (双引擎+更新熵+IP基因)'
    }
    
    save_path = 'resources/models/model_g_ultimate.pkl'
    joblib.dump(model_g, save_path)
    print(f"   模型已保存: {save_path}")
    
    # 9. 总结
    print("\n" + "="*70)
    print("Model G 训练完成!")
    print("="*70)
    print(f"   总样本: {len(df)}")
    print(f"   总特征: {len(df.columns)}")
    print(f"   有改编: {df['has_adaptation'].sum()} 本")
    print(f"   成熟期: {(df['months_since_start'] >= 6).sum()} 本")
    print(f"   孵化期: {(df['months_since_start'] < 6).sum()} 本")
    
    if model_results['metrics']:
        m = model_results['metrics']
        print(f"\n   性能指标:")
        print(f"     MAPE: {m['mape']:.2f}%")
        print(f"     R²: {m['r2']:.4f}")
    
    print("="*70)

if __name__ == "__main__":
    main()
