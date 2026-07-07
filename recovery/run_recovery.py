"""Batch-run the citation recovery pipeline over verifier results."""

import json
import time
import argparse
import os
from datetime import datetime
from pathlib import Path
from recovery_module import RecoveryModule

VALID_VERDICTS = ("LEVEL_1_PERFECT", "LEVEL_2_FLAWED", "LEVEL_3_FAKE")


def _get_clean_verdict(citation: dict) -> str:
    verdict = citation.get("clean_verdict")
    if verdict:
        return verdict

    system_result = citation.get("system_result")
    if isinstance(system_result, list) and system_result:
        return system_result[0]
    if isinstance(system_result, str):
        return system_result

    return ""


def _normalize_citation(citation: dict) -> dict:
    verdict = _get_clean_verdict(citation)
    if verdict and not citation.get("clean_verdict"):
        citation["clean_verdict"] = verdict

    system_result = citation.get("system_result")
    if isinstance(system_result, list) and len(system_result) > 1 and not citation.get("raw_agent_response"):
        citation["raw_agent_response"] = system_result[1]

    return citation


def _load_citations(results_path: str) -> list[dict]:
    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return [_normalize_citation(c) for c in data]
    if isinstance(data, dict) and "detailed_results" in data:
        return [_normalize_citation(c) for c in data["detailed_results"]]
    return [_normalize_citation(data)]


def _is_supported(r: dict) -> bool:
    return (r.get("semantic_verdict") in ("SUPPORTED", "PARTIALLY_SUPPORTED")
            and r.get("semantic_confidence", 0) >= 0.5)


def _build_summary_lines(results: list[dict], pdf_path: str, results_path: str) -> list[str]:
    """Build summary lines for console and report output."""
    total  = len(results)
    failed = sum(1 for r in results if r.get("final_status") == "failed")

    l1_all = [r for r in results if r.get("input_verdict") == "LEVEL_1_PERFECT"]
    l2_all = [r for r in results if r.get("input_verdict") == "LEVEL_2_FLAWED"]
    l3_all = [r for r in results if r.get("input_verdict") == "LEVEL_3_FAKE"]

    lines = []
    lines += [
        "=" * 60,
        "PIPELINE SUMMARY",
        f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"PDF       : {pdf_path}",
        f"Results   : {results_path}",
        f"Total     : {total}  (L1={len(l1_all)}, L2={len(l2_all)}, L3={len(l3_all)})",
        "=" * 60,
    ]

    if l2_all:
        n             = len(l2_all)
        repaired      = sum(1 for r in l2_all if r.get("layer2_status") == "repaired")
        repair_failed = sum(1 for r in l2_all if r.get("layer2_status") == "repair_failed")
        not_reached   = sum(1 for r in l2_all if r.get("final_status") == "failed")
        lines += [
            "",
            f"Layer 2 - Repair Rate  (L2 n={n})",
            f"  Repaired:                    {repaired}/{n}  ({repaired/n:.0%})",
            f"  Repair failed (treat as L3):  {repair_failed}/{n}  ({repair_failed/n:.0%})",
            f"  Not reached (pipeline fail): {not_reached}/{n}  ({not_reached/n:.0%})",
        ]

    supported_all = sum(1 for r in results if _is_supported(r))
    not_sup_all   = total - supported_all
    lines += [
        "",
        f"Layer 3 - Semantic Support Rate  (all n={total})",
        f"  Supported (S + PS, conf>=0.5):  {supported_all}/{total}  ({supported_all/total:.0%})",
        f"  Not supported / uncertain:     {not_sup_all}/{total}  ({not_sup_all/total:.0%})",
        f"    of which pipeline failed:    {failed}/{total}  ({failed/total:.0%})",
    ]
    breakdown = []
    if l1_all:
        l1_sup = sum(1 for r in l1_all if _is_supported(r))
        breakdown.append(f"L1: {l1_sup}/{len(l1_all)} ({l1_sup/len(l1_all):.0%})")
    if l2_all:
        l2_sup = sum(1 for r in l2_all if _is_supported(r))
        breakdown.append(f"L2: {l2_sup}/{len(l2_all)} ({l2_sup/len(l2_all):.0%})")
    if l3_all:
        l3_sup = sum(1 for r in l3_all if _is_supported(r))
        breakdown.append(f"L3: {l3_sup}/{len(l3_all)} ({l3_sup/len(l3_all):.0%})")
    if breakdown:
        lines.append("  By level:  " + "    ".join(breakdown))

    not_supported = [r for r in results if not _is_supported(r)]
    l4_verified   = [r for r in not_supported
                     if r.get("layer4_status") in ("retrieved", "partial")]
    l4_unverified = [r for r in not_supported
                     if r.get("layer4_status") == "unverified"]
    l4_found      = l4_verified + l4_unverified
    n_ns = len(not_supported)
    if n_ns:
        lines += [
            "",
            f"Layer 4 - Alternative Retrieval Rate  (not-supported n={n_ns})",
            f"  Retrieved candidates:          {len(l4_found)}/{n_ns}  ({len(l4_found)/n_ns:.0%})",
            f"  Verified support (R+partial):  {len(l4_verified)}/{n_ns}  ({len(l4_verified)/n_ns:.0%})",
            f"  Retrieved but unverified:      {len(l4_unverified)}/{n_ns}  ({len(l4_unverified)/n_ns:.0%})",
            f"  Not retrieved / not reached:   {n_ns-len(l4_found)}/{n_ns}  ({(n_ns-len(l4_found))/n_ns:.0%})",
        ]

    status_counts: dict[str, int] = {}
    for r in results:
        s = r.get("final_status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
    lines += ["", f"Final Status Breakdown  (total={total})"]
    for s, c in sorted(status_counts.items()):
        lines.append(f"  {s}: {c}")

    return lines


def _save_report(
    results: list[dict],
    pdf_path: str,
    results_path: str,
    report_path: str
) -> None:
    """Write summary and detailed reports to a text file."""
    summary_lines = _build_summary_lines(results, pdf_path, results_path)

    detail_lines = [
        "",
        "=" * 60,
        "DETAILED REPORTS",
        "=" * 60,
    ]
    for r in results:
        detail_lines.append("")
        detail_lines.append(r.get("report", "[No report]"))
        detail_lines.append("-" * 40)

    all_lines = summary_lines + detail_lines
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines))

    print(f"Report saved to: {report_path}")


def run_pipeline(pdf_path: str, results_path: str) -> None:
    citations  = _load_citations(results_path)
    to_process = [c for c in citations
                  if _get_clean_verdict(c) in VALID_VERDICTS]

    counts = {v: sum(1 for c in to_process if _get_clean_verdict(c) == v)
              for v in VALID_VERDICTS}

    print(f"Total citations:   {len(citations)}")
    print(f"To process:        {len(to_process)}")
    for v, n in counts.items():
        print(f"  {v}: {n}")
    print(f"PDF: {pdf_path}\n")

    if not to_process:
        print("Nothing to process.")
        return

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env or the environment.")

    module  = RecoveryModule(gemini_api_key=gemini_key, pdf_path=pdf_path)
    results = []

    for i, citation in enumerate(to_process):
        title   = citation.get("title", "")[:60]
        verdict = citation.get("clean_verdict", "")
        print(f"\n[{i+1}/{len(to_process)}] {verdict} | {title}...")

        result = module.process(citation)
        results.append(result)
        citation["pipeline_result"] = result

        if i < len(to_process) - 1:
            time.sleep(5)

    for line in _build_summary_lines(results, pdf_path, results_path):
        print(line)

    stem        = Path(results_path).stem
    json_path   = stem + "_pipeline.json"
    report_path = stem + "_pipeline_report.txt"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(citations, f, ensure_ascii=False, indent=2)
    print(f"\nJSON  saved to: {json_path}")

    _save_report(results, pdf_path, results_path, report_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf",     required=True)
    parser.add_argument("--results", required=True)
    args = parser.parse_args()
    run_pipeline(args.pdf, args.results)
