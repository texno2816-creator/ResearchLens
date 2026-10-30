"""Проверка стабильности моделей: одинаковые ли категории ставит модель,
если оценивать одни и те же статьи несколько раз подряд.

Берёт ровно те 20 статей на каждый из 3 тестовых запросов, которые ты оценивал вручную
(последний сохранённый поиск по запросу в researchlens.db, только бесплатные статьи).
Нумерация статей — по алфавиту, как в таблице «Ручная_оценка_60_статей.xlsx».

Что считается:
- Стабильность = статьи, у которых категория одинаковая во ВСЕХ прогонах, / 20.
- Опасные смены = статьи, которые хотя бы раз были No и хотя бы раз Yes/Unclear
  (пользователь то видит статью, то нет).
- Безопасные смены = только Yes <-> Unclear (статья видна в любом случае).

Запуск из папки проекта:
    python tools/stability.py
    python tools/stability.py --runs 5 --models groq:openai/gpt-oss-20b
Результаты: tools/stability_results.csv (каждый прогон) и итог в терминале.
"""
import argparse
import csv
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from services import llm_client, scorer  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_FILE = os.path.join(HERE, "stability_results.csv")

QUERIES = [
    "Training a neural network on board games",
    "The use of nanotechnology in medicine",
    "To what extent does the use of AI affect the quality of education for children under the age of 13?",
]
DEFAULT_MODELS = [
    "groq:openai/gpt-oss-120b",
    "groq:openai/gpt-oss-20b",
    "groq:qwen/qwen3.8-27b",
]


def load_articles(query):
    """Последний поиск по запросу (только бесплатные) — те самые 20 статей."""
    conn = sqlite3.connect(config.DB_PATH)
    # rstrip убирает случайную кавычку в конце запроса (в одном прогоне она была)
    rows = conn.execute(
        "SELECT query, results_json FROM searches WHERE free_only = 1 ORDER BY id DESC"
    ).fetchall()
    conn.close()
    for saved_query, results_json in rows:
        if saved_query.strip().rstrip('"”').strip() == query:
            articles = json.loads(results_json)
            keep = ("id", "title", "year", "abstract", "is_free", "topics", "link")
            articles = [{k: a.get(k) for k in keep} for a in articles]
            return sorted(articles, key=lambda a: a["title"].lower())
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5, help="сколько раз оценить каждую статью")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="список вида провайдер:модель")
    args = parser.parse_args()

    data = {}
    for q in QUERIES:
        articles = load_articles(q)
        if not articles:
            print(f"Не найден сохранённый поиск для запроса: {q}\nСначала выполни его на сайте.")
            return
        data[q] = articles

    # categories[(model, query)][номер статьи] = [категория в прогоне 1, 2, ...]
    categories = {}
    total = args.runs * len(QUERIES) * len(args.models)
    done = 0
    started_all = time.time()

    with open(RESULTS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["model", "query", "run", "n", "title", "category", "score"])

        # Модели чередуются: у каждой свой лимит Groq, поэтому так быстрее
        for run in range(1, args.runs + 1):
            for q_index, q in enumerate(QUERIES, start=1):
                for spec in args.models:
                    provider, model = spec.split(":", 1)
                    done += 1
                    print(f"[{done}/{total}] прогон {run}, запрос {q_index}, {model} ...", end=" ", flush=True)
                    try:
                        scored, stats = scorer.score_articles(q, data[q], provider=provider, model=model)
                    except llm_client.LLMError as e:
                        print(f"ОШИБКА: {e}")
                        continue
                    by_id = {a["id"]: a for a in scored}
                    cell = categories.setdefault((spec, q), {})
                    for n, article in enumerate(data[q], start=1):
                        result = by_id[article["id"]]
                        cell.setdefault(n, []).append(result["category"])
                        writer.writerow([spec, q_index, run, n, article["title"], result["category"], result["score"]])
                    f.flush()
                    print(f"{stats['seconds']} с, ошибок ИИ: {stats['errors']}")

    print(f"\nГотово за {(time.time() - started_all) / 60:.1f} мин. Все прогоны: {RESULTS_FILE}\n")

    print("ИТОГ: стабильность (статьи с одинаковой категорией во всех прогонах)")
    for spec in args.models:
        stable_sum, total_sum, danger_sum = 0, 0, 0
        print(f"\n{spec}")
        for q_index, q in enumerate(QUERIES, start=1):
            cell = categories.get((spec, q), {})
            if not cell:
                print(f"  Запрос {q_index}: нет данных")
                continue
            runs_done = min(len(v) for v in cell.values())
            stable, danger, jumping = 0, 0, []
            for n, cats in sorted(cell.items()):
                kinds = set(cats)
                if len(kinds) == 1:
                    stable += 1
                    continue
                is_danger = "No" in kinds
                danger += is_danger
                jumping.append(f"    №{n} {'ОПАСНО ' if is_danger else ''}{' → '.join(cats)} | {data[q][n - 1]['title'][:60]}")
            stable_sum += stable
            total_sum += len(cell)
            danger_sum += danger
            print(f"  Запрос {q_index}: стабильно {stable}/{len(cell)} ({stable / len(cell):.0%}), "
                  f"опасных смен: {danger}, прогонов: {runs_done}")
            for line in jumping:
                print(line)
        if total_sum:
            print(f"  ВСЕГО: стабильно {stable_sum}/{total_sum} ({stable_sum / total_sum:.0%}), опасных смен: {danger_sum}")


if __name__ == "__main__":
    main()
