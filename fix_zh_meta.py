import pymysql

def fix_zh_meta():
    conn = pymysql.connect(host='localhost', user='root', password='root', autocommit=True)
    cursor = conn.cursor()
    
    print("Propagating Zongheng metadata to null rows...")
    sql = """
    UPDATE zongheng_analysis_v8.zongheng_book_ranks t1
    JOIN (
        SELECT book_id, 
            MAX(title) as title,
            MAX(author) as author, 
            MAX(category) as category, 
            MAX(status) as status, 
            MAX(word_count) as word_count, 
            MAX(total_click) as total_click,
            MAX(total_rec) as total_rec,
            MAX(week_rec) as week_rec,
            MAX(post_count) as post_count,
            MAX(fan_count) as fan_count,
            MAX(is_signed) as is_signed,
            MAX(book_url) as book_url,
            MAX(forum_id) as forum_id,
            MAX(update_frequency) as update_frequency,
            MAX(chapter_interval) as chapter_interval,
            MAX(latest_chapter) as latest_chapter
        FROM zongheng_analysis_v8.zongheng_book_ranks
        WHERE title IS NOT NULL AND status IS NOT NULL
        GROUP BY book_id
    ) t2 ON t1.book_id = t2.book_id
    SET 
        t1.title = IFNULL(t1.title, t2.title),
        t1.author = IFNULL(t1.author, t2.author),
        t1.category = IFNULL(t1.category, t2.category),
        t1.status = IF(t1.status IS NULL OR t1.status='', t2.status, t1.status),
        t1.word_count = IF(t1.word_count=0 OR t1.word_count IS NULL, t2.word_count, t1.word_count),
        t1.total_click = IF(t1.total_click=0 OR t1.total_click IS NULL, t2.total_click, t1.total_click),
        t1.total_rec = IF(t1.total_rec=0 OR t1.total_rec IS NULL, t2.total_rec, t1.total_rec),
        t1.week_rec = IF(t1.week_rec=0 OR t1.week_rec IS NULL, t2.week_rec, t1.week_rec),
        t1.post_count = IF(t1.post_count=0 OR t1.post_count IS NULL, t2.post_count, t1.post_count),
        t1.fan_count = IF(t1.fan_count=0 OR t1.fan_count IS NULL, t2.fan_count, t1.fan_count),
        t1.is_signed = IFNULL(t1.is_signed, t2.is_signed),
        t1.book_url = IFNULL(t1.book_url, t2.book_url),
        t1.forum_id = IFNULL(t1.forum_id, t2.forum_id),
        t1.update_frequency = IFNULL(t1.update_frequency, t2.update_frequency),
        t1.chapter_interval = IFNULL(t1.chapter_interval, t2.chapter_interval),
        t1.latest_chapter = IFNULL(t1.latest_chapter, t2.latest_chapter)
    WHERE t1.status IS NULL OR t1.author IS NULL OR t1.book_url IS NULL OR t1.total_click IS NULL;
    """
    try:
        cursor.execute(sql)
        print("Successfully propagated Zongheng metadata.")
    except Exception as e:
        print("Error propagating Zongheng metadata:", e)

    conn.close()

if __name__ == '__main__':
    fix_zh_meta()
