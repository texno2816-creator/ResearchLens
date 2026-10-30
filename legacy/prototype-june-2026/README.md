# ResearchLens prototype (June 2026)

The first prototype of ResearchLens, kept for history. The files date from 23–25 June 2026. It is not maintained and is not part of the current platform.

- `test.py` — the first experiment with the Semantic Scholar API (23.06.2026).
- `app.py`, `services/`, `templates/`, `static/` — the first website (25.06.2026): Semantic Scholar + OpenAlex search, removal of duplicates by DOI, Research Fit Score and Credibility Score, AI summaries and Deep Analysis through Groq, APA and BibTeX export.

Why it was replaced is described in the [development diary](../../docs/dev-diary.md#background-may--september-2026).

To run it you would need a `.env` file with `S2_KEY` (Semantic Scholar) and `GROQ_KEY`. Keys are never stored in the repository.
