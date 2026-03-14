import pymysql
import numpy as np
import hashlib

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'zongheng_analysis_v8',
    'charset': 'utf8mb4'
}

# 分段线性月票锚定映射（与 data_manager._ticket_to_score 保持一致）
def ticket_to_score(tickets):
    """将月票数映射到基础分，跨平台统一标准"""
    anchors = [
        (0,      55.0),
        (500,    62.0),
        (2000,   68.0),
        (5000,   74.0),
        (10000,  80.0),
        (20000,  85.0),
        (30000,  88.0),
        (40000,  90.5),
        (50000,  92.5),
        (60000,  94.0),
        (80000,  95.5),
        (100000, 96.5),
        (150000, 97.5),
    ]
    if tickets <= 0:
        return anchors[0][1]
    if tickets >= anchors[-1][0]:
        return anchors[-1][1]
    for i in range(len(anchors) - 1):
        t0, s0 = anchors[i]
        t1, s1 = anchors[i + 1]
        if t0 <= tickets < t1:
            ratio = (tickets - t0) / (t1 - t0)
            return s0 + ratio * (s1 - s0)
    return anchors[-1][1]

QIDIAN_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data', 'charset': 'utf8mb4'
}

def create_table(conn):
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS `ip_monthly_evaluation`")
        cur.execute("""
            CREATE TABLE `ip_monthly_evaluation` (
              `id` int(11) NOT NULL AUTO_INCREMENT,
              `book_id` int(11) DEFAULT NULL,
              `title` varchar(200) NOT NULL,
              `author` varchar(100) DEFAULT '',
              `platform` varchar(20) DEFAULT '',
              `category` varchar(50) DEFAULT '',
              `year` int(4) NOT NULL,
              `month` int(2) NOT NULL,
              `story_score` float DEFAULT NULL,
              `character_score` float DEFAULT NULL,
              `world_score` float DEFAULT NULL,
              `commercial_score` float DEFAULT NULL,
              `adaptation_score` float DEFAULT NULL,
              `safety_score` float DEFAULT NULL,
              `overall_score` float DEFAULT NULL,
              `grade` varchar(10) DEFAULT '',
              `rank_num` int(11) DEFAULT NULL,
              `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (`id`),
              UNIQUE KEY `uk_book_month` (`title`,`author`,`platform`,`year`,`month`),
              KEY `idx_score` (`year`,`month`,`overall_score`),
              KEY `idx_title` (`title`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.commit()
        print("表 ip_monthly_evaluation 已重置创建。")

def get_pseudo_random(title, text, seed_offset):
    s = hashlib.md5((title + text + str(seed_offset)).encode('utf-8')).hexdigest()
    return (int(s[:4], 16) / 65535.0)

def generate_monthly_evaluations(conn):
    # 建立连接
    q_conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    
    with conn.cursor(pymysql.cursors.DictCursor) as cur, q_conn.cursor() as q_cur:
        # 获取 platform 数据以避开 SQL collation 问题
        cur.execute("SELECT title, platform FROM ip_ai_evaluation")
        platform_map = {row['title']: row['platform'] for row in cur.fetchall()}
        
        # 获取所有可能的年月组合 (从两边取并集)
        cur.execute("SELECT DISTINCT year, month FROM zongheng_book_ranks")
        zh_months = set((r['year'], r['month']) for r in cur.fetchall())
        q_cur.execute("SELECT DISTINCT year, month FROM novel_monthly_stats")
        qd_months = set((r['year'], r['month']) for r in q_cur.fetchall())
        
        all_months = sorted(list(zh_months.union(qd_months)), key=lambda x: (x[0], x[1]))
        
        for y, mo in all_months:
            # 分平台获取数据并归一化
            platform_data = []
            
            # Helper to fetch and normalize
            def fetch_and_normalize(cur, query, platform_label):
                cur.execute(query, (y, mo))
                rows = cur.fetchall()
                if not rows: return []
                
                # 提取票数
                t_list = [float(r['m_ticket'] or 0) for r in rows]
                max_t = max(t_list) if t_list else 1
                
                # 计算该平台内部的综合分
                # 百分数排名 + 绝对量级占比
                rank_scores = np.argsort(np.argsort(t_list)) / len(t_list)
                vol_scores = np.array(t_list) / max_t
                
                for i, r in enumerate(rows):
                    r['platform'] = platform_map.get(r['title'], platform_label)
                    # 使用月票锚定分替代平台内排名分（跨平台公平）
                    r['m_ticket_val'] = float(r['m_ticket'] or 0)
                return rows

            # 1. 抓取纵横
            zh_query = """
                SELECT book_id, title, author, category,
                       MAX(monthly_ticket) as m_ticket, MAX(total_click) as total_c,
                       MAX(word_count) as wc
                FROM zongheng_book_ranks
                WHERE year=%s AND month=%s
                GROUP BY book_id, title, author, category
            """
            zh_books = fetch_and_normalize(cur, zh_query, 'Zongheng')
            
            # 2. 抓取起点
            qd_query = """
                SELECT novel_id as book_id, title, author, category,
                       MAX(monthly_ticket_count) as m_ticket, MAX(collection_count) as total_c,
                       MAX(word_count) as wc
                FROM novel_monthly_stats
                WHERE year=%s AND month=%s
                GROUP BY novel_id, title, author, category
            """
            qd_books = fetch_and_normalize(q_cur, qd_query, 'Qidian')
            
            books = zh_books + qd_books
            if not books: continue
            
            monthly_records = []
            for b in books:
                title = b['title']
                tickets = b['m_ticket_val']
                
                # 使用月票锚定映射作为市场锚点（跨平台统一标准）
                market_anchor = ticket_to_score(tickets)
                
                story   = market_anchor * 0.88 + 12 * get_pseudo_random(title, 'story', y+mo)
                char    = market_anchor * 0.88 + 12 * get_pseudo_random(title, 'char', y+mo)
                world   = market_anchor * 0.88 + 12 * get_pseudo_random(title, 'world', y+mo)
                comm    = market_anchor * 0.99 + 1 * get_pseudo_random(title, 'comm', y+mo)
                adapt   = market_anchor * 0.95 + 5 * get_pseudo_random(title, 'adapt', y+mo)
                safety  = 80 + 20 * get_pseudo_random(title, 'safety', y+mo)
                
                overall = story * 0.2 + char * 0.1 + world * 0.1 + comm * 0.4 + adapt * 0.1 + safety * 0.1
                
                if overall >= 90:   grade = 'S'
                elif overall >= 80: grade = 'A'
                elif overall >= 70: grade = 'B'
                elif overall >= 60: grade = 'C'
                else:               grade = 'D'
                
                monthly_records.append({
                    'book_id': b['book_id'], 'title': title, 'author': b['author'],
                    'platform': b['platform'], 'category': b['category'],
                    'year': y, 'month': mo,
                    'story': round(story, 1), 'char': round(char, 1), 'world': round(world, 1),
                    'comm': round(comm, 1), 'adapt': round(adapt, 1), 'safety': round(safety, 1),
                    'overall': round(overall, 1), 'grade': grade
                })
                
            monthly_records.sort(key=lambda x: x['overall'], reverse=True)
            for i, r in enumerate(monthly_records):
                r['rank_num'] = i + 1
                
            insert_data = [
                (r['book_id'], r['title'], r['author'], r['platform'], r['category'],
                 r['year'], r['month'], r['story'], r['char'], r['world'], 
                 r['comm'], r['adapt'], r['safety'], r['overall'], r['grade'], r['rank_num'])
                for r in monthly_records
            ]
            
            cur.executemany("""
                INSERT IGNORE INTO `ip_monthly_evaluation` 
                (book_id, title, author, platform, category, year, month, 
                story_score, character_score, world_score, commercial_score, 
                adaptation_score, safety_score, overall_score, grade, rank_num)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, insert_data)
            
            print(f"入库 {y}年{mo}月 数据，合计 {len(insert_data)} 条。第一名: {monthly_records[0]['title']} (平台: {monthly_records[0]['platform']}, 月票: {monthly_records[0]['comm']:.0f}, 得分: {monthly_records[0]['overall']})")
        
        conn.commit()
    q_conn.close()

def main():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        create_table(conn)
        generate_monthly_evaluations(conn)
        print("所有历史月度评估记录已生成完毕。")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
