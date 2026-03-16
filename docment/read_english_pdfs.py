"""
读取英文PDF文献并提取摘要
"""
import os
import sys

try:
    import PyPDF2
    print("✅ 使用PyPDF2读取PDF")
    use_lib = 'pypdf2'
except ImportError:
    print("❌ 未安装PyPDF2，尝试安装: pip install PyPDF2")
    sys.exit(1)

def extract_pdf_text(pdf_path, max_pages=10):
    """提取PDF前几页文本"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            num_pages = len(reader.pages)
            
            # 提取前max_pages页
            for i in range(min(max_pages, num_pages)):
                page = reader.pages[i]
                text += page.extract_text() + "\n"
            
            return text, num_pages
    except Exception as e:
        return f"❌ 读取错误: {str(e)}", 0

def main():
    # 新增的英文文献列表
    english_pdfs = [
        "Business-and-government-applications-of-text-mining--amp--Natu_2022_Decision.pdf",
        "Mining-longitudinal-user-sessions-with-deep-learning-to-_2022_Decision-Suppo.pdf",
        "Mining-voices-from-self-expressed-messages-on-social-media_2022_Decision-Sup.pdf",
        "Understanding-consumer-engagement-in-social-media--The_2022_Decision-Support.pdf",
        "Walking-on-air-or-hopping-mad--Understanding-the-impact-of-em_2022_Decision-.pdf",
        "Impact-of-information-timeliness-and-richness-on-public-engage_2022_Decision.pdf",
        "A-multistate-modeling-approach-for-organizational-cybers_2022_Decision-Suppo.pdf",
    ]
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    summaries = []
    
    for i, pdf_file in enumerate(english_pdfs, 1):
        pdf_path = os.path.join(base_dir, pdf_file)
        
        if not os.path.exists(pdf_path):
            print(f"\n⚠️  文件不存在: {pdf_file}")
            continue
        
        print(f"\n{'='*80}")
        print(f"📄 [{i}/{len(english_pdfs)}] {pdf_file[:60]}...")
        print(f"{'='*80}")
        
        text, total_pages = extract_pdf_text(pdf_path, max_pages=5)
        
        if total_pages > 0:
            print(f"📊 总页数: {total_pages}")
            print(f"📝 提取前5页内容（前2000字符）:\n")
            print(text[:2000])
            print("\n...(省略剩余内容)\n")
            
            summaries.append({
                'file': pdf_file,
                'pages': total_pages,
                'preview': text[:2000]
            })
        else:
            print(text)
    
    # 保存摘要到文件
    output_file = os.path.join(base_dir, 'english_papers_preview.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        for summary in summaries:
            f.write(f"\n{'='*80}\n")
            f.write(f"文件: {summary['file']}\n")
            f.write(f"页数: {summary['pages']}\n")
            f.write(f"{'='*80}\n")
            f.write(summary['preview'])
            f.write("\n\n")
    
    print(f"\n✅ 摘要已保存到: {output_file}")

if __name__ == "__main__":
    main()
