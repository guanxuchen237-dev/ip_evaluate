"""
Virtual reader profile generator.
"""

from __future__ import annotations

import json
import random
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from backend.ai_service import ai_service
except ImportError:
    try:
        from ..ai_service import ai_service
    except (ImportError, ValueError):
        import os
        import sys

        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        if backend_dir not in sys.path:
            sys.path.append(backend_dir)
        from ai_service import ai_service


@dataclass
class ReaderProfile:
    user_id: str
    name: str
    age: int
    gender: str
    bio: str
    persona: str
    reading_age: int
    preference_tags: List[str] = field(default_factory=list)
    region: str = ""
    toxicity_level: int = 1
    vip_level: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "bio": self.bio,
            "persona": self.persona,
            "reading_age": self.reading_age,
            "preference_tags": self.preference_tags,
            "region": self.region,
            "toxicity_level": self.toxicity_level,
            "vip_level": self.vip_level,
        }


class ReaderProfileGenerator:
    """Generate virtual reader profiles."""

    def generate_profiles(self, count: int = 5, novel_category: str = "通用") -> List[ReaderProfile]:
        profiles: List[ReaderProfile] = []
        for _ in range(max(1, count)):
            profile = self.generate_single_profile(novel_category)
            if profile:
                profiles.append(profile)
        return profiles

    def generate_single_profile(self, category: str = "通用") -> Optional[ReaderProfile]:
        import uuid

        user_id = f"reader_{str(uuid.uuid4())[:8]}"

        prompt = f"""
请生成一个真实的中国网文读者画像，偏好类型：{category}。

请返回 JSON，字段如下：
- name: 网名
- age: 年龄（整数）
- gender: male/female
- bio: 个性签名（50字内）
- persona: 详细人设（100-200字）
- reading_age: 书龄（1-20）
- preference_tags: 3-5个偏好标签
- region: 地区（省份或城市）
- toxicity_level: 1-10
- vip_level: 0-7
"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = ai_service._call_model("chat", messages, temperature=0.9)
            if not response:
                return self._mock_profile(category, user_id)

            content = str(response).replace("```json", "").replace("```", "").strip()
            data = json.loads(content)

            return ReaderProfile(
                user_id=user_id,
                name=data.get("name", f"书友{str(uuid.uuid4())[:4]}"),
                age=int(data.get("age", 22)),
                gender=str(data.get("gender", "male")),
                bio=str(data.get("bio", "一个普通的网文读者。")),
                persona=str(data.get("persona", "喜欢追更，关注剧情节奏与人物成长。")),
                reading_age=int(data.get("reading_age", 3)),
                preference_tags=data.get("preference_tags", ["热血"]),
                region=str(data.get("region", "")).strip(),
                toxicity_level=int(data.get("toxicity_level", 3)),
                vip_level=int(data.get("vip_level", 1)),
            )

        except Exception as exc:  # noqa: BLE001
            print(f"Profile generation failed: {exc}")
            traceback.print_exc()
            return self._mock_profile(category, user_id)

    def _mock_profile(self, category: str, user_id: str) -> ReaderProfile:
        return ReaderProfile(
            user_id=user_id,
            name=f"书友_{random.randint(1000, 9999)}",
            age=random.randint(18, 38),
            gender=random.choice(["male", "female"]),
            bio="临时读者画像，用于兜底模拟。",
            persona=f"偏好{category}题材，关注剧情推进与人物塑造。",
            reading_age=random.randint(2, 12),
            preference_tags=[category, "追更"],
            region=random.choice(["北京", "上海", "广东", "江苏", "浙江", "四川"]),
            toxicity_level=random.randint(1, 7),
            vip_level=random.randint(0, 4),
        )


reader_profile_generator = ReaderProfileGenerator()
