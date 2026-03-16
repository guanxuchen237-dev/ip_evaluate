"""
Model J Oracle v3 - 使用实际月票排名校准映射
"""
import pandas as pd
import numpy as np
import pymysql
import joblib
import warnings
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.utils import resample
import xgboost as xgb
from scipy import stats
from datetime import datetime

warnings.filterwarnings('ignore')

# 数据库配置
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

print("="*70)
print("Model J Oracle v3 - 使用实际月票排名校准")
print("="*70)

# ================================================================
#  基于真实排名的校准映射
# ================================================================

class RankCalibratedOracle:
    """基于实际排名的预言机评分"""
    
    def __init__(self):
        self.platform_scale = {'Zongheng': 1.0, 'Qidian': 1.0}  # 不再缩放，直接使用原始排名
        
    def compute_rank_based_score(self, df):
        """基于排名计算分数"""
        print("\n【基于排名的评分计算】")
        
        # 按平台分别计算排名
        df['rank_score'] = 0.0
        
        for platform in df['platform'].unique():
            mask = df['platform'] == platform
            platform_df = df[mask].copy()
            
            # 按月票排序计算百分位排名
            platform_df = platform_df.sort_values('monthly_tickets', ascending=False)
            n = len(platform_df)
            
            # 百分位转分数 (0-100百分位 → 45-95分)
            # 排名前1% = 95分，排名100% = 45分
            platform_df['rank_pct'] = np.arange(n) / n
            platform_df['rank_score'] = 95.0 - platform_df['rank_pct'] * 50.0
            
            # 使用对数平滑高排名区域的差距
            platform_df['ticket_rank'] = stats.rankdata(-platform_df['monthly_tickets'])
            platform_df['rank_score_smooth'] = 70.0 + 25.0 * np.exp(-platform_df['ticket_rank'] / (n * 0.1))
            
            # 综合：百分位 + 对数平滑
            platform_df['final_rank_score'] = (
                platform_df['rank_score'] * 0.5 + 
                platform_df['rank_score_smooth'] * 0.5
            )
            
            df.loc[mask, 'rank_score'] = platform_df['final_rank_score']
        
        # 辅助维度
        df['inter_bonus'] = np.minimum(2.0, np.log1p(df['total_recommend'] / 30000) * 0.5)
        df['wc_bonus'] = np.minimum(1.5, np.log1p(df['word_count'] / 200000) * 0.3)
        df['pop_bonus'] = np.minimum(2.0, np.log1p(df['collection_count'] / 50000) * 0.4)
        
        # 综合评分
        df['ip_score'] = (
            df['rank_score'] * 0.8 +  # 排名占主导
            df['inter_bonus'] +
            df['wc_bonus'] +
            df['pop_bonus']
        )
        
        # 完结衰减
        df['ip_score'] = np.where(
            df['status'].str.contains('完', na=False),
            df['ip_score'] * 0.95,
            df['ip_score']
        )
        
        # 限制范围
        df['ip_score'] = df['ip_score'].clip(45.0, 99.5)
        
        print(f"  排名分范围: {df['rank_score'].min():.1f} - {df['rank_score'].max():.1f}")
        print(f"  IP评分均值: {df['ip_score'].mean():.2f}")
        print(f"  IP评分范围: {df['ip_score'].min():.1f} - {df['ip_score'].max():.1f}")
        
        return df

# ================================================================
#  IP等级制
# ================================================================

class IPGradingSystem:
    @staticmethod
    def score_to_grade(score):
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

# ================================================================
#  主流程 - 只计算评分不训练模型
# ================================================================

def compute_rank_based_scores():
    """计算基于排名的评分"""
    
    print("\n1. 获取纵横数据...")
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    df = pd.read_sql("""
        SELECT title, author, category, status, word_count,
               total_click as collection_count, total_rec as total_recommend,
               monthly_ticket as monthly_tickets,
               year, month, abstract
        FROM zongheng_book_ranks
        WHERE year >= 2024
    """, conn)
    conn.close()
    
    df['platform'] = 'Zongheng'
    
    # 清理数据
    df['monthly_tickets'] = pd.to_numeric(df['monthly_tickets'], errors='coerce').fillna(0)
    df['word_count'] = pd.to_numeric(df['word_count'], errors='coerce').fillna(0)
    df['collection_count'] = pd.to_numeric(df['collection_count'], errors='coerce').fillna(0)
    df['total_recommend'] = pd.to_numeric(df['total_recommend'], errors='coerce').fillna(0)
    
    # 去重取最新
    df = df.sort_values(['year', 'month'], ascending=[False, False])
    df = df.drop_duplicates(subset=['title', 'author'], keep='first')
    
    print(f"   去重后: {len(df)} 本书")
    
    # 计算基于排名的评分
    oracle = RankCalibratedOracle()
    df = oracle.compute_rank_based_score(df)
    
    # 计算等级
    df['ip_grade'] = df['ip_score'].apply(IPGradingSystem.score_to_grade)
    
    # 排序
    df = df.sort_values('ip_score', ascending=False).reset_index(drop=True)
    df['rank'] = range(1, len(df) + 1)
    
    # 显示Top 20
    print("\n" + "="*70)
    print("🏆 纵横平台 Top 20 (基于月票排名校准)")
    print("="*70)
    
    top20 = df.head(20)
    for i, row in top20.iterrows():
        print(f"{row['rank']:2d}. {row['title'][:20]:20s} | "
              f"月票:{int(row['monthly_tickets']):5d} | "
              f"评分:{row['ip_score']:5.1f} | "
              f"{row['ip_grade']}级")
    
    # 等级分布
    print("\n" + "="*70)
    print("📊 等级分布")
    print("="*70)
    
    grade_dist = df['ip_grade'].value_counts()
    for grade in ['S', 'A', 'B', 'C', 'D']:
        count = grade_dist.get(grade, 0)
        pct = count / len(df) * 100
        bar = '█' * int(pct / 2)
        print(f"{grade}级: {count:4d} ({pct:5.1f}%) {bar}")
    
    # 保存结果
    print("\n" + "="*70)
    print("保存评分结果")
    print("="*70)
    
    result_file = 'zongheng_rank_scores.csv'
    df[['rank', 'title', 'author', 'category', 'monthly_tickets', 
        'ip_score', 'ip_grade']].to_csv(result_file, index=False, encoding='utf-8-sig')
    print(f"   结果已保存: {result_file}")
    
    # 保存模型配置
    model_config = {
        'oracle': oracle,
        'version': 'Model_J_Oracle_v3.0_RankCalibrated',
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'method': '基于实际月票排名校准',
        'total_books': len(df)
    }
    
    model_file = 'resources/models/model_j_oracle_v3.pkl'
    joblib.dump(model_config, model_file)
    print(f"   模型配置已保存: {model_file}")
    
    print("\n" + "="*70)
    print("✅ Model J Oracle v3 完成!")
    print("="*70)
    print("特点：")
    print("  • 基于实际月票排名计算")
    print("  • 评分与实际排名一致")
    print("  • 使用百分位+对数平滑")
    print("="*70)
    
    return df

if __name__ == "__main__":
    df = compute_rank_based_scores()
