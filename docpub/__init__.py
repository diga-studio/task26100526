"""docpub：单页帮助文档发布库。"""
from .errors import PublishError, SourceLocation
from .publisher import publish

__all__ = ["publish", "PublishError", "SourceLocation"]
