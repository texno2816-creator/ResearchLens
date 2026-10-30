"""Хранение данных в SQLite: история поисков (с оценками) и сообщения в поддержку."""
import json
import sqlite3
from datetime import datetime

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TEXT NOT NULL,
    query TEXT NOT NULL,
    free_only INTEGER NOT NULL,
    provider TEXT,
    model TEXT,
    openalex_total INTEGER,
    is_empty INTEGER NOT NULL,      -- 1, если пользователю не показано ни одной оценённой статьи
    stats_json TEXT NOT NULL,
    results_json TEXT NOT NULL,     -- все статьи, включая No и статьи без аннотации
    version TEXT                    -- версия правил оценки (config.PROMPT_VERSION)
);
CREATE TABLE IF NOT EXISTS support_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TEXT NOT NULL,
    query TEXT,
    message TEXT NOT NULL,
    contact TEXT
);
"""


def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA)
        # База версии 1 не знала про колонку version — добавляем её, старые данные сохраняются
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(searches)")]
        if "version" not in columns:
            conn.execute("ALTER TABLE searches ADD COLUMN version TEXT DEFAULT '1'")


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_query(query):
    """Убираем лишние пробелы и случайные кавычки по краям, чтобы кэш не дробился."""
    return " ".join(query.strip().strip('"“”«»\'').split())


def save_search(query, free_only, openalex_total, results, stats):
    is_empty = stats["yes"] + stats["unclear"] == 0
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO searches (created, query, free_only, provider, model, openalex_total,"
            " is_empty, stats_json, results_json, version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (_now(), query, int(free_only), config.LLM_PROVIDER, config.LLM_MODEL,
             openalex_total, int(is_empty), json.dumps(stats),
             json.dumps(results, ensure_ascii=False), config.PROMPT_VERSION),
        )
        return cur.lastrowid


def update_search(search_id, results, stats):
    """Обновляет поиск после «Проверить ещё 20»."""
    is_empty = stats["yes"] + stats["unclear"] == 0
    with _connect() as conn:
        conn.execute(
            "UPDATE searches SET is_empty = ?, stats_json = ?, results_json = ? WHERE id = ?",
            (int(is_empty), json.dumps(stats), json.dumps(results, ensure_ascii=False), search_id),
        )


def _row_to_search(row):
    if row is None:
        return None
    data = dict(row)
    data["stats"] = json.loads(data.pop("stats_json"))
    data["results"] = json.loads(data.pop("results_json"))
    return data


def get_search(search_id):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM searches WHERE id = ?", (search_id,)).fetchone()
    return _row_to_search(row)


def find_cached(query, free_only):
    """Последний поиск с тем же запросом, галочкой доступа, моделью и версией правил."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM searches WHERE lower(query) = lower(?) AND free_only = ? AND model = ?"
            " AND version = ? ORDER BY id DESC LIMIT 1",
            (query, int(free_only), config.LLM_MODEL, config.PROMPT_VERSION),
        ).fetchone()
    return _row_to_search(row)


def list_searches(only_empty=False, limit=200):
    sql = "SELECT id, created, query, free_only, model, version, is_empty, stats_json FROM searches"
    if only_empty:
        sql += " WHERE is_empty = 1"
    sql += " ORDER BY id DESC LIMIT ?"
    with _connect() as conn:
        rows = conn.execute(sql, (limit,)).fetchall()
    out = []
    for row in rows:
        data = dict(row)
        data["stats"] = json.loads(data.pop("stats_json"))
        out.append(data)
    return out


def clear_history():
    """Удаляет все поиски (и кэш). Сообщения в поддержку не трогает."""
    with _connect() as conn:
        conn.execute("DELETE FROM searches")


def save_support_message(query, message, contact):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO support_messages (created, query, message, contact) VALUES (?, ?, ?, ?)",
            (_now(), query, message, contact),
        )


def list_support_messages(limit=200):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM support_messages ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
