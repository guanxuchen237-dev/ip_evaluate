"""
修复方案：让AI审计使用你的XGBoost+K-Means模型
替换 data_manager.py 中的 predict_ip() 方法
"""

# 在 data_manager.py 顶部添加导入
import xgboost as xgb

# 替换 predict_ip() 方法（约第893行开始）
def predict_ip_v2(self, input_data):
    """
    V2.0: 使用XGBoost+K-Means模型预测（替代启发式）
    """
    title = input_data.get('title', '')
    platform = input_data.get('platform', 'Qidian')
    
    # 如果没有加载v2模型，回退到启发式
    if not hasattr(self, 'pipeline_v2') or self.pipeline_v2 is None:
        print("[WARN] v2模型未加载，使用启发式评分")
        return self.predict_ip(input_data)  # 调用旧方法
    
    try:
        # 1. 从数据库获取该书的时序数据
        from datetime import datetime
        
        # 查最近3个月的数据用于计算特征
        config = QIDIAN_CONFIG if platform == 'Qidian' else ZONGHENG_CONFIG
        table = 'novel_monthly_stats' if platform == 'Qidian' else 'zongheng_book_ranks'
        fin_col = 'monthly_ticket_count' if platform == 'Qidian' else 'monthly_ticket'
        
        conn = pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT year, month, word_count, 
                       {fin_col} as finance,
                       collection_count as popularity,
                       reward_count as fans_count
                FROM {table} 
                WHERE title = %s 
                ORDER BY year DESC, month DESC 
                LIMIT 3
            """, (title,))
            rows = cur.fetchall()
        conn.close()
        
        if len(rows) < 2:
            # 数据不足，回退到启发式
            return self.predict_ip(input_data)
        
        # 2. 计算时序特征（模仿你的predictive_model_v2.py）
        latest = rows[0]
        prev = rows[1]
        
        word_count = float(latest['word_count'] or 0)
        word_count_diff = word_count - float(prev['word_count'] or 0)
        word_count_diff = max(0, word_count_diff)  # 修复负数
        
        finance = float(latest['finance'] or 0)
        prev_finance = float(prev['finance'] or 0)
        finance_growth_rate = (finance - prev_finance) / (prev_finance + 1)
        
        fans_count = float(latest['fans_count'] or 0)
        prev_fans = float(prev.get('fans_count', 0) or 0)
        fans_diff = fans_count - prev_fans
        
        popularity = float(latest['popularity'] or 0)
        prev_pop = float(prev.get('popularity', 0) or 0)
        pop_diff = popularity - prev_pop
        
        retention_rate = fans_diff / (pop_diff + 1)
        
        # 估算断更月数（字数未增长）
        cum_drop_months = sum(1 for r in rows[1:] if r['word_count'] == rows[rows.index(r)-1]['word_count'])
        
        # 修正月票（处理月中数据不完整）
        recalc_finance = finance * 1.2 if finance > 0 else 0
        
        # 3. 组装特征向量
        features = {
            'word_count': word_count,
            'word_count_diff': word_count_diff,
            'cum_drop_months': cum_drop_months,
            'popularity': popularity,
            'pop_diff': pop_diff,
            'retention_rate': retention_rate,
            'fans_count': fans_count,
            'fans_diff': fans_diff,
            'recalc_finance': recalc_finance,
            'finance_growth_rate': finance_growth_rate
        }
        
        # 4. 准备模型输入
        feature_order = self.pipeline_v2['features']
        X = np.array([[features.get(f, 0) for f in feature_order]])
        
        # 5. 标准化
        scaler = self.pipeline_v2['scaler']
        X_scaled = scaler.transform(X)
        
        # 6. XGBoost预测
        model = self.pipeline_v2['model']
        dmatrix = xgb.DMatrix(X_scaled, feature_names=feature_order)
        pred_log = model.predict(dmatrix)
        
        # 对数反变换
        predicted_finance = np.expm1(pred_log)[0]
        
        # 7. 转换为IP分数（0-100）
        ip_score = self._ticket_to_score(predicted_finance)
        
        print(f"[INFO] XGBoost预测: {title} | 预测月票={predicted_finance:.0f} | IP分={ip_score:.1f}")
        
        return ip_score
        
    except Exception as e:
        print(f"[ERROR] XGBoost预测失败: {e}, 回退到启发式")
        import traceback
        traceback.print_exc()
        return self.predict_ip(input_data)


# 使用说明：
# 1. 将此代码添加到 data_manager.py 中
# 2. 将原来的 predict_ip() 改名为 predict_ip_legacy()
# 3. 将此方法命名为 predict_ip()
# 4. 确保 __init__ 中已加载 self.pipeline_v2 = joblib.load('model_v2.pkl')
