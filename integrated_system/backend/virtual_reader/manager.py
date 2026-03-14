"""
Persona manager for virtual reader and chat features.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .models import Persona


class PersonaManager:
    def __init__(self) -> None:
        self.personas: Dict[str, Persona] = {}
        self._load_presets()

    def _load_presets(self) -> None:
        presets = [
            Persona(
                id="critic",
                name="毒舌老书虫",
                title="书龄15年 - 鉴毒师",
                avatar="🧐",
                color="bg-slate-700 text-slate-100",
                bio="毒舌书评人",
                persona=(
                    "你是一个阅书十五年的资深老书虫，眼光极高且毒舌。"
                    "看重逻辑自洽和人物智商，对小白文和降智光环深恶痛绝。"
                    "评论风格犀利，一针见血，但对真正的好书不吝赞美。"
                ),
                scenario="书评区",
                reading_age=15,
                gender="male",
                age=35,
                region="北京",
                preference_tags=["逻辑", "黑暗流", "智斗"],
                toxicity_level=8,
                vip_level=8,
            ),
            Persona(
                id="meme_master",
                name="满级乐子人",
                title="互联网冲浪冠军",
                avatar="🤡",
                color="bg-amber-500 text-white",
                bio="乐子人",
                persona=(
                    "你是互联网冲浪十级选手，喜欢玩梗、吐槽、复读。"
                    "不在乎合理性，只要剧情有趣、爽、或者有槽点就行。"
                    "说话幽默风趣，经常使用网络流行语。"
                ),
                scenario="章说",
                reading_age=5,
                gender="male",
                age=22,
                region="四川",
                preference_tags=["玩梗", "搞笑", "迪化"],
                toxicity_level=4,
                vip_level=4,
            ),
            Persona(
                id="sweet_cp",
                name="CP嗑学家",
                title="专注发糖一百年",
                avatar="🍬",
                color="bg-pink-500 text-white",
                bio="民政局搬运工",
                persona=(
                    "你是一个专注于角色情感互动的CP党。"
                    "擅长在玻璃渣里找糖吃，对于感情戏极其敏感，"
                    "致力于把男女主送入洞房，无法接受虐文。"
                ),
                scenario="超话",
                reading_age=3,
                gender="female",
                age=20,
                region="上海",
                preference_tags=["甜宠", "HE", "感情线"],
                toxicity_level=2,
                vip_level=6,
            ),
        ]

        for persona in presets:
            self.personas[persona.id] = persona

    def get_all(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.personas.values()]

    def get_persona(self, persona_id: str) -> Optional[Persona]:
        return self.personas.get(persona_id)

    def add_persona(self, persona_data: Dict[str, Any]) -> Persona:
        normalized = self._validate_and_normalize(persona_data)
        new_persona = Persona.from_dict(normalized)
        self.personas[new_persona.id] = new_persona
        return new_persona

    def _validate_and_normalize(self, persona_data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(persona_data, dict):
            raise ValueError("invalid payload")

        data = dict(persona_data)
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("name is required")
        data["name"] = name

        try:
            reading_age = int(data.get("reading_age", 0))
        except Exception as exc:  # noqa: BLE001
            raise ValueError("reading_age must be an integer") from exc
        if reading_age < 1 or reading_age > 40:
            raise ValueError("reading_age must be between 1 and 40")
        data["reading_age"] = reading_age

        try:
            toxicity = int(data.get("toxicity_level", 1))
        except Exception as exc:  # noqa: BLE001
            raise ValueError("toxicity_level must be an integer") from exc
        if toxicity < 1 or toxicity > 10:
            raise ValueError("toxicity_level must be between 1 and 10")
        data["toxicity_level"] = toxicity

        tags = data.get("preference_tags", [])
        if isinstance(tags, str):
            tags = [t for t in re.split(r"[,\s，]+", tags) if t]
        if not isinstance(tags, list):
            tags = []
        tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        if not tags:
            raise ValueError("preference_tags must contain at least one tag")
        data["preference_tags"] = tags[:8]

        data["gender"] = str(data.get("gender", "unknown")).strip() or "unknown"
        data["age"] = int(data.get("age", 20))
        data["region"] = str(data.get("region", "")).strip()[:32]
        data["bio"] = str(data.get("bio", "")).strip() or f"{name} is an active reader."
        data["persona"] = str(data.get("persona", "")).strip() or "A passionate novel reader."
        data["scenario"] = str(data.get("scenario", "")).strip() or "reader_space"
        data["title"] = str(data.get("title", "")).strip() or "读者"
        data["color"] = str(data.get("color", "")).strip() or "bg-slate-500"
        data["avatar"] = str(data.get("avatar", "")).strip() or "👤"

        return data


persona_manager = PersonaManager()
