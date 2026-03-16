import re
import subprocess

def solve_waf_cookie(html):
    m_render = re.search(r'<textarea id="renderData"[^>]*>(.*?)</textarea>', html, flags=re.S)
    m_script = re.search(r'<script[^>]*name="aliyunwaf[^>]*">(.*?)</script>', html, flags=re.S)
    
    if not m_render or not m_script:
        print("未检测到 WAF 指纹")
        return None
        
    renderData = m_render.group(1).strip()
    script_content = m_script.group(1).strip()
    
    # 构造能够被 Node.js 执行并输出 cookie 的 js
    # 我们知道原脚本最终会调用 reload(acw_sc__v2)
    # 所以我们覆盖 reload 并在其中 console.log
    js_code = f"""
        var window = {{}};
        var document = {{cookie: '', referrer: ''}};
        var location = {{href: ''}};
        var navigator = {{userAgent: 'Mozilla/5.0'}};
        var renderData = {renderData};
        var arg1 = renderData.l1.slice(10, 60);
        function setCookie(e, r) {{ 
            if (e === 'acw_sc__v2') {{
                console.log(r);
                process.exit(0);
            }}
        }}
        function reload(e) {{
            console.log(e); 
            process.exit(0);
        }}
        {script_content}
    """
    
    with open('solve.js', 'w', encoding='utf-8') as f:
        f.write(js_code)
        
    try:
        out = subprocess.check_output(['node', 'solve.js'], timeout=5).decode('utf-8').strip()
        return out
    except Exception as e:
        print(f"Node 执行失败: {e}")
        return None

if __name__ == '__main__':
    with open('zongheng_m_debug.html', 'r', encoding='utf-8') as f:
        html = f.read()
    cookie = solve_waf_cookie(html)
    print("生成 Cookie:", cookie)
    
    if cookie:
        import requests
        s = requests.Session()
        s.trust_env = False
        url = 'https://m.zongheng.com/h5/book?bookId=1328623'
        resp = s.get(url, headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)'}, cookies={'acw_sc__v2': cookie})
        print("验证结果 (是否有textarea):", '<textarea' in resp.text)
        print("Title contained:", '霜雪照曦言之九州化龙诀' in resp.text)
