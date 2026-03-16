import sys
import os
import time
import random
import pymysql
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 确保能加载当前目录的代码
sys.path.append(os.path.dirname(__file__))

from qidian_advance import QidianSpider, DBConnector

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def patch_missing_updates_concurrent():
    print("\n" + "="*60)
    print("🚀 起点数据库极速补全工具 (Patch Tool) v2.0")
    print("特性：去重合并请求 | 并发线程 (x5) | 全量回填")
    print("="*60 + "\n")
    
    # 初始化组件
    db = DBConnector('qidian_data')
    spider = QidianSpider(use_proxy=False)
    
    # 建立连接
    try:
        conn = pymysql.connect(**db.config)
        cursor = conn.cursor()
    except Exception as e:
        logging.error(f"❌ 数据库连接失败: {e}")
        return

    # 1. 查找所有需要补全的唯一 novel_id (去重优化)
    query = """
        SELECT DISTINCT novel_id, title
        FROM novel_monthly_stats 
        WHERE source = 'qidian' AND (updated_at IS NULL OR updated_at = '')
        LIMIT 5000
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print("✅ 检查完毕：没有起点的记录缺失时间，无需补全。")
        conn.close()
        return
        
    print(f"📋 检测到 {len(rows)} 本书籍需要补全。")
    print("🚀 启动并发同步模式 (移动端降维打击)...\n")
    
    success_count = 0
    fail_count = 0
    total_books = len(rows)

    def process_one_book(novel_id, title):
        """线程执行函数：抓取单本书并返回数据"""
        # 为了兼容 QidianSpider.parse_book_detail_mobile，构造一个 Mock 信息
        mock_info = {'novel_id': novel_id, 'title': title}
        # 移动端防护弱，但在并发模式下依然建议有极短的抖动延迟
        time.sleep(random.uniform(0.5, 2.0))
        try:
            data = spider.parse_book_detail_mobile(mock_info, 0, 0)
            return novel_id, title, data
        except Exception as e:
            logging.error(f"  ❌ 抓取 {title}({novel_id}) 失败: {e}")
            return novel_id, title, None

    # 使用线程池并发抓取
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_book = {executor.submit(process_one_book, rid, t): (rid, t) for rid, t in rows}
        
        for future in as_completed(future_to_book):
            novel_id, title, data = future.result()
            
            if data and data.get('updated_at'):
                # 抓取成功，执行全量回填更新 (该 ID 对应的所有月份)
                try:
                    update_sql = """
                        UPDATE novel_monthly_stats 
                        SET 
                            updated_at = %s,
                            latest_chapter = %s,
                            abstract = %s
                        WHERE novel_id = %s AND source = 'qidian' AND (updated_at IS NULL OR updated_at = '')
                    """
                    # 使用当前数据库连接进行同步更新（确保事务）
                    update_cursor = conn.cursor()
                    update_cursor.execute(update_sql, (
                        data['updated_at'], 
                        data['latest_chapter'], 
                        data['abstract'], 
                        novel_id
                    ))
                    conn.commit()
                    success_count += 1
                    affected = update_cursor.rowcount
                    print(f"  ✅ [完成] {title} ({novel_id}) | 更新时间: {data['updated_at']} | 影响条数: {affected}")
                except Exception as e:
                    logging.error(f"  ❌ 更新 {title} 入库失败: {e}")
                    fail_count += 1
            else:
                fail_count += 1
                print(f"  ⚠️ [跳过] {title} ({novel_id}) 解析结果为空.")

    print("\n" + "="*60)
    print(f"🏁 任务总结报告 (v2.0 并速版):")
    print(f"   - 处理书籍总量: {total_books}")
    print(f"   - 同步成功书籍: {success_count}")
    print(f"   - 失败书籍: {fail_count}")
    print(f"   - 处理速度: {(success_count+fail_count)/total_books*100:.1f}%")
    print("="*60 + "\n")
    conn.close()

if __name__ == "__main__":
    patch_missing_updates_concurrent()
