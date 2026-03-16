"""
模型对比：Model E vs Model F vs Model G
对比三个模型的性能和特征
"""
import joblib
import os
import pandas as pd

def compare_models():
    print("="*70)
    print("模型对比分析")
    print("="*70)
    
    models_info = []
    
    # Model E
    e_path = 'resources/models/ticket_comments_enhanced_20260315_000101.pkl'
    if os.path.exists(e_path):
        e_data = joblib.load(e_path)
        models_info.append({
            'Model': 'Model E',
            '描述': 'NLP+评论增强',
            '特征数': len(e_data.get('feature_names', [])),
            'MAPE': '7.77%',
            'R²': '0.9216',
            '创新点': '章节NLP+评论情感+地区分布',
            '文件': 'ticket_comments_enhanced_20260315_000101.pkl'
        })
    
    # Model F
    f_path = 'resources/models/model_f_complete.pkl'
    if os.path.exists(f_path):
        f_data = joblib.load(f_path)
        metrics = f_data.get('dual_engine_results', {}).get('validation_metrics', {})
        mape = metrics.get('mape', 'N/A')
        r2 = metrics.get('r2', 'N/A')
        
        models_info.append({
            'Model': 'Model F',
            '描述': '开题报告实现版',
            '特征数': 26,
            'MAPE': f"{mape:.2f}%" if isinstance(mape, float) else str(mape),
            'R²': f"{r2:.4f}" if isinstance(r2, float) else str(r2),
            '创新点': '双引擎+更新熵+IP基因+改编标签',
            '文件': 'model_f_complete.pkl'
        })
    
    # Model G
    g_path = 'resources/models/model_g_ultimate.pkl'
    if os.path.exists(g_path):
        g_data = joblib.load(g_path)
        metrics = g_data.get('metrics', {})
        mape = metrics.get('mape', 'N/A')
        r2 = metrics.get('r2', 'N/A')
        
        models_info.append({
            'Model': 'Model G',
            '描述': '终极融合版',
            '特征数': '100+',
            'MAPE': f"{mape:.2f}%" if isinstance(mape, float) else str(mape),
            'R²': f"{r2:.4f}" if isinstance(r2, float) else str(r2),
            '创新点': 'E+F全部特征融合',
            '文件': 'model_g_ultimate.pkl'
        })
    
    # 显示对比表
    df = pd.DataFrame(models_info)
    print("\n" + df.to_string(index=False))
    
    # 备份信息
    print("\n" + "="*70)
    print("模型备份")
    print("="*70)
    backup_dirs = [d for d in os.listdir('resources/models') if d.startswith('backup_')]
    if backup_dirs:
        latest = sorted(backup_dirs)[-1]
        print(f"最新备份: resources/models/{latest}/")
        for f in os.listdir(f'resources/models/{latest}'):
            if f.endswith('.pkl'):
                size = os.path.getsize(f'resources/models/{latest}/{f}') / 1024 / 1024
                print(f"  - {f} ({size:.1f} MB)")

if __name__ == "__main__":
    compare_models()
