from openai import OpenAI
import os
import json
import random

class AIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except:
                pass

    def analyze_prediction(self, title, category, score, abstract, velocity=0, trend=0.5, intensity=0):
        # Even if we use Mock, we define the prompt for potential future usage
        prompt = f"""
        请分析这部网络小说IP:
        标题: {title}
        题材: {category}
        预测分数: {score}
        简介: {abstract}
        
        请返回严格的JSON格式 (不要Markdown):
        {{
            "pros": ["优势1", "优势2", "优势3"],
            "cons": ["风险1", "风险2", "风险3"],
            "comment": "简短的一段战略建议 (50字以内)",
            "trend": [未来6个月热度数值...],
            "scores": {{ "Innovation": 0-100, "Story": 0-100, "Commercial": 0-100 }}
        }}
        请使用中文回复。
        """
        
        # Currently defaulting to Mock for stability/speed as requested
        # If API key is present, one could uncomment the real call logic
        return self._mock_response(score, title)

    def _mock_response(self, base_score=60, title="", abstract=""):
        # Keyword Analysis Engine
        text = (title + abstract).lower()
        
        # 1. Determine Genre/Tone
        is_horror = any(k in text for k in ['鬼', '尸', '惊', '恐', '命', '棺', '灵异'])
        is_urban = any(k in text for k in ['都市', '豪门', '赘婿', '神医', '鉴宝', '直播'])
        is_xuanhuan = any(k in text for k in ['仙', '帝', '神', '魔', '宗', '剑', '玄', '逆天'])
        is_system = '系统' in text
        
        # 2. Dynamic Comments
        if base_score >= 85:
            if is_horror:
                comment = f"《{title}》氛围营造极佳，开篇悬念设置扣人心弦。建议在保持惊悚感的同时，强化主角的破局能力，以提升爽感。"
            elif is_urban:
                comment = f"《{title}》切中都市热点，代入感极强。建议加快打脸节奏，并在中期引入更有张力的反派角色。"
            elif is_xuanhuan:
                comment = f"《{title}》世界观宏大，升级体系清晰。不仅保留了传统玄幻的热血，还融入了新颖的设定，具备爆款潜质。"
            else:
                comment = f"作品《{title}》展现了极高的数据潜力，核心读者群稳固。建议加强粉丝运营，并考虑多版权开发的可能。"
        elif base_score >= 70:
            if is_horror:
                comment = f"题材具有一定稀缺性，恐怖氛围尚可。但剧情推进稍显缓慢，建议在三章内引爆第一个小高潮。"
            elif is_system:
                comment = f"系统流设定符合市场主流，但金手指的爽点释放不够密集。建议优化系统的奖励机制，增强期待感。"
            else:
                comment = f"该作品有一定亮点，文笔流畅。建议优化开篇节奏，前三章需更直接地抛出核心矛盾，避免慢热。"
        else:
            comment = "整体表现中规中矩，缺乏辨识度。建议重新打磨开篇，强化主角的核心驱动力，并增加更有趣的金手指设定。"

        # 3. Dynamic Pros/Cons
        pros = ["文笔流畅"] # Default
        cons = ["更新稳定性需关注"] # Default
        
        if is_horror:
            pros = ["恐怖氛围浓厚", "悬念设置巧妙", "沉浸感强"]
            cons = ["受众群体相对垂直", "后期剧情易崩坏", "审核风险需注意"]
        elif is_system:
            pros = ["金手指设定有趣", "升级反馈清晰", "节奏轻快"]
            cons = ["系统任务略显单一", "主角依赖性过强", "后期数值易膨胀"]
        elif is_urban:
            pros = ["代入感强", "贴近现实生活", "脸谱化反派易拉恨"]
            cons = ["剧情套路化风险", "情感线略显生硬", "缺乏核心创新点"]
        elif is_xuanhuan:
            pros = ["世界观独特", "战斗场面精彩", "热血感足"]
            cons = ["前期铺垫过长", "境界体系略显复杂", "同质化竞争激烈"]
            
        if base_score > 90:
            pros.append("具备全版权开发潜力")
            
        # Deterministic Score Generation
        # Map base_score (60-100) to sub-scores
        s_inno = min(98, int(base_score * 0.95) + 5)
        s_story = min(98, int(base_score * 1.0))
        s_comm = min(98, int(base_score * 0.9) + 10)
        s_world = min(95, int(base_score * 0.95))
        s_char = min(95, int(base_score * 0.98))
        
        # Deterministic Trend
        trend_base = [base_score]
        for i in range(1, 6):
            # Create a simple curve: +2, +3, +1, +4, +2
            increment = (i % 3) + 2
            trend_base.append(min(99, trend_base[-1] + increment))
        
        return {
            "pros": pros,
            "cons": cons,
            "comment": comment,
            "trend": trend_base,
            "scores": {
                "Innovation": s_inno,
                "Story": s_story,
                "Commercial": s_comm,
                "World": s_world,
                "Character": s_char
            }
        }

ai_service = AIService()
