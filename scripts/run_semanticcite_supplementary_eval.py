#!/usr/bin/env python3
"""
Small supplementary evaluation for the semantic verifier.

This script evaluates the verifier on a stratified sample from the
SemanticCite dataset. It is a component-level check: it does not run the full
PDF/reference pipeline. By default it uses only the abstract in SemanticCite
metadata, but it can also evaluate with SemanticCite reference snippets.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from dotenv import load_dotenv
from google import genai

ROOT = Path(__file__).resolve().parents[1]
RECOVERY_DIR = ROOT / "recovery"
sys.path.insert(0, str(RECOVERY_DIR))

from verifier import verify_one_candidate  # noqa: E402

DATASET_URL = (
    "https://huggingface.co/datasets/sebsigma/SemanticCite-Dataset/resolve/main/"
    "SemanticCite_dataset.json"
)
VALID_LABELS = ("SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "UNCERTAIN")

SNIPPET_NLI_PROMPT = """You are a strict but fair scientific evidence evaluator. Your task is to verify whether the provided evidence snippets from an academic paper support the given claim.

CLAIM (the assertion that this citation is supposed to support):
{claim}

PAPER:
Title: {title}
Year: {year}

EVIDENCE SNIPPETS:
{snippets}

EVALUATION RULES:
1. Evaluate only the evidence provided in the snippets. Do not assume support from outside knowledge.
2. Focus on the CORE TASK and ENTITIES. Sharing broad keywords is not enough if the evidence is about a different topic, method, or task.
3. Be flexible with academic paraphrasing. The snippets do not need to use the exact same words as the claim, as long as the semantic meaning aligns.

Classify as exactly one of the following:
- SUPPORTED: The snippets clearly and directly prove the core assertion of the claim.
- PARTIALLY_SUPPORTED: The snippets address the same core topic but only support part of the claim.
- UNSUPPORTED: The snippets focus on a different topic, method, or task, OR explicitly contradict the claim.
- UNCERTAIN: Cannot determine from the snippets alone.

Respond ONLY with valid JSON in this exact format (no markdown, no extra text):
{{"verdict": "SUPPORTED", "confidence": 0.85, "justification": "one sentence explaining your reasoning"}}

verdict must be exactly one of: SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, UNCERTAIN
confidence is a float between 0.0 and 1.0"""


def _download_dataset(cache_path: Path) -> list[dict]:
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(DATASET_URL, timeout=60) as response:
        raw = response.read()
    cache_path.write_bytes(raw)
    return json.loads(raw)


def _metadata_field(metadata: str, field: str) -> str:
    pattern = rf"{re.escape(field)}:\s*(.*?)(?=\n[A-Z][A-Za-z ]+:\s|\Z)"
    match = re.search(pattern, metadata or "", flags=re.S)
    if not match:
        return ""
    return match.group(1).strip()


def _paper_from_item(item: dict) -> dict:
    metadata = item.get("input", {}).get("ref_metadata", "")
    title = _metadata_field(metadata, "Title")
    year = _metadata_field(metadata, "Year")
    abstract = _metadata_field(metadata, "Abstract")

    return {
        "title": title or item.get("citation_title") or "Unknown",
        "year": year or item.get("citation_year") or "Unknown",
        "abstract": abstract,
        "url": item.get("citation_url", ""),
    }


def _snippets_from_item(item: dict, max_chars: int = 2500) -> str:
    snippets = item.get("input", {}).get("ref_snippets", [])
    if isinstance(snippets, str):
        return snippets[:max_chars]
    parts = []
    for snippet in snippets or []:
        if isinstance(snippet, dict):
            text = (snippet.get("text") or "").strip()
        else:
            text = str(snippet).strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)[:max_chars]


def _stratified_sample(
    items: list[dict],
    per_label: int,
    seed: int,
    evidence_mode: str,
) -> list[dict]:
    rng = random.Random(seed)
    by_label: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        label = item.get("output", {}).get("classification", "")
        if label in VALID_LABELS:
            paper = _paper_from_item(item)
            claim = item.get("input", {}).get("claim", "")
            has_evidence = bool(paper.get("abstract"))
            if evidence_mode == "snippets":
                has_evidence = bool(_snippets_from_item(item))
            if claim and has_evidence:
                by_label[label].append(item)

    sample = []
    for label in VALID_LABELS:
        bucket = by_label[label]
        rng.shuffle(bucket)
        sample.extend(bucket[:per_label])
    rng.shuffle(sample)
    return sample


def _binary(label: str) -> str:
    if label in ("SUPPORTED", "PARTIALLY_SUPPORTED"):
        return "SUPPORTED_OR_PARTIAL"
    return "UNSUPPORTED_OR_UNCERTAIN"


def _summarize(results: list[dict]) -> dict:
    evaluated = [r for r in results if not r.get("failed")]
    total = len(evaluated)
    exact = sum(1 for r in evaluated if r["gold"] == r["prediction"])
    binary = sum(1 for r in evaluated if _binary(r["gold"]) == _binary(r["prediction"]))

    gold_counts = Counter(r["gold"] for r in evaluated)
    pred_counts = Counter(r["prediction"] for r in evaluated)
    confusion: dict[str, dict[str, int]] = {
        g: {p: 0 for p in VALID_LABELS} for g in VALID_LABELS
    }
    for r in evaluated:
        confusion[r["gold"]][r["prediction"]] += 1

    return {
        "total": total,
        "attempted": len(results),
        "failed": len(results) - total,
        "exact_accuracy": exact / total if total else 0.0,
        "binary_accuracy": binary / total if total else 0.0,
        "gold_counts": dict(gold_counts),
        "prediction_counts": dict(pred_counts),
        "confusion_matrix": confusion,
    }


def _write_json_output(output_path: Path, args, summary: dict, results: list[dict]) -> None:
    output = {
        "dataset": "sebsigma/SemanticCite-Dataset",
        "dataset_url": DATASET_URL,
        "evaluation_note": (
            f"Component-level evaluation using {args.evidence_mode}; SemanticCite "
            "labels were produced for claim-source pairs with richer source evidence."
        ),
        "evidence_mode": args.evidence_mode,
        "per_label": args.per_label,
        "seed": args.seed,
        "summary": summary,
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


def _verify_with_snippets(claim: str, paper: dict, snippets: str, client) -> tuple[str, float, str]:
    if not snippets.strip():
        return "UNCERTAIN", 0.0, "No evidence snippets available for semantic verification."

    prompt = SNIPPET_NLI_PROMPT.format(
        claim=claim,
        title=paper.get("title", "Unknown"),
        year=paper.get("year", "Unknown"),
        snippets=snippets,
    )

    try:
        response = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview",
                    contents=prompt,
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

        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            retry_prompt = prompt + "\n\nYour previous response was not valid JSON. Return only the required JSON object."
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=retry_prompt,
            )
            raw = response.text.strip().replace("```json", "").replace("```", "").strip()
            result = json.loads(raw)

        verdict = result.get("verdict", "UNCERTAIN")
        if verdict not in VALID_LABELS:
            verdict = "UNCERTAIN"
        confidence = max(0.0, min(1.0, float(result.get("confidence", 0.0))))
        justification = result.get("justification", "No justification provided.")
        return verdict, confidence, justification

    except json.JSONDecodeError:
        return "UNCERTAIN", 0.0, "Verification failed: invalid response format."
    except Exception as e:
        print(f"    [NLI ERROR] {e}")
        return "UNCERTAIN", 0.0, f"Verification failed: {str(e)[:100]}"


def _write_report(path: Path, summary: dict, results: list[dict], per_label: int, evidence_mode: str) -> None:
    evidence_label = "abstracts" if evidence_mode == "abstract" else "SemanticCite reference snippets"
    lines = [
        "# SemanticCite Supplementary Evaluation",
        "",
        f"This is a component-level evaluation of the semantic verifier using {evidence_label}.",
        "It uses SemanticCite claim-source labels as external labels, but evaluates only",
        "the selected evidence field, not the full reference PDF.",
        "",
        f"Sample: {summary['total']} items ({per_label} per label when available)",
        f"Exact four-class accuracy: {summary['exact_accuracy']:.1%}",
        f"Binary supported-vs-unsupported accuracy: {summary['binary_accuracy']:.1%}",
        "",
        "## Label Counts",
        "",
        f"Gold: {summary['gold_counts']}",
        f"Predicted: {summary['prediction_counts']}",
        "",
        "## Confusion Matrix",
        "",
        "| Gold \\ Pred | SUPPORTED | PARTIAL | UNSUPPORTED | UNCERTAIN |",
        "|---|---:|---:|---:|---:|",
    ]
    for gold in VALID_LABELS:
        row = summary["confusion_matrix"][gold]
        lines.append(
            f"| {gold} | {row['SUPPORTED']} | {row['PARTIALLY_SUPPORTED']} | "
            f"{row['UNSUPPORTED']} | {row['UNCERTAIN']} |"
        )

    lines += ["", "## Mismatches", ""]
    mismatches = [
        r for r in results
        if not r.get("failed") and r["gold"] != r["prediction"]
    ]
    if not mismatches:
        lines.append("No exact-label mismatches in this sample.")
    for r in mismatches[:20]:
        lines += [
            f"- `{r['gold']}` -> `{r['prediction']}`: {r['title']}",
            f"  Claim: {r['claim']}",
            f"  Reason: {r['justification']}",
        ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-label", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--cache",
        default=str(ROOT / "recovery" / "semanticcite_dataset_cache.json"),
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "recovery" / "semanticcite_supplementary_eval.json"),
    )
    parser.add_argument(
        "--report",
        default=str(ROOT / "recovery" / "semanticcite_supplementary_eval.md"),
    )
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument(
        "--evidence-mode",
        choices=("abstract", "snippets"),
        default="abstract",
        help="Use source abstracts or SemanticCite reference snippets as evidence.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse successful rows already present in the output JSON and only rerun failed/missing rows.",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env or environment.")

    items = _download_dataset(Path(args.cache))
    sample = _stratified_sample(
        items,
        per_label=args.per_label,
        seed=args.seed,
        evidence_mode=args.evidence_mode,
    )
    client = genai.Client(api_key=api_key)
    output_path = Path(args.output)

    previous_by_index = {}
    if args.resume and output_path.exists():
        previous = json.loads(output_path.read_text(encoding="utf-8"))
        previous_by_index = {
            r.get("index"): r
            for r in previous.get("results", [])
            if r.get("index") is not None and not r.get("failed")
        }
        print(f"[Resume] Reusing {len(previous_by_index)} successful previous rows.")

    results = []
    for i, item in enumerate(sample, 1):
        claim = item["input"]["claim"]
        gold = item["output"]["classification"]
        paper = _paper_from_item(item)
        if i in previous_by_index:
            print(f"[{i}/{len(sample)}] Reuse | {gold} | {paper['title'][:70]}")
            results.append(previous_by_index[i])
            continue

        print(f"[{i}/{len(sample)}] {gold} | {paper['title'][:70]}")
        snippets = _snippets_from_item(item)
        if args.evidence_mode == "snippets":
            prediction, confidence, justification = _verify_with_snippets(
                claim, paper, snippets, client
            )
        else:
            prediction, confidence, justification = verify_one_candidate(
                claim, paper, client, is_route_a=False
            )
        failed = justification.lower().startswith("verification failed")
        results.append({
            "index": i,
            "gold": gold,
            "prediction": prediction,
            "confidence": confidence,
            "failed": failed,
            "claim": claim,
            "title": paper["title"],
            "year": paper["year"],
            "url": paper.get("url", ""),
            "abstract": paper["abstract"],
            "snippets": snippets,
            "justification": justification,
            "semanticcite_reasoning": item.get("output", {}).get("reasoning", ""),
        })
        checkpoint_summary = _summarize(results)
        if checkpoint_summary["total"] > 0:
            _write_json_output(output_path, args, checkpoint_summary, results)
        if args.sleep:
            time.sleep(args.sleep)

    summary = _summarize(results)
    if summary["total"] == 0 and output_path.exists():
        raise RuntimeError(
            f"No successful evaluations; preserving existing output at {output_path}"
        )
    _write_json_output(output_path, args, summary, results)
    _write_report(Path(args.report), summary, results, args.per_label, args.evidence_mode)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Wrote {output_path}")
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
