"""
清洗脚本：去除 zongheng_chapters 表内容中末尾的奇怪数字
例如："齐麟方才念着的，正是齐家的祖训。5" → "齐麟方才念着的，正是齐家的祖训。"
"""
import pymysql
import re

ZONGHENG_CONFIG = {
    'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 
    'database': 'zongheng_analysis_v8', 'charset': 'utf8mb4'
}

def clean_content():
    print("开始清洗 zongheng_chapters 表内容...")
    
    conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    cursor = conn.cursor()
    
    # 获取所有内容不为空的记录
    cursor.execute("SELECT id, content FROM zongheng_chapters WHERE content IS NOT NULL AND content != ''")
    rows = cursor.fetchall()
    print(f"✓ 找到 {len(rows)} 条需要处理的记录")
    
    cleaned_count = 0
    pattern = r'^(.*?)\s*\d+$'  # 匹配末尾的数字
    
    for row in rows:
        original = row['content']
        lines = original.split('\n')
        new_lines = []
        changed = False
        
        for line in lines:
            # 去除行尾的空白和数字
            cleaned_line = re.sub(r'\s*\d+$', '', line.rstrip())
            new_lines.append(cleaned_line)
            if cleaned_line != line:
                changed = True
        
        new_content = '\n'.join(new_lines)
        
        if changed:
            cursor.execute(
                "UPDATE zongheng_chapters SET content = %s WHERE id = %s",
                (new_content, row['id'])
            )
            cleaned_count += 1
            
            if cleaned_count % 500 == 0:
                conn.commit()
                print(f"✓ 已清洗 {cleaned_count} 条记录")
    
    conn.commit()
    print(f"\n清洗完成！共处理 {cleaned_count} 条记录")
    
    # 显示一个示例
    cursor.execute("SELECT title, chapter_num, content FROM zongheng_chapters WHERE content IS NOT NULL LIMIT 1")
    sample = cursor.fetchone()
    if sample:
        print(f"\n示例 (前200字符):")
        print(f"书名: {sample['title']}, 第{sample['chapter_num']}章")
        print(f"内容: {sample['content'][:200]}...")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    try:
        clean_content()
    except Exception as e:
        print(f"清洗失败: {e}")
        import traceback
        traceback.print_exc()
