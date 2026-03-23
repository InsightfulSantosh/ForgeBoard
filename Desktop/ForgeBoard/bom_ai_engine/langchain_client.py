from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_PROVIDER = "google_genai"
SUPPORTED_PROVIDERS = {DEFAULT_PROVIDER}
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


@dataclass(frozen=True)
class LangChainConfig:
    model: str
    provider: str = DEFAULT_PROVIDER
    temperature: float = 0.0


def parse_model_spec(model_spec: str) -> LangChainConfig:
    spec = model_spec.strip()
    if not spec:
        return LangChainConfig(model=DEFAULT_GEMINI_MODEL, provider=DEFAULT_PROVIDER, temperature=0.0)

    if ":" in spec:
        prefix, remainder = spec.split(":", 1)
        if prefix not in SUPPORTED_PROVIDERS:
            raise ValueError(
                "Only Google Gemini through LangChain is supported. "
                "Use a model like `gemini-2.5-flash` or `google_genai:gemini-2.5-flash`."
            )
        if not remainder:
            raise ValueError("A Gemini model name is required after the provider prefix.")
        return LangChainConfig(model=remainder, provider=DEFAULT_PROVIDER, temperature=0.0)

    return LangChainConfig(model=spec, provider=DEFAULT_PROVIDER, temperature=0.0)


def invoke_langchain_chat(prompt: str, config: LangChainConfig) -> str:
    try:
        from langchain.chat_models import init_chat_model
    except ImportError as exc:
        raise RuntimeError(
            "LangChain Gemini support is not installed. Install `langchain` and `langchain-google-genai`."
        ) from exc

    kwargs: dict[str, Any] = {
        "model": config.model,
        "temperature": config.temperature,
        "model_provider": config.provider,
    }

    chat_model = init_chat_model(**kwargs)
    response = chat_model.invoke(prompt)

    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
            else:
                text = getattr(item, "text", None)
                if text:
                    parts.append(str(text))
        if parts:
            return "\n".join(part.strip() for part in parts if part).strip()

    return str(content).strip()
