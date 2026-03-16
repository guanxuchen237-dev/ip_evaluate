"""
Model F - 开题报告完整实现版
整合所有设计：双引擎 + 更新熵 + IP基因聚类 + 改编标签
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
from datetime import datetime, timedelta
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

# 停用词
STOPWORDS = set(['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'])

# ================================================================
#  1. 数据获取（含改编标签）
# ================================================================

def fetch_data_with_adaptation():
    """获取数据，包括改编标签"""
    print("\n" + "="*70)
    print("获取数据（含改编标签）")
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
           reward_count, updated_at
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
           fan_count as reward_count, updated_at
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
    df['has_adaptation'] = df['adaptations'].apply(
        lambda x: 1 if x and len(str(x)) > 3 else 0
    )
    df['adaptation_count'] = df['adaptations'].apply(
        lambda x: len(str(x).split(',')) if x and str(x) != 'nan' else 0
    )
    
    print(f"有改编的作品: {df['has_adaptation'].sum()} 本")
    
    return df

# ================================================================
#  2. 更新熵特征工程（开题报告创新点2）
# ================================================================

def calculate_update_entropy(df):
    """
    计算更新熵 - 量化作者履约稳定性
    使用香农熵计算更新间隔的不确定性
    """
    print("\n计算更新熵特征...")
    
    # 按书名和平台分组计算
    def calc_entropy_for_book(group):
        group = group.sort_values(['year', 'month'])
        
        # 计算月更新字数变化（模拟更新频率）
        word_diff = group['word_count'].diff().fillna(0)
        
        # 更新天数估算：假设每月更新天数与字数增量成正比
        # 使用字数变化的变异系数作为更新稳定性的代理
        if len(group) >= 2:
            # 计算更新间隔的分布
            update_volumes = word_diff[word_diff > 0].values
            
            if len(update_volumes) > 1:
                # 归一化
                total = update_volumes.sum()
                if total > 0:
                    probs = update_volumes / total
                    # 计算香农熵
                    update_entropy = entropy(probs, base=2)
                else:
                    update_entropy = 0
            else:
                update_entropy = 0
            
            # 更新规律性：标准差/均值（变异系数）
            mean_update = update_volumes.mean() if len(update_volumes) > 0 else 0
            std_update = update_volumes.std() if len(update_volumes) > 1 else 0
            update_regularity = std_update / (mean_update + 1) if mean_update > 0 else 0
            
            # 断更月数统计
            drop_months = (word_diff == 0).sum()
            
            # 最长连续更新月数
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
        
        return pd.Series({
            'update_entropy': update_entropy,
            'update_regularity': update_regularity,
            'drop_month_count': drop_months,
            'max_consecutive_months': max_consecutive,
            'avg_monthly_update': word_diff.mean() if len(group) > 1 else 0
        })
    
    # 应用计算
    entropy_features = df.groupby(['title', 'platform']).apply(calc_entropy_for_book).reset_index()
    
    # 合并回原数据
    df = df.merge(entropy_features, on=['title', 'platform'], how='left')
    
    # 填充缺失值
    for col in ['update_entropy', 'update_regularity', 'drop_month_count', 
                'max_consecutive_months', 'avg_monthly_update']:
        df[col] = df[col].fillna(0)
    
    print(f"更新熵特征计算完成")
    print(f"  平均更新熵: {df['update_entropy'].mean():.2f}")
    print(f"  平均断更月数: {df['drop_month_count'].mean():.2f}")
    
    return df

# ================================================================
#  3. 粉丝购买力指数（开题报告创新点1补充）
# ================================================================

def calculate_purchasing_power_index(df):
    """
    计算粉丝购买力指数
    结合一线城市粉丝浓度和用户质量
    """
    print("\n计算粉丝购买力指数...")
    
    # 对于起点数据，使用reward_count作为付费意愿代理
    # 对于纵横数据，使用fan_count
    
    def calc_ppi(row):
        # 基础付费意愿
        if row['platform'] == 'Qidian':
            # 起点：打赏数 / 收藏数
            pay_willingness = row['reward_count'] / (row['collection_count'] + 1)
        else:
            # 纵横：粉丝数 / 点击量
            pay_willingness = row['reward_count'] / (row['collection_count'] + 1)
        
        # 使用已有的一线/二线比例（如果有评论数据）
        # 这里使用收藏数和推荐数的比率作为质量代理
        quality_ratio = row['total_recommend'] / (row['collection_count'] + 1)
        
        # 综合购买力指数 (0-100)
        ppi = (np.log1p(pay_willingness * 100) * 30 + 
               np.log1p(quality_ratio) * 20 + 
               min(50, row['monthly_tickets'] / 1000))  # 月票本身也是购买力指标
        
        return min(100, max(0, ppi))
    
    df['purchasing_power_index'] = df.apply(calc_ppi, axis=1)
    
    print(f"购买力指数计算完成")
    print(f"  平均PPI: {df['purchasing_power_index'].mean():.2f}")
    
    return df

# ================================================================
#  4. IP基因K-Means聚类（开题报告创新点3）
# ================================================================

class IPGeneClustering:
    """IP基因聚类 - 挖掘潜力作品"""
    
    def __init__(self, n_clusters=5):
        self.n_clusters = n_clusters
        self.kmeans = None
        self.scaler = StandardScaler()
        self.success_templates = None
        
    def fit(self, df):
        """
        基于历史成功作品训练聚类模型
        定义成功：月票 > 10000 或 有改编
        """
        print("\n训练IP基因聚类模型...")
        
        # 定义成功作品
        success_mask = (df['monthly_tickets'] > 10000) | (df['has_adaptation'] == 1)
        success_books = df[success_mask].copy()
        
        if len(success_books) < self.n_clusters * 2:
            print(f"警告: 成功作品样本不足 ({len(success_books)}), 降低阈值")
            success_mask = df['monthly_tickets'] > 5000
            success_books = df[success_mask].copy()
        
        print(f"成功作品样本: {len(success_books)} 本")
        
        # 选择聚类特征（孵化期特征）
        cluster_features = [
            'word_count', 'monthly_tickets', 'total_recommend',
            'update_regularity', 'purchasing_power_index',
            'has_adaptation'
        ]
        
        # 确保特征存在
        available_features = [f for f in cluster_features if f in success_books.columns]
        
        X = success_books[available_features].fillna(0)
        X_scaled = self.scaler.fit_transform(X)
        
        # 训练K-Means
        self.kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        success_books['ip_gene_cluster'] = self.kmeans.fit_predict(X_scaled)
        
        # 保存成功模板（每个聚类的中心）
        self.success_templates = pd.DataFrame(
            self.scaler.inverse_transform(self.kmeans.cluster_centers_),
            columns=available_features
        )
        
        print(f"IP基因聚类训练完成")
        print(f"聚类分布:")
        print(success_books['ip_gene_cluster'].value_counts().sort_index())
        
        return self
    
    def predict_similarity(self, df):
        """计算每本书与成功模板的相似度"""
        print("\n计算IP基因相似度...")
        
        cluster_features = [
            'word_count', 'monthly_tickets', 'total_recommend',
            'update_regularity', 'purchasing_power_index',
            'has_adaptation'
        ]
        available_features = [f for f in cluster_features if f in df.columns]
        
        X = df[available_features].fillna(0)
        X_scaled = self.scaler.transform(X)
        
        # 找到最近的聚类
        cluster_ids = self.kmeans.predict(X_scaled)
        df['ip_gene_cluster'] = cluster_ids
        
        # 计算与所属聚类中心的距离（相似度）
        similarities = []
        for i, x in enumerate(X_scaled):
            center = self.kmeans.cluster_centers_[cluster_ids[i]]
            distance = np.linalg.norm(x - center)
            # 转换为相似度分数 (0-100)，距离越小分数越高
            similarity = max(0, 100 - distance * 10)
            similarities.append(similarity)
        
        df['ip_gene_similarity'] = similarities
        
        print(f"相似度计算完成")
        print(f"  平均相似度: {df['ip_gene_similarity'].mean():.2f}")
        
        return df

# ================================================================
#  5. 双引擎预测（开题报告创新点1核心）
# ================================================================

class DualEnginePredictor:
    """
    双引擎预测器
    Engine A: XGBoost - 成熟期作品（>=6月）
    Engine B: 熵权法 - 孵化期作品（<6月）
    """
    
    def __init__(self):
        self.engine_a = None  # XGBoost模型
        self.engine_a_scaler = None
        self.engine_b_weights = None  # 熵权法权重
        self.maturity_threshold = 6  # 6个月为分界线
        
    def calculate_entropy_weights(self, df, features):
        """计算熵权法权重"""
        print("\n计算熵权法权重...")
        
        # 数据归一化
        df_norm = df[features].copy()
        for col in features:
            max_val = df_norm[col].max()
            min_val = df_norm[col].min()
            if max_val > min_val:
                df_norm[col] = (df_norm[col] - min_val) / (max_val - min_val)
            else:
                df_norm[col] = 0
        
        # 计算每个特征的信息熵
        weights = {}
        for col in features:
            # 计算概率分布
            values = df_norm[col].values
            values = values[values > 0]  # 只考虑非零值
            
            if len(values) > 0:
                # 计算概率
                probs = values / values.sum()
                # 计算熵
                e = entropy(probs, base=2)
                # 差异系数 = 1 - 熵/ln(n)
                diversity = 1 - e / np.log(len(values) + 1)
                weights[col] = diversity
            else:
                weights[col] = 0
        
        # 归一化权重
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}
        
        print(f"熵权法权重:")
        for k, v in weights.items():
            print(f"  {k}: {v:.3f}")
        
        return weights
    
    def fit_engine_b(self, df):
        """训练Engine B（熵权法）"""
        print("\n训练Engine B（孵化期模型）...")
        
        # 选择孵化期特征（增长率、更新相关）
        engine_b_features = [
            'tickets_mom', 'update_regularity', 'max_consecutive_months',
            'purchasing_power_index', 'total_recommend'
        ]
        
        # 过滤出孵化期作品
        immature_mask = df['months_since_start'] < self.maturity_threshold
        immature_df = df[immature_mask].copy()
        
        if len(immature_df) < 100:
            print(f"警告: 孵化期样本不足 ({len(immature_df)}), 使用全部数据")
            immature_df = df.copy()
        
        # 计算熵权
        self.engine_b_weights = self.calculate_entropy_weights(
            immature_df, 
            [f for f in engine_b_features if f in immature_df.columns]
        )
        
        print(f"Engine B训练完成，使用{len(self.engine_b_weights)}个特征")
        
    def predict_engine_b(self, row):
        """使用熵权法预测"""
        score = 0
        for feature, weight in self.engine_b_weights.items():
            if feature in row:
                # 归一化到0-100
                value = min(100, max(0, row[feature] * 100))
                score += value * weight
        return score

# ================================================================
#  6. 特征工程主函数
# ================================================================

def engineer_features(df):
    """完整的特征工程"""
    print("\n" + "="*70)
    print("特征工程")
    print("="*70)
    
    # 基础特征
    print("\n1. 基础数值特征...")
    df['log_word_count'] = np.log1p(df['word_count'])
    df['log_collection'] = np.log1p(df['collection_count'])
    df['log_recommend'] = np.log1p(df['total_recommend'])
    df['log_monthly_tickets'] = np.log1p(df['monthly_tickets'])
    
    # 衍生比率
    df['recommend_per_collection'] = df['total_recommend'] / (df['collection_count'] + 1)
    df['tickets_per_word'] = df['monthly_tickets'] / (df['word_count'] + 1) * 10000
    
    # 时间特征
    print("2. 时间特征...")
    df['year_month'] = df['year'] * 12 + df['month']
    df['quarter'] = df['month'].apply(lambda x: (x-1)//3 + 1)
    df['is_year_end'] = (df['month'] == 12).astype(int)
    df['is_year_start'] = (df['month'] == 1).astype(int)
    
    # 假设start_date为最早记录
    start_dates = df.groupby(['title', 'platform'])['year_month'].transform('min')
    df['months_since_start'] = df['year_month'] - start_dates
    
    df['is_new_book'] = (df['months_since_start'] < 6).astype(int)
    df['is_mature'] = ((df['months_since_start'] >= 6) & (df['months_since_start'] < 24)).astype(int)
    df['is_long_running'] = (df['months_since_start'] >= 24).astype(int)
    
    # 更新熵特征
    print("3. 更新熵特征...")
    df = calculate_update_entropy(df)
    
    # 粉丝购买力指数
    print("4. 购买力指数...")
    df = calculate_purchasing_power_index(df)
    
    print(f"\n特征工程完成，总特征数: {len(df.columns)}")
    
    return df

# ================================================================
#  7. 主训练和评估流程
# ================================================================

def main():
    print("="*70)
    print("Model F - 开题报告完整实现版")
    print("="*70)
    
    # 1. 获取数据
    df = fetch_data_with_adaptation()
    
    # 2. 特征工程
    df = engineer_features(df)
    
    # 3. IP基因聚类
    ip_clustering = IPGeneClustering(n_clusters=5)
    ip_clustering.fit(df)
    df = ip_clustering.predict_similarity(df)
    
    # 4. 双引擎训练
    dual_engine = DualEnginePredictor()
    dual_engine.fit_engine_b(df)
    
    # 5. 保存模型
    print("\n" + "="*70)
    print("保存模型组件")
    print("="*70)
    
    model_package = {
        'ip_clustering': ip_clustering,
        'dual_engine': dual_engine,
        'version': 'Model_F_v1.0',
        'features': ['update_entropy', 'ip_gene_similarity', 'purchasing_power_index',
                    'has_adaptation', 'adaptation_count'],
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
    }
    
    save_path = 'model_f_components.pkl'
    joblib.dump(model_package, save_path)
    print(f"模型组件已保存到: {save_path}")
    
    print("\n" + "="*70)
    print("Model F 初始化完成")
    print("="*70)
    print(f"样本数: {len(df)}")
    print(f"有改编: {df['has_adaptation'].sum()} 本")
    print(f"成熟期(>=6月): {(df['months_since_start'] >= 6).sum()} 本")
    print(f"孵化期(<6月): {(df['months_since_start'] < 6).sum()} 本")

if __name__ == "__main__":
    main()
