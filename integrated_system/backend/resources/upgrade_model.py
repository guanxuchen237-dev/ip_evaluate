import pandas as pd
import numpy as np
import jieba
import joblib
import os
from snownlp import SnowNLP
from gensim import corpora, models
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from sklearn.metrics import r2_score, mean_squared_error

# 配置路径 (Adapted to project structure)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'cleaned_data.csv')
MODEL_DIR = os.path.join(BASE_DIR, 'models')
if not os.path.exists(MODEL_DIR): os.makedirs(MODEL_DIR)

MODEL_SAVE_PATH = os.path.join(MODEL_DIR, 'ip_predictor_v2.pkl')
SCALER_SAVE_PATH = os.path.join(MODEL_DIR, 'scaler_v2.pkl')
LDA_MODEL_PATH = os.path.join(MODEL_DIR, 'lda.model')
DICT_PATH = os.path.join(MODEL_DIR, 'dictionary.dict')
COLS_SAVE_PATH = os.path.join(BASE_DIR, 'data', 'feature_columns_v2.txt')

def load_and_preprocess(filepath):
    print("Step 1: 加载数据...")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Data not found at {filepath}")
        
    df = pd.read_csv(filepath)
    
    # 填充缺失值
    df['abstract'] = df['abstract'].fillna('')
    df['word_count'] = df['word_count'].fillna(0)
    df['popularity'] = df['popularity'].fillna(0)
    df['interaction'] = df['interaction'].fillna(0)
    df['finance'] = pd.to_numeric(df['finance'], errors='coerce').fillna(0)
    
    # Clean IP Score
    df['IP_Score'] = pd.to_numeric(df['IP_Score'], errors='coerce').fillna(0)
    
    print(f"数据加载完成，共 {len(df)} 条记录")
    return df

def feature_engineering_nlp(df):
    print("Step 2: 正在进行 NLP 特征提取 (情感分析 + LDA主题)...")
    
    # --- 2.1 情感分析 ---
    # SnowNLP: 0 (负面) -> 1 (正面)
    def safe_snow(text):
        if not isinstance(text, str) or len(text) < 5: return 0.5
        return SnowNLP(text).sentiments
        
    df['sentiment_score'] = df['abstract'].apply(safe_snow)
    print("  -> 情感特征提取完毕")

    # --- 2.2 LDA 主题建模 ---
    # 分词
    stop_words = set(['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '与', '及', '其', '但是', '而'])
    
    def tokenize(text):
        if not isinstance(text, str): return []
        return [w for w in jieba.cut(text) if len(w) > 1 and w not in stop_words]

    docs = df['abstract'].apply(tokenize)
    
    # 构建词典和语料库
    dictionary = corpora.Dictionary(docs)
    # 过滤极端词频
    dictionary.filter_extremes(no_below=3, no_above=0.6)
    corpus = [dictionary.doc2bow(text) for text in docs]
    
    # 训练 LDA 模型
    num_topics = 5
    lda = models.LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=10, random_state=42)
    
    # Save LDA assets for inference
    print(f"  -> Saving LDA model to {LDA_MODEL_PATH}")
    lda.save(LDA_MODEL_PATH)
    dictionary.save(DICT_PATH)
    
    # 获取每本书的主题概率分布
    topic_features = []
    for doc_bow in corpus:
        topics = lda.get_document_topics(doc_bow, minimum_probability=0.0)
        # 转换为向量 [prob_topic_0, prob_topic_1, ..., prob_topic_4]
        topic_vec = [0.0] * num_topics
        for t_id, prob in topics:
            if t_id < num_topics:
                topic_vec[t_id] = prob
        topic_features.append(topic_vec)
    
    # 将主题概率添加到 DataFrame
    topic_df = pd.DataFrame(topic_features, columns=[f'topic_{i}' for i in range(num_topics)])
    df = pd.concat([df, topic_df], axis=1)
    
    # 打印主题关键词
    print("  -> LDA 主题模型训练完毕，发现以下主题:")
    for i in range(num_topics):
        print(f"    Topic {i}: {lda.print_topic(i, topn=5)}")
        
    return df

def feature_engineering_basic(df):
    print("Step 3: 进行数值与类别特征工程...")
    
    # --- 3.1 数值变换 (Log & Ratios) ---
    df['word_count_log'] = np.log1p(df['word_count'])
    df['popularity_log'] = np.log1p(df['popularity'])
    df['interaction_log'] = np.log1p(df['interaction'])
    df['finance_log'] = np.log1p(df['finance'])
    
    # 衍生特征
    df['interaction_rate'] = df['interaction'] / (df['popularity'] + 1)
    df['gold_content'] = df['finance'] / (df['word_count'] + 1)
    
    # --- 3.2 类别特征 One-Hot ---
    if 'category' not in df.columns: df['category'] = '未知'
    top_categories = df['category'].value_counts().nlargest(10).index.tolist()
    df['category_clean'] = df['category'].apply(lambda x: x if x in top_categories else '其他')
    
    # One-Hot 编码 (dummy)
    df = pd.get_dummies(df, columns=['category_clean'], prefix=['cat'])
    
    # Note: status/platform might be less relevant or consistent, keeping checks
    if 'status' in df.columns:
         df = pd.get_dummies(df, columns=['status'], prefix=['status'])
    if 'platform' in df.columns:
         df = pd.get_dummies(df, columns=['platform'], prefix=['plat'])
    
    return df

def train_model(df):
    print("Step 4: 训练 XGBoost 模型...")
    
    exclude_cols = ['title', 'author', 'novel_id', 'abstract', 'year', 'month', 'IP_Score', 
                    'category', 'is_sign', 'fans_count', 'week_recommend', 'category_clean'] 
    
    feature_cols = [c for c in df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])]
    
    print(f"  -> 使用特征数量: {len(feature_cols)}")
    print(f"  -> 特征列表: {feature_cols}")
    
    X = df[feature_cols]
    y = df['IP_Score']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    model = XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42, n_jobs=-1)
    model.fit(X_train_scaled, y_train)
    
    y_pred = model.predict(X_test_scaled)
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    print(f"\n✅ 模型训练完成!")
    print(f"  -> R² Score: {r2:.4f}")
    print(f"  -> RMSE: {rmse:.4f}")
    
    print("Step 5: 保存模型与配置...")
    joblib.dump(model, MODEL_SAVE_PATH)
    joblib.dump(scaler, SCALER_SAVE_PATH)
    
    with open(COLS_SAVE_PATH, 'w') as f:
        f.write('\n'.join(feature_cols))
        
    print(f"  -> 模型已保存至 {MODEL_SAVE_PATH}")
    
    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n🔍 Top 10 重要特征 (特征重要性):")
    print(importances.head(10))

if __name__ == "__main__":
    df = load_and_preprocess(DATA_PATH)
    df = feature_engineering_nlp(df)   
    df = feature_engineering_basic(df) 
    train_model(df)
