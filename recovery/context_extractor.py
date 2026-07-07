"""Locate citation context and extract the claim supported by a reference."""

import re
from google import genai
from lxml import etree

NAMESPACE = {"tei": "http://www.tei-c.org/ns/1.0"}

def find_ref_id_by_title(xml_root: etree._Element, title: str) -> str | None:
    """Find the Grobid bibliography id that best matches a citation title."""
    from rapidfuzz import fuzz

    bib_structs = xml_root.findall(".//tei:listBibl/tei:biblStruct", NAMESPACE)
    best_id = None
    best_score = 0

    for bib in bib_structs:
        title_els = bib.findall(".//tei:title", NAMESPACE)
        for t_el in title_els:
            bib_title = "".join(t_el.itertext()).strip()
            score = fuzz.ratio(title.lower(), bib_title.lower())
            if score > best_score:
                best_score = score
                xml_id = bib.get("{http://www.w3.org/XML/1998/namespace}id")
                best_id = xml_id

    if best_score >= 85:
        return best_id

    return None


def locate_context_by_ref_id(
    xml_root: etree._Element,
    ref_id: str,
    before_sentences: int = 2,
    after_sentences: int = 1
) -> str | None:
    target = f"#{ref_id}"

    # Prefer sentence-level TEI nodes when GROBID provides them.
    for s_el in xml_root.findall(".//tei:body//tei:s", NAMESPACE):
        refs_in_s = s_el.findall(".//tei:ref[@type='bibr']", NAMESPACE)
        targets_in_s = [r.get("target", "") for r in refs_in_s]
        if target in targets_in_s:
            return " ".join(s_el.itertext()).strip()

    for p_el in xml_root.findall(".//tei:body//tei:p", NAMESPACE):
        refs_in_p = p_el.findall(".//tei:ref[@type='bibr']", NAMESPACE)
        targets_in_p = [r.get("target", "") for r in refs_in_p]
        if target in targets_in_p:
            full_text = " ".join(p_el.itertext()).strip()
            sentences = re.split(r'(?<=[.!?])\s+', full_text)
            for i, sent in enumerate(sentences):
                ref_texts = [
                    "".join(r.itertext()).strip()
                    for r in refs_in_p
                    if r.get("target") == target
                ]
                for ref_text in ref_texts:
                    if ref_text in sent:
                        start = max(0, i - before_sentences)
                        end = min(len(sentences), i + after_sentences + 1)
                        return " ".join(sentences[start:end])
            return full_text

    return None


def _trim_paragraph(paragraph: str, before: int, after: int) -> str:
    """Trim a paragraph to a small sentence window."""
    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
    total = before + after + 1
    if len(sentences) <= total:
        return paragraph
    return " ".join(sentences[:total])


def locate_context_from_text(
    raw_text: str,
    title: str,
    before: int = 2,
    after: int = 1
) -> str | None:
    """Fallback text search when XML reference matching fails."""
    keywords = title.split()[:4]
    pattern = re.compile(re.escape(" ".join(keywords)), re.IGNORECASE)

    sentences = re.split(r'(?<=[.!?])\s+', raw_text)
    for i, sent in enumerate(sentences):
        if pattern.search(sent):
            start = max(0, i - before)
            end = min(len(sentences), i + after + 1)
            return " ".join(sentences[start:end])

    return None


CLAIM_PROMPT = """You are a strict and precise scientific claim extractor.

Below is a text passage from an academic paper. It contains a citation marker {ref_marker}.

PASSAGE:
{context}

Task: Locate the citation marker {ref_marker} within the PASSAGE. Read the specific sentence containing it (and the immediately surrounding context). Extract ONLY the specific scientific assertion, technical method, or factual claim that the author is using {ref_marker} to support.

CRITICAL RULES:
1. STRICT LOCALITY: You MUST extract the claim STRICTLY based on the semantic meaning of the sentence containing {ref_marker}. DO NOT guess or infer what the cited paper is about.
2. NO BIBLIOGRAPHY: If the passage shows that {ref_marker} is just an entry in a reference list or bibliography (e.g., "[1] Author, Title, Journal, Year"), you MUST output exactly: UNCERTAIN
3. Output ONLY a concise search query (10-25 words) representing the core technical claim.
4. Write it as KEYWORDS (e.g., "retrieval augmented generation mitigate hallucination multi-hop"), NOT a full grammatical sentence.
5. Do NOT include phrases like "The authors claim", "studies show", or mention any author names.
6. If the claim cannot be determined from the surrounding text, output exactly: UNCERTAIN

Output:"""


def extract_claim(context, title, ref_marker, client) -> tuple[str, float]:
    prompt = CLAIM_PROMPT.format(
        ref_marker=ref_marker,
        title=title,
        context=context[:2000]
    )
    """Return the extracted claim and a simple confidence score."""
    try:
        prompt = CLAIM_PROMPT.format(ref_marker=ref_marker, title=title, context=context[:2000])
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt
        )
        claim = response.text.strip()

        if not claim or claim == "UNCERTAIN":
            return "UNCERTAIN", 0.5

        if len(claim.split()) < 4:
            return claim, 0.4

        if title[:20].lower() in claim.lower():
            return claim, 0.6

        return claim, 1.0

    except Exception as e:
        print(f"  [Claim extraction ERROR] {e}")
        return "", 0.0


def get_claim_for_citation(title, xml_root, raw_text, client):
    ref_id = find_ref_id_by_title(xml_root, title)
    
    ref_marker = None
    if ref_id:
        target = f"#{ref_id}"
        for r in xml_root.findall(".//tei:body//tei:ref[@type='bibr']", NAMESPACE):
            if r.get("target") == target:
                ref_marker = "".join(r.itertext()).strip()
                break
    
    ref_marker = ref_marker or title[:20]
    
    context = locate_context_by_ref_id(xml_root, ref_id) if ref_id else None
    if not context:
        context = locate_context_from_text(raw_text, title)
    if not context:
        return "", 0.0, ""

    claim, confidence = extract_claim(context, title, ref_marker, client)
    return claim, confidence, context