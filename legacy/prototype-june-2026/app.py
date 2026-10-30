from flask import Flask, request, jsonify, render_template
from services import semantic_scholar, openalex, ai_analyzer, ranking, citation

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify([])

    year_start = request.args.get("year_start", "")
    year_end = request.args.get("year_end", "")
    min_citations = int(request.args.get("min_citations", 0))
    open_access = request.args.get("open_access", "false") == "true"

    # Собираем из двух источников
    s2_papers = semantic_scholar.search(query, year_start, year_end, min_citations, open_access, limit=8)
    oa_papers = openalex.search(query, year_start, year_end, min_citations, open_access, limit=7)

    # Дедупликация по DOI
    seen_dois = set()
    all_papers = []
    for p in s2_papers + oa_papers:
        doi = p.get("doi", "")
        if doi and doi in seen_dois:
            continue
        if doi:
            seen_dois.add(doi)
        all_papers.append(p)

    # Оценка релевантности и надёжности
    all_papers = ranking.compute_scores(all_papers, query)

    # AI-саммари для топ-10
    for p in all_papers[:10]:
        summary, score = ai_analyzer.quick_summary(p["title"], p["abstract"], query)
        p["summary"] = summary
        p["ai_score"] = score

    # Цитирования
    for p in all_papers:
        p["apa"] = citation.to_apa(p)
        p["bibtex"] = citation.to_bibtex(p)

    return jsonify(all_papers)


@app.route("/deep_analysis")
def deep_analysis():
    title = request.args.get("title", "")
    abstract = request.args.get("abstract", "")
    query = request.args.get("query", "")

    result = ai_analyzer.deep_analysis(title, abstract, query)
    if not result:
        return jsonify({"error": "Не удалось выполнить анализ"}), 500

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)