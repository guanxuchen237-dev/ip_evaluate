"""
评估 model_v2.pkl 模型性能
"""
import joblib
import pandas as pd
import numpy as np
import pymysql
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import warnings
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


def load_model_v2():
    """加载model_v2.pkl"""
    print("="*70)
    print("加载 model_v2.pkl")
    print("="*70)
    
    try:
        model_data = joblib.load('model_v2.pkl')
        print(f"\n模型结构:")
        print(f"  类型: {type(model_data)}")
        
        if isinstance(model_data, dict):
            print(f"  包含键: {list(model_data.keys())}")
            for key, value in model_data.items():
                print(f"    {key}: {type(value)}")
                if hasattr(value, 'feature_names_in_'):
                    print(f"      特征数: {len(value.feature_names_in_)}")
        else:
            print(f"  模型类型: {type(model_data)}")
            if hasattr(model_data, 'feature_names_in_'):
                print(f"  特征数: {len(model_data.feature_names_in_)}")
                print(f"  特征名: {model_data.feature_names_in_[:10]}...")
        
        return model_data
    except Exception as e:
        print(f"加载失败: {e}")
        return None


def fetch_test_data():
    """获取2024年测试数据"""
    print("\n" + "="*70)
    print("获取2024年测试数据")
    print("="*70)
    
    conn_qidian = pymysql.connect(**QIDIAN_CONFIG)
    conn_zongheng = pymysql.connect(**ZONGHENG_CONFIG)
    
    # 起点数据
    query_qidian = """
    SELECT year, month, title, author, category, word_count,
           collection_count, monthly_tickets_on_list as monthly_tickets,
           monthly_ticket_count, rank_on_list as monthly_ticket_rank,
           recommendation_count as total_recommend,
           week_recommendation_count as weekly_recommend,
           is_vip, is_sign as is_signed
    FROM novel_monthly_stats
    WHERE year = 2024
    """
    
    # 纵横数据
    query_zongheng = """
    SELECT year, month, title, author, category, word_count,
           monthly_ticket, rank_num as monthly_ticket_rank,
           total_click, total_rec as total_recommend,
           week_rec as weekly_recommend,
           month_donate as contribution_value,
           post_count, fan_count
    FROM zongheng_book_ranks
    WHERE year = 2024
    """
    
    df_qidian = pd.read_sql(query_qidian, conn_qidian)
    df_zongheng = pd.read_sql(query_zongheng, conn_zongheng)
    
    conn_qidian.close()
    conn_zongheng.close()
    
    print(f"  起点: {len(df_qidian)} 条")
    print(f"  纵横: {len(df_zongheng)} 条")
    
    return df_qidian, df_zongheng


def evaluate_model(model_data, df_qidian, df_zongheng):
    """评估模型性能"""
    print("\n" + "="*70)
    print("模型评估")
    print("="*70)
    
    # 提取模型和scaler
    if isinstance(model_data, dict):
        model = model_data.get('model', model_data.get('xgboost_model', None))
        scaler = model_data.get('scaler', None)
        feature_names = model_data.get('feature_names', model_data.get('features', None))
    else:
        model = model_data
        scaler = None
        feature_names = None
    
    if model is None:
        print("错误: 无法提取模型")
        return
    
    print(f"\n模型类型: {type(model)}")
    
    # 打印模型特征名
    if feature_names:
        print(f"模型期望特征: {feature_names}")
        print(f"特征数量: {len(feature_names)}")
    
    # 检查是否为XGBoost模型
    if isinstance(model, xgb.Booster):
        print("检测到XGBoost Booster模型")
        
        # 使用模型保存的特征名
        if feature_names:
            model_features = feature_names
        else:
            # 默认特征列表
            model_features = ['word_count', 'collection_count', 'monthly_ticket_rank', 
                             'total_recommend', 'weekly_recommend']
        
        # 为起点数据准备 - 只使用模型期望的特征
        qidian_features = []
        for col in model_features:
            if col in df_qidian.columns:
                qidian_features.append(col)
            else:
                print(f"  警告: 特征 '{col}' 不在数据中，将用0填充")
        
        if len(qidian_features) > 0:
            # 创建特征矩阵，确保列数与模型期望一致
            X_qidian = pd.DataFrame()
            for col in model_features:
                if col in df_qidian.columns:
                    X_qidian[col] = df_qidian[col]
                else:
                    X_qidian[col] = 0
            
            X_qidian = X_qidian.fillna(0).values
            y_qidian = df_qidian['monthly_tickets'].values
            
            # 清理无效值
            valid_mask = np.isfinite(y_qidian) & (y_qidian >= 0)
            X_qidian = X_qidian[valid_mask]
            y_qidian = y_qidian[valid_mask]
            
            print(f"\n起点数据: {len(y_qidian)} 条有效")
            print(f"使用特征: {model_features}")
            print(f"特征矩阵形状: {X_qidian.shape}")
            
            if scaler:
                X_qidian = scaler.transform(X_qidian)
            
            # 预测 - 使用特征名创建DMatrix
            dmatrix = xgb.DMatrix(X_qidian, feature_names=model_features)
            y_pred_log = model.predict(dmatrix)
            
            # 判断是否需要exp转换
            if np.mean(y_pred_log) < 10:
                y_pred = np.expm1(y_pred_log)
            else:
                y_pred = y_pred_log
            
            # 计算指标
            rmse = np.sqrt(mean_squared_error(y_qidian, y_pred))
            mae = mean_absolute_error(y_qidian, y_pred)
            r2 = r2_score(y_qidian, y_pred)
            mape = np.mean(np.abs((y_qidian - y_pred) / (y_qidian + 1))) * 100
            
            print(f"\n起点测试结果:")
            print(f"  RMSE: {rmse:.2f}")
            print(f"  MAE: {mae:.2f}")
            print(f"  R²: {r2:.4f}")
            print(f"  MAPE: {mape:.2f}%")
    
    elif hasattr(model, 'predict'):
        # sklearn风格模型
        print("检测到sklearn风格模型")
        
        # 准备特征
        feature_cols = [c for c in df_qidian.columns 
                       if c not in ['title', 'author', 'category', 'year', 'month', 
                                   'monthly_tickets', 'monthly_ticket_rank', 'is_vip', 'is_signed']]
        
        X = df_qidian[feature_cols].fillna(0).values
        y = df_qidian['monthly_tickets'].values
        
        valid_mask = np.isfinite(y) & (y >= 0)
        X = X[valid_mask]
        y = y[valid_mask]
        
        print(f"\n数据: {len(y)} 条有效")
        print(f"特征数: {X.shape[1]}")
        
        if scaler:
            X = scaler.transform(X)
        
        y_pred = model.predict(X)
        
        # 计算指标
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        mae = mean_absolute_error(y, y_pred)
        r2 = r2_score(y, y_pred)
        mape = np.mean(np.abs((y - y_pred) / (y + 1))) * 100
        
        print(f"\n测试结果:")
        print(f"  RMSE: {rmse:.2f}")
        print(f"  MAE: {mae:.2f}")
        print(f"  R²: {r2:.4f}")
        print(f"  MAPE: {mape:.2f}%")


if __name__ == "__main__":
    # 1. 加载模型
    model_data = load_model_v2()
    
    if model_data is None:
        print("模型加载失败，退出")
        exit(1)
    
    # 2. 获取测试数据
    df_qidian, df_zongheng = fetch_test_data()
    
    # 3. 评估模型
    evaluate_model(model_data, df_qidian, df_zongheng)
    
    print("\n" + "="*70)
    print("评估完成")
    print("="*70)
