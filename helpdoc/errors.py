"""发布过程的错误类型。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceLocation:
    """定位到来源主题及具体片段插入位置。"""

    topic_id: str
    include_path: tuple[str, ...] = field(default_factory=tuple)

    def __str__(self) -> str:
        if not self.include_path:
            return f"topic '{self.topic_id}'"
        path = " -> ".join(self.include_path)
        return f"topic '{self.topic_id}' at include {path}"


class PublishError(Exception):
    """发布失败。携带出错的来源位置与原因。"""

    def __init__(self, message: str, location: SourceLocation | None = None) -> None:
        self.location = location
        if location is not None:
            message = f"{message} ({location})"
        super().__init__(message)
