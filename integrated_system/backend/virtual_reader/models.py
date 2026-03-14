"""
Unified Persona model shared by chat and virtual-reader modules.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List
import uuid


@dataclass
class Persona:
    # Common identity
    id: str
    name: str
    avatar: str
    bio: str

    # Roleplay fields
    persona: str
    scenario: str
    color: str
    title: str

    # Reader fields
    reading_age: int

    # Defaults
    gender: str = "unknown"
    age: int = 20
    region: str = ""
    preference_tags: List[str] = field(default_factory=list)
    toxicity_level: int = 1
    vip_level: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "avatar": self.avatar,
            "bio": self.bio,
            "gender": self.gender,
            "age": self.age,
            "region": self.region,
            "persona": self.persona,
            "scenario": self.scenario,
            "color": self.color,
            "title": self.title,
            "reading_age": self.reading_age,
            "preference_tags": self.preference_tags,
            "toxicity_level": self.toxicity_level,
            "vip_level": self.vip_level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Persona":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "未知用户"),
            avatar=data.get("avatar", "👤"),
            bio=data.get("bio", ""),
            gender=data.get("gender", "unknown"),
            age=int(data.get("age", 20)),
            region=str(data.get("region", "") or "").strip(),
            persona=data.get("persona", ""),
            scenario=data.get("scenario", "普通书友"),
            color=data.get("color", "bg-slate-500"),
            title=data.get("title", "读者"),
            reading_age=int(data.get("reading_age", 1)),
            preference_tags=data.get("preference_tags", []),
            toxicity_level=int(data.get("toxicity_level", 1)),
            vip_level=int(data.get("vip_level", 0)),
        )
