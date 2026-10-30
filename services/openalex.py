import re

import requests

import config

OPENALEX_URL = "https://api.openalex.org/works"

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
    """OpenAlex returns 400 for some characters such as "?", so keep only letters, digits, spaces, hyphens and apostrophes."""
    query = re.sub(r"[^\w\s\-']", " ", query)
    return " ".join(query.split())


def rebuild_abstract(inverted_index):
    """OpenAlex stores abstracts as {word: [positions]}; rebuild the text."""
    if not inverted_index:
        return ""
    positions = []
    for word, places in inverted_index.items():
        for place in places:
            positions.append((place, word))
    positions.sort()
    return " ".join(word for _, word in positions)


def simplify_work(work):
    doi = work.get("doi") or ""
    openalex_id = work.get("id") or ""
    open_access = work.get("open_access") or {}
    topics = [t.get("display_name") for t in (work.get("topics") or []) if t.get("display_name")]
    return {
        "id": openalex_id.rsplit("/", 1)[-1],
        "title": work.get("display_name") or "(без названия)",
        "year": work.get("publication_year"),
        "abstract": rebuild_abstract(work.get("abstract_inverted_index")),
        "is_free": bool(open_access.get("is_oa")),
        "topics": topics,
        "link": doi if doi else openalex_id,
        "has_doi": bool(doi),
    }


def _title_key(title):
    return clean_query(title).lower()


def _quality(article):
    return (bool(article["abstract"]), article["has_doi"], len(article["abstract"]))


def remove_duplicates(articles):
    """OpenAlex sometimes stores one paper as several records; keep the best copy."""
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
    with_abstract, without_abstract = [], []
    for article in articles:
        if len(with_abstract) >= limit:
            break
        (with_abstract if article["abstract"] else without_abstract).append(article)
    return with_abstract, without_abstract


def collect(query, free_only, start, limit, seen, first_page=None):
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
        if len(works) < page_size:
            break

    return {"to_score": to_score, "without_abstract": without_abstract,
            "duplicates": duplicates, "position": position, "total": total}


def title_key(title):
    return _title_key(title)


def search(query, free_only=True, limit=None, page=1):
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
    works, _ = search(title, free_only=False, limit=1)
    return works[0] if works else None
