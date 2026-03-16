import pandas as pd
import pymysql
import os
from snownlp import SnowNLP

ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

DATA_DIR = r"d:\analysis-novel\data_analysis_v3"
RAW_FILE = os.path.join(DATA_DIR, "featured_data.csv")

def get_sentiment(text):
    if not isinstance(text, str) or not text.strip():
        return 0.5
    try:
        return SnowNLP(text[:200]).sentiments # Limit length
    except:
        return 0.5

def augment_zongheng_sentiment():
    print("Fetching Zongheng comments for sentiment analysis...")
    
    conn = pymysql.connect(**ZONGHENG_CONFIG)
    try:
        # Optimization: Fetch limited random sample directly from DB
        print("Reading sample comments from DB...")
        sql = "SELECT book_id, content FROM zongheng_book_comments LIMIT 30000"
        df_comments = pd.read_sql(sql, conn)
        
        print(f"Loaded {len(df_comments)} comments. columns: {df_comments.columns.tolist()}")
        
        if len(df_comments) == 0:
            return pd.DataFrame(columns=['title', 'avg_comment_sentiment'])

        # Calculate sentiment per comment
        df_comments = df_comments[df_comments['content'].str.len() > 2]
        print("Calculating SnowNLP sentiment...")
        df_comments['sent'] = df_comments['content'].apply(get_sentiment)
        
        # Group by book_id
        # Ensure book_id is string
        df_comments['book_id'] = df_comments['book_id'].astype(str)
        
        book_sent = df_comments.groupby('book_id')['sent'].mean().reset_index()
        book_sent.columns = ['book_id', 'avg_comment_sentiment'] # Rename columns explicitly
        print(f"Grouped into {len(book_sent)} books.")
        
        # Map to Title
        sql_map = "SELECT DISTINCT book_id, title FROM zongheng_book_ranks"
        df_map = pd.read_sql(sql_map, conn)
        df_map['book_id'] = df_map['book_id'].astype(str)
        
        print(f"Loaded map: {len(df_map)} books. columns: {df_map.columns.tolist()}")
        
        # Merge
        result = pd.merge(book_sent, df_map, on='book_id', how='inner')
        print(f"Merged result: {len(result)} rows")
        
        # Handle duplicates if any (one book_id multiple titles?)
        result = result.drop_duplicates(subset=['title'])
        
        return result[['title', 'avg_comment_sentiment']]
        
    finally:
        conn.close()

def update_dataset():
    if not os.path.exists(RAW_FILE):
        print("Raw data not found")
        return
        
    df = pd.read_csv(RAW_FILE)
    
    # 1. Get Zongheng Sentiment
    df_zh_sent = augment_zongheng_sentiment()
    
    # 2. Merge
    # Zongheng rows only
    # Join on 'title'. Note: titles might be duplicates? Usually unique in raw_data extraction
    
    # Pre-calculate Qidian Abstract Sentiment
    print("Calculating Qidian Abstract Sentiment...")
    df['abstract_sentiment'] = df['abstract'].apply(get_sentiment)
    
    # 3. Combine Logic
    # If Platform=Zongheng: use Comment Sentiment (if avail) -> else 0.5
    # If Platform=Qidian: use Abstract Sentiment
    
    # Merge comment sentiment dict
    sent_map = dict(zip(df_zh_sent['title'], df_zh_sent['avg_comment_sentiment']))
    
    def final_sent(row):
        if row['platform'] == 'Qidian':
            return row['abstract_sentiment']
        else:
            # Zongheng
            return sent_map.get(row['title'], 0.5)
            
    df['sentiment_score'] = df.apply(final_sent, axis=1)
    
    # Recalculate intensity
    df['sentiment_intensity'] = (df['sentiment_score'] - 0.5).abs() * 2
    
    # Save back to featured_data (or raw?)
    # Feature engineering script does cleaning too. 
    # Let's write a new 'featured_data_v2.csv'
    
    OUT_FILE = os.path.join(DATA_DIR, "featured_data_v2.csv")
    df.to_csv(OUT_FILE, index=False, encoding='utf-8-sig')
    print(f"✅ Enhanced sentiment data saved to {OUT_FILE}")

if __name__ == "__main__":
    update_dataset()
