import requests

def search(query, year_start="", year_end="", min_citations=0, open_access=False, limit=10):
    params = {
        "search": query,
        "per-page": limit,
        "select": "title,authorships,publication_year,abstract_inverted_index,cited_by_count,doi,open_access,primary_location,biblio"
    }

    filters = []
    if year_start and year_end:
        filters.append(f"publication_year:{year_start}-{year_end}")
    if open_access:
        filters.append("open_access.is_oa:true")
    if filters:
        params["filter"] = ",".join(filters)

    try:
        response = requests.get(
            "https://api.openalex.org/works",
            params=params,
            headers={"User-Agent": "ResearchLens/1.0 (research tool)"},
            timeout=15
        )
        data = response.json()
    except Exception as e:
        print(f"OpenAlex error: {e}")
        return []

    papers = []
    for p in data.get("results", []):
        citations = p.get("cited_by_count", 0)
        if citations < min_citations:
            continue

        # Восстановить абстракт из inverted index
        abstract = ""
        inv = p.get("abstract_inverted_index") or {}
        if inv:
            words = {}
            for word, positions in inv.items():
                for pos in positions:
                    words[pos] = word
            abstract = " ".join(words[i] for i in sorted(words))

        authors = []
        for a in p.get("authorships", [])[:4]:
            name = a.get("author", {}).get("display_name", "")
            if name:
                authors.append(name)

        doi = (p.get("doi") or "").replace("https://doi.org/", "")
        location = p.get("primary_location") or {}
        source = location.get("source") or {}
        pdf_url = location.get("pdf_url", "") or ""

        papers.append({
            "title": p.get("title", "") or "",
            "year": p.get("publication_year", ""),
            "citations": citations,
            "authors": authors,
            "abstract": abstract,
            "doi": doi,
            "doi_url": f"https://doi.org/{doi}" if doi else "",
            "pdf_url": pdf_url,
            "venue": source.get("display_name", ""),
            "source": "OpenAlex"
        })

    return papers