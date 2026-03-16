import sys
import os
from datetime import datetime
import pymysql

# Patch input to avoid blocking for Qidian and Zongheng
def mock_input(prompt):
    if "起始" in prompt:
        return "2024-01"
    elif "结束" in prompt:
        return "2024-01"
    elif "目标" in prompt:
        return "100"
    elif "每页数量" in prompt:
        return "20"
    elif "页数" in prompt:
        return "5"
    elif "线程数" in prompt:
        return "3"
    return "1"

import builtins
builtins.input = mock_input

try:
    print("=== 开始更新起点榜单数据 (2024-01) ===")
    import qidian_advance
    qidian_advance.main()
except Exception as e:
    print(f"起点爬取异常: {e}")


