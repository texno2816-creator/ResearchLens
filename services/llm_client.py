"""Отправка запросов к ИИ через Groq или OpenRouter.

Оба провайдера принимают одинаковый формат запроса (как у OpenAI),
поэтому отличаются только адрес, ключ и пара настроек.
"""
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
    """Запрос больше лимита токенов в минуту — его надо разбить на части."""


def _api_key(provider):
    key = config.GROQ_API_KEY if provider == "groq" else config.OPENROUTER_API_KEY
    if not key:
        raise LLMError(f"Не указан ключ для провайдера '{provider}' в файле .env")
    return key


def _build_body(provider, model, messages):
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0,  # минимум случайности: одинаковые оценки при повторе
    }
    # Ограничиваем длину ответа: Groq считает её в лимит заранее
    if provider == "groq":
        body["max_completion_tokens"] = config.MAX_OUTPUT_TOKENS
    else:
        body["max_tokens"] = config.MAX_OUTPUT_TOKENS
    # gpt-oss "думает" перед ответом. Ставим низкий уровень рассуждения: быстрее и дешевле.
    if "gpt-oss" in model:
        if provider == "groq":
            body["reasoning_effort"] = "low"
        else:
            body["reasoning"] = {"effort": "low"}
    return body


def chat(messages, provider=None, model=None):
    """Отправляет сообщения модели. Возвращает (текст ответа, сколько токенов потрачено)."""
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

        # 429 = упёрлись в лимит (например, 8000 токенов в минуту на Groq). Ждём и пробуем снова.
        if response.status_code == 429 or response.status_code >= 500:
            wait = response.headers.get("retry-after")
            wait = float(wait) if wait else 2 ** attempt * 2
            time.sleep(min(wait, 60))
            continue

        # 413 = один запрос больше лимита токенов в минуту. Повтор не поможет — нужно разбить пачку.
        if response.status_code == 413:
            raise RequestTooLarge(f"Запрос слишком большой для лимита {provider}: {response.text[:200]}")

        if response.status_code != 200:
            raise LLMError(f"Ошибка {response.status_code} от {provider}: {response.text[:300]}")

        data = response.json()
        text = data["choices"][0]["message"].get("content") or ""
        tokens = (data.get("usage") or {}).get("total_tokens", 0)
        return text, tokens

    raise LLMError(f"{provider} не ответил после {MAX_RETRIES} попыток (лимиты или сбой)")
