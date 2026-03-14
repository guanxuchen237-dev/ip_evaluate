import pymysql
import json
import re
import jieba

try:
    from snownlp import SnowNLP
    HAS_SNOWNLP = True
except ImportError:
    HAS_SNOWNLP = False

QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data', 'charset': 'utf8mb4'
}

def clean_text(text):
    if not text:
        return ""
    # Remove HTML tags if any
    text = re.sub(r'<[^>]+>', '', text)
    # Remove markdown/formatting characters
    text = re.sub(r'[\r\n\t\*#_~]+', ' ', text)
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_writing_features(chapter_content):
    if isinstance(chapter_content, str):
        try:
            # Maybe it's json from DB
            content_list = json.loads(chapter_content)
            full_text = " ".join(content_list)
        except:
            full_text = chapter_content
    elif isinstance(chapter_content, list):
        full_text = " ".join(chapter_content)
    else:
        full_text = str(chapter_content)
        
    full_text = clean_text(full_text)
    
    if len(full_text) < 50:
        return None
        
    # 1. Word richness (Lexical Diversity)
    words = list(jieba.cut(full_text))
    words = [w for w in words if len(w.strip()) > 0 and w not in ['的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这']]
    unique_words = set(words)
    lexical_diversity = len(unique_words) / len(words) if len(words) > 0 else 0
    
    # 2. Dialogue Ratio (Quotes percentage)
    quotes = re.findall(r'[“「](.*?)[”」]', full_text)
    quotes_length = sum(len(q) for q in quotes)
    dialogue_ratio = quotes_length / len(full_text) if len(full_text) > 0 else 0
    
    # 3. Sentence features
    sentences = re.split(r'[。！？.?!]', full_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 0]
    avg_sentence_len = sum(len(s) for s in sentences) / len(sentences) if len(sentences) > 0 else 0
    
    # 4. Sentiment (Emotional polarity)
    sentiment_score = 0.5
    if HAS_SNOWNLP and len(full_text) > 0:
        # snownlp works best on sentence level, so average it or sample
        sample_sentences = sentences[:20] if len(sentences) > 20 else sentences
        if sample_sentences:
            try:
                scores = [SnowNLP(s).sentiments for s in sample_sentences]
                sentiment_score = sum(scores) / len(scores)
            except Exception as e:
                pass

    return {
        "text_length": len(full_text),
        "lexical_diversity": round(lexical_diversity, 3),
        "dialogue_ratio": round(dialogue_ratio, 3),
        "avg_sentence_len": round(avg_sentence_len, 1),
        "sentiment_score": round(sentiment_score, 3)
    }

def main():
    print(f"SnowNLP Installed: {HAS_SNOWNLP}")
    conn = pymysql.connect(**QIDIAN_CONFIG)
    try:
        with conn.cursor() as cur:
            # Fetch a few random distinct books
            cur.execute("SELECT DISTINCT title FROM zongheng_chapters LIMIT 5")
            books = cur.fetchall()
            
            for book in books:
                title = book[0]
                print(f"\n============================")
                print(f"书名: {title}")
                print(f"============================")
                
                # Fetch 2 chapters for this book
                cur.execute("SELECT chapter_num, chapter_title, content FROM zongheng_chapters WHERE title=%s LIMIT 2", (title,))
                chapters = cur.fetchall()
                
                for cap in chapters:
                    c_num, c_title, content = cap
                    features = extract_writing_features(content)
                    if not features: continue
                    
                    print(f"-> 第{c_num}章: {c_title}")
                    print(f"   字数: {features['text_length']}")
                    print(f"   词汇丰富度: {features['lexical_diversity']} (越高说明用词越丰富)")
                    print(f"   对话比重: {features['dialogue_ratio'] * 100:.1f}%")
                    print(f"   平均句长: {features['avg_sentence_len']} 字")
                    if HAS_SNOWNLP:
                        print(f"   前20句平均情感值: {features['sentiment_score']} (0=负向, 1=正向)")
                        
    finally:
         conn.close()

if __name__ == "__main__":
    main()
