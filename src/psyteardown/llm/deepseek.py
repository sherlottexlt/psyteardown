"""DeepSeek LLM provider:OpenAI 兼容 /chat/completions,纯标准库,零新依赖。

结构化输出策略:DeepSeek 的 JSON mode(response_format=json_object)只保证输出
合法 JSON,不保证匹配 schema——所以把 Pydantic JSON Schema 拼进 system 提示,
拿到文本后本地 model_validate_json 校验,失败重试(与 ClaudeProvider 同语义)。
"""

import json
import os
from urllib.request import Request, urlopen

from psyteardown.llm.base import LLMError, LLMProvider, T

DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com"
_TIMEOUT_SECONDS = 600


def _strip_fence(text: str) -> str:
    """容错:剥掉模型偶尔包裹的 ```json ... ``` 代码栅栏。"""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


class DeepSeekProvider(LLMProvider):
    def __init__(
        self,
        model: str | None = None,
        max_retries: int = 2,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise LLMError(
                "未找到 DEEPSEEK_API_KEY。请设置环境变量,或传入 api_key。"
            )
        self._key = key
        self.model = model or os.environ.get("DEEPSEEK_MODEL") or DEFAULT_MODEL
        raw = base_url or os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_BASE_URL
        self.base_url = raw.rstrip("/")
        self._max_retries = max_retries

    def _chat(self, messages: list[dict], *, json_mode: bool) -> str:
        body: dict = {"model": self.model, "messages": messages}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        req = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._key}",
            },
        )
        with urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"DeepSeek 响应格式异常:{payload}") from e

    def structured_complete(self, prompt, schema: type[T], *, system=None) -> T:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        sys_msg = (
            (f"{system}\n\n" if system else "")
            + "你必须只输出一个 JSON 对象(不要多余文字、不要代码栅栏),"
            f"严格符合以下 JSON Schema:\n{schema_json}"
        )
        messages = [{"role": "system", "content": sys_msg},
                    {"role": "user", "content": prompt}]
        last_err: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                text = self._chat(messages, json_mode=True)
                return schema.model_validate_json(_strip_fence(text))
            except Exception as e:  # noqa: BLE001 — 网络/JSON/校验统一重试
                last_err = e
        raise LLMError(f"结构化调用在重试后仍失败: {last_err}") from last_err

    def complete(self, prompt, *, system=None) -> str:
        messages = ([{"role": "system", "content": system}] if system else []) \
            + [{"role": "user", "content": prompt}]
        try:
            return self._chat(messages, json_mode=False)
        except LLMError:
            raise
        except Exception as e:  # noqa: BLE001
            raise LLMError(f"文本调用失败: {e}") from e
