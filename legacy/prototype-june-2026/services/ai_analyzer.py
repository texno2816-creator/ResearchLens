import requests
import re
from config import GROQ_KEY

def quick_summary(title, abstract, query):
    if not abstract:
        return "Абстракт недоступен.", 5

    prompt = f"""You are a research assistant. A user is searching for papers about: "{query}"

Paper title: {title}
Abstract: {abstract}

Respond in Russian. Give:
1. A 2-3 sentence summary of what this paper is about and what it found.
2. A relevance score from 1 to 10.

Format exactly:
SUMMARY: [summary here]
SCORE: [number 1-10]"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300
            },
            timeout=30
        )

        if response.status_code != 200:
            return "Не удалось получить саммари.", 5

        text = response.json()["choices"][0]["message"]["content"]
        summary = ""
        score = 5

        summary_match = re.search(r'SUMMARY:\s*(.+?)(?=SCORE:|$)', text, re.DOTALL)
        score_match = re.search(r'SCORE:\s*(\d+)', text)

        if summary_match:
            summary = summary_match.group(1).strip().replace("\\n", " ")
        if score_match:
            score = int(score_match.group(1))

        return summary, score

    except Exception as e:
        print(f"Groq error: {e}")
        return "Саммари недоступно.", 5


def deep_analysis(title, abstract, query):
    if not abstract:
        return None

    prompt = f"""You are an expert research analyst. Analyze this paper for a user researching: "{query}"

Title: {title}
Abstract: {abstract}

Respond ENTIRELY in Russian. Translate all terms including scientific and medical ones.

Use this EXACT format (keep the labels in English, content in Russian):
RESEARCH_QUESTION: [исследовательский вопрос на русском]
METHODOLOGY: [методология на русском, 1-2 предложения]
KEY_FINDINGS: [находка 1 на русском] | [находка 2 на русском] | [находка 3 на русском]
LIMITATIONS: [ограничение 1 на русском] | [ограничение 2 на русском]
BEST_USED_FOR: [одно из: Введение / Обзор литературы / Методология / Обсуждение]
RELEVANCE: [число от 1 до 10]
ANALYSIS_BASED_ON: Только абстракт"""
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 600
            },
            timeout=30
        )

        if response.status_code != 200:
            return None

        text = response.json()["choices"][0]["message"]["content"]

        def extract(key):
            m = re.search(rf'{key}:\s*(.+?)(?=\n[A-Z_]+:|$)', text, re.DOTALL)
            return m.group(1).strip() if m else ""

        return {
            "research_question": extract("RESEARCH_QUESTION"),
            "methodology": extract("METHODOLOGY"),
            "key_findings": [f.strip().capitalize() for f in extract("KEY_FINDINGS").split("|") if f.strip()],
            "limitations": [l.strip().capitalize() for l in extract("LIMITATIONS").split("|") if l.strip()],
            "best_used_for": extract("BEST_USED_FOR"),
            "relevance": extract("RELEVANCE"),
            "analysis_based_on": extract("ANALYSIS_BASED_ON") or "Abstract only"
        }

    except Exception as e:
        print(f"Deep analysis error: {e}")
        return None