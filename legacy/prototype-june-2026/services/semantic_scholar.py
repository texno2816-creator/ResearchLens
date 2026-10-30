import requests
from config import S2_KEY

def search(query, year_start="", year_end="", min_citations=0, open_access=False, limit=10):
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,abstract,citationCount,externalIds,openAccessPdf,publicationVenue"
    }

    if year_start and year_end:
        params["year"] = f"{year_start}-{year_end}"

    headers = {"x-api-key": str(S2_KEY).strip()}

    try:
        response = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params=params,
            headers=headers,
            timeout=15
        )
        data = response.json()
    except Exception as e:
        print(f"Semantic Scholar error: {e}")
        return []

    papers = []
    for p in data.get("data", []):
        if p.get("citationCount", 0) < min_citations:
            continue

        pdf = p.get("openAccessPdf") or {}
        pdf_url = pdf.get("url", "")

        if open_access and not pdf_url:
            continue

        doi = p.get("externalIds", {}).get("DOI", "")
        venue = p.get("publicationVenue") or {}

        papers.append({
            "title": p.get("title", ""),
            "year": p.get("year", ""),
            "citations": p.get("citationCount", 0),
            "authors": [a["name"] for a in p.get("authors", [])[:4]],
            "abstract": p.get("abstract", ""),
            "doi": doi,
            "doi_url": f"https://doi.org/{doi}" if doi else "",
            "pdf_url": pdf_url,
            "venue": venue.get("name", ""),
            "source": "Semantic Scholar"
        })

    return papers