def to_apa(paper):
    authors = paper.get("authors", [])
    year = paper.get("year", "n.d.")
    title = paper.get("title", "")
    venue = paper.get("venue", "")
    doi = paper.get("doi", "")

    if authors:
        last_first = []
        for a in authors[:6]:
            parts = a.strip().split()
            if len(parts) >= 2:
                last = parts[-1]
                initials = ". ".join(p[0] for p in parts[:-1]) + "."
                last_first.append(f"{last}, {initials}")
            else:
                last_first.append(a)
        if len(authors) > 6:
            author_str = ", ".join(last_first[:6]) + ", et al."
        else:
            author_str = ", ".join(last_first)
    else:
        author_str = "Unknown Author"

    apa = f"{author_str} ({year}). {title}."
    if venue:
        apa += f" {venue}."
    if doi:
        apa += f" https://doi.org/{doi}"

    return apa


def to_bibtex(paper):
    authors = paper.get("authors", [])
    year = paper.get("year", "")
    title = paper.get("title", "")
    venue = paper.get("venue", "")
    doi = paper.get("doi", "")

    key = ""
    if authors:
        key += authors[0].split()[-1].lower()
    if year:
        key += str(year)
    if title:
        key += title.split()[0].lower()

    author_str = " and ".join(authors) if authors else "Unknown"

    bibtex = f"@article{{{key},\n"
    bibtex += f"  author = {{{author_str}}},\n"
    bibtex += f"  title = {{{title}}},\n"
    if year:
        bibtex += f"  year = {{{year}}},\n"
    if venue:
        bibtex += f"  journal = {{{venue}}},\n"
    if doi:
        bibtex += f"  doi = {{{doi}}}\n"
    bibtex += "}"

    return bibtex