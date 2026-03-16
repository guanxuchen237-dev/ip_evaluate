import pandas as pd
import jieba
from snownlp import SnowNLP
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import re

# Config
input_file = "d:/analysis-novel/data_analysis/qidian_features.csv"
output_file = "d:/analysis-novel/data_analysis/qidian_nlp.csv"

def analyze_nlp():
    print("Loading data...")
    df = pd.read_csv(input_file)
    
    # Fill NaN synopsis
    df['synopsis'] = df['synopsis'].fillna('')

    print("1. Performing Sentiment Analysis (SnowNLP)...")
    # Simulate reputation score from description sentiment
    # (In real scenario, use comments. Here we follow Lit 2's method on available text)
    def get_sentiment(text):
        if not text or len(str(text)) < 5:
            return 0.5
        try:
            return SnowNLP(str(text)).sentiments
        except:
            return 0.5

    df['sentiment_score'] = df['synopsis'].apply(get_sentiment)
    print("   Avg Sentiment:", df['sentiment_score'].mean())

    print("2. Topic Modeling (LDA)...")
    # Preprocessing
    stopwords = set(['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '他'])
    
    def cut_text(text):
        words = jieba.cut(str(text))
        return " ".join([w for w in words if w not in stopwords and len(w) > 1])

    df['cut_synopsis'] = df['synopsis'].apply(cut_text)

    # Vectorize
    tf_vectorizer = CountVectorizer(max_df=0.95, min_df=2, max_features=1000)
    tf = tf_vectorizer.fit_transform(df['cut_synopsis'])

    # LDA
    lda = LatentDirichletAllocation(n_components=5, max_iter=20, learning_method='online', random_state=0)
    lda.fit(tf)

    # Extract Dominant Topic
    topic_values = lda.transform(tf)
    df['topic_id'] = topic_values.argmax(axis=1)
    
    # Print Topics
    feature_names = tf_vectorizer.get_feature_names_out()
    print("\nTop 5 Topics found:")
    for topic_idx, topic in enumerate(lda.components_):
        message = "Topic #%d: " % topic_idx
        message += " ".join([feature_names[i] for i in topic.argsort()[:-10 - 1:-1]])
        print(message)
        
    # Save
    df.to_csv(output_file, index=False, encoding='utf-8_sig')
    print(f"\nSaved NLP results to {output_file}")

if __name__ == "__main__":
    analyze_nlp()
