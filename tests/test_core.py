import json
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from services import llm_client, openalex, scorer


def test_rebuild_abstract():
    assert openalex.rebuild_abstract({"world": [1], "Hello": [0], "again": [2]}) == "Hello world again"
    assert openalex.rebuild_abstract(None) == ""


def test_clean_query_removes_bad_symbols():
    q = "Can Board Games Prevent Impairment? A Review: “effects” (2020)"
    assert openalex.clean_query(q) == "Can Board Games Prevent Impairment A Review effects 2020"
    assert openalex.clean_query("обучение нейросети?") == "обучение нейросети"


def test_simplify_work_prefers_doi():
    work = {"id": "https://openalex.org/W1", "display_name": "T", "publication_year": 2020,
            "doi": "https://doi.org/10.1/x", "open_access": {"is_oa": True},
            "topics": [{"display_name": "Games"}], "abstract_inverted_index": {"a": [0]}}
    a = openalex.simplify_work(work)
    assert a["link"] == "https://doi.org/10.1/x"
    assert a["id"] == "W1" and a["is_free"] and a["topics"] == ["Games"]
    work["doi"] = None
    assert openalex.simplify_work(work)["link"] == "https://openalex.org/W1"


def art(id_, title, abstract="text", doi=True):
    return {"id": id_, "title": title, "year": 2020, "abstract": abstract, "is_free": True,
            "topics": [], "link": "l" + id_, "has_doi": doi}


def test_remove_duplicates_keeps_best_copy_in_first_place():
    items = [art("1", "Paper A"), art("2", "Targeting miRNA medicines", "", False),
             art("3", "Targeting miRNA medicines?", "good abstract", True), art("4", "Paper B")]
    out, removed = openalex.remove_duplicates(items)
    assert removed == 1
    assert [a["id"] for a in out] == ["1", "3", "4"]


def test_select_for_scoring_replaces_articles_without_abstract():
    items = [art("1", "a"), art("2", "b", ""), art("3", "c"), art("4", "d", ""), art("5", "e")]
    scored, without = openalex.select_for_scoring(items, 3)
    assert [a["id"] for a in scored] == ["1", "3", "5"]
    assert [a["id"] for a in without] == ["2", "4"]


def test_category_thresholds():
    assert scorer.category_for(7.5) == "Yes"
    assert scorer.category_for(7.4) == "Unclear"
    assert scorer.category_for(4.0) == "Unclear"
    assert scorer.category_for(3.9) == "No"


def test_parse_response_strips_think_clamps_and_reads_type():
    text = ('<think>hmm [not json]</think> Here: [{"id": "A1", "type": "study", "reason": "r", "score": 12},'
            ' {"id": "A2", "type": "weird", "reason": "r", "score": 5}]')
    parsed = scorer.parse_response(text)
    assert parsed["A1"] == {"reason": "r", "score": 10.0, "type": "study"}
    assert parsed["A2"]["type"] == "other"


def fake_chat_factory(scores, calls):
    def fake_chat(messages, provider=None, model=None):
        calls.append(1)
        user = messages[1]["content"]
        items = []
        for block in user.split("[id: ")[1:]:
            batch_id = block.split("]")[0]
            title = block.split("Title: ")[1].split("\n")[0]
            if title in scores:
                items.append({"id": batch_id, "type": "review", "reason": f"about {title}", "score": scores[title]})
        return json.dumps(items), 100
    return fake_chat


def make_articles():
    return [
        {"id": "W1", "title": "Good", "year": 2023, "abstract": "a", "is_free": True, "topics": ["Games"], "link": "l1", "has_doi": True},
        {"id": "W2", "title": "Medium", "year": 2019, "abstract": "a", "is_free": True, "topics": ["AI"], "link": "l2", "has_doi": True},
        {"id": "W3", "title": "Medicine", "year": 2021, "abstract": "a", "is_free": True, "topics": [], "link": "l3", "has_doi": True},
        {"id": "W4", "title": "NoAbstract", "year": 2020, "abstract": "", "is_free": True, "topics": [], "link": "l4", "has_doi": False},
        {"id": "W5", "title": "Missing", "year": 2022, "abstract": "a", "is_free": True, "topics": [], "link": "l5", "has_doi": True},
        {"id": "W6", "title": "Good", "year": 2023, "abstract": "", "is_free": True, "topics": [], "link": "l6", "has_doi": False},
    ]


def test_score_articles(monkeypatch):
    calls = []
    monkeypatch.setattr(llm_client, "chat", fake_chat_factory({"Good": 9, "Medium": 5, "Medicine": 1.5}, calls))
    monkeypatch.setattr(config, "BATCH_SIZE", 2)
    articles = make_articles()[:5]
    results, stats = scorer.score_articles("q", articles)

    by_title = {a["title"]: a for a in results}
    assert by_title["Good"]["category"] == "Yes" and by_title["Good"]["type"] == "review"
    assert by_title["Medium"]["category"] == "Unclear"
    assert by_title["Medicine"]["category"] == "No"
    assert by_title["NoAbstract"]["no_abstract"]
    assert by_title["Missing"]["error"]
    assert results[0]["title"] == "Good"
    assert stats["total"] == 4 and stats["no_abstract"] == 1
    assert len(calls) == 3


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "ADMIN_PASSWORD", "secret")
    import app as app_module
    import storage
    storage.init_db()
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def patch_search(monkeypatch, scores, calls):
    monkeypatch.setattr(openalex, "search", lambda q, free_only=True, limit=None, page=1: (make_articles(), 1234))
    monkeypatch.setattr(llm_client, "chat", fake_chat_factory(scores, calls))


def test_user_sees_only_relevant_and_no_abstract_block(client, monkeypatch):
    calls = []
    patch_search(monkeypatch, {"Good": 9, "Medium": 5, "Medicine": 1, "Missing": 2}, calls)
    r = client.get("/search?q=board+games", follow_redirects=True)
    html = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Good" in html and "Medium" in html
    assert "Medicine" not in html
    assert "Статьи без аннотации: 1" in html and "NoAbstract" in html
    assert html.count('class="paper ') == 2

    n = len(calls)
    client.get('/search?q="Board+Games"', follow_redirects=True)
    assert len(calls) == n


def test_test_mode_sees_everything(client, monkeypatch):
    patch_search(monkeypatch, {"Good": 9, "Medium": 5, "Medicine": 1, "Missing": 2}, [])
    client.post("/test-login", data={"password": "secret"})
    html = client.get("/search?q=x", follow_redirects=True).get_data(as_text=True)
    assert "Medicine" in html and "Тестовый режим" in html and "Убрано дубликатов" in html


def test_empty_result_support_admin_and_clear(client, monkeypatch):
    patch_search(monkeypatch, {"Good": 2, "Medium": 1, "Medicine": 1, "Missing": 1}, [])
    html = client.get("/search?q=very+narrow", follow_redirects=True).get_data(as_text=True)
    assert "Подходящих статей среди первых" in html

    client.post("/support", data={"query": "very narrow", "message": "help", "contact": "", "back": "https://evil.example"})
    assert client.get("/admin").status_code == 302
    client.post("/test-login", data={"password": "secret"})
    admin = client.get("/admin").get_data(as_text=True)
    assert "very narrow" in admin and "help" in admin

    client.post("/admin/clear")
    admin = client.get("/admin").get_data(as_text=True)
    assert "Пока пусто" in admin and "help" in admin


def test_nothing_found_in_openalex(client, monkeypatch):
    monkeypatch.setattr(openalex, "search", lambda q, free_only=True, limit=None, page=1: ([], 0))
    html = client.get("/search?q=brian+nerral", follow_redirects=True).get_data(as_text=True)
    assert "OpenAlex не нашёл ни одной статьи" in html and "среди первых 0" not in html


def test_typo_is_corrected_like_google(client, monkeypatch):
    calls = []
    found = {"brain's neural signals": (make_articles(), 5000)}
    monkeypatch.setattr(openalex, "search",
                        lambda q, free_only=True, limit=None, page=1: found.get(q.lower(), ([], 0)))
    monkeypatch.setattr(llm_client, "chat", fake_chat_factory({"Good": 9, "Medium": 5}, calls))
    from services import spelling
    monkeypatch.setattr(spelling, "correct_query", lambda q: "brain's neural signals")

    html = client.get("/search?q=Brian's+nerral+signals", follow_redirects=True).get_data(as_text=True)
    assert "Показаны результаты по запросу" in html and "Good" in html

    html = client.get("/search?q=Brian's+nerral+signals&exact=1", follow_redirects=True).get_data(as_text=True)
    assert "OpenAlex не нашёл ни одной статьи" in html and "Показаны результаты" not in html

    html = client.get("/search?q=Brian's+nerral+signals", follow_redirects=True).get_data(as_text=True)
    assert "Показаны результаты по запросу" in html


def test_spelling_ignores_rewrites(monkeypatch):
    from services import spelling
    monkeypatch.setattr(llm_client, "chat", lambda m, provider=None, model=None: ('{"corrected": "brain\'s neural signals"}', 10))
    assert spelling.correct_query("Brian's nerral signals") == "brain's neural signals"
    monkeypatch.setattr(llm_client, "chat", lambda m, provider=None, model=None: ('{"corrected": "board games"}', 10))
    assert spelling.correct_query("Board games") is None
    monkeypatch.setattr(llm_client, "chat", lambda m, provider=None, model=None: ('{"corrected": "a completely different long query here"}', 10))
    assert spelling.correct_query("board games") is None


def test_collect_walks_pages_and_skips_seen(monkeypatch):
    monkeypatch.setattr(config, "OPENALEX_FETCH", 4)
    pool = [art(str(i), f"Paper {i}", "" if i in (2, 6) else "abs") for i in range(1, 15)]
    pool[4]["title"] = "Paper 1"

    def fake(q, free_only=True, limit=None, page=1):
        return pool[(page - 1) * 4: page * 4], len(pool)
    monkeypatch.setattr(openalex, "search", fake)

    seen = set()
    first = openalex.collect("q", True, start=0, limit=3, seen=seen)
    assert [a["id"] for a in first["to_score"]] == ["1", "3", "4"]
    assert [a["id"] for a in first["without_abstract"]] == ["2"]
    assert first["position"] == 4

    second = openalex.collect("q", True, start=first["position"], limit=3, seen=seen)
    assert [a["id"] for a in second["to_score"]] == ["7", "8", "9"]
    assert [a["id"] for a in second["without_abstract"]] == ["6"]
    assert second["duplicates"] == 1
    ids = {a["id"] for a in first["to_score"] + second["to_score"]}
    assert len(ids) == 6


def test_check_more_adds_next_articles(client, monkeypatch):
    monkeypatch.setattr(config, "ARTICLES_TO_SCORE", 2)
    monkeypatch.setattr(config, "OPENALEX_FETCH", 3)
    pool = [art(str(i), f"Paper {i}") for i in range(1, 8)]

    def fake(q, free_only=True, limit=None, page=1):
        return pool[(page - 1) * 3: page * 3], len(pool)
    monkeypatch.setattr(openalex, "search", fake)
    monkeypatch.setattr(llm_client, "chat", fake_chat_factory({f"Paper {i}": 9 for i in range(1, 8)}, []))

    r = client.get("/search?q=papers")
    search_id = int(r.headers["Location"].split("/results/")[1].split("?")[0])
    html = client.get(f"/results/{search_id}").get_data(as_text=True)
    assert html.count('class="paper ') == 2 and "Проверить ещё 2 статей" in html

    client.post(f"/results/{search_id}/more")
    html = client.get(f"/results/{search_id}").get_data(as_text=True)
    assert html.count('class="paper ') == 4 and "Paper 3" in html and "Paper 4" in html

    html = client.get("/search?q=papers", follow_redirects=True).get_data(as_text=True)
    assert html.count('class="paper ') == 4

    client.post(f"/results/{search_id}/more")
    client.post(f"/results/{search_id}/more")
    html = client.get(f"/results/{search_id}").get_data(as_text=True)
    assert html.count('class="paper ') == 7 and "проверил все статьи" in html


def test_check_more_respects_limit(client, monkeypatch):
    monkeypatch.setattr(config, "ARTICLES_TO_SCORE", 2)
    monkeypatch.setattr(config, "MAX_ARTICLES_PER_QUERY", 3)
    pool = [art(str(i), f"Paper {i}") for i in range(1, 10)]
    monkeypatch.setattr(openalex, "search", lambda q, free_only=True, limit=None, page=1: (pool[(page - 1) * 50: page * 50], len(pool)))
    monkeypatch.setattr(llm_client, "chat", fake_chat_factory({f"Paper {i}": 9 for i in range(1, 10)}, []))
    r = client.get("/search?q=limit")
    search_id = int(r.headers["Location"].split("/results/")[1].split("?")[0])
    assert "Проверить ещё 1 статей" in client.get(f"/results/{search_id}").get_data(as_text=True)
    client.post(f"/results/{search_id}/more")
    html = client.get(f"/results/{search_id}").get_data(as_text=True)
    assert html.count('class="paper ') == 3 and "это предел для одного запроса" in html


def test_other_pages(client):
    for path in ["/", "/projects", "/about", "/test-login"]:
        assert client.get(path).status_code == 200
    assert client.get("/folders").status_code == 302
    assert client.get("/nope").status_code == 404
    assert client.post("/test-login", data={"password": "wrong"}).status_code == 200


def test_errors_are_shown_clearly(client, monkeypatch):
    monkeypatch.setattr(openalex, "search", lambda q, free_only=True, limit=None, page=1: (make_articles(), 5))

    def broken(messages, provider=None, model=None):
        raise llm_client.LLMError("Не указан ключ")
    monkeypatch.setattr(llm_client, "chat", broken)
    r = client.get("/search?q=y")
    assert r.status_code == 502 and "Не указан ключ" in r.get_data(as_text=True)


def test_old_database_is_upgraded(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE searches (id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT NOT NULL, query TEXT NOT NULL,"
                 " free_only INTEGER NOT NULL, provider TEXT, model TEXT, openalex_total INTEGER, is_empty INTEGER NOT NULL,"
                 " stats_json TEXT NOT NULL, results_json TEXT NOT NULL)")
    conn.execute("INSERT INTO searches (created, query, free_only, model, is_empty, stats_json, results_json)"
                 " VALUES ('d', 'q', 1, 'openai/gpt-oss-20b', 0, '{}', '[]')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(config, "DB_PATH", str(path))
    import storage
    storage.init_db()
    assert storage.find_cached("q", True) is None
    assert storage.list_searches()[0]["version"] == "1"


def test_long_abstract_is_shortened():
    from prompts import shorten
    text = "word " * 2000
    short = shorten(text)
    assert len(short) <= config.MAX_ABSTRACT_CHARS + 2 and short.endswith("…")
    assert shorten("short abstract") == "short abstract"


def test_batches_fit_token_limit():
    from services.scorer import make_batches, estimate_tokens
    from prompts import SYSTEM_PROMPT, build_user_message
    huge = [{"id": str(i), "title": f"Paper {i}", "abstract": "long text " * 400} for i in range(10)]
    batches = make_batches("query", huge)
    budget = config.REQUEST_TOKEN_LIMIT - config.MAX_OUTPUT_TOKENS
    for batch in batches:
        assert len(batch) <= config.BATCH_SIZE
        assert estimate_tokens(SYSTEM_PROMPT) + estimate_tokens(build_user_message("query", batch)) < budget
    assert sum(len(b) for b in batches) == 10


def test_too_large_request_is_split(monkeypatch):
    from services import llm_client, scorer
    calls = []

    def fake_chat(messages, provider=None, model=None):
        ids = [part.split("]")[0] for part in messages[1]["content"].split("[id: ")[1:]]
        calls.append(len(ids))
        if len(ids) > 2:
            raise llm_client.RequestTooLarge("413")
        return json.dumps([{"id": i, "type": "study", "reason": "ok", "score": 8} for i in ids]), 100

    monkeypatch.setattr(llm_client, "chat", fake_chat)
    articles = [{"id": str(i), "title": f"P{i}", "abstract": "text"} for i in range(5)]
    results, stats = scorer.score_articles("q", articles)
    assert stats["errors"] == 0 and stats["yes"] == 5
    assert calls == [5, 2, 3, 1, 2]
