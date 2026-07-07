"""Manual smoke tests for the recovery pipeline modules."""

import sys
import json
import os

def test_grobid(pdf_path: str):
    print("\n" + "="*50)
    print("TEST 1: Grobid fulltext extraction")
    print("="*50)

    from grobid_fulltext import extract_fulltext
    from lxml import etree

    NAMESPACE = {"tei": "http://www.tei-c.org/ns/1.0"}
    raw_text, xml_root = extract_fulltext(pdf_path)

    print(f"raw_text length: {len(raw_text)} chars")
    print(f"raw_text preview: {raw_text[:200]}...")

    refs = xml_root.findall(".//tei:ref[@type='bibr']", NAMESPACE)
    print(f"Found {len(refs)} <ref type='bibr'> tags in XML")

    if refs:
        sample_ref = refs[0]
        ref_text = "".join(sample_ref.itertext()).strip()
        ref_target = sample_ref.get("target", "none")
        print(f"  Sample ref: text='{ref_text}', target='{ref_target}'")
    else:
        print("  WARNING: No <ref type='bibr'> tags found!")

    bib_structs = xml_root.findall(".//tei:listBibl/tei:biblStruct", NAMESPACE)
    print(f"Found {len(bib_structs)} biblStruct entries in reference list")

    return raw_text, xml_root


def test_context_extraction(xml_root, raw_text, title: str, gemini_api_key: str):
    print("\n" + "="*50)
    print("TEST 2: Context location + Claim extraction")
    print("="*50)
    print(f"Target title: {title}")

    from google import genai
    from context_extractor import get_claim_for_citation

    client = genai.Client(api_key=gemini_api_key)

    claim, confidence, context = get_claim_for_citation(
        title=title,
        xml_root=xml_root,
        raw_text=raw_text,
        client=client
    )

    print(f"\nContext found: {bool(context)}")
    if context:
        print(f"  Context ({len(context)} chars): {context[:300]}...")
    print(f"\nClaim: '{claim}'")
    print(f"  Confidence: {confidence}")

    if confidence < 0.5:
        print("  WARNING: Low confidence claim")

    return claim, confidence


def test_retrieval(title: str, claim: str, verdict: str):
    print("\n" + "="*50)
    print("TEST 3: Retrieval")
    print("="*50)
    print(f"  verdict: {verdict}")
    print(f"  title:   {title[:60]}")
    print(f"  claim:   {claim[:60]}")

    from retrieval import dispatch_retrieval

    candidates, route = dispatch_retrieval(
        verdict=verdict,
        claim=claim,
        raw_title=title,
        raw_year=None
    )

    print(f"\nRoute: {route}")
    print(f"Candidates: {len(candidates)}")
    for i, p in enumerate(candidates[:3]):
        has_abstract = bool(p.get("abstract"))
        print(f"  [{i+1}] {p.get('title', '?')[:70]} ({p.get('year')}) "
              f"[abstract: {'yes' if has_abstract else 'no'}]")

    if not candidates:
        print("  No candidates found")
        if verdict == "LEVEL_1_REAL":
            print("  -> Check if S2 has this paper indexed")
        elif verdict == "LEVEL_2_FLAWED":
            print("  -> CrossRef and S2 both failed")
        else:
            print("  -> S2 semantic search returned nothing, try a different claim")

    return candidates, route


def test_nli(claim: str, candidates: list, gemini_api_key: str, route: str):
    print("\n" + "="*50)
    print("TEST 4: Semantic Support Verification")
    print("="*50)

    from google import genai
    from verifier import rank_candidates

    client = genai.Client(api_key=gemini_api_key)

    ranked = rank_candidates(claim, candidates[:3], client, route)

    print(f"\nVerified {len(ranked)} papers passed (not UNSUPPORTED):")
    for paper, conf, just, verdict in ranked:
        print(f"  [{verdict}] [{conf:.0%}] {paper.get('title', '?')[:70]}")
        print(f"    -> {just}")

    if not ranked:
        print("  All candidates returned UNSUPPORTED")

    return ranked


if __name__ == "__main__":

    PDF_PATH    = "exp3.pdf"
    GEMINI_KEY  = os.getenv("GEMINI_API_KEY")
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in .env or the environment.")

    TEST_TITLE  = "A method for calibrating false-match rates in record linkage"
    TEST_VERDICT = "LEVEL_2_FLAWED"   # LEVEL_1_REAL / LEVEL_2_FLAWED / LEVEL_3_FAKE

    from rapidfuzz import fuzz
    from lxml import etree
    NAMESPACE = {"tei": "http://www.tei-c.org/ns/1.0"}

    # Test 1
    raw_text, xml_root = test_grobid(PDF_PATH)

    bib_structs = xml_root.findall(".//tei:listBibl/tei:biblStruct", NAMESPACE)
    print(f"\n  DEBUG: biblStruct fuzzy scores for TEST_TITLE:")
    for bib in bib_structs:
        title_els = bib.findall(".//tei:title", NAMESPACE)
        for t_el in title_els:
            bib_title = "".join(t_el.itertext()).strip()
            score = fuzz.ratio(TEST_TITLE.lower(), bib_title.lower())
            xml_id = bib.get("{http://www.w3.org/XML/1998/namespace}id")
            if score > 30:
                print(f"    [{xml_id}] score={score:5.1f} | {bib_title[:70]}")

    # Test 2
    claim, conf = test_context_extraction(xml_root, raw_text, TEST_TITLE, GEMINI_KEY)

    if not claim or conf < 0.3:
        print("\nStopping: claim extraction failed or low confidence")
        print("  -> Fix TEST 2 before proceeding")
        sys.exit(0)

    # Test 3
    candidates, route = test_retrieval(TEST_TITLE, claim, TEST_VERDICT)

    if not candidates:
        print("\nStopping: no candidates found")
        print("  -> Fix TEST 3 before proceeding")
        sys.exit(0)

    # Test 4
    ranked = test_nli(claim, candidates, GEMINI_KEY, route)

    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"  Title:   {TEST_TITLE[:60]}")
    print(f"  Verdict: {TEST_VERDICT}")
    print(f"  Claim:   {claim}")
    print(f"  Route:   {route}")
    if ranked:
        best = ranked[0]
        print(f"  Best:    {best[0].get('title', '?')[:60]}")
        print(f"  Support: {best[3]} ({best[1]:.0%})")
    else:
        print("  Result:  No supporting paper found")
    print("="*50)
