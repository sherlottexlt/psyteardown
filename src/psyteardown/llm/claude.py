"""默认 LLM provider:Anthropic Claude。结构化输出走 messages.parse。"""

import os

import anthropic

from psyteardown.llm.base import LLMError, LLMProvider, T

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 16000


class ClaudeProvider(LLMProvider):
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        max_retries: int = 2,
        api_key: str | None = None,
    ):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError(
                "未找到 ANTHROPIC_API_KEY。请设置环境变量,或传入 api_key。"
            )
        self._client = anthropic.Anthropic(api_key=key)
        self._model = model
        self._max_tokens = max_tokens
        self._max_retries = max_retries

    def structured_complete(self, prompt, schema: type[T], *, system=None) -> T:
        last_err: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                resp = self._client.messages.parse(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system or anthropic.NOT_GIVEN,
                    messages=[{"role": "user", "content": prompt}],
                    output_format=schema,
                )
                parsed = resp.parsed_output
                if parsed is None:
                    raise LLMError("Claude 返回的结构化输出无法解析为目标 schema")
                return parsed
            except (anthropic.APIError, LLMError) as e:
                last_err = e
        raise LLMError(f"结构化调用在重试后仍失败: {last_err}") from last_err

    def complete(self, prompt, *, system=None) -> str:
        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system or anthropic.NOT_GIVEN,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as e:
            raise LLMError(f"文本调用失败: {e}") from e
        return "".join(b.text for b in resp.content if b.type == "text")
