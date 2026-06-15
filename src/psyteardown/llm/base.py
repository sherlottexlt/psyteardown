"""LLM provider 抽象。pipeline 各步只依赖此接口,不 import 具体 SDK。"""

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """LLM 调用或结构化解析失败。"""


class LLMProvider(ABC):
    @abstractmethod
    def structured_complete(
        self, prompt: str, schema: type[T], *, system: str | None = None
    ) -> T:
        """返回校验过的 schema 实例;解析失败由实现内部重试,仍失败抛 LLMError。"""

    @abstractmethod
    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """返回纯文本回复。"""


class FakeProvider(LLMProvider):
    """测试用:按队列返回预置结果,并记录调用,绝不触网。"""

    def __init__(
        self,
        structured_responses: list | None = None,
        text_responses: list[str] | None = None,
    ):
        self._structured = list(structured_responses or [])
        self._text = list(text_responses or [])
        self.calls: list[dict] = []

    def structured_complete(self, prompt, schema, *, system=None):
        self.calls.append({"prompt": prompt, "system": system, "schema": schema})
        if not self._structured:
            raise LLMError("FakeProvider: structured_responses 队列已耗尽")
        item = self._structured.pop(0)
        if isinstance(item, schema):
            return item
        return schema.model_validate(item)

    def complete(self, prompt, *, system=None):
        self.calls.append({"prompt": prompt, "system": system})
        if not self._text:
            raise LLMError("FakeProvider: text_responses 队列已耗尽")
        return self._text.pop(0)
