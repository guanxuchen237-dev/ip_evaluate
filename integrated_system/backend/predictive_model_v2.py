import pandas as pd
import numpy as np
import pymysql
import warnings
import joblib
import os
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from sklearn.metrics import mean_squared_error, r2_score

warnings.filterwarnings('ignore')

# 数据库配置
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306,
    'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306,
    'user': 'root', 'password': 'root',
    'database': 'qidian_data', 'charset': 'utf8mb4'
}

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_v2.pkl')

def load_data():
    """加载2020-2025全量历史库数据用于时序切片"""
    dfs = []
    
    for cfg, sql, plat in [
        (ZONGHENG_CONFIG,
         """SELECT title, author, category, status, word_count,
                   total_click as popularity, total_rec as interaction,
                   monthly_ticket as finance, fan_count as fans_count,
                   year, month
            FROM zongheng_book_ranks""", "Zongheng"),
        (QIDIAN_CONFIG,
         """SELECT title, author, category, status, word_count,
                   collection_count as popularity,
                   recommendation_count as interaction,
                   monthly_tickets_on_list as finance,
                   reward_count as fans_count,
                   year, month
            FROM novel_monthly_stats""", "Qidian")
    ]:
        try:
            conn = pymysql.connect(**cfg)
            df = pd.read_sql(sql, conn)
            df['platform'] = plat
            dfs.append(df)
            conn.close()
            print(f"[OK] {plat} 加载了 {len(df)} 月度记录")
        except Exception as e:
            print(f"[ERR] {plat} 加载失败: {e}")
            
    df_all = pd.concat(dfs, ignore_index=True)
    
    # 清洗：将缺失值填0
    num_cols = ['word_count', 'popularity', 'interaction', 'finance', 'fans_count']
    for c in num_cols:
        df_all[c] = pd.to_numeric(df_all[c], errors='coerce').fillna(0)
    df_all['year'] = pd.to_numeric(df_all['year'], errors='coerce').fillna(2020)
    df_all['month'] = pd.to_numeric(df_all['month'], errors='coerce').fillna(1)
    
    return df_all

def extract_timeseries_features(df):
    """提取断更风险、更新频率、留存等新六维特征"""
    print("开始提取时序特征...")
    
    # 按作品和时间排序
    df = df.sort_values(by=['platform', 'title', 'year', 'month'])
    
    # 填充缺失月份带来的不连续
    df['time_idx'] = df['year'] * 12 + df['month']
    
    # === 构建序列特征 ===
    grouped = df.groupby(['platform', 'title'])
    
    # 1. 更新频率 (月更新字数)
    df['word_count_diff'] = grouped['word_count'].diff().fillna(df['word_count'])
    df['word_count_diff'] = df['word_count_diff'].clip(lower=0) 
    # 修复有时字数变少或出错的问题
    
    # 2. 断更风险特征 (更新字数为0且状态非完结)
    df['is_dropped'] = ((df['word_count_diff'] == 0) & (~df['status'].astype(str).str.contains('完'))).astype(int)
    # 历史累计断更次数
    df['cum_drop_months'] = grouped['is_dropped'].cumsum()
    
    # 3. 读者留存黏性 (人气或粉丝是否还在一直涨)
    df['fans_diff'] = grouped['fans_count'].diff().fillna(df['fans_count']).clip(lower=0)
    df['pop_diff'] = grouped['popularity'].diff().fillna(df['popularity']).clip(lower=0)
    df['retention_rate'] = (df['fans_diff'] / (df['pop_diff'] + 1)).fillna(0)
    
    # 4. 月票商业爆发力
    df['finance_diff'] = grouped['finance'].diff().fillna(df['finance'])
    # 计算月票环比增幅
    df['finance_growth_rate'] = grouped['finance'].pct_change().fillna(0).replace([np.inf, -np.inf], 0)
    
    return df

def apply_kmeans_imputation(df):
    """
    使用 K-Means 进行同圈层填补 (针对 2025.12 缺失或新书)
    """
    print("应用 K-Means 模型划分圈层并填补初期/缺失特征...")
    
    # 我们只对 2025 年 12 月（或其他当月数据异常低）的作品进行填补
    # 特征选取：当前总字数、所属题材、历史月均增幅
    
    # 先选出近几个月的活跃书本作为聚类基底
    df_recent = df[df['time_idx'] >= (2025 * 12 + 1)].copy() 
    if len(df_recent) < 50:
        # 如果2025年数据不足，拉上2024年的
        df_recent = df[df['time_idx'] >= (2024 * 12 + 1)].copy()
        
    # 构建书籍的元特征聚合
    meta_features = df_recent.groupby(['platform', 'title']).agg({
        'word_count': 'max',
        'pop_diff': 'mean',
        'word_count_diff': 'mean',
        'cum_drop_months': 'max'
    }).fillna(0)
    
    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(meta_features)
    
    # 聚成 8 个圈层
    km = KMeans(n_clusters=8, random_state=42, n_init=10)
    meta_features['cluster'] = km.fit_predict(X_scaled)
    
    # 计算圈层均值补丁
    cluster_patch = meta_features.groupby('cluster').agg({
        'pop_diff': 'median',
        'word_count_diff': 'median'
    }).to_dict('index')
    
    # 把 cluster 回贴给大表
    df = df.merge(meta_features[['cluster']], left_on=['platform', 'title'], right_index=True, how='left')
    df['cluster'] = df['cluster'].fillna(-1) # -1 代表无圈层（太老）
    
    # 针对 12 月新书或断崖下降的，提供一个修正后的期望特征列做参考
    def patch_finance(row):
        c = row['cluster']
        if c != -1 and row['year'] == 2025 and row['month'] == 12 and row['finance'] < 100:
             # 如果是 12 月且月票很低，说明是月中没爬完的半衰期。用聚层均值托底或用上月*1.2
             return row['finance'] * 2.5 # 粗略修正
        return row['finance']
    
    df['recalc_finance'] = df.apply(patch_finance, axis=1)
    
    return df, scaler, km, cluster_patch

def train_prophet_xgboost(df):
    """
    时序切分: 
    Train: 2020-2023 (拟合长线价值)
    Valid: 2024 (防过拟合验证)
    Predict: 2025 (预言机输出期)
    """
    print("划分时序数据集训练 XGBoost 价值预言机...")
    
    # 目标值 (Target): Y为下一期的月票表现(即潜力的现实验证)
    # 我们用当前期的各项指标(时序增量)预测下个月的 finance
    df['target_finance'] = df.groupby(['platform', 'title'])['recalc_finance'].shift(-1)
    
    # 过滤掉无法验证的行 (每本书的最后一个月没有target)
    df_valid_target = df.dropna(subset=['target_finance'])
    
    # 目标变量转换 (对数化缓解长尾)
    df_valid_target['target_log'] = np.log1p(df_valid_target['target_finance'])
    
    # 特征选择
    features = [
        'word_count', 'word_count_diff', 'cum_drop_months',
        'popularity', 'pop_diff', 'retention_rate', 
        'fans_count', 'fans_diff', 'recalc_finance', 'finance_growth_rate'
    ]
    
    # ==== 时序切分 ====
    train_mask = df_valid_target['year'] <= 2023
    val_mask = df_valid_target['year'] == 2024
    test_mask = df_valid_target['year'] == 2025
    
    X_train = df_valid_target[train_mask][features]
    y_train = df_valid_target[train_mask]['target_log']
    
    X_val = df_valid_target[val_mask][features]
    y_val = df_valid_target[val_mask]['target_log']
    
    # 验证集可能为空如果数据主要集中在24/25年，需要Fallback
    if len(X_train) < 100:
        print("[WARN] 历史数据过少，采用退化划分 80/20")
        from sklearn.model_selection import train_test_split
        X_all = df_valid_target[features]
        y_all = df_valid_target['target_log']
        X_train, X_val, y_train, y_val = train_test_split(X_all, y_all, test_size=0.2, random_state=42)
    
    print(f"训练集大小: {len(X_train)}, 验证集大小: {len(X_val)}")
    
    # 标准化
    feature_scaler = StandardScaler()
    X_train_scaled = feature_scaler.fit_transform(X_train)
    X_val_scaled = feature_scaler.transform(X_val)
    
    # XGBoost 训练
    dtrain = xgb.DMatrix(X_train_scaled, label=y_train, feature_names=features)
    dval = xgb.DMatrix(X_val_scaled, label=y_val, feature_names=features)
    
    params = {
        'objective': 'reg:squarederror',
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'eval_metric': 'rmse',
        'seed': 42
    }
    
    evals = [(dtrain, 'train'), (dval, 'eval')]
    
    print("开始训练模型...")
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=300,
        evals=evals,
        early_stopping_rounds=30,
        verbose_eval=50
    )
    
    # 在 2025 预言集上测试并计算分数
    X_test_df = df_valid_target[test_mask]
    if len(X_test_df) > 0:
        X_test = X_test_df[features]
        y_test = X_test_df['target_log']
        X_test_scaled = feature_scaler.transform(X_test)
        dtest = xgb.DMatrix(X_test_scaled, feature_names=features)
        
        preds = model.predict(dtest)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2 = r2_score(y_test, preds)
        print(f"\n[2025推演集评测] 样本={len(y_test)} | RMSE: {rmse:.4f} | R2: {r2:.4f}")
    
    return model, feature_scaler, features

def export_pipeline(model, scaler, features, km_model, km_patch):
    pipeline = {
        'model': model,
        'scaler': scaler,
        'features': features,
        'kmeans_model': km_model,
        'kmeans_patch': km_patch,
        'version': 'v2_timeseries'
    }
    joblib.dump(pipeline, MODEL_PATH)
    print(f"\n[部署] 模型管道已导出至: {MODEL_PATH}")

if __name__ == "__main__":
    df_raw = load_data()
    if df_raw.empty:
        print("无数据，退出。")
        exit()
        
    df_ts = extract_timeseries_features(df_raw)
    df_imp, meta_scaler, km_model, km_patch = apply_kmeans_imputation(df_ts)
    xgb_model, feat_scaler, fe_cols = train_prophet_xgboost(df_imp)
    
    export_pipeline(xgb_model, feat_scaler, fe_cols, km_model, km_patch)
