import pymysql
import json
import re
import jieba
import time
import pandas as pd
import numpy as np

try:
    from snownlp import SnowNLP
    HAS_SNOWNLP = True
except ImportError:
    HAS_SNOWNLP = False

QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data', 'charset': 'utf8mb4'
}
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[\r\n\t\*#_~]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_features(chapter_content):
    if isinstance(chapter_content, str):
        try:
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
        
    words = list(jieba.cut(full_text))
    # Basic stopwords
    stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
    words_filtered = [w for w in words if len(w.strip()) > 0 and w not in stopwords]
    
    lexical_diversity = len(set(words_filtered)) / len(words_filtered) if len(words_filtered) > 0 else 0
    
    quotes = re.findall(r'[“「](.*?)[”」]', full_text)
    quotes_length = sum(len(q) for q in quotes)
    dialogue_ratio = quotes_length / len(full_text) if len(full_text) > 0 else 0
    
    sentences = re.split(r'[。！？.?!]', full_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 0]
    avg_sentence_len = sum(len(s) for s in sentences) / len(sentences) if len(sentences) > 0 else 0
    
    sentiment_score = 0.5
    if HAS_SNOWNLP and len(full_text) > 0:
        sample_sentences = sentences[:15] if len(sentences) > 15 else sentences
        if sample_sentences:
            try:
                scores = [SnowNLP(s).sentiments for s in sample_sentences]
                sentiment_score = sum(scores) / len(scores)
            except:
                pass

    return {
        "lexical_diversity": lexical_diversity,
        "dialogue_ratio": dialogue_ratio,
        "avg_sentence_len": avg_sentence_len,
        "sentiment_score": sentiment_score
    }

def main():
    print("开始全量抽取书籍的章节文本特征...")
    start_time = time.time()
    
    # 1. 获取带有真实商业数据的书单 (月票榜前列等)
    books_meta = {}
    conn_val = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    with conn_val.cursor() as cur:
        # 取纵横实录的书籍信息（月票、点击量作为 Y 值目标）
        cur.execute("""
            SELECT title, max(monthly_ticket) as max_tickets, max(total_click) as max_clicks
            FROM zongheng_book_ranks
            GROUP BY title
        """)
        for row in cur.fetchall():
            books_meta[row['title']] = {
                'max_tickets': row['max_tickets'] or 0,
                'max_clicks': row['max_clicks'] or 0
            }
    conn_val.close()
    
    # 2. 从章节库中抽取特征
    results = []
    conn_chap = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    with conn_chap.cursor() as cur:
        # 查出拥有章节记录的书籍 (为了快速试练，随机抽取300本)
        cur.execute("SELECT DISTINCT title FROM zongheng_chapters LIMIT 300")
        all_titles = [row['title'] for row in cur.fetchall()]
        
        print(f"找到 {len(all_titles)} 本拥有章节缓存的书籍。正在抽样分析...")
        
        for idx, title in enumerate(all_titles):
            # 每本书抽取前 5 章取平均值，防止数据量过大导致内存溢出和处理过慢
            cur.execute("SELECT content FROM zongheng_chapters WHERE title=%s ORDER BY chapter_num ASC LIMIT 5", (title,))
            chapters = cur.fetchall()
            if not chapters: continue
            
            book_features = []
            for ch in chapters:
                f = extract_features(ch['content'])
                if f: book_features.append(f)
                
            if book_features:
                # 平均该书的各项特征
                target_tickets = books_meta.get(title, {}).get('max_tickets', 0)
                target_clicks = books_meta.get(title, {}).get('max_clicks', 0)
                
                avg_lex = np.mean([f['lexical_diversity'] for f in book_features])
                avg_dia = np.mean([f['dialogue_ratio'] for f in book_features])
                avg_len = np.mean([f['avg_sentence_len'] for f in book_features])
                avg_snt = np.mean([f['sentiment_score'] for f in book_features])
                
                results.append({
                    'title': title,
                    'lexical_diversity': round(float(avg_lex), 3),
                    'dialogue_ratio': round(float(avg_dia), 3),
                    'avg_sentence_len': round(float(avg_len), 1),
                    'sentiment': round(float(avg_snt), 3),
                    'target_tickets': target_tickets,
                    'target_clicks': target_clicks
                })
                
            if (idx + 1) % 10 == 0:
                print(f"已处理 {idx + 1}/{len(all_titles)} 本书...")
                
    conn_chap.close()
    
    # 3. 将结果保存或展示
    df = pd.DataFrame(results)
    df.to_csv('chapter_nlp_features.csv', index=False, encoding='utf-8-sig')
    
    print(f"\n✅ 特征提取完成！耗时 {time.time()-start_time:.1f} 秒")
    print(f"共成功对 {len(df)} 本书进行了特征标定与实绩关联。结果已保存为 chapter_nlp_features.csv")
    
    if len(df) > 0:
        # 计算相关性
        corr_tickets = df[['lexical_diversity', 'dialogue_ratio', 'avg_sentence_len', 'sentiment', 'target_tickets']].corr()['target_tickets']
        print("\n=== 各项写作手法与 [最高月票] 的皮尔逊相关系数 ===")
        for k, v in corr_tickets.items():
            if k != 'target_tickets':
                print(f" - {k}: {v:.3f}")
                
if __name__ == "__main__":
    main()
