from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_SYSTEM_PROMPT = "你是一名专业的AI求职面试助手，回答要具体、可执行，并贴合应届生求职场景。"
VOLCENGINE_DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
VOLCENGINE_DEFAULT_MODEL = "doubao-seed-1-6-250615"
DASHSCOPE_DEFAULT_MODEL = "qwen3.7-plus"


@dataclass(frozen=True)
class LLMResponse:
    content: str
    used_model: str
    offline: bool
    notice: str = ""
    provider: str = "offline"


RUNTIME_ERRORS = (
    OSError,
    RuntimeError,
    TimeoutError,
    ConnectionError,
    ValueError,
    KeyError,
    TypeError,
    AttributeError,
    urllib.error.URLError,
    urllib.error.HTTPError,
)

DASHSCOPE_RUNTIME_ERRORS = RUNTIME_ERRORS


def _read_persisted_windows_env(name: str) -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg
    except ImportError:
        return ""

    locations = [
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ]
    for root, path in locations:
        try:
            with winreg.OpenKey(root, path) as key:
                value, _ = winreg.QueryValueEx(key, name)
                return str(value).strip()
        except OSError:
            continue
    return ""


def get_env(name: str) -> str:
    current = os.getenv(name)
    if current:
        return current.strip()
    if os.getenv("PYTEST_CURRENT_TEST"):
        return ""
    return _read_persisted_windows_env(name).strip()


def volcengine_api_configured() -> bool:
    return bool(get_env("VOLCENGINE_API_KEY"))


def dashscope_api_configured() -> bool:
    return bool(get_env("DASHSCOPE_API_KEY"))


def llm_api_configured() -> bool:
    return volcengine_api_configured() or dashscope_api_configured()


def embedding_api_configured() -> bool:
    return (volcengine_api_configured() and bool(get_env("VOLCENGINE_EMBEDDING_MODEL"))) or dashscope_api_configured()


def active_llm_label() -> str:
    if volcengine_api_configured():
        return "豆包"
    if dashscope_api_configured():
        return "通义千问"
    return "本地模式"


def active_model_name() -> str:
    if volcengine_api_configured():
        return get_env("VOLCENGINE_MODEL") or VOLCENGINE_DEFAULT_MODEL
    if dashscope_api_configured():
        return DASHSCOPE_DEFAULT_MODEL
    return "offline-fallback"


def embed_texts(texts: list[str], model: str = "text-embedding-v3") -> list[list[float]]:
    vectors = _embed_with_volcengine(texts)
    if vectors:
        return vectors
    return _embed_with_dashscope(texts, model=model)


def _embed_with_volcengine(texts: list[str]) -> list[list[float]]:
    api_key = get_env("VOLCENGINE_API_KEY")
    model = get_env("VOLCENGINE_EMBEDDING_MODEL")
    if not api_key or not model:
        return []

    base_url = get_env("VOLCENGINE_BASE_URL") or VOLCENGINE_DEFAULT_BASE_URL
    url = f"{base_url.rstrip('/')}/embeddings"
    payload = {"model": model, "input": texts}
    try:
        data = _post_json(url, api_key, payload, timeout=45)
        embeddings = data.get("data", [])
        return [item.get("embedding", []) for item in embeddings if item.get("embedding")]
    except RUNTIME_ERRORS:
        return []


def _embed_with_dashscope(texts: list[str], model: str = "text-embedding-v3") -> list[list[float]]:
    try:
        import dashscope
    except ImportError:
        return []

    dashscope.api_key = get_env("DASHSCOPE_API_KEY")
    if not dashscope.api_key:
        return []
    try:
        response = dashscope.TextEmbedding.call(model=model, input=texts)
        output = (response.get("output") or {}) if isinstance(response, dict) else {}
        embeddings = output.get("embeddings") or []
        return [item.get("embedding", []) for item in embeddings]
    except DASHSCOPE_RUNTIME_ERRORS:
        return []


class VolcengineLLM:
    def __init__(self, model: str | None = None, base_url: str | None = None) -> None:
        self.model = model or get_env("VOLCENGINE_MODEL") or VOLCENGINE_DEFAULT_MODEL
        self.base_url = (base_url or get_env("VOLCENGINE_BASE_URL") or VOLCENGINE_DEFAULT_BASE_URL).rstrip("/")

    def generate(self, prompt: str, system: str = DEFAULT_SYSTEM_PROMPT) -> LLMResponse:
        api_key = get_env("VOLCENGINE_API_KEY")
        if not api_key:
            return _fallback(prompt, "未检测到 VOLCENGINE_API_KEY，已切换离线演示模式。", provider="volcengine")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.35,
            "max_tokens": 1200,
        }
        try:
            data = _post_json(f"{self.base_url}/chat/completions", api_key, payload, timeout=60)
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                if content:
                    return LLMResponse(content=content, used_model=self.model, offline=False, provider="volcengine")
            return _fallback(prompt, "火山方舟返回为空，已切换离线演示模式。", provider="volcengine")
        except RUNTIME_ERRORS as exc:
            return _fallback(prompt, f"火山方舟调用失败：{_safe_error(exc)}，已切换离线演示模式。", provider="volcengine")


class DashScopeLLM:
    """Compatibility wrapper. Prefer Volcengine when VOLCENGINE_API_KEY exists."""

    def __init__(self, model: str = DASHSCOPE_DEFAULT_MODEL) -> None:
        self.model = model

    def generate(self, prompt: str, system: str = DEFAULT_SYSTEM_PROMPT) -> LLMResponse:
        if volcengine_api_configured():
            response = VolcengineLLM().generate(prompt=prompt, system=system)
            if not response.offline:
                return response
            if not dashscope_api_configured():
                return response

        try:
            import dashscope
        except ImportError:
            return _fallback(prompt, "未安装 DashScope SDK，已切换离线演示模式。", provider="dashscope")

        dashscope.api_key = get_env("DASHSCOPE_API_KEY")
        if not dashscope.api_key:
            return _fallback(prompt, "未检测到可用在线模型 API Key，已切换离线演示模式。", provider="offline")

        try:
            response = dashscope.Generation.call(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                result_format="message",
            )
            if isinstance(response, dict):
                output = response.get("output") or {}
                choices = output.get("choices") or []
                error_message = response.get("message") or response.get("code") or ""
            else:
                output = getattr(response, "output", None) or {}
                choices = output.get("choices") if isinstance(output, dict) else []
                error_message = getattr(response, "message", "") or getattr(response, "code", "")
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                if content:
                    return LLMResponse(content=content, used_model=self.model, offline=False, provider="dashscope")
            if error_message:
                return _fallback(prompt, f"DashScope 调用失败：{_safe_error(RuntimeError(str(error_message)))}，已切换离线演示模式。", provider="dashscope")
        except DASHSCOPE_RUNTIME_ERRORS as exc:
            return _fallback(prompt, f"DashScope 调用失败：{_safe_error(exc)}，已切换离线演示模式。", provider="dashscope")
        return _fallback(prompt, "DashScope 返回为空，已切换离线演示模式。", provider="dashscope")


def _post_json(url: str, api_key: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            data = json.loads(body)
            message = data.get("error", {}).get("message") or data.get("message") or body
        except ValueError:
            message = body or str(exc)
        raise RuntimeError(f"HTTP {exc.code}: {message}") from exc

    data = json.loads(body)
    if "error" in data:
        error = data["error"]
        message = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        raise RuntimeError(message)
    return data


def _fallback(prompt: str, notice: str, provider: str = "offline") -> LLMResponse:
    clipped = " ".join(prompt.split())[:160]
    content = (
        "参考回答：先明确岗位要求，再用 STAR 结构组织经历，"
        f"结合数据、项目结果和个人反思展开。问题摘要：{clipped}"
    )
    return LLMResponse(content=content, used_model="offline-fallback", offline=True, notice=notice, provider=provider)


def _safe_error(exc: BaseException) -> str:
    text = str(exc)
    for secret in [get_env("VOLCENGINE_API_KEY"), get_env("DASHSCOPE_API_KEY")]:
        if secret:
            text = text.replace(secret, "***")
    return text[:240]


def generate_text(prompt: str, system: str = DEFAULT_SYSTEM_PROMPT) -> str:
    return DashScopeLLM().generate(prompt=prompt, system=system).content
