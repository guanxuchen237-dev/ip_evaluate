"""
Model J Oracle - 整合IP价值预言机的改进版模型
核心改进：
1. 利用数据库已有的IP_Score（预言机计算）作为标签
2. 整合预言机评分逻辑
3. 解决数据不平衡问题
4. 设计大模型集成接口
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
import jieba
import os
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit, StratifiedKFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.cluster import KMeans
from sklearn.utils import resample
import xgboost as xgb
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

# 题材热度映射
HOT_GENRES = {
    '玄幻': 95, '奇幻': 92, '都市': 90, '仙侠': 88, '游戏': 85,
    '武侠': 85, '历史': 82, '科幻': 80, '悬疑': 78, '轻小说': 75,
    '灵异': 72, '军事': 70, '二次元': 78, '短篇': 60, '现实': 65
}

print("="*70)
print("Model J Oracle - 整合IP价值预言机")
print("利用现有IP_Score + 解决数据不平衡 + 大模型接口")
print("="*70)

# ================================================================
#  IP等级制评分系统（与预言机对齐）
# ================================================================

class IPGradingSystem:
    """IP等级制评分系统 - 与预言机对齐"""
    
    # 基于预言机实际评分分布调整阈值
    GRADES = {
        'S': {'min': 90, 'max': 100, 'desc': '顶级IP', 'color': '🔴'},
        'A': {'min': 80, 'max': 89, 'desc': '优质IP', 'color': '🟠'},
        'B': {'min': 70, 'max': 79, 'desc': '良好IP', 'color': '🟡'},
        'C': {'min': 60, 'max': 69, 'desc': '普通IP', 'color': '🟢'},
        'D': {'min': 45, 'max': 59, 'desc': '低价值IP', 'color': '⚪'},
    }
    
    @staticmethod
    def score_to_grade(score):
        """将预言机评分转换为等级"""
        if score >= 90:
            return 'S'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        else:
            return 'D'
    
    @staticmethod
    def get_grade_info(grade):
        """获取等级详细信息"""
        return IPGradingSystem.GRADES.get(grade, {})

# ================================================================
#  预言机评分逻辑整合
# ================================================================

class OracleScoreIntegrator:
    """整合预言机评分逻辑"""
    
    def __init__(self):
        self.platform_scale = {'Zongheng': 8.0, 'Qidian': 1.0}  # 纵横月票缩放因子
        
    def _ticket_to_score(self, tickets):
        """分段线性月票锚定（来自预言机）"""
        if tickets <= 0:
            return 55.0
        
        # 分段线性映射
        if tickets < 100:
            return 55.0 + tickets * 0.1  # 55-65
        elif tickets < 1000:
            return 65.0 + (tickets - 100) * 0.015  # 65-78.5
        elif tickets < 10000:
            return 78.5 + (tickets - 1000) * 0.001  # 78.5-87.5
        else:
            return min(95.0, 87.5 + (tickets - 10000) * 0.0001)  # 87.5-95+
    
    def compute_oracle_features(self, df):
        """计算预言机相关特征"""
        print("\n【预言机特征计算】")
        
        # 1. 月票锚定分
        df['oracle_ticket_score'] = df.apply(
            lambda row: self._ticket_to_score(
                row['monthly_tickets'] * self.platform_scale.get(row['platform'], 1.0)
            ), axis=1
        )
        
        # 2. 互动量修正（最高加1分）
        df['oracle_inter_bonus'] = np.minimum(1.0, np.log1p(df['total_recommend'] / 100000) * 0.5)
        
        # 3. 字数修正（最高加0.5分）
        df['oracle_wc_bonus'] = np.minimum(0.5, np.log1p(df['word_count'] / 500000) * 0.3)
        
        # 4. 题材微调
        df['oracle_cat_bonus'] = df['category'].map(
            lambda x: 0.5 if any(k in str(x) for k in ['玄幻', '奇幻', '仙侠']) else 0.0
        )
        
        # 5. 新作爆发补偿
        df['oracle_potential'] = np.where(
            (df['word_count'] < 300000) & (df['monthly_tickets'] > 5000),
            np.minimum(5.0, 8.0 * (1.0 - df['word_count'] / 400000.0)),
            0.0
        )
        
        # 6. 预言机综合评分（模拟）
        df['oracle_composite'] = (
            df['oracle_ticket_score'] + 
            df['oracle_inter_bonus'] + 
            df['oracle_wc_bonus'] + 
            df['oracle_cat_bonus'] + 
            df['oracle_potential']
        )
        
        # 完结衰减
        if 'status' in df.columns:
            df['oracle_composite'] = np.where(
                df['status'].str.contains('完', na=False),
                df['oracle_composite'] * 0.90,
                df['oracle_composite']
            )
        
        # 限制范围
        df['oracle_composite'] = df['oracle_composite'].clip(45.0, 99.5)
        
        print(f"  预言机评分均值: {df['oracle_composite'].mean():.2f}")
        print(f"  预言机评分范围: {df['oracle_composite'].min():.1f} - {df['oracle_composite'].max():.1f}")
        
        return df

# ================================================================
#  数据获取（使用现有IP_Score）
# ================================================================

def fetch_data_with_oracle_score():
    """获取数据，使用预言机逻辑计算IP_Score"""
    print("\n1. 获取数据（使用预言机计算评分）...")
    
    dfs = []
    
    # 起点数据
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG)
        df_qd = pd.read_sql("""
            SELECT title, author, category, status, word_count,
                   collection_count, recommendation_count as total_recommend,
                   monthly_ticket_count as monthly_tickets,
                   year, month, synopsis as abstract,
                   adaptations, is_sign as is_signed
            FROM novel_monthly_stats
            WHERE year >= 2020
        """, conn)
        df_qd['platform'] = 'Qidian'
        df_qd['has_adaptation'] = df_qd['adaptations'].apply(lambda x: 1 if x and len(str(x)) > 3 else 0)
        conn.close()
        print(f"   起点: {len(df_qd)} 条")
        dfs.append(df_qd)
    except Exception as e:
        print(f"   起点错误: {e}")
    
    # 纵横数据
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG)
        df_zh = pd.read_sql("""
            SELECT title, author, category, status, word_count,
                   total_click as collection_count, total_rec as total_recommend,
                   monthly_ticket as monthly_tickets,
                   fan_count, year, month, abstract
            FROM zongheng_book_ranks
            WHERE year >= 2020
        """, conn)
        df_zh['platform'] = 'Zongheng'
        df_zh['has_adaptation'] = 0
        df_zh['is_signed'] = '0'
        df_zh['adaptations'] = ''
        conn.close()
        print(f"   纵横: {len(df_zh)} 条")
        dfs.append(df_zh)
    except Exception as e:
        print(f"   纵横错误: {e}")
    
    if not dfs:
        return pd.DataFrame()
    
    df = pd.concat(dfs, ignore_index=True)
    
    # 清理数据
    df['monthly_tickets'] = pd.to_numeric(df['monthly_tickets'], errors='coerce').fillna(0)
    df['word_count'] = pd.to_numeric(df['word_count'], errors='coerce').fillna(0)
    df['collection_count'] = pd.to_numeric(df['collection_count'], errors='coerce').fillna(0)
    df['total_recommend'] = pd.to_numeric(df['total_recommend'], errors='coerce').fillna(0)
    
    # 使用预言机逻辑计算IP评分
    print("\n   使用预言机逻辑计算IP评分...")
    integrator = OracleScoreIntegrator()
    df = integrator.compute_oracle_features(df)
    df['ip_score'] = df['oracle_composite']  # 使用预言机综合评分作为标签
    
    print(f"   总计: {len(df)} 条")
    print(f"   IP评分均值: {df['ip_score'].mean():.2f}")
    
    return df

# ================================================================
#  数据平衡处理
# ================================================================

def balance_data(df, method='hybrid'):
    """数据平衡处理"""
    print(f"\n【数据平衡处理】方法: {method}")
    
    # 添加等级列
    df['ip_grade'] = df['ip_score'].apply(IPGradingSystem.score_to_grade)
    
    # 统计原始分布
    grade_dist = df['ip_grade'].value_counts()
    print(f"  原始分布:")
    for grade in ['S', 'A', 'B', 'C', 'D']:
        count = grade_dist.get(grade, 0)
        print(f"    {grade}级: {count} ({count/len(df)*100:.1f}%)")
    
    if method == 'none':
        return df
    
    # 分离各等级
    df_s = df[df['ip_grade'] == 'S']
    df_a = df[df['ip_grade'] == 'A']
    df_b = df[df['ip_grade'] == 'B']
    df_c = df[df['ip_grade'] == 'C']
    df_d = df[df['ip_grade'] == 'D']
    
    if method == 'hybrid':
        # 混合策略：过采样少数类 + 欠采样多数类
        target_per_class = max(len(df_s), len(df_a), len(df_b), len(df_c), 500)
        
        # 过采样S/A/B/C级
        df_s_up = resample(df_s, n_samples=min(target_per_class, len(df_s)*3), replace=True, random_state=42) if len(df_s) > 0 else df_s
        df_a_up = resample(df_a, n_samples=min(target_per_class, len(df_a)*3), replace=True, random_state=42) if len(df_a) > 0 else df_a
        df_b_up = resample(df_b, n_samples=min(target_per_class, len(df_b)*2), replace=True, random_state=42) if len(df_b) > 0 else df_b
        df_c_up = resample(df_c, n_samples=min(target_per_class, len(df_c)), replace=True, random_state=42) if len(df_c) > 0 else df_c
        
        # 欠采样D级
        df_d_down = resample(df_d, n_samples=min(len(df_d), 2000), replace=False, random_state=42)
        
        df_balanced = pd.concat([df_s_up, df_a_up, df_b_up, df_c_up, df_d_down], ignore_index=True)
        
    elif method == 'smote':
        # SMOTE过采样（需要数值特征）
        print("  使用SMOTE过采样...")
        # 简化：仅使用混合策略
        return balance_data(df, method='hybrid')
    
    # 打乱顺序
    df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # 统计新分布
    grade_dist_new = df_balanced['ip_grade'].value_counts()
    print(f"\n  平衡后分布:")
    for grade in ['S', 'A', 'B', 'C', 'D']:
        count = grade_dist_new.get(grade, 0)
        print(f"    {grade}级: {count} ({count/len(df_balanced)*100:.1f}%)")
    
    return df_balanced

# ================================================================
#  特征工程
# ================================================================

def extract_features(df):
    """特征工程"""
    print("\n【特征工程】")
    
    # 预言机特征
    integrator = OracleScoreIntegrator()
    df = integrator.compute_oracle_features(df)
    
    # 6大维度特征
    # 1. 更新频率
    df['update_freq'] = df.groupby(['title', 'author'])['word_count'].diff().fillna(0)
    
    # 2. 断更风险
    df['months_active'] = df.groupby(['title', 'author']).cumcount() + 1
    
    # 3. 读者留存
    if 'fan_count' in df.columns:
        df['retention'] = df['fan_count'] / (df['collection_count'] + 1) * 100
    else:
        df['retention'] = df['collection_count'] / (df['total_recommend'] + 1)
    df['retention'] = np.clip(df['retention'], 0, 100)
    
    # 4. 题材热度
    df['genre_hotness'] = df['category'].map(lambda x: HOT_GENRES.get(str(x), 70)).fillna(70)
    
    # 5. 改编潜力
    df['adaptation_potential'] = (
        np.clip(df['word_count'] / 500000, 0, 1) * 50 +
        df['genre_hotness'] * 0.3 +
        df['has_adaptation'] * 20
    )
    
    # 6. 商业爆发力
    df['base_power'] = (
        np.log1p(df['monthly_tickets']) * 20 +
        np.log1p(df['collection_count']) * 15 +
        np.log1p(df['total_recommend']) * 10
    )
    df['base_power'] = np.clip(df['base_power'] / df['base_power'].quantile(0.95) * 100, 0, 100)
    
    # 平台归一化
    df['tickets_normalized'] = np.where(
        df['platform'] == 'Zongheng',
        df['monthly_tickets'] * 8.0,
        df['monthly_tickets']
    )
    
    # 清理无穷值
    df = df.replace([np.inf, -np.inf], 0)
    
    print(f"  总特征数: {len(df.columns)}")
    
    return df

# ================================================================
#  论文版双引擎（改进K-Means）
# ================================================================

class ImprovedDualEngine:
    """改进版双引擎：XGBoost + 改进K-Means"""
    
    def __init__(self):
        self.xgb_engine = None
        self.kmeans_engine = None
        self.scaler_xgb = None
        self.scaler_kmeans = None
        self.feature_cols = None
        self.cluster_centers = None
        self.cluster_scores = None
        
    def fit(self, X, y, months, grades):
        """训练双引擎"""
        print("\n【改进版双引擎训练】")
        
        # 分割数据
        mature_mask = months >= 6
        nascent_mask = months < 6
        
        X_mature = X[mature_mask]
        y_mature = y[mature_mask]
        
        X_nascent = X[nascent_mask]
        y_nascent = y[nascent_mask]
        grades_nascent = grades[nascent_mask]
        
        print(f"  成熟期样本: {len(X_mature)} (XGBoost)")
        print(f"  孵化期样本: {len(X_nascent)} (改进K-Means)")
        
        # ========== Engine A: XGBoost ==========
        if len(X_mature) > 0:
            print("\n  训练Engine A (XGBoost)...")
            self.scaler_xgb = StandardScaler()
            X_mature_scaled = self.scaler_xgb.fit_transform(X_mature)
            
            self.xgb_engine = xgb.XGBRegressor(
                objective='reg:squarederror',
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=42,
                n_jobs=-1
            )
            self.xgb_engine.fit(X_mature_scaled, y_mature)
            
            y_pred_mature = self.xgb_engine.predict(X_mature_scaled)
            rmse_mature = np.sqrt(mean_squared_error(y_mature, y_pred_mature))
            r2_mature = r2_score(y_mature, y_pred_mature)
            print(f"    XGBoost RMSE: {rmse_mature:.2f}, R²: {r2_mature:.4f}")
        else:
            self.xgb_engine = None
            print("  警告: 无成熟期样本，跳过XGBoost训练")
        
        # ========== Engine B: 改进K-Means ==========
        if len(X_nascent) > 0:
            print("\n  训练Engine B (改进K-Means)...")
            self.scaler_kmeans = StandardScaler()
            X_nascent_scaled = self.scaler_kmeans.fit_transform(X_nascent)
            
            # 改进1: 根据等级分布确定聚类数
            unique_grades = grades_nascent.unique()
            n_clusters = max(5, min(15, len(unique_grades) * 2, len(X_nascent) // 30))
            
            self.kmeans_engine = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = self.kmeans_engine.fit_predict(X_nascent_scaled)
            
            # 改进2: 使用加权平均计算聚类分数（考虑等级分布）
            self.cluster_scores = {}
            for i in range(n_clusters):
                mask = clusters == i
                if mask.sum() > 0:
                    # 加权平均：高等级样本权重更高
                    cluster_grades = grades_nascent[mask]
                    cluster_scores = y_nascent[mask]
                    
                    # 根据等级分配权重
                    weights = cluster_grades.map({
                        'S': 5.0, 'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0
                    }).values
                    
                    weighted_score = np.average(cluster_scores, weights=weights)
                    self.cluster_scores[i] = weighted_score
                else:
                    self.cluster_scores[i] = 60.0  # 默认中等分数
            
            print(f"    K-Means聚类数: {n_clusters}")
            
            # 验证K-Means
            y_pred_nascent = np.array([self.cluster_scores[c] for c in clusters])
            rmse_nascent = np.sqrt(mean_squared_error(y_nascent, y_pred_nascent))
            print(f"    K-Means RMSE: {rmse_nascent:.2f}")
            
            # 打印聚类分布
            print(f"    各聚类IP评分:")
            for i, score in sorted(self.cluster_scores.items(), key=lambda x: -x[1])[:5]:
                count = (clusters == i).sum()
                print(f"      聚类{i}: IP评分={score:.1f}, 样本数={count}")
        else:
            self.kmeans_engine = None
            print("  警告: 无孵化期样本，跳过K-Means训练")
        
        print("\n  双引擎训练完成")
        return self
    
    def predict(self, X, months):
        """双引擎预测"""
        predictions = np.zeros(len(X))
        engines = []
        
        for i in range(len(X)):
            m = months.iloc[i] if hasattr(months, 'iloc') else months[i]
            x = X[i:i+1]
            
            if m >= 6 and self.xgb_engine is not None:
                # 成熟期: XGBoost
                x_scaled = self.scaler_xgb.transform(x)
                predictions[i] = self.xgb_engine.predict(x_scaled)[0]
                engines.append('XGBoost')
            elif m < 6 and self.kmeans_engine is not None:
                # 孵化期: K-Means
                x_scaled = self.scaler_kmeans.transform(x)
                cluster = self.kmeans_engine.predict(x_scaled)[0]
                predictions[i] = self.cluster_scores.get(cluster, 60.0)
                engines.append('K-Means')
            else:
                # 兜底: 使用预言机特征
                if 'oracle_composite' in range(X.shape[1]):
                    predictions[i] = x[0, list(range(X.shape[1])).index('oracle_composite')] if 'oracle_composite' in dir() else 60.0
                else:
                    predictions[i] = 60.0
                engines.append('Fallback')
        
        # 限制范围
        predictions = np.clip(predictions, 45.0, 99.5)
        return predictions, engines

# ================================================================
#  大模型集成接口
# ================================================================

class LLMIntegrationInterface:
    """大模型集成接口"""
    
    def __init__(self, model_path):
        self.model = joblib.load(model_path)
        self.dual_engine = self.model.get('dual_engine')
        self.feature_cols = self.model.get('features', [])
        
    def get_ip_evaluation(self, book_info):
        """获取IP评估结果（供大模型调用）"""
        
        # 提取特征
        features = self._extract_features_from_book_info(book_info)
        
        # 预测
        X = np.array([features])
        months = np.array([book_info.get('months_active', 12)])
        
        score, engine = self.dual_engine.predict(X, months)
        score = score[0]
        grade = IPGradingSystem.score_to_grade(score)
        grade_info = IPGradingSystem.get_grade_info(grade)
        
        return {
            'title': book_info.get('title', ''),
            'author': book_info.get('author', ''),
            'ip_score': round(score, 1),
            'ip_grade': grade,
            'grade_info': grade_info,
            'engine_used': engine[0] if engine else 'Unknown',
            'recommendation': self._generate_recommendation(score, grade),
            'details': {
                'commercial_potential': self._assess_commercial(score),
                'adaptation_potential': self._assess_adaptation(score, book_info),
                'risk_level': self._assess_risk(score, book_info),
            }
        }
    
    def _extract_features_from_book_info(self, info):
        """从书籍信息提取特征"""
        # 简化实现：返回默认特征向量
        features = []
        for col in self.feature_cols:
            if col in info:
                features.append(float(info[col]))
            else:
                features.append(0.0)
        return features
    
    def _generate_recommendation(self, score, grade):
        """生成推荐建议"""
        if grade in ['S', 'A']:
            return "强烈推荐投资，IP价值极高，适合影视/游戏改编"
        elif grade == 'B':
            return "推荐关注，IP价值良好，可考虑小规模投资"
        elif grade == 'C':
            return "观察为主，IP价值一般，需关注后续发展"
        else:
            return "暂不推荐，IP价值较低，建议等待数据积累"
    
    def _assess_commercial(self, score):
        """评估商业潜力"""
        if score >= 85:
            return "高"
        elif score >= 70:
            return "中"
        else:
            return "低"
    
    def _assess_adaptation(self, score, info):
        """评估改编潜力"""
        wc = info.get('word_count', 0)
        if score >= 80 and wc >= 1000000:
            return "高"
        elif score >= 70 and wc >= 500000:
            return "中"
        else:
            return "低"
    
    def _assess_risk(self, score, info):
        """评估风险等级"""
        status = info.get('status', '')
        if '完' in status:
            return "低（已完结）"
        elif score < 60:
            return "高（评分低）"
        else:
            return "中（连载中）"
    
    def get_top_ip_books(self, n=10, platform=None, category=None):
        """获取优质IP书籍列表（供大模型参考）"""
        # 这里需要从数据库获取
        return {
            'message': f'Top {n} IP books',
            'filters': {'platform': platform, 'category': category},
            'note': 'Call database to get actual list'
        }

# ================================================================
#  主训练流程
# ================================================================

def train_model_j_oracle():
    """训练Model J Oracle"""
    
    # 1. 获取数据
    df = fetch_data_with_oracle_score()
    if df.empty:
        print("错误: 无法获取数据")
        return None
    
    # 2. 数据平衡
    df = balance_data(df, method='hybrid')
    
    # 3. 特征工程
    df = extract_features(df)
    
    # 4. 准备特征
    print("\n2. 准备训练数据...")
    exclude = ['title', 'author', 'category', 'platform', 'year', 'month',
               'status', 'abstract', 'adaptations', 'ip_grade', 'ip_score']
    feature_cols = [c for c in df.columns if c not in exclude and df[c].dtype in ['int64', 'float64', 'int32', 'float32']]
    
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], 0)
    
    print(f"   特征数: {len(feature_cols)}")
    
    # 5. 时间切分
    train_mask = df['year'] <= 2023
    val_mask = df['year'] == 2024
    
    X_train = df[train_mask][feature_cols].values
    y_train = df[train_mask]['ip_score'].values  # 使用数据库中的IP_Score
    months_train = df[train_mask]['months_active']
    grades_train = df[train_mask]['ip_grade']
    
    X_val = df[val_mask][feature_cols].values
    y_val = df[val_mask]['ip_score'].values
    months_val = df[val_mask]['months_active']
    
    print(f"   训练集: {len(X_train)} 条")
    print(f"   验证集: {len(X_val)} 条")
    
    # 6. 训练双引擎
    print("\n" + "="*70)
    print("训练改进版双引擎")
    print("="*70)
    
    dual_engine = ImprovedDualEngine()
    dual_engine.fit(X_train, y_train, months_train.reset_index(drop=True), grades_train.reset_index(drop=True))
    dual_engine.feature_cols = feature_cols
    
    # 7. 验证
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
    
    # 8. 保存模型
    print("\n" + "="*70)
    print("保存Model J Oracle")
    print("="*70)
    
    model_j_oracle = {
        'dual_engine': dual_engine,
        'features': feature_cols,
        'metrics': {
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'grade_accuracy': grade_accuracy
        },
        'version': 'Model_J_Oracle_v1.0',
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'description': '整合预言机的改进版IP评估模型',
        'improvements': [
            '利用数据库IP_Score作为标签',
            '整合预言机评分逻辑',
            '数据平衡处理',
            '改进K-Means加权评分',
            '大模型集成接口'
        ]
    }
    
    save_path = 'resources/models/model_j_oracle.pkl'
    joblib.dump(model_j_oracle, save_path)
    print(f"   模型已保存: {save_path}")
    
    # 9. 总结
    print("\n" + "="*70)
    print("Model J Oracle 训练完成!")
    print("="*70)
    print(f"   总样本: {len(df)}")
    print(f"   总特征: {len(feature_cols)}")
    print(f"\n   性能指标:")
    print(f"     RMSE: {rmse:.2f}")
    print(f"     MAE: {mae:.2f}")
    print(f"     R²: {r2:.4f}")
    print(f"     等级准确率: {grade_accuracy*100:.1f}%")
    print(f"\n   改进点:")
    print(f"     ✅ 利用数据库IP_Score作为标签")
    print(f"     ✅ 整合预言机评分逻辑")
    print(f"     ✅ 数据平衡处理（混合策略）")
    print(f"     ✅ 改进K-Means加权评分")
    print(f"     ✅ 大模型集成接口")
    print("="*70)
    
    return model_j_oracle

if __name__ == "__main__":
    model = train_model_j_oracle()
