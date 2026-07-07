"""Verify whether candidate paper evidence supports a citation claim."""

import json
import time
from google import genai

NLI_PROMPT = """You are a strict but fair scientific evidence evaluator. Your task is to verify if the academic paper's abstract supports the given claim.

CLAIM (the assertion that this citation is supposed to support):
{claim}

PAPER:
Title: {title}
Year: {year}
Abstract: {abstract}

EVALUATION RULES:
1. Focus on the CORE TASK and ENTITIES. If the claim is about a specific subfield (e.g., Retrieval-Augmented Generation, Multi-hop queries), the paper MUST be about that same subfield. 
2. Sharing broad keywords (like "LLM" or "Machine Learning") is NOT enough. If the paper focuses on a fundamentally different task (e.g., optimization algorithms, gradient compression, hardware) than the claim, it is UNSUPPORTED.
3. Be flexible with academic paraphrasing. The paper does not need to use the exact same words as the claim, as long as the semantic meaning aligns.

Classify as exactly one of the following:
- SUPPORTED: The abstract clearly and directly proves the core assertion of the claim (allowing for academic paraphrasing).
- PARTIALLY_SUPPORTED: The abstract addresses the SAME core task as the claim, but only provides evidence for a subset of the claim's assertions.
- UNSUPPORTED: The abstract focuses on a fundamentally different topic, method, or task, OR explicitly contradicts the claim.
- UNCERTAIN: Cannot determine from the abstract alone.

Respond ONLY with valid JSON in this exact format (no markdown, no extra text):
{{"verdict": "SUPPORTED", "confidence": 0.85, "justification": "one sentence explaining your reasoning"}}

verdict must be exactly one of: SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, UNCERTAIN
confidence is a float between 0.0 and 1.0"""


def verify_one_candidate(
    claim: str,
    paper: dict,
    client,
    is_route_a: bool = False
) -> tuple[str, float, str]:
    """Return a semantic verdict, confidence, and short justification."""
    title = paper.get("title", "Unknown")
    abstract = (paper.get("abstract") or "").strip()
    year = paper.get("year", "Unknown")

    # A title match can repair metadata, but semantic support needs evidence text.
    if not abstract:
        return "UNCERTAIN", 0.0, "No abstract available for semantic verification."

    prompt = NLI_PROMPT.format(
        claim=claim,
        title=title,
        year=year,
        abstract=abstract[:1500]
    )

    try:
        response = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview",
                    contents=prompt
                )
                break
            except Exception as e:
                if "503" in str(e) and attempt < 2:
                    wait = (attempt + 1) * 10
                    print(f"    [Retry {attempt+1}] 503 error, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                raise e

        if response is None:
            return "UNCERTAIN", 0.0, "Verification failed: no response after retries."

        raw = response.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

        verdict = result.get("verdict", "UNCERTAIN")
        confidence = float(result.get("confidence", 0.0))
        justification = result.get("justification", "No justification provided.")

        # Normalize invalid model output into a conservative fallback.
        valid_verdicts = ("SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "UNCERTAIN")
        if verdict not in valid_verdicts:
            verdict = "UNCERTAIN"
        confidence = max(0.0, min(1.0, confidence))

        return verdict, confidence, justification

    except json.JSONDecodeError:
        raw_lower = response.text.lower()
        if "supported" in raw_lower and "partially" not in raw_lower:
            return "PARTIALLY_SUPPORTED", 0.5, \
                "Verification inconclusive (JSON parse error, text suggests support)."
        return "UNCERTAIN", 0.0, "Verification failed: invalid response format."

    except Exception as e:
        print(f"    [NLI ERROR] {e}")
        return "UNCERTAIN", 0.0, f"Verification failed: {str(e)[:100]}"


def rank_candidates(
    claim: str,
    candidates: list[dict],
    client,
    route: str
) -> list[tuple[dict, float, str]]:
    """Verify candidates and keep non-unsupported results by confidence."""
    is_route_a = route == "A"
    ranked = []

    for i, paper in enumerate(candidates):
        title = paper.get("title", "?")
        print(f"    [Verify {i+1}/{len(candidates)}] {title[:60]}...")

        verdict, confidence, justification = verify_one_candidate(
            claim, paper, client, is_route_a=is_route_a
        )
        print(f"    -> {verdict} ({confidence:.0%}): {justification[:80]}")

        if verdict != "UNSUPPORTED":
            ranked.append((paper, confidence, justification, verdict))

    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked

BATCH_NLI_PROMPT = """You are a scientific evidence evaluator.

CLAIM (the assertion that needs to be supported):
{claim}

Below are {n} candidate papers. For each paper, decide whether its abstract supports the claim.

{papers_block}

Respond ONLY with a valid JSON array, one object per paper, in this exact format:
[
  {{"index": 1, "verdict": "SUPPORTED", "confidence": 0.85, "justification": "one sentence"}},
  {{"index": 2, "verdict": "UNSUPPORTED", "confidence": 0.95, "justification": "one sentence"}},
  ...
]

verdict must be exactly one of: SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, UNCERTAIN
confidence is a float between 0.0 and 1.0
Return exactly {n} objects in the array, no markdown, no extra text."""


def rank_candidates_batch(
    claim: str,
    candidates: list[dict],
    client,
    max_candidates: int = 5
) -> list[dict]:
    """Batch-rank candidates and keep non-unsupported results."""
    if not candidates:
        return []

    papers = candidates[:max_candidates]
    VALID = ("SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "UNCERTAIN")

    blocks = []
    for i, p in enumerate(papers, 1):
        abstract = (p.get("abstract") or "").strip()[:800]
        if not abstract:
            abstract = "(no abstract available)"
        blocks.append(
            f"[{i}] Title: {p.get('title', 'Unknown')}\n"
            f"    Year: {p.get('year', 'N/A')}\n"
            f"    Abstract: {abstract}"
        )
    papers_block = "\n\n".join(blocks)

    prompt = BATCH_NLI_PROMPT.format(
        claim=claim,
        n=len(papers),
        papers_block=papers_block
    )

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=prompt
            )
            raw = response.text.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            results = json.loads(raw)

            scored = []
            for item in results:
                idx = item.get("index", 0) - 1
                if not (0 <= idx < len(papers)):
                    continue
                paper = dict(papers[idx])
                verdict = item.get("verdict", "UNCERTAIN")
                if verdict not in VALID:
                    verdict = "UNCERTAIN"
                confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0))))
                justification = item.get("justification", "")

                paper["_verdict"]       = verdict
                paper["_confidence"]    = confidence
                paper["_justification"] = justification
                scored.append(paper)

            scored = [p for p in scored if p["_verdict"] != "UNSUPPORTED"]
            scored.sort(key=lambda p: p["_confidence"], reverse=True)
            print(f"  [Batch NLI] {len(papers)} candidates -> {len(scored)} passed")
            return scored

        except json.JSONDecodeError:
            print(f"  [Batch NLI] JSON parse error on attempt {attempt+1}")
            if attempt < 2:
                time.sleep(5)
        except Exception as e:
            print(f"  [Batch NLI] Error on attempt {attempt+1}: {e}")
            if attempt < 2:
                time.sleep(5)

    return []
