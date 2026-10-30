import os
import requests

API_KEY = os.getenv("S2_KEY")  # the key is kept in .env, not in the code

query = "machine learning in education"

url = "https://api.semanticscholar.org/graph/v1/paper/search"

params = {
    "query": query,
    "limit": 5,
    "fields": "title,authors,year,abstract,citationCount"
}

headers = {
    "x-api-key": API_KEY
}

response = requests.get(url, params=params, headers=headers)
data = response.json()

for paper in data["data"]:
    print("=" * 60)
    print(f"Название: {paper['title']}")
    print(f"Год: {paper.get('year', 'н/д')}")
    print(f"Цитирований: {paper.get('citationCount', 0)}")
    authors = [a["name"] for a in paper.get("authors", [])]
    print(f"Авторы: {', '.join(authors[:3])}")
    abstract = paper.get("abstract", "")
    if abstract:
        print(f"Абстракт: {abstract[:200]}...")
    print()