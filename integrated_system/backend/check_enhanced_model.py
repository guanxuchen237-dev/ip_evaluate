"""
检查已有的增强模型特征
"""
import joblib
import numpy as np

print("=" * 70)
print("检查已有增强模型")
print("=" * 70)

# 加载最新的评论增强模型
model_path = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/ticket_comments_enhanced_20260315_000101.pkl'

try:
    model_data = joblib.load(model_path)
    
    print(f"\n模型类型: {type(model_data)}")
    
    if isinstance(model_data, dict):
        print(f"\n模型包含的键:")
        for key in model_data.keys():
            print(f"   - {key}")
        
        # 检查特征名
        if 'feature_names' in model_data:
            features = model_data['feature_names']
            print(f"\n总特征数: {len(features)}")
            
            # 分类特征
            nlp_features = [f for f in features if any(k in f for k in ['sentiment', 'chapter', 'vocabulary', 'action', 'dialog', 'scene', 'title_', 'topic_'])]
            comment_features = [f for f in features if any(k in f for k in ['comment_', 'tier', 'region_', 'positive_', 'negative_', 'top_region'])]
            numeric_features = [f for f in features if f not in nlp_features and f not in comment_features]
            
            print(f"\n特征分类:")
            print(f"   数值特征: {len(numeric_features)}")
            print(f"   NLP特征: {len(nlp_features)}")
            print(f"   评论特征: {len(comment_features)}")
            
            print(f"\nNLP特征列表:")
            for f in nlp_features[:15]:
                print(f"   - {f}")
            if len(nlp_features) > 15:
                print(f"   ... 还有{len(nlp_features)-15}个")
            
            print(f"\n评论特征列表:")
            for f in comment_features[:15]:
                print(f"   - {f}")
            if len(comment_features) > 15:
                print(f"   ... 还有{len(comment_features)-15}个")
            
            print(f"\n数值特征列表:")
            for f in numeric_features[:20]:
                print(f"   - {f}")
            if len(numeric_features) > 20:
                print(f"   ... 还有{len(numeric_features)-20}个")
        
        # 检查模型性能
        if 'model' in model_data:
            print(f"\n模型类型: {type(model_data['model'])}")
            
except Exception as e:
    print(f"加载错误: {e}")

# 也检查xgboost_model.pkl
print("\n" + "=" * 70)
print("检查默认xgboost模型")
print("=" * 70)

try:
    model_path2 = 'd:/ip-lumina-main-2/ip-lumina-main/integrated_system/backend/resources/models/xgboost_model.pkl'
    model_data2 = joblib.load(model_path2)
    
    print(f"\n模型类型: {type(model_data2)}")
    
    if isinstance(model_data2, dict):
        print(f"\n模型包含的键:")
        for key in model_data2.keys():
            print(f"   - {key}")
        
        if 'feature_names' in model_data2:
            features2 = model_data2['feature_names']
            print(f"\n总特征数: {len(features2)}")
            
            # 分类
            nlp_features2 = [f for f in features2 if any(k in f for k in ['sentiment', 'chapter', 'vocabulary', 'action', 'dialog', 'scene', 'title_', 'topic_'])]
            comment_features2 = [f for f in features2 if any(k in f for k in ['comment_', 'tier', 'region_', 'positive_', 'negative_', 'top_region'])]
            
            print(f"\nNLP特征: {len(nlp_features2)}")
            print(f"评论特征: {len(comment_features2)}")
            
            if nlp_features2:
                print(f"\nNLP特征示例:")
                for f in nlp_features2[:10]:
                    print(f"   - {f}")
            
            if comment_features2:
                print(f"\n评论特征示例:")
                for f in comment_features2[:10]:
                    print(f"   - {f}")
                    
except Exception as e:
    print(f"加载错误: {e}")

print("\n" + "=" * 70)
print("检查完成!")
print("=" * 70)
