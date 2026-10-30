import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

import config
from prompts import SYSTEM_PROMPT, build_user_message
from services import llm_client

NO_ABSTRACT_REASON = "No abstract — not evaluated by AI."
ERROR_REASON = "AI evaluation failed for this article."
WORK_TYPES = ("review", "study", "theory", "other")


def category_for(score):
    """The category comes from the score thresholds in config, not from the AI."""
    if score >= config.YES_THRESHOLD:
        return "Yes"
    if score >= config.UNCLEAR_THRESHOLD:
        return "Unclear"
    return "No"


def parse_response(text):
    # Some models wrap their reasoning in <think>...</think>
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("В ответе ИИ нет JSON-массива")
    items = json.loads(text[start:end + 1])

    parsed = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            score = float(item["score"])
        except (KeyError, TypeError, ValueError):
            continue
        work_type = str(item.get("type", "other")).strip().lower()
        parsed[str(item.get("id"))] = {
            "reason": str(item.get("reason", "")).strip(),
            "score": max(1.0, min(10.0, score)),
            "type": work_type if work_type in WORK_TYPES else "other",
        }
    return parsed


def estimate_tokens(text):
    return int(len(text) / 3.5) + 1


def make_batches(query, articles):
    size = max(1, config.BATCH_SIZE)
    budget = config.REQUEST_TOKEN_LIMIT - config.MAX_OUTPUT_TOKENS - 500
    base = estimate_tokens(SYSTEM_PROMPT) + estimate_tokens(build_user_message(query, []))
    batches, current, used = [], [], base
    for article in articles:
        cost = estimate_tokens(build_user_message(query, [dict(article, batch_id="A9")])) - estimate_tokens(build_user_message(query, []))
        if current and (len(current) >= size or used + cost > budget):
            batches.append(current)
            current, used = [], base
        current.append(article)
        used += cost
    if current:
        batches.append(current)
    for batch in batches:
        for n, article in enumerate(batch, start=1):
            article["batch_id"] = f"A{n}"
    return batches


def _score_batch(query, batch, provider, model):
    try:
        return _score_batch_once(query, batch, provider, model)
    except llm_client.RequestTooLarge:
        if len(batch) == 1:
            return {}, 0
        half = len(batch) // 2
        parsed, tokens = {}, 0
        for part in (batch[:half], batch[half:]):
            p, t = _score_batch(query, part, provider, model)
            parsed.update(p)
            tokens += t
        return parsed, tokens


def _score_batch_once(query, batch, provider, model):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(query, batch)},
    ]
    total_tokens = 0
    parsed = {}
    for _ in range(2):
        try:
            text, tokens = llm_client.chat(messages, provider=provider, model=model)
            total_tokens += tokens
            parsed = parse_response(text)
        except (ValueError, json.JSONDecodeError):
            continue
        if all(a["batch_id"] in parsed for a in batch):
            break
    return parsed, total_tokens


def score_articles(query, articles, provider=None, model=None):
    started = time.time()
    with_abstract, results = [], []

    for article in articles:
        article = dict(article)
        if not article.get("abstract"):
            article.update(reason=NO_ABSTRACT_REASON, score=0.0, category="No",
                           type="other", no_abstract=True, error=False)
            results.append(article)
        else:
            with_abstract.append(article)

    batches = make_batches(query, with_abstract)

    total_tokens = 0
    with ThreadPoolExecutor(max_workers=max(1, config.MAX_PARALLEL)) as pool:
        futures = [pool.submit(_score_batch, query, b, provider, model) for b in batches]
        for batch, future in zip(batches, futures):
            parsed, tokens = future.result()
            total_tokens += tokens
            for article in batch:
                found = parsed.get(article["batch_id"])
                if found:
                    article.update(reason=found["reason"], score=found["score"], type=found["type"],
                                   category=category_for(found["score"]), error=False)
                else:
                    article.update(reason=ERROR_REASON, score=0.0, category="No",
                                   type="other", error=True)
                article["no_abstract"] = False
                article.pop("batch_id", None)
                results.append(article)

    results.sort(key=lambda a: a["score"], reverse=True)

    scored = [a for a in results if not a["no_abstract"]]
    stats = {
        "seconds": round(time.time() - started, 1),
        "tokens": total_tokens,
        "total": len(scored),
        "yes": sum(a["category"] == "Yes" for a in scored),
        "unclear": sum(a["category"] == "Unclear" for a in scored),
        "no": sum(a["category"] == "No" for a in scored),
        "no_abstract": sum(a["no_abstract"] for a in results),
        "errors": sum(a["error"] for a in results),
    }
    return results, stats
