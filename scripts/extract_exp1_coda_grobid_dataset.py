import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "grobid_datasets" / "exp1.pdf"
CLEAN_JSON = ROOT / "json_datasets" / "exp1.json"
OUTPUT_JSON = ROOT / "grobid_datasets" / "exp1.json"
GROBID_URL = "http://localhost:8070/api/processReferences"


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _sim(left: str, right: str) -> float:
    return SequenceMatcher(None, _norm(left), _norm(right)).ratio()


def _tokens(text: str) -> set[str]:
    return {x for x in _norm(text).split() if len(x) > 1 and x not in {"and", "et", "al"}}


def _overlap(left: str, right: str) -> float:
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(len(left_tokens), len(right_tokens))


def _extract_all_references() -> list[dict]:
    with PDF_PATH.open("rb") as pdf:
        resp = requests.post(GROBID_URL, files={"input": pdf}, timeout=120)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "xml")
    references = []
    for idx, bib in enumerate(soup.find_all("biblStruct"), 1):
        title = bib.find("title", type="main")
        title_text = title.get_text(" ", strip=True) if title else "Unknown Title"

        date = bib.find("date", type="published")
        year = date["when"] if date and date.has_attr("when") else "Unknown Year"

        authors = []
        for author_node in bib.find_all("author"):
            pers_name = author_node.find("persName")
            if not pers_name:
                continue
            surname = pers_name.find("surname")
            forenames = pers_name.find_all("forename")
            parts = [x.get_text(" ", strip=True) for x in forenames if x.get_text(strip=True)]
            if surname and surname.get_text(strip=True):
                parts.append(surname.get_text(" ", strip=True))
            if parts:
                authors.append(" ".join(parts))

        link = "N/A"
        doi_tag = bib.find("idno", type="DOI")
        arxiv_tag = bib.find("idno", type="arXiv")
        ptr_tag = bib.find("ptr")
        if doi_tag and doi_tag.get_text(strip=True):
            link = "https://doi.org/" + doi_tag.get_text(strip=True)
        elif arxiv_tag and arxiv_tag.get_text(strip=True):
            link = "https://arxiv.org/abs/" + arxiv_tag.get_text(strip=True)
        elif ptr_tag and ptr_tag.has_attr("target"):
            link = ptr_tag["target"]

        references.append(
            {
                "source_id": idx,
                "title": title_text,
                "author": ", ".join(authors) if authors else "Unknown Author",
                "year": year,
                "link": link,
                "is_real": True,
                "group": "Exp1_CoDa_GROBID_Level1",
                "raw_text": bib.get_text(" ", strip=True),
            }
        )
    return references


def _select_matching_twenty(clean_items: list[dict], grobid_items: list[dict]) -> list[dict]:
    selected = []
    used = set()
    for target in clean_items:
        best_i, best, best_score, best_parts = None, None, -1.0, None
        for idx, candidate in enumerate(grobid_items):
            if idx in used:
                continue
            title_score = max(
                _sim(target["title"], candidate.get("title", "")),
                _sim(target["title"], candidate.get("raw_text", "")),
            )
            author_score = _overlap(target.get("author", ""), candidate.get("author", ""))
            doi = target.get("link", "").lower().replace("https://doi.org/", "")
            doi_score = 1.0 if doi and doi in candidate.get("link", "").lower() else 0.0
            score = max(title_score, 0.92 * author_score + 0.08 * doi_score)
            if score > best_score:
                best_i, best, best_score, best_parts = idx, candidate, score, (title_score, author_score)

        if best is None or best_score < 0.50:
            raise RuntimeError(f"No GROBID match for Exp1 item {target['id']}: {target['title']}")

        used.add(best_i)
        row = dict(best)
        row["id"] = target["id"]
        row["clean_title"] = target["title"]
        row["grobid_match_score"] = round(best_score, 3)
        row["grobid_title_score"] = round(best_parts[0], 3)
        row["grobid_author_score"] = round(best_parts[1], 3)
        selected.append(row)
    return selected


def main() -> None:
    clean_items = json.loads(CLEAN_JSON.read_text(encoding="utf-8"))
    grobid_items = _extract_all_references()
    selected = _select_matching_twenty(clean_items, grobid_items)
    OUTPUT_JSON.write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(grobid_items)} references and selected {len(selected)} Exp1 references.")
    print(f"Updated {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
