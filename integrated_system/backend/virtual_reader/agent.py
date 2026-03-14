"""
Virtual Reader Agent.
Simulates reader feedback based on persona profile and chapter content.
"""

from __future__ import annotations

import json
import random
import re
import time
from typing import Any, Dict, List, Optional

try:
    from backend.ai_service import ai_service
    from .profile_generator import ReaderProfile
except ImportError:
    try:
        from ..ai_service import ai_service
        from .profile_generator import ReaderProfile
    except (ImportError, ValueError):
        import os
        import sys

        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        if backend_dir not in sys.path:
            sys.path.append(backend_dir)
        from ai_service import ai_service
        from virtual_reader.profile_generator import ReaderProfile


ALLOWED_EMOTIONS = {"excited", "angry", "bored", "sad", "happy", "neutral"}


class VirtualReaderAgent:
    def __init__(self, profile: ReaderProfile):
        self.profile = profile
        self.memory: List[str] = []

    def seed_memory(self, history: List[str]) -> None:
        if not history:
            return
        seeded: List[str] = []
        for item in history:
            text = str(item or "").strip()
            if not text:
                continue
            if text in seeded:
                continue
            seeded.append(text[:180])
        if seeded:
            self.memory = seeded[-6:]

    def read_and_comment(
        self,
        novel_title: str,
        chapter_title: str,
        chapter_content: str,
        style_examples: Optional[List[Dict[str, str]]] = None,
        story_context: Optional[Dict[str, Any]] = None,
        context_comments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        content_preview = chapter_content[:2200]
        if len(chapter_content) > 2200:
            content_preview += "\n...(后文省略)..."

        event_hint = self._extract_event_hint(chapter_content)
        system_prompt = self._build_system_prompt(
            event_hint,
            style_examples or [],
            context_comments or [],
            story_context or {},
        )
        user_prompt = (
            f"小说：{novel_title}\n"
            f"章节：{chapter_title}\n"
            f"内容片段：\n{content_preview}\n"
        )

        start_time = time.time()
        result: Dict[str, Any]
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = ai_service._call_model(
                "chat",
                messages,
                temperature=0.85,
                max_tokens=220,
            )
            parsed = self._parse_model_response(response)
            result = self._normalize_result(parsed, style_examples or [], story_context or {})
        except Exception as exc:  # noqa: BLE001
            print(f"Agent {self.profile.name} generation failed: {exc}")
            result = self._mock_comment(style_examples or [])

        reader_id = getattr(self.profile, "user_id", getattr(self.profile, "id", "unknown"))
        result["reader_id"] = reader_id
        result["reader_name"] = self.profile.name
        result["vip_level"] = int(getattr(self.profile, "vip_level", 0))
        result["reader_region"] = str(getattr(self.profile, "region", "") or "").strip()
        result["simulated_duration"] = max(int(len(chapter_content) / 22), 3)
        result["latency_ms"] = int((time.time() - start_time) * 1000)

        remember = str(result.get("comment", "")).strip()
        if remember:
            self.memory.append(remember[:180])
            self.memory = self.memory[-5:]

        return result

    def _extract_event_hint(self, content: str) -> str:
        marker = "附加事件："
        if marker not in content:
            return ""
        return content.split(marker, 1)[-1].strip()[:120]

    def _build_system_prompt(
        self,
        event_hint: str,
        style_examples: List[Dict[str, str]],
        context_comments: List[Dict[str, Any]],
        story_context: Dict[str, Any],
    ) -> str:
        tags = ", ".join(getattr(self.profile, "preference_tags", []) or [])
        memory = "；".join(self.memory[-2:]) if self.memory else "无"
        region = str(getattr(self.profile, "region", "") or "").strip() or "未知地区"
        style_block = self._build_style_examples(style_examples)

        context_block = ""
        if context_comments:
            recent = context_comments[-5:]
            lines = [f"#{i} {c.get('reader_name', '未知')}: {c.get('comment', '')}" for i, c in enumerate(recent)]
            context_block = "\n当前评论区环境（可回复其中某条，需在JSON中指定reply_to_index）:\n" + "\n".join(lines) + "\n"
        story_block = self._build_story_context_block(story_context)

        return (
            "你在扮演一位中文网文读者，请给出真实、口语化反馈。\n"
            f"昵称: {self.profile.name}\n"
            f"性别: {getattr(self.profile, 'gender', 'unknown')}\n"
            f"地区: {region}\n"
            f"书龄: {getattr(self.profile, 'reading_age', 1)} 年\n"
            f"人设: {getattr(self.profile, 'persona', '')}\n"
            f"偏好标签: {tags or '通用'}\n"
            f"毒舌指数: {getattr(self.profile, 'toxicity_level', 1)}/10\n"
            f"最近观点记忆: {memory}\n"
            f"外部事件提示: {event_hint or '无'}\n"
            f"{context_block}"
            f"{story_block}"
            f"{style_block}"
            "\n输出要求:\n"
            "1) 只输出 JSON，不要输出任何解释文本。\n"
            "2) score 取值 1-5，允许 0.5 步长。\n"
            "3) emotion 只能是 excited/angry/bored/sad/happy/neutral。\n"
            "4) comment 必须像用户评论，不要出现“作为AI/模型”。\n"
            "4.1) 有剧情证据时，comment 必须和剧情证据一致，不得编造未出现设定。\n"
            "5) 若提供了【评论区环境】，请优先从其中选择一条进行反驳、赞同或补刀（设置 reply_to_index），营造真实讨论氛围。\n"
            "6) comment 不得出现“任务已提交/已暂停模拟/System”等系统文案。\n"
            "7) 风格样本只可借鉴语气，不可复用样本中的具体情节、结论或原句。\n"
            "8) 如果风格样本与剧情证据冲突，必须以剧情证据为准。\n"
            "9) 若回复环境中的评论，请在JSON中包含 \"reply_to_index\" (整数，对应 #i)。\n"
            "10) evidence_ids 填证据编号数组，例如 [\"W1\",\"C1\"]；若提供了剧情证据则至少填1个。\n"
            "11) confidence 为 0-1 小数，表示这条评论与剧情证据的贴合度。\n"
            "\nJSON schema:\n"
            "{\"score\": 3.5, \"emotion\": \"happy\", \"comment\": \"...\", \"reply_to_index\": 0, \"evidence_ids\": [\"W1\"], \"confidence\": 0.82}"
        )

    @staticmethod
    def _build_style_examples(style_examples: List[Dict[str, str]]) -> str:
        if not style_examples:
            return "\n真实评论风格样本: 无\n"
        sample = style_examples[:6]
        lines = []
        for idx, item in enumerate(sample, start=1):
            text = str(item.get("content", "")).strip()
            if not text:
                continue
            if "全是问号" in text or "几个意思" in text:
                continue
            region = str(item.get("region", "")).strip()
            if region:
                lines.append(f"{idx}. [{region}] {text}")
            else:
                lines.append(f"{idx}. {text}")
        if not lines:
            return "\n真实评论风格样本: 无\n"
        return "\n真实评论风格样本（仅参考语气，不要照抄）:\n" + "\n".join(lines) + "\n"

    @staticmethod
    def _build_story_context_block(story_context: Dict[str, Any]) -> str:
        if not story_context:
            return "\n剧情证据: 无（可基于当前片段评论）。\n"
        summary = str(story_context.get("storyline_summary") or "").strip()
        points = story_context.get("key_plot_points") or []
        characters = story_context.get("character_state") or []
        refs = story_context.get("source_refs") or []

        ref_lines: List[str] = []
        if isinstance(refs, list):
            for item in refs[:6]:
                if not isinstance(item, dict):
                    continue
                ref_id = str(item.get("ref_id") or "").strip()
                snippet = str(item.get("snippet") or item.get("reason") or "").strip()
                if ref_id and snippet:
                    ref_lines.append(f"{ref_id}: {snippet[:100]}")

        return (
            "\n剧情证据摘要（优先依据这里发言）:\n"
            f"- 总结: {summary or '无'}\n"
            f"- 关键情节: {'；'.join(str(x) for x in points[:4]) if points else '无'}\n"
            f"- 人物状态: {'；'.join(str(x) for x in characters[:4]) if characters else '无'}\n"
            + (
                "- 证据编号:\n" + "\n".join(f"  - {line}" for line in ref_lines) + "\n"
                if ref_lines
                else "- 证据编号: 无\n"
            )
        )

    def _parse_model_response(self, response: Any) -> Dict[str, Any]:
        if response is None:
            raise ValueError("empty model response")

        text = str(response).strip()
        text = text.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if not match:
                raise
            return json.loads(match.group(0))

    def _normalize_result(
        self,
        data: Dict[str, Any],
        style_examples: List[Dict[str, str]],
        story_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            score = float(data.get("score", 3.0))
        except Exception:  # noqa: BLE001
            score = 3.0
        score = min(max(score, 1.0), 5.0)
        score = round(score * 2) / 2

        emotion = str(data.get("emotion", "neutral")).strip().lower()
        if emotion not in ALLOWED_EMOTIONS:
            emotion = "neutral"

        comment = str(data.get("comment", "")).strip()
        if not comment:
            comment = self._mock_comment(style_examples)["comment"]

        # Drop system-like phrases that should never appear in reader comments.
        bad_tokens = ("任务已提交", "已暂停模拟", "system", "System")
        lowered = comment.lower()
        if any(token.lower() in lowered for token in bad_tokens):
            comment = self._mock_comment(style_examples)["comment"]

        # 计算 sentiment: 将 1-5 分数转换为 -1 到 1 的范围
        # score 3.0 = sentiment 0, score 1.0 = sentiment -1, score 5.0 = sentiment 1
        sentiment = (score - 3.0) / 2.0
        
        reply_to_index = data.get("reply_to_index")
        if isinstance(reply_to_index, (int, float)):
            reply_to_index = int(reply_to_index)
        else:
            reply_to_index = None

        raw_evidence_ids = data.get("evidence_ids")
        evidence_ids: List[str] = []
        if isinstance(raw_evidence_ids, list):
            for item in raw_evidence_ids:
                value = str(item or "").strip()
                if not value or value in evidence_ids:
                    continue
                evidence_ids.append(value[:24])
                if len(evidence_ids) >= 4:
                    break
        available_refs = story_context.get("source_refs") if isinstance(story_context, dict) else []
        valid_ref_ids = set()
        if isinstance(available_refs, list):
            for ref in available_refs:
                if not isinstance(ref, dict):
                    continue
                ref_id = str(ref.get("ref_id") or "").strip()
                if ref_id:
                    valid_ref_ids.add(ref_id)
        if valid_ref_ids:
            evidence_ids = [x for x in evidence_ids if x in valid_ref_ids]
            if not evidence_ids:
                evidence_ids = [next(iter(valid_ref_ids))]

        raw_confidence = data.get("confidence", 0.5)
        try:
            confidence = float(raw_confidence)
        except Exception:  # noqa: BLE001
            confidence = 0.5
        confidence = min(max(confidence, 0.0), 1.0)

        return {
            "score": score,
            "emotion": emotion,
            "comment": comment,
            "sentiment": round(sentiment, 2),
            "reply_to_index": reply_to_index,
            "evidence_ids": evidence_ids,
            "confidence": round(confidence, 3),
        }

    def _mock_comment(self, style_examples: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        toxicity = int(getattr(self.profile, "toxicity_level", 1) or 1)
        tags = getattr(self.profile, "preference_tags", []) or []
        tag = tags[0] if tags else "剧情"

        tone_hint = ""
        if style_examples:
            joined = " ".join(
                str(item.get("content", "")).strip() for item in style_examples[:4]
            )
            if any(w in joined for w in ("绝了", "上头", "期待", "好看", "精彩")):
                tone_hint = "这波情绪算是拉起来了。"
            elif any(w in joined for w in ("崩", "降智", "拖", "水", "失望")):
                tone_hint = "问题主要还是在节奏和推进上。"

        mild_pool = [
            f"这章的{tag}味道还可以，再紧一点会更好。",
            "节奏顺了很多，人物情绪也更自然。",
            "整体能看，期待下一章把冲突再拉满。",
        ]
        sharp_pool = [
            f"{tag}点子不错，但推进还是有点松。",
            "能看出想要高能，但关键节点还差临门一脚。",
            "优点有，问题也明显：信息量够了，张力还不够。",
        ]

        pool = sharp_pool if toxicity >= 7 else mild_pool
        comment = random.choice(pool)
        if tone_hint:
            comment = f"{tone_hint}{comment}"

        if toxicity >= 7:
            emotion = "angry"
            score = random.choice([2.0, 2.5, 3.0])
        else:
            emotion = random.choice(["happy", "neutral", "excited"])
            score = random.choice([3.0, 3.5, 4.0, 4.5])

        # 计算 sentiment: 将 1-5 分数转换为 -1 到 1 的范围
        sentiment = (score - 3.0) / 2.0

        return {
            "score": score,
            "emotion": emotion,
            "comment": comment,
            "sentiment": round(sentiment, 2),  # 情感值 -1 到 1
            "evidence_ids": [],
            "confidence": 0.32,
        }
