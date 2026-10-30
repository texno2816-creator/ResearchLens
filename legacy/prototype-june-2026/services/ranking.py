from datetime import datetime

CURRENT_YEAR = datetime.now().year

def compute_scores(papers, query):
    query_words = set(query.lower().split())

    for p in papers:
        title_words = set((p.get("title") or "").lower().split())
        abstract_words = set((p.get("abstract") or "").lower().split())

        # Семантическая релевантность (0-40)
        title_overlap = len(query_words & title_words) / max(len(query_words), 1)
        abstract_overlap = len(query_words & abstract_words) / max(len(query_words), 1)
        semantic = min(40, int((title_overlap * 25 + abstract_overlap * 15)))

        # Свежесть (0-20)
        year = p.get("year") or 0
        age = CURRENT_YEAR - int(year) if year else 10
        recency = max(0, 20 - age * 2)

        # Сила цитирований (0-25)
        citations = p.get("citations", 0)
        cite_score = min(25, int(citations / 20)) if citations else 0

        # Качество источника (0-15)
        quality = 0
        if p.get("doi"):
            quality += 5
        if p.get("venue"):
            quality += 5
        if p.get("pdf_url"):
            quality += 3
        if p.get("abstract"):
            quality += 2

        fit_score = semantic + recency + cite_score + quality

        # Credibility Score (0-10)
        cred = 0
        if p.get("doi"):
            cred += 3
        if p.get("venue"):
            cred += 2
        if citations > 50:
            cred += 3
        elif citations > 10:
            cred += 2
        elif citations > 0:
            cred += 1
        if p.get("pdf_url"):
            cred += 2

        p["fit_score"] = min(100, fit_score)
        p["credibility"] = min(10, cred)

    return sorted(papers, key=lambda x: x["fit_score"], reverse=True)