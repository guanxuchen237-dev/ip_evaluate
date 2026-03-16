"""
测试AI审计当前使用的预测模型
"""
import joblib
import os
import pandas as pd
import numpy as np
import pymysql
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb

# 数据库配置
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'qidian_data', 'charset': 'utf8mb4'
}
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}


def check_current_models():
    """检查当前项目使用的模型文件"""
    print("="*70)
    print("检查AI审计当前使用的模型")
    print("="*70)
    
    base_dir = "d:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend"
    models_dir = os.path.join(base_dir, 'resources/models')
    
    # 1. 检查 model_v2.pkl (发现已损坏)
    model_v2_path = os.path.join(base_dir, 'model_v2.pkl')
    print(f"\n1. model_v2.pkl:")
    print(f"   路径: {model_v2_path}")
    print(f"   存在: {os.path.exists(model_v2_path)}")
    if os.path.exists(model_v2_path):
        size = os.path.getsize(model_v2_path) / 1024 / 1024
        print(f"   大小: {size:.2f} MB")
        print(f"   状态: ❌ 已测试，MAPE 99.79%，不可用")
    
    # 2. 检查 xgboost_model.pkl (默认模型)
    xgb_path = os.path.join(models_dir, 'xgboost_model.pkl')
    print(f"\n2. xgboost_model.pkl (默认模型):")
    print(f"   路径: {xgb_path}")
    print(f"   存在: {os.path.exists(xgb_path)}")
    if os.path.exists(xgb_path):
        size = os.path.getsize(xgb_path) / 1024 / 1024
        print(f"   大小: {size:.2f} MB")
        
        # 加载并检查
        try:
            model_data = joblib.load(xgb_path)
            print(f"   类型: {type(model_data)}")
            if isinstance(model_data, dict):
                print(f"   包含键: {list(model_data.keys())}")
                if 'model' in model_data:
                    model = model_data['model']
                    print(f"   模型类型: {type(model)}")
                    if hasattr(model, 'feature_names_in_'):
                        features = model.feature_names_in_
                        print(f"   特征数: {len(features)}")
                        print(f"   特征名: {list(features[:5])}...")
            return model_data
        except Exception as e:
            print(f"   加载错误: {e}")
    
    return None


def test_model_on_2024_data(model_data):
    """在2024年数据上测试模型"""
    print("\n" + "="*70)
    print("在2024年数据上测试当前默认模型")
    print("="*70)
    
    # 提取模型
    if isinstance(model_data, dict):
        model = model_data.get('model')
        scaler = model_data.get('scaler')
        feature_names = model_data.get('feature_names', model_data.get('features'))
    else:
        model = model_data
        scaler = None
        feature_names = None
    
    if model is None:
        print("错误: 无法提取模型")
        return
    
    # 获取2024年测试数据
    print("\n获取2024年测试数据...")
    conn = pymysql.connect(**QIDIAN_CONFIG)
    query = """
    SELECT year, month, title, author, category, word_count,
           collection_count, monthly_tickets_on_list as monthly_tickets,
           monthly_ticket_count, rank_on_list as monthly_ticket_rank,
           recommendation_count as total_recommend,
           week_recommendation_count as weekly_recommend
    FROM novel_monthly_stats
    WHERE year = 2024
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"获取到 {len(df)} 条起点2024年数据")
    
    # 准备特征
    if feature_names:
        print(f"\n模型期望特征: {feature_names}")
        
        # 创建特征矩阵
        X = pd.DataFrame()
        for col in feature_names:
            if col in df.columns:
                X[col] = df[col]
            else:
                print(f"   警告: 特征 '{col}' 缺失，用0填充")
                X[col] = 0
        
        X = X.fillna(0).values
        y = df['monthly_tickets'].values
        
        # 清理无效值
        valid_mask = np.isfinite(y) & (y >= 0)
        X = X[valid_mask]
        y = y[valid_mask]
        
        print(f"\n有效样本: {len(y)} 条")
        print(f"特征矩阵形状: {X.shape}")
        
        # 标准化
        if scaler:
            X = scaler.transform(X)
        
        # 预测
        if isinstance(model, xgb.Booster):
            dmatrix = xgb.DMatrix(X, feature_names=feature_names)
            y_pred_log = model.predict(dmatrix)
            # 判断是否需要exp转换
            if np.mean(y_pred_log) < 10:
                y_pred = np.expm1(y_pred_log)
            else:
                y_pred = y_pred_log
        else:
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
        
        return {'rmse': rmse, 'mae': mae, 'r2': r2, 'mape': mape}
    else:
        print("错误: 模型没有特征名信息")
        return None


def compare_with_model_e():
    """与Model E对比"""
    print("\n" + "="*70)
    print("与最新训练的Model E对比")
    print("="*70)
    
    models_dir = "d:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models"
    model_e_path = os.path.join(models_dir, 'ticket_comments_enhanced_20260315_000101.pkl')
    
    print(f"\nModel E 路径: {model_e_path}")
    print(f"存在: {os.path.exists(model_e_path)}")
    
    if os.path.exists(model_e_path):
        print("\nModel E 性能 (已测试):")
        print("  MAPE: 7.77%")
        print("  R²: 0.9216")
        print("  特征数: 97")
        print("  包含: 章节NLP + 评论情感 + 地区分布")


if __name__ == "__main__":
    # 1. 检查当前模型
    model_data = check_current_models()
    
    # 2. 测试当前模型
    if model_data:
        result = test_model_on_2024_data(model_data)
    
    # 3. 与Model E对比
    compare_with_model_e()
    
    print("\n" + "="*70)
    print("总结")
    print("="*70)
    print("AI审计功能当前可能使用的模型:")
    print("  1. model_v2.pkl - ❌ 已损坏 (MAPE 99.79%)")
    print("  2. xgboost_model.pkl - 待测试")
    print("\n建议: 如果当前默认模型性能不佳，应替换为Model E")
    print("      (ticket_comments_enhanced_20260315_000101.pkl)")
