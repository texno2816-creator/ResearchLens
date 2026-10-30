import time

import requests

import config

PROVIDERS = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}

MAX_RETRIES = 5


class LLMError(Exception):
    pass


class RequestTooLarge(LLMError):
    """The request is larger than the per-minute token limit and has to be split."""


def _api_key(provider):
    key = config.GROQ_API_KEY if provider == "groq" else config.OPENROUTER_API_KEY
    if not key:
        raise LLMError(f"Не указан ключ для провайдера '{provider}' в файле .env")
    return key


def _build_body(provider, model, messages):
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0,
    }
    if provider == "groq":
        body["max_completion_tokens"] = config.MAX_OUTPUT_TOKENS
    else:
        body["max_tokens"] = config.MAX_OUTPUT_TOKENS
    if "gpt-oss" in model:
        if provider == "groq":
            body["reasoning_effort"] = "low"
        else:
            body["reasoning"] = {"effort": "low"}
    return body


def chat(messages, provider=None, model=None):
    provider = provider or config.LLM_PROVIDER
    model = model or config.LLM_MODEL
    if provider not in PROVIDERS:
        raise LLMError(f"Неизвестный провайдер: {provider}")

    headers = {
        "Authorization": f"Bearer {_api_key(provider)}",
        "Content-Type": "application/json",
    }
    body = _build_body(provider, model, messages)

    for attempt in range(MAX_RETRIES):
        response = requests.post(PROVIDERS[provider], headers=headers, json=body, timeout=120)

        # 429: rate limit hit, wait and retry
        if response.status_code == 429 or response.status_code >= 500:
            wait = response.headers.get("retry-after")
            wait = float(wait) if wait else 2 ** attempt * 2
            time.sleep(min(wait, 60))
            continue

        # 413: the request is larger than the per-minute limit; retrying won't help, the batch must be split
        if response.status_code == 413:
            raise RequestTooLarge(f"Запрос слишком большой для лимита {provider}: {response.text[:200]}")

        if response.status_code != 200:
            raise LLMError(f"Ошибка {response.status_code} от {provider}: {response.text[:300]}")

        data = response.json()
        text = data["choices"][0]["message"].get("content") or ""
        tokens = (data.get("usage") or {}).get("total_tokens", 0)
        return text, tokens

    raise LLMError(f"{provider} не ответил после {MAX_RETRIES} попыток (лимиты или сбой)")
