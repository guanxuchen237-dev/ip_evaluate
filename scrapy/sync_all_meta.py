# -*- coding: utf-8 -*-
import os
import sys
import logging

# 确保脚本所在目录在路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from qidian_sync_intro import deep_sync_qidian
from zongheng_sync_meta import sync_zongheng_meta

def main():
    print("="*60)
    print("🌟 跨平台全自动【作品元数据同步】工具 v1.0")
    print("目标字段：封面图 (Cover)、简介 (Abstract/Synopsis)、最新章节时间")
    print("-" * 60)
    
    print("\n[Step 1/2] 正在启动 纵横 (Requests) 补全任务...")
    try:
        sync_zongheng_meta()
    except Exception as e:
        print(f"❌ 纵横同步发生错误: {e}")

    print("\n[Step 2/2] 正在启动 起点 (Selenium) 【定向深度补完】任务...")
    try:
        # 改用深度同步模式，直接从数据库查询缺失 ID 并爬取详情页
        deep_sync_qidian()
    except Exception as e:
        print(f"❌ 起点同步发生错误: {e}")

    print("\n" + "="*60)
    print("🎉 全平台同步任务已完成！您可以前往数据库或前端查看最新数据。")
    print("="*60)

if __name__ == '__main__':
    main()
