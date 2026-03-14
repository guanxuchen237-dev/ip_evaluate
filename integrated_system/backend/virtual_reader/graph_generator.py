"""
关系图谱生成器
通过 AI 从书籍简介中提取实体和关系，生成知识图谱
"""

import os
import json
import re
import uuid
from typing import Dict, List, Any, Optional

# 导入 AI 服务单例（而不是类）
try:
    from backend.ai_service import ai_service
except ImportError:
    try:
        from ai_service import ai_service
    except ImportError:
        ai_service = None


class GraphGenerator:
    """图谱生成器"""
    
    # 实体类型定义
    ENTITY_TYPES = {
        "角色": {"color": "#4F46E5", "icon": "👤"},
        "物品": {"color": "#10B981", "icon": "📦"},
        "地点": {"color": "#F59E0B", "icon": "📍"},
        "组织": {"color": "#EC4899", "icon": "🏛️"},
        "功法": {"color": "#8B5CF6", "icon": "⚡"},
        "事件": {"color": "#EF4444", "icon": "📢"},
    }
    
    # 关系类型定义
    EDGE_TYPES = {
        "RELATIONSHIP": "关系",
        "CONFLICT": "冲突",
        "POSSESSION": "持有",
        "LOCATION": "位于",
        "ACTION": "行动",
        "BELONGS_TO": "属于",
    }
    
    def __init__(self):
        # 使用已初始化的 ai_service 单例
        self.ai_service = ai_service
    
    def generate_graph(
        self,
        title: str,
        abstract: str,
        content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        根据书籍信息生成关系图谱
        
        Args:
            title: 书名
            abstract: 简介
            content: 可选的章节内容
            
        Returns:
            包含 nodes 和 edges 的图谱数据
        """
        if not self.ai_service:
            return self._generate_empty_graph(title)
        
        # 构建提取文本
        text = f"书名: {title}\n\n简介: {abstract}"
        if content:
            text += f"\n\n内容片段:\n{content[:3000]}"
        
        # 调用 AI 提取实体和关系
        prompt = self._build_extraction_prompt(text)
        
        try:
            print(f"[GraphGenerator] 开始为《{title}》生成图谱...")
            print(f"[GraphGenerator] AI Service 可用: {self.ai_service is not None}")
            
            # 使用正确的 messages 格式调用 AI，model_key 使用 'chat'
            messages = [{"role": "user", "content": prompt}]
            response = self.ai_service._call_model("chat", messages, temperature=0.7, max_tokens=2000)
            
            print(f"[GraphGenerator] AI 返回长度: {len(response) if response else 0}")
            if response:
                print(f"[GraphGenerator] AI 返回前200字: {response[:200]}...")
            
            if response:
                graph_data = self._parse_ai_response(response)
                print(f"[GraphGenerator] 解析得到 {len(graph_data.get('nodes', []))} 个节点")
                if graph_data and len(graph_data.get("nodes", [])) > 1:
                    print(f"[GraphGenerator] 成功生成图谱！")
                    return graph_data
            # 如果 AI 返回无效，使用 fallback
            print(f"[GraphGenerator] AI 返回无效或解析失败，使用 fallback")
            return self._generate_fallback_graph(title, abstract)
        except Exception as e:
            import traceback
            print(f"[GraphGenerator] AI 提取失败: {e}")
            print(f"[GraphGenerator] 详细错误: {traceback.format_exc()}")
            return self._generate_fallback_graph(title, abstract)
    
    def _build_extraction_prompt(self, text: str) -> str:
        """构建实体关系提取 Prompt"""
        return f"""你是一个专业的网络小说分析专家，对各类热门网文非常熟悉。

【任务】
请根据以下书籍信息，结合你对这本小说的了解，生成完整的人物关系图谱。

{text}

【重要说明】
1. 不要局限于简介中提到的内容！简介通常只描述书的特点，不包含具体人物。
2. 请根据你对这本小说的了解，回忆并列出书中的主要角色、重要物品、关键地点等。
3. 如果你不熟悉这本小说，可以根据书名和简介的风格，合理推断可能的角色类型和关系。

【提取要求】
1. 实体类型: 角色、物品、地点、组织、功法、事件
2. 关系类型: 
   - 师徒(RELATIONSHIP) - 师父与弟子
   - 敌对(CONFLICT) - 对手、仇人
   - 持有(POSSESSION) - 拥有某物品/功法
   - 位于(LOCATION) - 在某地点
   - 情感(RELATIONSHIP) - 恋人、朋友、兄弟
   - 属于(BELONGS_TO) - 隶属某组织/势力
3. 请提取 8-15 个关键实体，5-12 条重要关系
4. 主角用 "(主角)" 标注
5. 优先列出：主角、主要配角、反派、重要神器/法宝、关键地点

【输出格式】
请严格按照以下 JSON 格式输出，不要添加任何其他文字：
```json
{{
    "nodes": [
        {{"uuid": "n1", "name": "角色名 (主角)", "labels": ["角色"]}},
        {{"uuid": "n2", "name": "配角名", "labels": ["角色"]}},
        {{"uuid": "n3", "name": "神器名", "labels": ["物品"]}},
        ...
    ],
    "edges": [
        {{"source_node_uuid": "n1", "target_node_uuid": "n2", "name": "师徒", "fact_type": "RELATIONSHIP"}},
        {{"source_node_uuid": "n1", "target_node_uuid": "n3", "name": "持有", "fact_type": "POSSESSION"}},
        ...
    ]
}}
```

请开始生成（记住：利用你对小说的了解，不要只看简介）："""

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """解析 AI 返回的图谱数据"""
        # 尝试提取 JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析
            json_match = re.search(r'\{[\s\S]*"nodes"[\s\S]*"edges"[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group(0)
            else:
                return self._generate_empty_graph("未知")
        
        try:
            data = json.loads(json_str)
            # 验证格式
            if "nodes" not in data or "edges" not in data:
                return self._generate_empty_graph("未知")
            
            # 规范化节点
            for node in data["nodes"]:
                if "uuid" not in node:
                    node["uuid"] = f"n{uuid.uuid4().hex[:8]}"
                if "labels" not in node:
                    node["labels"] = ["角色"]
            
            # 规范化边
            for edge in data["edges"]:
                if "fact_type" not in edge:
                    edge["fact_type"] = "RELATIONSHIP"
            
            return data
        except json.JSONDecodeError as e:
            print(f"[GraphGenerator] JSON 解析失败: {e}")
            return self._generate_empty_graph("未知")
    
    def _generate_empty_graph(self, title: str) -> Dict[str, Any]:
        """生成空图谱"""
        return {
            "nodes": [
                {"uuid": "n1", "name": f"{title} (主角)", "labels": ["角色"]}
            ],
            "edges": []
        }
    
    def _generate_fallback_graph(self, title: str, abstract: str) -> Dict[str, Any]:
        """生成备用图谱（基于简单规则）"""
        nodes = [{"uuid": "n1", "name": f"{title} (主角)", "labels": ["角色"]}]
        edges = []
        
        # 简单的关键词提取
        keywords = self._extract_keywords(abstract)
        
        node_id = 2
        for kw in keywords[:8]:
            node_uuid = f"n{node_id}"
            nodes.append({
                "uuid": node_uuid,
                "name": kw,
                "labels": ["角色"] if node_id <= 3 else ["地点"] if node_id <= 5 else ["物品"]
            })
            edges.append({
                "source_node_uuid": "n1",
                "target_node_uuid": node_uuid,
                "name": "相关",
                "fact_type": "RELATIONSHIP"
            })
            node_id += 1
        
        return {"nodes": nodes, "edges": edges}
    
    def _extract_keywords(self, text: str) -> List[str]:
        """简单的关键词提取"""
        # 匹配中文名字或术语（2-4个字）
        import jieba
        words = list(jieba.cut(text))
        # 过滤停用词和短词
        stopwords = {"的", "是", "在", "了", "和", "与", "或", "一个", "一位", "这个", "那个", "他", "她", "它"}
        keywords = [w for w in words if len(w) >= 2 and w not in stopwords]
        return list(dict.fromkeys(keywords))[:10]  # 去重并取前10个


# 单例
graph_generator = GraphGenerator()
