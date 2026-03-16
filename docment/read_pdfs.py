import os
import sys

# 尝试导入PDF处理库
try:
    import PyPDF2
    print("使用PyPDF2读取PDF")
    use_lib = 'pypdf2'
except ImportError:
    try:
        import pdfplumber
        print("使用pdfplumber读取PDF")
        use_lib = 'pdfplumber'
    except ImportError:
        print("错误：未安装PDF处理库")
        print("请运行: pip install PyPDF2 或 pip install pdfplumber")
        sys.exit(1)

def read_pdf_pypdf2(pdf_path):
    """使用PyPDF2读取PDF"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            num_pages = len(reader.pages)
            print(f"总页数: {num_pages}")
            # 只读取前5页作为摘要
            for i in range(min(5, num_pages)):
                page = reader.pages[i]
                text += page.extract_text()
            return text
    except Exception as e:
        return f"读取错误: {str(e)}"

def read_pdf_pdfplumber(pdf_path):
    """使用pdfplumber读取PDF"""
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            print(f"总页数: {num_pages}")
            # 只读取前5页作为摘要
            for i in range(min(5, num_pages)):
                page = pdf.pages[i]
                text += page.extract_text()
        return text
    except Exception as e:
        return f"读取错误: {str(e)}"

def main():
    pdf_files = [
        "网络文学IP影视化和衍生开发价值评估研究_刘恒.pdf",
        "网络文学IP的影视转化价值评估模型研究_桑子文.pdf",
        "基于自然语言处理技术的电力客户投诉工单文本挖掘分析_吴刚勇.pdf",
        "基于自然语言处理技术的电力文本挖掘与分类_魏焱.pdf",
        "基于Python网络爬虫技术的乡村旅游数据采集与分析_张启宁.pdf",
        "网络爬虫针对"反爬"网站的爬取策略分析_刘清.pdf",
        "网络爬虫针对"反爬"网站的爬取策略研究_邹科文.pdf",
        "网络爬虫对互联网安全的影响及"反爬"策略的研究_黄子豪.pdf",
        "数据可视化在企业价值管理中的应用_刘倩云.pdf",
        "《中国千年区域极端旱涝地图集（1000—2020）》对历史气候数据可视化的价值与应用_白江涛.pdf",
    ]
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(base_dir, pdf_file)
        if not os.path.exists(pdf_path):
            print(f"\n❌ 文件不存在: {pdf_file}")
            continue
            
        print(f"\n{'='*80}")
        print(f"📄 正在读取: {pdf_file}")
        print(f"{'='*80}")
        
        if use_lib == 'pypdf2':
            text = read_pdf_pypdf2(pdf_path)
        else:
            text = read_pdf_pdfplumber(pdf_path)
        
        # 打印前1000个字符
        print(text[:1000])
        print("\n...(省略)\n")

if __name__ == "__main__":
    main()
