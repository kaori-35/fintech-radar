from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Source:
    name: str
    url: str
    type: str = "rss"
    enabled: bool = True
    tags: list[str] = field(default_factory=list)
    channel_id: Optional[str] = None
    max_items: int = 20
    same_domain_only: bool = False

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            name=data["name"],
            url=data["url"],
            type=data.get("type", "rss"),
            enabled=data.get("enabled", True),
            tags=data.get("tags", []),
            channel_id=data.get("channel_id"),
            max_items=data.get("max_items", 20),
            same_domain_only=data.get("same_domain_only", False),
        )


@dataclass
class FeedItem:
    source_name: str
    source_url: str
    title: str
    link: str
    summary: str = ""
    published_at: Optional[datetime] = None
    source_type: str = "rss"
    categories: list[str] = field(default_factory=list)
    title_zh: str = ""
    summary_zh: str = ""

    @property
    def primary_category(self) -> str:
        return self.categories[0] if self.categories else "general_fintech"
