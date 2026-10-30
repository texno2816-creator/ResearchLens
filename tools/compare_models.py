import argparse
import csv
import difflib
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import openalex, scorer

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL_FILE = os.path.join(HERE, "eval_google_scholar.csv")
ABSTRACTS_DIR = os.path.join(HERE, "eval_abstracts")
FETCHED_FILE = os.path.join(HERE, "eval_articles_fetched.csv")
RESULTS_FILE = os.path.join(HERE, "eval_results.csv")

QUERY = "Training a neural network on board games"
DEFAULT_MODELS = [
    "groq:openai/gpt-oss-120b",
    "groq:openai/gpt-oss-20b",
    "groq:qwen/qwen3.8-27b",
]
TITLE_SIMILARITY = 0.85


def similar(a, b):
    a = openalex.clean_query(a).lower()
    b = openalex.clean_query(b).lower()
    return difflib.SequenceMatcher(None, a, b).ratio()


def manual_abstract(number):
    path = os.path.join(ABSTRACTS_DIR, f"{number:02d}.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            return " ".join(f.read().split())
    return ""


def load_fetched():
    if not os.path.exists(FETCHED_FILE):
        return {}
    with open(FETCHED_FILE, encoding="utf-8") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def load_articles():
    fetched = load_fetched()
    articles, problems = [], []

    with open(EVAL_FILE, encoding="utf-8") as f:
        for n, row in enumerate(csv.DictReader(f), start=1):
            article = {"id": str(n), "title": row["title"], "my_label": row["my_label"],
                       "abstract": "", "found_title": "", "source": ""}

            manual = manual_abstract(n) or (row.get("abstract") or "").strip()
            if manual:
                article.update(abstract=manual, found_title=row["title"], source="вручную")
            elif str(n) in fetched:
                cached = fetched[str(n)]
                article.update(abstract=cached.get("abstract", ""),
                               found_title=cached.get("found_title", ""), source="OpenAlex")
            else:
                try:
                    found = openalex.find_by_title(row["title"])
                except Exception as e:
                    print(f"Не удалось найти статью {n}: {e}")
                    found = None
                if found:
                    article.update(abstract=found["abstract"], found_title=found["title"])
                article["source"] = "OpenAlex"
                time.sleep(0.2)

            if article["source"] == "OpenAlex":
                if not article["found_title"]:
                    problems.append(f"  {n:02d}: статья не найдена в OpenAlex")
                elif similar(article["title"], article["found_title"]) < TITLE_SIMILARITY:
                    problems.append(f"  {n:02d}: найдена ДРУГАЯ статья: «{article['found_title'][:70]}»")
                elif not article["abstract"]:
                    problems.append(f"  {n:02d}: в OpenAlex нет аннотации")
            articles.append(article)

    with open(FETCHED_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "found_title", "source", "my_label", "abstract"])
        writer.writeheader()
        writer.writerows(articles)

    if problems:
        print("ВНИМАНИЕ: эти статьи не совпадают с твоими. Вставь их аннотации из Google Scholar")
        print(f"в файлы <номер>.txt в папке {ABSTRACTS_DIR} (например 03.txt) и запусти снова:")
        print("\n".join(problems))
        print()
    return articles, len(problems)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="список вида провайдер:модель")
    parser.add_argument("--runs", type=int, default=1, help="сколько раз прогнать каждую модель")
    args = parser.parse_args()

    articles, problems = load_articles()
    manual = sum(1 for a in articles if a["source"] == "вручную")
    print(f"Статей: {len(articles)} (аннотаций вставлено вручную: {manual}, проблемных: {problems})\n")
    if problems:
        print("Тест нечестный, пока есть проблемные статьи. Результат ниже — только для справки.\n")

    detail_rows, summary = [], []
    for spec in args.models:
        provider, model = spec.split(":", 1)
        for run in range(1, args.runs + 1):
            started = time.time()
            scored, stats = scorer.score_articles(QUERY, articles, provider=provider, model=model)
            seconds = time.time() - started
            by_id = {a["id"]: a for a in scored}

            matches = 0
            for a in articles:
                result = by_id[a["id"]]
                match = result["category"] == a["my_label"]
                matches += match
                detail_rows.append({
                    "model": spec, "run": run, "id": a["id"], "title": a["title"],
                    "my_label": a["my_label"], "ai_category": result["category"],
                    "ai_score": result["score"], "match": "yes" if match else "NO",
                    "reason": result["reason"],
                })
            summary.append((spec, run, matches, len(articles), seconds, stats["tokens"]))
            print(f"{spec} (прогон {run}): совпало {matches}/{len(articles)}, "
                  f"{seconds:.1f} с, {stats['tokens']} токенов, ошибок ИИ: {stats['errors']}")

    with open(RESULTS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(detail_rows[0].keys()))
        writer.writeheader()
        writer.writerows(detail_rows)

    print("\nИтог (точность = совпадения с твоей таблицей):")
    for spec, run, matches, total, seconds, tokens in summary:
        print(f"  {spec:35} прогон {run}: {matches / total:.0%}  ({matches}/{total}), "
              f"{seconds:.1f} с, {tokens} токенов")
    print(f"\nПодробно по каждой статье: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
