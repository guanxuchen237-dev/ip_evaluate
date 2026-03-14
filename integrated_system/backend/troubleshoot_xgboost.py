import sys, os, pandas as pd, numpy as np
sys.path.append('d:/ip-lumina-main/integrated_system/backend')
from data_manager import DataManager

dm = DataManager()
payload1 = {'title': '无敌天命', 'category': '玄幻', 'word_count': 3864000, 'finance': 12841, 'interaction': 87050000, 'popularity': 134590000, 'status': ''}
payload2 = {'title': '无敌天命', 'category': '玄幻奇幻', 'word_count': 3864367, 'finance': 43337, 'interaction': 445076, 'popularity': 89015.2, 'status': ''}

print("----- Payload 1 ------")
def get_raw_score(payload):
    p = dm.predict_ip(payload)
    df_sim = pd.DataFrame([{
        'word_count': payload.get('word_count', 1000000),
        'interaction': payload.get('interaction', 500000),
        'finance': payload.get('finance', 5000),
        'popularity': payload.get('popularity', 50000),
        'category': payload.get('category', '未知'),
        'status': payload.get('status', ''),
        'platform': payload.get('platform', ''),
        'abstract': payload.get('abstract', '')
    }])
    df_sim['sentiment_score'] = 0.5
    df_sim = dm._engineer_features_batch(df_sim)
    f_cols = ['word_count', 'interaction', 'finance', 'popularity', 'sentiment_score', 'topic_0', 'topic_1', 'topic_2', 'topic_3', 'topic_4', 'word_count_log', 'popularity_log', 'interaction_log', 'finance_log', 'interaction_rate', 'gold_content', 'cat_东方玄幻', 'cat_其他', 'cat_历史', 'cat_古典仙侠', 'cat_异世大陆', 'cat_异术超能', 'cat_武侠仙侠', 'cat_玄幻奇幻', 'cat_科幻', 'cat_都市', 'cat_都市生活', 'status_0', 'plat_qidian', 'plat_zongheng']
    for c in f_cols:
        if c not in df_sim.columns: df_sim[c] = 0
    df_sim = df_sim[f_cols]
    return dm.model.predict(dm.scaler.transform(df_sim))[0]

print("----- Payload 1 ------")
p1 = dm.predict_ip(payload1)
print("Score (Clipped):", p1['score'], "Raw:", get_raw_score(payload1))

print("----- Payload 2 ------")
p2 = dm.predict_ip(payload2)
print("Score (Clipped):", p2['score'], "Raw:", get_raw_score(payload2))

from xgboost import DMatrix
import json
print("Done")
