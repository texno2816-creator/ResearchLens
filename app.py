"""ResearchLens — версия 2.

Запуск: python app.py  → открыть http://127.0.0.1:5000
"""
from collections import Counter
from functools import wraps

import requests
from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)

import config
import storage
from services import llm_client, openalex, scorer, spelling

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
storage.init_db()

WORK_TYPE_LABELS = {
    "review": "Обзор",
    "study": "Исследование",
    "theory": "Метод или теория",
    "other": "Другое",
}
CATEGORY_LABELS = {"Yes": "Подходит", "Unclear": "Частично", "No": "Не подходит"}


def is_test_mode():
    return bool(session.get("test_mode"))


def test_mode_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not is_test_mode():
            return redirect(url_for("test_login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_globals():
    return {
        "test_mode": is_test_mode(),
        "config": config,
        "work_type_labels": WORK_TYPE_LABELS,
        "category_labels": CATEGORY_LABELS,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    query = storage.normalize_query(request.args.get("q") or "")
    if not query:
        return redirect(url_for("index"))
    free_only = request.args.get("paid") != "1"
    # В тестовом режиме можно заставить оценить заново, без кэша
    fresh = is_test_mode() and request.args.get("fresh") == "1"
    # exact=1 — «Искать именно так»: не исправлять опечатки
    exact = request.args.get("exact") == "1"

    if not fresh:
        cached = storage.find_cached(query, free_only)
        # Поиск «именно так» с малым числом статей не мешает обычному поиску исправить опечатку
        skip = (cached and not exact and cached["stats"].get("exact")
                and (cached["openalex_total"] or 0) < config.SPELLCHECK_BELOW)
        if cached and not skip:
            return redirect(url_for("results", search_id=cached["id"]))

    original_query = None
    try:
        works, total = openalex.search(query, free_only=free_only)

        # Мало результатов — возможно, опечатка. Пробуем исправленный запрос, как Google.
        if not exact and total < config.SPELLCHECK_BELOW:
            corrected = spelling.correct_query(query)
            if corrected:
                corrected = storage.normalize_query(corrected)
                cached = None if fresh else storage.find_cached(corrected, free_only)
                if cached:
                    return redirect(url_for("results", search_id=cached["id"], original=query))
                works2, total2 = openalex.search(corrected, free_only=free_only)
                if total2 > total:
                    original_query, query, works, total = query, corrected, works2, total2

        batch = openalex.collect(query, free_only, start=0, limit=config.ARTICLES_TO_SCORE,
                                 seen=set(), first_page=(works, total))
        results, stats = scorer.score_articles(query, batch["to_score"] + batch["without_abstract"])
    except llm_client.LLMError as e:
        return render_template("error.html", query=query,
                               title="ИИ не смог оценить статьи",
                               message=str(e)), 502
    except requests.RequestException as e:
        return render_template("error.html", query=query,
                               title="База статей OpenAlex не ответила",
                               message=f"Попробуй ещё раз через минуту. Техническая причина: {e}"), 502

    stats["duplicates"] = batch["duplicates"]
    stats["position"] = batch["position"]
    stats["rounds"] = 1
    stats["exact"] = exact
    if original_query:
        stats["original_query"] = original_query
    search_id = storage.save_search(query, free_only, total, results, stats)
    if original_query:
        return redirect(url_for("results", search_id=search_id, original=original_query))
    return redirect(url_for("results", search_id=search_id))


def can_check_more(data):
    """Можно ли нажать «Проверить ещё 20»: есть ли ещё статьи в выдаче и не достигнут ли предел."""
    stats = data["stats"]
    position = stats.get("position")
    if position is None:  # поиски версии 1 не помнят позицию
        return False
    if position >= (data["openalex_total"] or 0):
        return False
    return stats.get("total", 0) < config.MAX_ARTICLES_PER_QUERY


@app.route("/results/<int:search_id>/more", methods=["POST"])
def check_more(search_id):
    data = storage.get_search(search_id)
    if not data:
        abort(404)
    original = request.form.get("original") or None
    back = url_for("results", search_id=search_id, original=original, _anchor="more")
    if not can_check_more(data):
        flash("Больше статей по этому запросу проверить нельзя.")
        return redirect(back)

    stats = data["stats"]
    old_results = data["results"]
    seen = {openalex.title_key(a["title"]) for a in old_results}
    left = config.MAX_ARTICLES_PER_QUERY - stats.get("total", 0)
    try:
        batch = openalex.collect(data["query"], bool(data["free_only"]), start=stats["position"],
                                 limit=min(config.ARTICLES_TO_SCORE, left), seen=seen)
        if not batch["to_score"] and not batch["without_abstract"]:
            stats["position"] = data["openalex_total"] or stats["position"]  # выдача закончилась
            storage.update_search(search_id, old_results, stats)
            flash("В выдаче OpenAlex больше нет новых статей по этому запросу.")
            return redirect(back)
        new_results, new_stats = scorer.score_articles(data["query"], batch["to_score"] + batch["without_abstract"])
    except llm_client.LLMError as e:
        return render_template("error.html", query=data["query"],
                               title="ИИ не смог оценить следующие статьи", message=str(e)), 502
    except requests.RequestException as e:
        return render_template("error.html", query=data["query"],
                               title="База статей OpenAlex не ответила",
                               message=f"Попробуй ещё раз через минуту. Техническая причина: {e}"), 502

    # Складываем счётчики старых и новых статей
    for key in ("seconds", "tokens", "total", "yes", "unclear", "no", "no_abstract", "errors"):
        stats[key] = round(stats.get(key, 0) + new_stats[key], 1)
    stats["duplicates"] = stats.get("duplicates", 0) + batch["duplicates"]
    stats["position"] = batch["position"]
    stats["rounds"] = stats.get("rounds", 1) + 1

    merged = sorted(old_results + new_results, key=lambda a: a["score"], reverse=True)
    storage.update_search(search_id, merged, stats)
    found = new_stats["yes"] + new_stats["unclear"]
    flash(f"Проверено ещё {new_stats['total']} статей, подходящих среди них: {found}.")
    return redirect(back)


@app.route("/results/<int:search_id>")
def results(search_id):
    data = storage.get_search(search_id)
    if not data:
        abort(404)

    all_articles = data["results"]
    without_abstract = [a for a in all_articles if a.get("no_abstract")]
    scored = [a for a in all_articles if not a.get("no_abstract")]
    visible = [a for a in scored if a["category"] in ("Yes", "Unclear")]
    # Пользователь видит только Yes и Unclear; в тестовом режиме видно всё
    shown = scored if is_test_mode() else visible

    years = Counter(a["year"] for a in visible if a.get("year"))
    year_rows = sorted(years.items(), reverse=True)
    topics = Counter(t for a in visible for t in a.get("topics", []))
    types = Counter(a.get("type", "other") for a in visible)

    return render_template(
        "results.html",
        search=data,
        articles=shown,
        dots=scored,
        shown_ids={a["id"] for a in shown},
        visible_count=len(visible),
        without_abstract=without_abstract,
        year_rows=year_rows,
        year_max=max(years.values()) if years else 1,
        topics=topics.most_common(),
        types=[(t, types[t]) for t in WORK_TYPE_LABELS if types[t]],
        free_only=bool(data["free_only"]),
        original_query=storage.normalize_query(request.args.get("original") or "") or None,
        can_more=can_check_more(data),
        max_articles=config.MAX_ARTICLES_PER_QUERY,
    )


@app.route("/support", methods=["POST"])
def support():
    message = (request.form.get("message") or "").strip()
    query = request.form.get("query", "")
    if message:
        storage.save_support_message(query, message, (request.form.get("contact") or "").strip())
        flash("Сообщение отправлено. Спасибо, что помогаешь улучшить поиск.")
    back = request.form.get("back") or ""
    # Возвращаем только на страницы этого сайта
    return redirect(back if back.startswith("/") else url_for("index"))


@app.route("/projects")
def projects():
    return render_template("projects.html")


@app.route("/folders")
def folders_redirect():
    return redirect(url_for("projects"))


@app.route("/about")
def about():
    return render_template("about.html")


# ---------- Тестовый режим ----------

@app.route("/test-login", methods=["GET", "POST"])
def test_login():
    if request.method == "POST":
        if request.form.get("password") == config.ADMIN_PASSWORD:
            session["test_mode"] = True
            target = request.args.get("next") or ""
            return redirect(target if target.startswith("/") else url_for("admin"))
        flash("Неверный пароль")
    return render_template("test_login.html")


@app.route("/test-logout")
def test_logout():
    session.pop("test_mode", None)
    return redirect(url_for("index"))


@app.route("/admin")
@test_mode_required
def admin():
    return render_template(
        "admin.html",
        empty_searches=storage.list_searches(only_empty=True),
        all_searches=storage.list_searches(),
        messages=storage.list_support_messages(),
    )


@app.route("/admin/clear", methods=["POST"])
@test_mode_required
def admin_clear():
    storage.clear_history()
    flash("История поисков очищена. Следующие запросы будут оценены заново.")
    return redirect(url_for("admin"))


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", title="Такой страницы нет",
                           message="Проверь адрес или начни новый поиск."), 404


if __name__ == "__main__":
    app.run(debug=config.DEBUG)
