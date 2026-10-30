"""Поиск статей через OpenAlex API и подготовка их к оценке."""
import re

import requests

import config

OPENALEX_URL = "https://api.openalex.org/works"

# Берём из OpenAlex только нужные поля, чтобы ответ был меньше и быстрее
FIELDS = ",".join([
    "id",
    "display_name",
    "publication_year",
    "doi",
    "abstract_inverted_index",
    "open_access",
    "topics",
])


def clean_query(query):
    """OpenAlex отвечает ошибкой 400 на некоторые знаки (например, «?»).
    Оставляем только буквы, цифры, пробелы, дефис и апостроф."""
    query = re.sub(r"[^\w\s\-']", " ", query)
    return " ".join(query.split())


def rebuild_abstract(inverted_index):
    """OpenAlex хранит аннотацию как {слово: [позиции]}. Собираем обратно в текст."""
    if not inverted_index:
        return ""
    positions = []
    for word, places in inverted_index.items():
        for place in places:
            positions.append((place, word))
    positions.sort()
    return " ".join(word for _, word in positions)


def simplify_work(work):
    """Превращаем статью OpenAlex в словарь с нужными нам полями."""
    doi = work.get("doi") or ""
    openalex_id = work.get("id") or ""
    open_access = work.get("open_access") or {}
    topics = [t.get("display_name") for t in (work.get("topics") or []) if t.get("display_name")]
    return {
        "id": openalex_id.rsplit("/", 1)[-1],  # короткий id, например W2741809807
        "title": work.get("display_name") or "(без названия)",
        "year": work.get("publication_year"),
        "abstract": rebuild_abstract(work.get("abstract_inverted_index")),
        "is_free": bool(open_access.get("is_oa")),
        "topics": topics,
        # Ссылка: сначала DOI (страница статьи у издателя), иначе страница в OpenAlex
        "link": doi if doi else openalex_id,
        "has_doi": bool(doi),
    }


def _title_key(title):
    return clean_query(title).lower()


def _quality(article):
    """Какую из копий одной статьи оставить: с аннотацией и DOI лучше."""
    return (bool(article["abstract"]), article["has_doi"], len(article["abstract"]))


def remove_duplicates(articles):
    """OpenAlex иногда хранит одну статью в нескольких записях (журнал, архив, препринт).
    Оставляем одну — лучшую по качеству — на месте первой копии.
    Возвращает (статьи без дублей, сколько дублей убрано)."""
    best, order = {}, []
    for article in articles:
        key = _title_key(article["title"])
        if key not in best:
            best[key] = article
            order.append(key)
        elif _quality(article) > _quality(best[key]):
            best[key] = article
    return [best[k] for k in order], len(articles) - len(order)


def select_for_scoring(articles, limit):
    """Идём по выдаче OpenAlex по порядку и набираем `limit` статей с аннотацией.
    Статьи без аннотации, встреченные по пути, не теряются: их покажем отдельно.
    Возвращает (статьи для ИИ, статьи без аннотации)."""
    with_abstract, without_abstract = [], []
    for article in articles:
        if len(with_abstract) >= limit:
            break
        (with_abstract if article["abstract"] else without_abstract).append(article)
    return with_abstract, without_abstract


def collect(query, free_only, start, limit, seen, first_page=None):
    """Идёт по выдаче OpenAlex с позиции `start` и набирает `limit` новых статей с аннотацией.

    - `seen` — названия уже показанных статей (ключи); копии пропускаются, набор пополняется.
    - Если копия статьи попалась сначала без аннотации, а потом с аннотацией — берём вторую.
    - `first_page` — уже загруженная первая страница (works, total), чтобы не запрашивать её дважды.

    Возвращает словарь: to_score, without_abstract, duplicates, position (до куда дошли), total.
    """
    page_size = config.OPENALEX_FETCH
    to_score, without_abstract = [], []
    no_abstract_by_key = {}
    duplicates, position, total = 0, start, 0
    pages_loaded = 0

    while len(to_score) < limit and pages_loaded < config.MAX_PAGES_PER_ROUND:
        page = position // page_size + 1
        if first_page and page == 1 and pages_loaded == 0:
            works, total = first_page
        else:
            works, total = search(query, free_only=free_only, limit=page_size, page=page)
        pages_loaded += 1
        chunk = works[position % page_size:]
        if not chunk:
            break
        for work in chunk:
            position += 1
            key = _title_key(work["title"])
            if key in seen:
                duplicates += 1
                # Ранее была копия без аннотации, а эта — с аннотацией: заменяем
                earlier = no_abstract_by_key.pop(key, None)
                if earlier is not None and work["abstract"]:
                    without_abstract.remove(earlier)
                    to_score.append(work)
                    if len(to_score) >= limit:
                        break
                continue
            seen.add(key)
            if work["abstract"]:
                to_score.append(work)
                if len(to_score) >= limit:
                    break
            else:
                without_abstract.append(work)
                no_abstract_by_key[key] = work
        if len(works) < page_size:  # это была последняя страница выдачи
            break

    return {"to_score": to_score, "without_abstract": without_abstract,
            "duplicates": duplicates, "position": position, "total": total}


def title_key(title):
    return _title_key(title)


def search(query, free_only=True, limit=None, page=1):
    """Ищет статьи в OpenAlex. Возвращает (список статей, сколько всего найдено в OpenAlex)."""
    params = {
        "search": clean_query(query),
        "per_page": limit or config.OPENALEX_FETCH,
        "page": page,
        "select": FIELDS,
    }
    if free_only:
        params["filter"] = "open_access.is_oa:true"
    if config.OPENALEX_EMAIL:
        params["mailto"] = config.OPENALEX_EMAIL
    if config.OPENALEX_API_KEY:
        params["api_key"] = config.OPENALEX_API_KEY

    response = requests.get(OPENALEX_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    works = [simplify_work(w) for w in data.get("results", [])]
    total = (data.get("meta") or {}).get("count", len(works))
    return works, total


def find_by_title(title):
    """Ищет одну статью по точному названию (нужно для теста моделей). Возвращает статью или None."""
    works, _ = search(title, free_only=False, limit=1)
    return works[0] if works else None
