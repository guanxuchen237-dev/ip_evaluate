#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试脚本：测试图谱生成器的 AI 调用
"""

import sys
sys.path.insert(0, r'd:\ip-lumina-main\integrated_system\backend')

from ai_service import ai_service

print("=" * 60)
print("测试 AI 服务连接状态")
print("=" * 60)

print(f"ai_service 实例: {ai_service}")
print(f"ai_service.client: {ai_service.client}")

# 测试 AI 调用
prompt = """你是一个专业的网络小说分析专家。

请列出《斗破苍穹》这本小说中的 5 个主要角色，以 JSON 格式返回：
```json
{
    "nodes": [
        {"uuid": "n1", "name": "萧炎 (主角)", "labels": ["角色"]},
        ...
    ]
}
```
"""

print("\n调用 AI (model_key='chat')...")
messages = [{"role": "user", "content": prompt}]

try:
    print(f"使用的模型: {ai_service.models.get('chat', 'unknown')}")
    response = ai_service._call_model("chat", messages, temperature=0.7, max_tokens=1000)
    print(f"\nAI 返回长度: {len(response) if response else 0}")
    print(f"\nAI 返回内容:\n{response[:500] if response else 'None'}...")
except Exception as e:
    print(f"\n调用失败: {e}")
    import traceback
    traceback.print_exc()
