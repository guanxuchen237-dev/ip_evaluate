"""
章节内容 NLP 评分器
- 基于已爬取的前 10 章内容进行多维度 NLP 分析
- 输出单一 nlp_score (0-100) 用于整合进总评分
"""
import pymysql
import jieba
import re
import json
import math
from collections import Counter

# 数据库配置
QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306,
    'user': 'root', 'password': 'root',
    'database': 'qidian_data', 'charset': 'utf8mb4'
}
ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306,
    'user': 'root', 'password': 'root',
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

# 情感词典
POSITIVE_WORDS = set('突破 觉醒 震撼 强大 惊叹 兴奋 希望 感激 胜利 勇气 坚定 自信 欢喜 痛快 '
                     '大笑 微笑 温暖 幸福 成功 喜悦 激动 赞叹 精妙 绝妙 威猛 霸气 豪迈 '
                     '感动 心动 期待 惊喜 畅快 爽快 崇拜 敬仰 光芒 辉煌 壮观 奇迹'.split())
NEGATIVE_WORDS = set('死亡 绝望 恐惧 阴谋 黑暗 诅咒 背叛 愤怒 痛苦 悲伤 危机 毁灭 残忍 '
                     '邪恶 阴险 狠毒 恐怖 凄惨 挣扎 崩溃 窒息 恶毒 杀戮 仇恨 颤抖 '
                     '绝境 噩梦 血腥 阴森 哀嚎 哭泣 悲惨 衰败'.split())
TENSION_WORDS = set('突然 骤然 猛然 陡然 忽然 瞬间 爆发 冲击 暴起 急转 剧变 猛增 '
                    '震惊 惊骇 大惊 吃惊 骇然 变色 暴怒 狂风 雷霆 战斗 攻击 '
                    '碰撞 撕裂 崩碎 粉碎 轰鸣'.split())

def extract_text(content):
    """从数据库内容字段提取纯文本"""
    if not content:
        return ""
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return '\n'.join(str(p) for p in parsed)
        except (json.JSONDecodeError, TypeError):
            pass
        return content
    return str(content)


def analyze_chapter_text(text):
    """对单章文本进行多维 NLP 分析"""
    if not text or len(text) < 100:
        return None
    
    # 1. 分词
    words = list(jieba.cut(text))
    words_clean = [w for w in words if len(w) >= 2 and not re.match(r'^[\d\s\W]+$', w)]
    
    if len(words_clean) < 50:
        return None
    
    total_words = len(words_clean)
    unique_words = len(set(words_clean))
    
    # 2. 情感分析
    pos_count = sum(1 for w in words_clean if w in POSITIVE_WORDS)
    neg_count = sum(1 for w in words_clean if w in NEGATIVE_WORDS)
    tension_count = sum(1 for w in words_clean if w in TENSION_WORDS)
    
    emotion_density = (pos_count + neg_count) / total_words * 100 if total_words > 0 else 0
    tension_density = tension_count / total_words * 100 if total_words > 0 else 0
    
    # 情感极性（-1 到 1）
    emotion_total = pos_count + neg_count
    polarity = (pos_count - neg_count) / (emotion_total + 1e-6) if emotion_total > 0 else 0
    
    # 3. 词汇丰富度 (TTR - Type-Token Ratio)
    ttr = unique_words / total_words if total_words > 0 else 0
    
    # 4. 叙事节奏分析
    paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 5]
    avg_para_len = sum(len(p) for p in paragraphs) / max(len(paragraphs), 1)
    
    # 对话密度（引号出现频率）
    dialogue_marks = text.count('"') + text.count('"') + text.count('「') + text.count('"')
    dialogue_density = dialogue_marks / max(len(text) / 1000, 1)
    
    return {
        'total_words': total_words,
        'unique_words': unique_words,
        'ttr': round(ttr, 4),
        'pos_count': pos_count,
        'neg_count': neg_count,
        'tension_count': tension_count,
        'emotion_density': round(emotion_density, 4),
        'tension_density': round(tension_density, 4),
        'polarity': round(polarity, 4),
        'avg_para_len': round(avg_para_len, 1),
        'dialogue_density': round(dialogue_density, 2),
        'paragraph_count': len(paragraphs),
    }


def compute_nlp_score(chapter_analyses):
    """将多章分析结果合成一个 NLP 分数 (0-100)"""
    if not chapter_analyses:
        return 50.0  # 无数据时给50分基准
    
    # 聚合多章指标
    avg_ttr = sum(c['ttr'] for c in chapter_analyses) / len(chapter_analyses)
    avg_emotion = sum(c['emotion_density'] for c in chapter_analyses) / len(chapter_analyses)
    avg_tension = sum(c['tension_density'] for c in chapter_analyses) / len(chapter_analyses)
    avg_dialogue = sum(c['dialogue_density'] for c in chapter_analyses) / len(chapter_analyses)
    
    # 情感变化幅度（多章间的极性标准差，越大说明剧情越跌宕）
    polarities = [c['polarity'] for c in chapter_analyses]
    if len(polarities) >= 2:
        polarity_mean = sum(polarities) / len(polarities)
        polarity_std = math.sqrt(sum((p - polarity_mean) ** 2 for p in polarities) / len(polarities))
    else:
        polarity_std = 0
    
    # 评分维度（各维度 0-20 分，总计 0-100）
    # 1. 词汇丰富度 (0-20): TTR 0.3-0.7 映射到 5-20
    vocab_score = min(20, max(5, (avg_ttr - 0.25) / 0.45 * 15 + 5))
    
    # 2. 情感密度 (0-20): 0.3%-2% 情感词密度较好
    emotion_score = min(20, max(5, avg_emotion / 1.5 * 15 + 5))
    
    # 3. 张力 (0-20): 有紧张感的叙事
    tension_score = min(20, max(5, avg_tension / 0.8 * 12 + 5))
    
    # 4. 叙事节奏 (0-20): 对话密度 + 段落变化
    rhythm_score = min(20, max(5, avg_dialogue * 2 + 5))
    
    # 5. 情感跌宕 (0-20): 极性在章节间的变化
    drama_score = min(20, max(5, polarity_std * 30 + 5))
    
    total = vocab_score + emotion_score + tension_score + rhythm_score + drama_score
    return round(max(20, min(100, total)), 1)


def batch_score_all_books():
    """批量计算所有书籍的 NLP 分数"""
    results = {}
    
    # 1. 起点数据
    print("[NLP] 开始处理起点章节...")
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT book_title FROM qidian_chapters")
            books = [r['book_title'] for r in cur.fetchall()]
        
        for book_title in books:
            with conn.cursor() as cur:
                cur.execute("SELECT chapter_content FROM qidian_chapters WHERE book_title=%s ORDER BY chapter_index LIMIT 10", (book_title,))
                chapters = cur.fetchall()
            
            analyses = []
            for ch in chapters:
                text = extract_text(ch.get('chapter_content'))
                if text and len(text) > 100:
                    a = analyze_chapter_text(text)
                    if a:
                        analyses.append(a)
            
            score = compute_nlp_score(analyses)
            results[(book_title, 'Qidian')] = {
                'score': score,
                'chapters_analyzed': len(analyses),
            }
        
        conn.close()
        print(f"  [OK] 起点: {len([k for k in results if k[1] == 'Qidian'])} 本书完成 NLP 评分")
    except Exception as e:
        print(f"  [ERR] 起点 NLP 失败: {e}")
    
    # 2. 纵横数据
    print("[NLP] 开始处理纵横章节...")
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT title FROM zongheng_chapters WHERE source != 'placeholder'")
            books = [r['title'] for r in cur.fetchall()]
        
        for book_title in books:
            with conn.cursor() as cur:
                cur.execute("SELECT content FROM zongheng_chapters WHERE title=%s AND source != 'placeholder' ORDER BY chapter_num LIMIT 10", (book_title,))
                chapters = cur.fetchall()
            
            analyses = []
            for ch in chapters:
                text = extract_text(ch.get('content'))
                if text and len(text) > 100:
                    a = analyze_chapter_text(text)
                    if a:
                        analyses.append(a)
            
            score = compute_nlp_score(analyses)
            results[(book_title, 'Zongheng')] = {
                'score': score,
                'chapters_analyzed': len(analyses),
            }
        
        conn.close()
        print(f"  [OK] 纵横: {len([k for k in results if k[1] == 'Zongheng'])} 本书完成 NLP 评分")
    except Exception as e:
        print(f"  [ERR] 纵横 NLP 失败: {e}")
    
    print(f"[NLP] 总计 {len(results)} 本书完成章节 NLP 评分")
    return results


if __name__ == '__main__':
    results = batch_score_all_books()
    # 打印 TOP 10 和 BOTTOM 10
    sorted_r = sorted(results.items(), key=lambda x: x[1]['score'], reverse=True)
    print("\n=== NLP TOP 10 ===")
    for (title, plat), info in sorted_r[:10]:
        print(f"  {info['score']:5.1f}  [{plat:10s}] ch={info['chapters_analyzed']}  {title}")
    print("\n=== NLP BOTTOM 10 ===")
    for (title, plat), info in sorted_r[-10:]:
        print(f"  {info['score']:5.1f}  [{plat:10s}] ch={info['chapters_analyzed']}  {title}")
