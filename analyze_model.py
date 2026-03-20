import joblib
import os

model_path = 'integrated_system/backend/resources/models/model_j_oracle_v7.pkl'
print(f'=== Model Analysis ===')
print(f'File: {model_path}')
print(f'Size: {os.path.getsize(model_path) / 1024:.1f} KB')

model = joblib.load(model_path)
print(f'\nType: {type(model).__name__}')

if isinstance(model, dict):
    print(f'Keys: {list(model.keys())}')
    
    # Analyze ip_model key
    if 'ip_model' in model:
        m = model['ip_model']
        print(f'\n--- sklearn Model (ip_model) ---')
        print(f'Class: {m.__class__.__module__}.{m.__class__.__name__}')
        print(f'Has predict: {hasattr(m, "predict")}')
        print(f'Has predict_proba: {hasattr(m, "predict_proba")}')
        
        if hasattr(m, 'feature_names_in_'):
            print(f'\nFeatures ({len(m.feature_names_in_)}): {list(m.feature_names_in_)}')
        if hasattr(m, 'n_features_in_'):
            print(f'n_features_in_: {m.n_features_in_}')
        if hasattr(m, 'feature_importances_'):
            print(f'feature_importances_ shape: {m.feature_importances_.shape}')
            # Top features
            if hasattr(m, 'feature_names_in_'):
                indices = m.feature_importances_.argsort()[::-1][:10]
                print('\nTop 10 features:')
                for i in indices:
                    print(f'  {m.feature_names_in_[i]}: {m.feature_importances_[i]:.4f}')
        if hasattr(m, 'get_params'):
            params = m.get_params()
            print(f'\nParameters:')
            for k in ['n_estimators', 'max_depth', 'learning_rate', 'loss', 'random_state', 'n_jobs', 'min_samples_split', 'min_samples_leaf']:
                if k in params:
                    print(f'  {k}: {params[k]}')
    
    # Analyze features key
    if 'features' in model:
        print(f'\n--- features ---')
        print(f'Type: {type(model["features"])}')
        print(f'Value: {model["features"]}')
    
    # Analyze metrics key
    if 'metrics' in model:
        print(f'\n--- metrics ---')
        print(f'Value: {model["metrics"]}')
    
    # Analyze version and timestamp
    if 'version' in model:
        print(f'\n--- version ---')
        print(f'Value: {model["version"]}')
    if 'timestamp' in model:
        print(f'\n--- timestamp ---')
        print(f'Value: {model["timestamp"]}')
    
    # Analyze improvements
    if 'improvements' in model:
        print(f'\n--- improvements ---')
        print(f'Value: {model["improvements"]}')
    
    # Analyze grade_distribution
    if 'grade_distribution' in model:
        print(f'\n--- grade_distribution ---')
        gd = model['grade_distribution']
        print(f'Grades: {list(gd.keys())}')
        for k in gd:
            print(f'  {k}: {gd[k]}')
