import sys
import os

# 尝试导入 openai，如果失败则提示检查环境
try:
    from openai import OpenAI
    import httpx
except ImportError:
    print("❌ 缺少依赖库 (openai 或 httpx)。请确保您在正确的虚拟环境中运行此脚本。")
    print("尝试运行: pip install openai httpx")
    sys.exit(1)

# 配置
API_KEY = "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"
BASE_URL = "https://integrate.api.nvidia.com/v1"

print(f"🔄 正在测试 NVIDIA API...")
print(f"🔑 Key: {API_KEY[:10]}******")

try:
    # 增加 verify=False 以避免某些代理/VPN 下的 SSL 问题
    http_client = httpx.Client(verify=False, timeout=30.0)
    
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        http_client=http_client
    )

    completion = client.chat.completions.create(
        model="minimaxai/minimax-m2.1",
        messages=[{"role": "user", "content": "Hello, simply reply 'OK'."}],
        temperature=0.5,
        max_tokens=50
    )
    
    print("\n✅ NVIDIA API 测试成功！")
    print(f"📝 回复: {completion.choices[0].message.content}")

except Exception as e:
    print(f"\n❌ NVIDIA API 测试失败！")
    print(f"错误详情: {e}")
    
    # 尝试分析错误
    error_str = str(e)
    if "401" in error_str:
        print("💡 原因: 401 Unauthorized。API Key 无效或已过期。")
    elif "429" in error_str:
        print("💡 原因: 429 Too Many Requests。请求过快或额度用尽。")
    elif "Connect" in error_str or "Time" in error_str:
        print("💡 原因: 连接超时或网络错误。请检查网络或是否需要代理。")
