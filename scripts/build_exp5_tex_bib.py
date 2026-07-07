import json
import re
import unicodedata
from pathlib import Path

from lxml import etree


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = Path(
    "/Users/jiangxiaoqi/Desktop/"
    "NeurIPS-2024-enhancing-chess-reinforcement-learning-with-graph-representation-Paper-Conference.pdf"
)
JSON_PATH = ROOT / "json_datasets" / "exp5.json"
OUT_DIR = ROOT / "exp5_constructed"
TEI_PATH = (
    ROOT
    / ".grobid_cache"
    / "NeurIPS-2024-enhancing-chess-reinforcement-learning-with-graph-representation-Paper-Conference_c0a9f79c50f8.tei.xml"
)
SELECTED_REF_ORDINALS = None
KEY_PREFIX = "exp5"

NS = {"tei": "http://www.tei-c.org/ns/1.0"}


UNICODE_REPLACEMENTS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": "``",
    "\u201d": "''",
    "\u2013": "--",
    "\u2014": "---",
    "\u2212": "-",
    "\u00a0": " ",
    "\u2026": "...",
    "\u00d7": "x",
    "\u2265": ">=",
    "\u2264": "<=",
    "\u2208": " in ",
    "\u22c5": " dot ",
    "\u223c": "~",
    "\u2032": "'",
    "\u239b": "(",
    "\u239d": "(",
    "\ufffd": "",
    "\u03b1": "alpha",
    "\u03b8": "theta",
    "\u03c0": "pi",
    "\u1e7d": "v",
}


def normalize_text(text: str) -> str:
    if not text:
        return ""
    for src, dst in UNICODE_REPLACEMENTS.items():
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text)
    return text


def latex_escape(text: str) -> str:
    text = normalize_text(text)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def bib_escape(text: str) -> str:
    return latex_escape(text).replace("\n", " ").strip()


def make_key(item: dict, index: int | None = None) -> str:
    item_id = item.get("id", index)
    return f"{KEY_PREFIX}fake{int(item_id):02d}"


def make_bib_entry(item: dict, index: int | None = None) -> str:
    key = make_key(item, index=index)
    title = bib_escape(item.get("title", "Untitled"))
    authors = [
        bib_escape(part.strip())
        for part in str(item.get("author", "Unknown Author")).split(",")
        if part.strip()
    ]
    author = " and ".join(authors) if authors else "Unknown Author"
    year = bib_escape(str(item.get("year", "n.d.")))
    link = str(item.get("link", "")).strip()

    fields = [
        f"  title = {{{title}}}",
        f"  author = {{{author}}}",
        "  journal = {Journal of Fabricated Research Artifacts}",
        f"  year = {{{year}}}",
    ]
    if link.upper() in {"", "N/A", "NA", "NONE", "NULL"}:
        pass
    elif "doi.org/" in link:
        doi = link.split("doi.org/", 1)[1]
        fields.append(f"  doi = {{{bib_escape(doi)}}}")
        fields.append(f"  url = {{{bib_escape(link)}}}")
    elif link.startswith("http://") or link.startswith("https://"):
        fields.append(f"  url = {{{bib_escape(link)}}}")
    elif link:
        doi = link.replace("https://doi.org/", "").replace("http://doi.org/", "")
        fields.append(f"  doi = {{{bib_escape(doi)}}}")
        fields.append(f"  url = {{{bib_escape('https://doi.org/' + doi)}}}")

    return "@article{" + key + ",\n" + ",\n".join(fields) + "\n}"


def local_name(node: etree._Element) -> str:
    return etree.QName(node).localname


def node_text_without_bibr(node: etree._Element) -> str:
    parts = []

    def walk(n):
        if n.text:
            parts.append(n.text)
        for child in n:
            if child.get("type") != "bibr":
                walk(child)
            if child.tail:
                parts.append(child.tail)

    walk(node)
    return normalize_text("".join(parts)).strip()


def render_inline(node: etree._Element, citation_state: dict, mapping: list[dict]) -> str:
    text = latex_escape(node.text or "")
    rendered = [text]

    for child in node:
        if child.get("type") == "bibr":
            citation_state["seen_refs"] += 1
            original = normalize_text("".join(child.itertext())).strip()
            should_insert = (
                citation_state["selected_ref_ordinals"] is None
                or citation_state["seen_refs"] in citation_state["selected_ref_ordinals"]
            )
            idx = citation_state["used"]
            if should_insert and idx < len(citation_state["keys"]):
                key = citation_state["keys"][idx]
                citation_state["used"] += 1
                rendered.append(r"\cite{" + key + "}")
                paragraph = node
                while paragraph is not None and local_name(paragraph) != "p":
                    paragraph = paragraph.getparent()
                context_node = paragraph if paragraph is not None else node
                context = node_text_without_bibr(context_node)
                mapping.append(
                    {
                        "fake_key": key,
                        "fake_title": citation_state["items"][idx].get("title", ""),
                        "original_ref_text": original,
                        "context": context[:600],
                    }
                )
            # Drop extra original citations after all 20 fake entries are placed.
            rendered.append(latex_escape(child.tail or ""))
            continue

        name = local_name(child)
        child_text = render_inline(child, citation_state, mapping)
        if name in {"formula"}:
            rendered.append(" " + child_text + " ")
        elif name in {"ref", "term", "hi", "label"}:
            rendered.append(child_text)
        else:
            rendered.append(child_text)
        rendered.append(latex_escape(child.tail or ""))

    return "".join(rendered)


def render_div(div: etree._Element, citation_state: dict, mapping: list[dict], depth: int = 0) -> list[str]:
    lines = []
    head = div.find("tei:head", NS)
    if head is not None:
        heading = render_inline(head, citation_state, mapping).strip()
        if heading:
            if depth <= 0:
                lines.extend(["", r"\section{" + heading + "}"])
            elif depth == 1:
                lines.extend(["", r"\subsection{" + heading + "}"])
            else:
                lines.extend(["", r"\subsubsection{" + heading + "}"])

    for child in div:
        name = local_name(child)
        if name == "head":
            continue
        if name == "p":
            para = render_inline(child, citation_state, mapping).strip()
            if para:
                lines.extend(["", para])
        elif name == "div":
            lines.extend(render_div(child, citation_state, mapping, depth + 1))

    return lines


def build_tex(root: etree._Element, fake_items: list[dict], bib_stem: str) -> tuple[str, list[dict]]:
    title = root.xpath("string(.//tei:titleStmt/tei:title)", namespaces=NS).strip()
    title = latex_escape(title or "Enhancing Chess Reinforcement Learning with Graph Representation")
    authors = root.xpath(".//tei:sourceDesc//tei:author", namespaces=NS)
    author_names = []
    for author in authors[:8]:
        name = normalize_text(" ".join(author.itertext())).strip()
        name = re.sub(r"\s+", " ", name)
        if name:
            author_names.append(latex_escape(name))
    author_block = r" \and ".join(author_names) if author_names else "Original authors"

    citation_state = {
        "used": 0,
        "seen_refs": 0,
        "keys": [make_key(item, index=i) for i, item in enumerate(fake_items, 1)],
        "items": fake_items,
        "selected_ref_ordinals": set(SELECTED_REF_ORDINALS) if SELECTED_REF_ORDINALS else None,
    }
    mapping = []

    body = root.find(".//tei:body", NS)
    body_lines = []
    for div in body.findall("tei:div", NS):
        body_lines.extend(render_div(div, citation_state, mapping, depth=0))

    preamble = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[margin=1in]{geometry}",
        r"\usepackage{natbib}",
        r"\usepackage{hyperref}",
        r"\usepackage{amsmath,amssymb}",
        r"\title{" + title + r"}",
        r"\author{" + author_block + r"}",
        r"\date{}",
        "",
        r"\begin{document}",
        r"\maketitle",
        "",
        (
            r"\noindent\textbf{Experiment 5 construction note.} "
            r"This LaTeX file was generated from the paper text and replaces the first "
            r"20 bibliography-reference locations with fabricated citations from "
            r"\texttt{exp5.json}. Each inserted citation contains exactly one BibTeX key."
        ),
    ]

    ending = [
        "",
        r"\bibliographystyle{unsrtnat}",
        r"\bibliography{" + bib_stem + r"}",
        r"\end{document}",
        "",
    ]

    if citation_state["used"] != len(fake_items):
        raise RuntimeError(
            f"Inserted {citation_state['used']} fake citations, expected {len(fake_items)}"
        )

    return "\n".join(preamble + body_lines + ending), mapping


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    fake_items = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    root = etree.fromstring(TEI_PATH.read_bytes())

    bib_stem = "exp5_fake"
    tex_text, mapping = build_tex(root, fake_items, bib_stem)
    bib_text = "\n\n".join(make_bib_entry(item) for item in fake_items) + "\n"

    (OUT_DIR / "exp5_chess_fake.tex").write_text(tex_text, encoding="utf-8")
    (OUT_DIR / "exp5_fake.bib").write_text(bib_text, encoding="utf-8")
    (OUT_DIR / "exp5_citation_mapping.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote {OUT_DIR / 'exp5_chess_fake.tex'}")
    print(f"Wrote {OUT_DIR / 'exp5_fake.bib'}")
    print(f"Wrote {OUT_DIR / 'exp5_citation_mapping.json'}")
    print(f"Inserted citations: {len(mapping)}")


if __name__ == "__main__":
    main()
