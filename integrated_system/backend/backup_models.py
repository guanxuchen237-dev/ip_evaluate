"""
备份现有模型
"""
import os
import shutil
from datetime import datetime

def backup_models():
    """备份Model E和Model F"""
    print("="*70)
    print("备份现有模型")
    print("="*70)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f'resources/models/backup_{timestamp}'
    os.makedirs(backup_dir, exist_ok=True)
    
    # 需要备份的文件
    models_to_backup = [
        'ticket_comments_enhanced_20260315_000101.pkl',  # Model E
        'model_f_complete.pkl',  # Model F
    ]
    
    backed_up = []
    for model_file in models_to_backup:
        src = f'resources/models/{model_file}'
        if os.path.exists(src):
            dst = f'{backup_dir}/{model_file}'
            shutil.copy2(src, dst)
            size = os.path.getsize(src) / 1024 / 1024
            print(f"✓ {model_file} ({size:.1f} MB) -> {backup_dir}/")
            backed_up.append(model_file)
        else:
            print(f"✗ {model_file} 不存在")
    
    print(f"\n备份完成: {len(backed_up)} 个模型")
    print(f"备份位置: {backup_dir}/")
    
    # 创建备份记录
    with open(f'{backup_dir}/backup_info.txt', 'w') as f:
        f.write(f"备份时间: {timestamp}\n")
        f.write(f"备份模型:\n")
        for m in backed_up:
            f.write(f"  - {m}\n")
        f.write(f"\n说明:\n")
        f.write(f"- Model E: 97维特征 (NLP+评论+时序)\n")
        f.write(f"- Model F: 双引擎+更新熵+IP基因聚类\n")
    
    return backup_dir

if __name__ == "__main__":
    backup_dir = backup_models()
