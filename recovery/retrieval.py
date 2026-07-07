"""Retrieval helpers for citation repair and semantic recovery."""

import re
import time
import os
import httpx
from rapidfuzz import fuzz

S2_API_KEY   = os.getenv("S2_API_KEY", "")
CROSSREF_URL = "https://api.crossref.org/works"
S2_URL       = "https://api.semanticscholar.org/graph/v1/paper/search"
OPENALEX_URL = "https://api.openalex.org/works"
DBLP_URL     = "https://dblp.org/search/publ/api"
MAILTO       = "jiangxq0213@gmail.com"

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "based", "between", "by", "for",
    "from", "in", "into", "is", "it", "of", "on", "or", "that", "the",
    "their", "to", "using", "versus", "via", "with", "without"
}


def _s2_headers() -> dict:
    return {"x-api-key": S2_API_KEY} if S2_API_KEY else {}


def _restore_openalex_abstract(inv: dict) -> str:
    if not inv:
        return ""
    try:
        words = [""] * (max(max(v) for v in inv.values()) + 1)
        for word, positions in inv.items():
            for pos in positions:
                words[pos] = word
        return " ".join(words)
    except Exception:
        return ""


def _strip_markup(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def _normalize_doi(doi: str) -> str:
    doi = (doi or "").strip().rstrip(".,;)")
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.I)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.I)
    return doi.strip()


def _crossref_item_to_paper(item: dict, source: str, score: int | float = 100) -> dict:
    title = (item.get("title") or [""])[0]
    return {
        "title": title,
        "authors": [
            {"name": f"{a.get('given','')} {a.get('family','')}".strip()}
            for a in item.get("author", [])
        ],
        "year": item.get("published", {}).get("date-parts", [[None]])[0][0],
        "abstract": _strip_markup(item.get("abstract", "")),
        "externalIds": {"DOI": item.get("DOI", "")},
        "citationCount": item.get("is-referenced-by-count"),
        "_source": source,
        "_fuzzy_score": score
    }


def _mark_retrieval_candidate(paper: dict, source: str, query: str) -> dict:
    paper["_source"] = source
    paper["_search_query"] = query
    paper["_has_abstract"] = bool(
        paper.get("abstract") and len(paper["abstract"]) > 50
    )
    return paper


def _candidate_key(paper: dict) -> str:
    doi = (paper.get("externalIds") or {}).get("DOI") or ""
    if doi:
        return "doi:" + doi.lower().replace("https://doi.org/", "")
    title = re.sub(r"\W+", " ", (paper.get("title") or "").lower()).strip()
    return "title:" + title


def _dedupe_candidates(candidates: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for paper in candidates:
        key = _candidate_key(paper)
        if key in seen or key == "title:":
            continue
        seen.add(key)
        deduped.append(paper)
    return deduped


def make_low_cost_queries(claim: str, max_queries: int = 3) -> list[str]:
    """Generate short deterministic queries without an LLM call."""
    if not claim or claim.strip().upper() == "UNCERTAIN":
        return []

    clean = re.sub(r"[^-A-Za-z0-9+#/\\ ]+", " ", claim or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return []

    tokens = re.findall(r"[-A-Za-z0-9+#/\\]+", clean)
    content = [
        t for t in tokens
        if len(t) > 2 and t.lower() not in STOPWORDS
    ]

    queries = [clean[:180]]
    if content:
        queries.append(" ".join(content[:10]))
    if len(content) > 5:
        queries.append(" ".join(content[-10:]))

    unique = []
    seen = set()
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        key = q.lower()
        if q and key not in seen:
            unique.append(q)
            seen.add(key)
    return unique[:max_queries]


def fetch_abstract_for_level1(title: str) -> dict | None:
    """Fetch an abstract for a known citation title."""
    if not title:
        return None
    result = _s2_by_title(title)
    if result:
        return result
    print("  [L1 fetch] S2 failed, trying OpenAlex...")
    candidates, _ = route_a_openalex(title, fuzzy_threshold=75)
    for candidate in candidates:
        if (candidate.get("abstract") or "").strip():
            candidate["_source"] = "openalex_level1"
            return candidate
    print("  [L1 fetch] OpenAlex failed, trying CrossRef...")
    return _crossref_by_title(title, fuzzy_threshold=75)


def _s2_by_title(title: str) -> dict | None:
    params = {
        "query": title,
        "limit": 3,
        "fields": "title,authors,year,abstract,externalIds,citationCount"
    }
    try:
        resp = httpx.get(
            S2_URL, params=params,
            headers=_s2_headers(),
            timeout=15.0
        )
        resp.raise_for_status()
        for paper in resp.json().get("data", []):
            score = fuzz.ratio(title.lower(), paper.get("title", "").lower())
            if score >= 70:
                paper["_source"]      = "semantic_scholar_level1"
                paper["_fuzzy_score"] = score
                print(f"  [S2] Found: {paper['title'][:60]} (score={score})")
                return paper
    except Exception as e:
        print(f"  [S2 ERROR] {e}")
    return None


def _crossref_by_title(title: str, fuzzy_threshold: int = 80) -> dict | None:
    params  = {"query.title": title, "rows": 3,
               "select": "title,author,published,DOI,abstract"}
    headers = {"User-Agent": f"CitationRecovery/1.0 (mailto:{MAILTO})"}
    try:
        resp = httpx.get(CROSSREF_URL, params=params,
                         headers=headers, timeout=15.0)
        resp.raise_for_status()
        for item in resp.json()["message"]["items"]:
            if not item.get("title"):
                continue
            cr_title = item["title"][0]
            score    = fuzz.ratio(title.lower(), cr_title.lower())
            if score >= fuzzy_threshold:
                print(f"  [CrossRef] Found: {cr_title[:60]} (score={score})")
                return _crossref_item_to_paper(item, "crossref_level1", score)
    except Exception as e:
        print(f"  [CrossRef ERROR] {e}")
    return None


def route_a_by_doi(doi: str) -> tuple[list[dict], str]:
    doi = _normalize_doi(doi)
    if not doi:
        return [], "A_doi_empty"

    headers = {"User-Agent": f"CitationRecovery/1.0 (mailto:{MAILTO})"}
    try:
        resp = httpx.get(f"{CROSSREF_URL}/{doi}", headers=headers, timeout=15.0)
        resp.raise_for_status()
        item = resp.json().get("message", {})
        if item.get("title"):
            print(f"  [Route A DOI] CrossRef found: {item['title'][0][:60]}")
            return [_crossref_item_to_paper(item, "crossref_doi", 100)], "A_crossref_doi"
    except Exception as e:
        print(f"  [Route A DOI] CrossRef missed: {e}")

    try:
        resp = httpx.get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
            params={"fields": "title,authors,year,abstract,externalIds,citationCount"},
            headers=_s2_headers(),
            timeout=15.0
        )
        resp.raise_for_status()
        paper = resp.json()
        if paper.get("title"):
            paper["_source"] = "semantic_scholar_doi"
            paper["_fuzzy_score"] = 100
            print(f"  [Route A DOI] S2 found: {paper['title'][:60]}")
            return [paper], "A_s2_doi"
    except Exception as e:
        print(f"  [Route A DOI] S2 missed: {e}")

    return [], "A_doi_no_match"


def route_a_crossref(title: str) -> tuple[list[dict], str]:
    """Search CrossRef by title and return fuzzy-matched candidates."""
    params  = {"query.title": title, "rows": 5,
               "select": "title,author,published,DOI,abstract"}
    headers = {"User-Agent": f"CitationRecovery/1.0 (mailto:{MAILTO})"}
    try:
        resp = httpx.get(CROSSREF_URL, params=params,
                         headers=headers, timeout=15.0)
        resp.raise_for_status()
        items = resp.json()["message"]["items"]
    except Exception as e:
        print(f"  [CrossRef ERROR] {e}")
        return [], "A_api_error"

    matched = []
    for item in items:
        if not item.get("title"):
            continue
        cr_title = item["title"][0]
        score    = fuzz.ratio(title.lower(), cr_title.lower())
        if score >= 80:
            matched.append(_crossref_item_to_paper(item, "crossref", score))

    if matched:
        matched.sort(key=lambda x: x["_fuzzy_score"], reverse=True)
        print(f"  [Route A] Matched {len(matched)} papers, "
              f"best score={matched[0]['_fuzzy_score']}")
        return matched, "A"

    print("  [Route A] No fuzzy match (threshold=80)")
    return [], "A_no_match"


def route_a_openalex(title: str, fuzzy_threshold: int = 80) -> tuple[list[dict], str]:
    """Search OpenAlex by title for candidates missed by CrossRef or S2."""
    params  = {"search": title, "per-page": 5,
               "select": "title,authorships,publication_year,doi,abstract_inverted_index"}
    try:
        resp = httpx.get(OPENALEX_URL, params=params, timeout=15.0)
        resp.raise_for_status()
        items = resp.json().get("results", [])
    except Exception as e:
        print(f"  [OpenAlex ERROR] {e}")
        return [], "A_openalex_error"

    matched = []
    for item in items:
        oa_title = item.get("title") or ""
        if not oa_title:
            continue
        score = fuzz.ratio(title.lower(), oa_title.lower())
        if score >= fuzzy_threshold:
            abstract = _restore_openalex_abstract(
                item.get("abstract_inverted_index") or {}
            )

            authors = [
                {"name": a.get("author", {}).get("display_name", "")}
                for a in item.get("authorships", [])
                if isinstance(a, dict)
            ]
            doi = (item.get("doi") or "").replace("https://doi.org/", "")
            matched.append({
                "title": oa_title,
                "authors": authors,
                "year": item.get("publication_year"),
                "abstract": abstract,
                "externalIds": {"DOI": doi},
                "citationCount": None,
                "_source": "openalex",
                "_fuzzy_score": score
            })

    if matched:
        matched.sort(key=lambda x: x["_fuzzy_score"], reverse=True)
        print(f"  [Route A OpenAlex] Matched {len(matched)} papers, "
              f"best score={matched[0]['_fuzzy_score']}")
        return matched, "A_openalex"

    print(f"  [Route A OpenAlex] No fuzzy match (threshold={fuzzy_threshold})")
    return [], "A_openalex_no_match"


def route_a_dblp(title: str, fuzzy_threshold: int = 80) -> tuple[list[dict], str]:
    """Search DBLP by title for computer-science proceedings."""
    params = {"q": title, "format": "json", "h": 5}
    try:
        resp = httpx.get(DBLP_URL, params=params, timeout=15.0)
        resp.raise_for_status()
        hits = resp.json().get("result", {}).get("hits", {}).get("hit", [])
    except Exception as e:
        print(f"  [DBLP ERROR] {e}")
        return [], "A_dblp_error"

    matched = []
    for hit in hits:
        info = hit.get("info", {})
        dblp_title = info.get("title", "")
        if not dblp_title:
            continue
        score = fuzz.ratio(title.lower(), dblp_title.lower())
        if score >= fuzzy_threshold:
            raw_authors = info.get("authors", {}).get("author", [])
            if isinstance(raw_authors, dict):
                raw_authors = [raw_authors]
            authors = [
                {"name": a.get("text", "") if isinstance(a, dict) else str(a)}
                for a in raw_authors
            ]
            doi = info.get("doi", "") or info.get("ee", "")
            matched.append({
                "title": dblp_title,
                "authors": authors,
                "year": info.get("year"),
                "abstract": "",
                "externalIds": {"DOI": doi},
                "citationCount": None,
                "_source": "dblp",
                "_fuzzy_score": score
            })

    if matched:
        matched.sort(key=lambda x: x["_fuzzy_score"], reverse=True)
        print(f"  [Route A DBLP] Matched {len(matched)} papers, "
              f"best score={matched[0]['_fuzzy_score']}")
        return matched, "A_dblp"

    print(f"  [Route A DBLP] No fuzzy match (threshold={fuzzy_threshold})")
    return [], "A_dblp_no_match"


def route_a_all(title: str) -> tuple[list[dict], str]:
    """Cascade CrossRef, S2, OpenAlex, and DBLP until one source matches."""
    candidates, route = route_a_crossref(title)
    if candidates:
        return candidates, route

    print("  [Route A] CrossRef missed -> trying S2...")
    s2_paper = _s2_by_title(title)
    if s2_paper:
        s2_paper["_source"] = "semantic_scholar_repair"
        return [s2_paper], "A_s2"

    print("  [Route A] S2 missed -> trying OpenAlex...")
    candidates, route = route_a_openalex(title)
    if candidates:
        return candidates, route

    print("  [Route A] OpenAlex missed -> trying DBLP...")
    candidates, route = route_a_dblp(title)
    if candidates:
        best = candidates[0]
        if not best.get("abstract"):
            print("  [Route A DBLP] No abstract, fetching from S2...")
            s2_paper = _s2_by_title(best["title"])
            if s2_paper and s2_paper.get("abstract"):
                best["abstract"]      = s2_paper["abstract"]
                best["citationCount"] = s2_paper.get("citationCount")
                best["_source"]       = "dblp+s2_abstract"
        return candidates, route

    print("  [Route A] All four databases missed.")
    return [], "A_all_no_match"


def route_b_semantic_scholar(
    claim: str,
    year_upper_bound: int | None = None,
    max_retries: int = 3
) -> tuple[list[dict], str]:
    """Search Semantic Scholar for semantic-recovery candidates."""
    if not claim or claim == "UNCERTAIN":
        print("  [Route B] Skipped: no valid claim")
        return [], "B_no_claim"

    params = {
        "query": claim,
        "limit": 7,
        "fields": "title,authors,year,abstract,externalIds,citationCount"
    }
    if year_upper_bound and isinstance(year_upper_bound, int):
        params["year"] = f"-{year_upper_bound}"

    for attempt in range(max_retries):
        try:
            resp = httpx.get(
                S2_URL, params=params,
                headers=_s2_headers(),
                timeout=20.0
            )
            if resp.status_code == 429:
                wait = 2 ** attempt * 10
                print(f"  [Route B] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json().get("data", [])

            if not data and year_upper_bound and "year" in params:
                print("  [Route B] No results with year filter, retrying without...")
                params.pop("year")
                resp2 = httpx.get(
                    S2_URL, params=params,
                    headers=_s2_headers(),
                    timeout=20.0
                )
                if resp2.status_code == 200:
                    data = resp2.json().get("data", [])

            candidates = []
            for p in data:
                p["_source"] = "semantic_scholar"
                p["_has_abstract"] = bool(
                    p.get("abstract") and len(p["abstract"]) > 50
                )
                candidates.append(p)

            candidates.sort(key=lambda p: (
                not p.get("_has_abstract"),
                -(p.get("citationCount") or 0)
            ))

            with_abstract = sum(1 for p in candidates if p.get("_has_abstract"))

            print(f"  [Route B] {len(data)} results, "
                  f"{with_abstract} with abstracts")
            return candidates[:7], "B"

        except Exception as e:
            print(f"  [Route B] Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)

    return [], "B_api_error"


def _search_openalex_general(query: str, per_page: int = 5) -> list[dict]:
    params = {
        "search": query,
        "per-page": per_page,
        "select": "title,authorships,publication_year,doi,abstract_inverted_index,cited_by_count"
    }
    try:
        resp = httpx.get(OPENALEX_URL, params=params, timeout=15.0)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [OpenAlex B ERROR] {e}")
        return []

    papers = []
    for item in resp.json().get("results", []):
        title = item.get("title") or ""
        if not title:
            continue
        authors = [
            {"name": a.get("author", {}).get("display_name", "")}
            for a in item.get("authorships", [])
            if isinstance(a, dict)
        ]
        doi = (item.get("doi") or "").replace("https://doi.org/", "")
        paper = {
            "title": title,
            "authors": authors,
            "year": item.get("publication_year"),
            "abstract": _restore_openalex_abstract(
                item.get("abstract_inverted_index") or {}
            ),
            "externalIds": {"DOI": doi},
            "citationCount": item.get("cited_by_count"),
        }
        papers.append(_mark_retrieval_candidate(paper, "openalex", query))

    with_abstract = sum(1 for p in papers if p.get("_has_abstract"))
    print(f"  [OpenAlex B] {len(papers)} results, {with_abstract} with abstracts")
    return papers


def _search_crossref_general(query: str, rows: int = 5) -> list[dict]:
    params = {
        "query.bibliographic": query,
        "rows": rows,
        "select": "title,author,published,DOI,abstract,is-referenced-by-count"
    }
    headers = {"User-Agent": f"CitationRecovery/1.0 (mailto:{MAILTO})"}
    try:
        resp = httpx.get(CROSSREF_URL, params=params,
                         headers=headers, timeout=15.0)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [CrossRef B ERROR] {e}")
        return []

    papers = []
    for item in resp.json().get("message", {}).get("items", []):
        if not item.get("title"):
            continue
        paper = {
            "title": item["title"][0],
            "authors": [
                {"name": f"{a.get('given','')} {a.get('family','')}".strip()}
                for a in item.get("author", [])
            ],
            "year": item.get("published", {}).get("date-parts", [[None]])[0][0],
            "abstract": _strip_markup(item.get("abstract", "")),
            "externalIds": {"DOI": item.get("DOI", "")},
            "citationCount": item.get("is-referenced-by-count"),
        }
        papers.append(_mark_retrieval_candidate(paper, "crossref", query))

    with_abstract = sum(1 for p in papers if p.get("_has_abstract"))
    print(f"  [CrossRef B] {len(papers)} results, {with_abstract} with abstracts")
    return papers


def route_b_multi_source(
    claim: str,
    max_queries: int = 3,
    max_candidates: int = 12
) -> tuple[list[dict], str]:
    """Run low-cost multi-source retrieval for Layer 4 recovery."""
    queries = make_low_cost_queries(claim, max_queries=max_queries)
    if not queries:
        return [], "B_multi_no_claim"

    print("  [Route B Multi] Queries:")
    for q in queries:
        print(f"    - {q}")

    all_candidates = []
    for i, query in enumerate(queries):
        s2_candidates, _ = route_b_semantic_scholar(query, max_retries=1)
        all_candidates.extend(s2_candidates[:5])

        if i < 2:
            all_candidates.extend(_search_openalex_general(query, per_page=5))
            all_candidates.extend(_search_crossref_general(query, rows=5))

    candidates = _dedupe_candidates(all_candidates)
    candidates.sort(key=lambda p: (
        not p.get("_has_abstract"),
        -(p.get("citationCount") or 0)
    ))
    candidates = candidates[:max_candidates]

    with_abstract = sum(1 for p in candidates if p.get("_has_abstract"))
    print(f"  [Route B Multi] {len(candidates)} unique candidates, "
          f"{with_abstract} with abstracts")
    return candidates, "B_multi"
