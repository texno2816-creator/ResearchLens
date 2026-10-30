import json
import re

from services import llm_client

PROMPT = """You fix spelling mistakes in academic search queries.
Rules:
- Fix only misspelled words (for example "nerral" -> "neural", "Brian's" -> "brain's" when the context is about the brain).
- Do not change the meaning, do not translate, do not add or remove words, do not rephrase.
- If there are no mistakes, return the query unchanged.
Answer with ONLY a JSON object: {"corrected": "<query>"}"""


def _normalize(text):
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def correct_query(query):
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": query},
    ]
    try:
        text, _ = llm_client.chat(messages)
        start, end = text.find("{"), text.rfind("}")
        corrected = json.loads(text[start:end + 1])["corrected"].strip()
    except (llm_client.LLMError, ValueError, KeyError, TypeError, AttributeError):
        return None
    if not corrected or _normalize(corrected) == _normalize(query):
        return None
    # Reject rewrites: a correction should not change the query length much
    if abs(len(corrected.split()) - len(query.split())) > 1:
        return None
    return corrected
