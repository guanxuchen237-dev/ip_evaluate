import sys
import os
from datetime import datetime

# 确保能导入 qidian_advance
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from qidian_advance import QidianSpider, DBConnector

def test_single_book():
    spider = QidianSpider()
    db = DBConnector('qidian_data')
    
    # 构造一个模拟的 book_info
    book_info = {
        'book_id': '1036370336', 
        'title': '测试书籍',
        'url': 'https://book.qidian.com/info/1036370336/',
        'rank_on_list': 1,
        'monthly_tickets_on_list': 100
    }
    
    print(f"🔍 正在通过 qidian_advance 逻辑抓取详情页: {book_info['url']}")
    data = spider.parse_book_detail(book_info, 2024, 1)
    
    if data:
        print("✅ 抓取成功！数据预览：")
        print(f"   标题: {data.get('title')}")
        print(f"   最新章节: {data.get('latest_chapter')}")
        print(f"   更新时间: {data.get('updated_at')}")
        print(f"   简介摘要: {data.get('abstract')[:30]}...")
        
        print("\n💾 尝试入库...")
        db.save_novel_monthly(data)
        print("✅ 入库操作完成（如有报错由于开启了 print 应会显示）")
    else:
        print("❌ 抓取失败，可能依然受阻。")

if __name__ == "__main__":
    test_single_book()
