"""Four-layer citation recovery pipeline."""

import re
from dataclasses import dataclass, field, asdict
from typing import Literal

from google import genai

from grobid_fulltext import extract_fulltext
from context_extractor import get_claim_for_citation
from retrieval import (
    fetch_abstract_for_level1,
    route_a_all,
    route_a_by_doi,
    route_b_multi_source,
    route_b_semantic_scholar,
)
from verifier import rank_candidates, rank_candidates_batch, verify_one_candidate


@dataclass
class PipelineResult:
    original_title: str
    input_verdict: str

    claim: str
    claim_confidence: float
    context_used: str

    layer2_status: Literal["repaired", "repair_failed", "skipped"]
    canonical_paper: dict | None

    semantic_verdict: str
    semantic_confidence: float
    semantic_justification: str
    paper_used_for_semantic: dict | None

    layer4_status: Literal["retrieved", "partial", "unverified", "not_retrieved", "skipped"]
    alternative_papers: list[dict]  # ranked candidates, each has _verdict/_confidence/_justification

    final_status: str
    report: str


def _extract_year(text: str) -> int | None:
    matches = re.findall(r'\b(19|20)\d{2}\b', text)
    return min(int(m) for m in matches) if matches else None


def _extract_title_from_response(text: str) -> str | None:
    EXCLUDE = ("VERDICT", "LEVEL", "extracting", "the title", "raw_text",
               "raw text", "By extracting", "However")

    patterns = [
        r'title(?:\s+(?:is|:|should be|provided is))\s+["“]([^"”]{15,})["”]',
        r'full title:\s*["“]?([^"”\n]{15,})["”]?',
        r'\*\*"([^"]+)"\*\*',
        r'\*\*([^*]{15,})\*\*',
        r'"([^"]{15,})"',
    ]

    for pattern in patterns:
        for match in re.findall(pattern, text):
            m = match.strip().rstrip(".,:;")
            if len(m) < 15:
                continue
            if any(ex.lower() in m.lower() for ex in EXCLUDE):
                continue
            if m[0].islower() or m.endswith(('.', ',', ':')):
                continue
            return m
    return None


def _extract_doi_from_response(text: str) -> str | None:
    patterns = [
        r'https?://(?:dx\.)?doi\.org/([^\s\])}>,;]+)',
        r'\bdoi[:\s]+(10\.\d{4,9}/[^\s\])}>,;]+)',
        r'\b(10\.\d{4,9}/[^\s\])}>,;]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text or "", flags=re.I)
        if match:
            return match.group(1).strip().rstrip(".,")
    return None


def _is_supported(verdict: str, confidence: float) -> bool:
    return verdict in ("SUPPORTED", "PARTIALLY_SUPPORTED") and confidence >= 0.5


def _has_retrievable_claim(claim: str, confidence: float) -> bool:
    if confidence <= 0.5:
        return False
    return bool(claim and claim.strip().upper() != "UNCERTAIN")


class RecoveryModule:
    def __init__(self, gemini_api_key: str, pdf_path: str):
        self.client = genai.Client(api_key=gemini_api_key)
        print("[Pipeline] Extracting fulltext via Grobid...")
        self.raw_text, self.xml_root = extract_fulltext(pdf_path)
        print(f"[Pipeline] Fulltext ready ({len(self.raw_text)} chars)")

    def process(self, citation: dict) -> dict:
        """Run the full pipeline for one citation."""
        title   = citation.get("title", "")
        verdict = citation.get("clean_verdict", "")

        # Recover a usable title when GROBID produced a placeholder.
        if title == "Unknown Title":
            extracted = _extract_title_from_response(
                citation.get("raw_agent_response", "")
            )
            if extracted:
                print(f"  [Title] Recovered from response: {extracted[:60]}")
                title = extracted
            else:
                return self._make_failed(title, verdict, "Unknown Title, cannot extract")

        if verdict not in ("LEVEL_1_PERFECT", "LEVEL_2_FLAWED", "LEVEL_3_FAKE"):
            return self._make_failed(title, verdict, f"Unknown verdict: {verdict}")

        print(f"\n{'='*60}")
        print(f"[Pipeline] {verdict} | {title[:70]}")

        # Every layer needs a citation-local claim.
        print("\n[Claim] Locating citation and extracting claim...")
        claim, claim_conf, context = get_claim_for_citation(
            title=title,
            xml_root=self.xml_root,
            raw_text=self.raw_text,
            client=self.client
        )
        print(f"  claim='{claim}' conf={claim_conf}")

        if not claim or claim_conf == 0.0:
            # Fallback: use title as claim so Layer 3/4 can still run
            print(f"  [Claim] Context not found, using title as fallback claim")
            claim = title
            claim_conf = 0.1
            context = ""

        layer2_status   = "skipped"
        canonical_paper = None
        effective_verdict = verdict

        if verdict == "LEVEL_2_FLAWED":
            layer2_status, canonical_paper = self._layer2_repair(citation, title)
            if layer2_status == "repair_failed":
                effective_verdict = "LEVEL_3_FAKE"
                print("  [Layer 2] Repair failed -> treating as LEVEL_3_FAKE")

        print("\n[Layer 3] Semantic check...")
        sem_verdict, sem_conf, sem_just, paper_for_sem = self._layer3_semantic(
            claim=claim,
            verdict=verdict,
            effective_verdict=effective_verdict,
            canonical_paper=canonical_paper,
            raw_title=title,
            raw_year=_extract_year(citation.get("raw_agent_response", "") or "")
        )
        print(f"  semantic={sem_verdict} ({sem_conf:.0%})")

        layer4_status     = "skipped"
        alternative_papers = []

        if not _is_supported(sem_verdict, sem_conf):
            if not _has_retrievable_claim(claim, claim_conf):
                print("\n[Layer 4] Skipped: no reliable claim for retrieval")
                layer4_status = "not_retrieved"
            else:
                print("\n[Layer 4] Not supported -> retrieving alternatives...")
                layer4_status, alternative_papers = self._layer4_retrieval(claim)

        final_status = self._final_status(
            verdict, layer2_status, sem_verdict, sem_conf, layer4_status
        )
        report = self._build_report(
            title, verdict, claim,
            layer2_status, canonical_paper,
            sem_verdict, sem_conf, sem_just, paper_for_sem,
            layer4_status, alternative_papers,
            final_status
        )

        result = PipelineResult(
            original_title=title,
            input_verdict=verdict,
            claim=claim,
            claim_confidence=claim_conf,
            context_used=context,
            layer2_status=layer2_status,
            canonical_paper=canonical_paper,
            semantic_verdict=sem_verdict,
            semantic_confidence=sem_conf,
            semantic_justification=sem_just,
            paper_used_for_semantic=paper_for_sem,
            layer4_status=layer4_status,
            alternative_papers=alternative_papers,
            final_status=final_status,
            report=report
        )
        print(f"\n[Pipeline] Done -> {final_status}")
        return asdict(result)
    def _layer2_repair(self, citation: dict, title: str) -> tuple[str, dict | None]:
        """Repair flawed metadata and enrich the canonical paper when possible."""
        raw_response = citation.get("raw_agent_response", "") or ""

        doi = _extract_doi_from_response(raw_response)
        if doi:
            print(f"  [Layer 2] Trying DOI from agent response: {doi}")
            candidates, route = route_a_by_doi(doi)
            if candidates:
                return self._finish_repair(candidates[0], title)

        search_titles = []
        response_title = _extract_title_from_response(raw_response)
        for candidate_title in (response_title, title):
            if candidate_title and candidate_title not in search_titles:
                search_titles.append(candidate_title)

        for search_title in search_titles:
            if search_title != title:
                print(f"  [Layer 2] Trying title from agent response: {search_title[:70]}")
            candidates, route = route_a_all(search_title)
            if candidates:
                return self._finish_repair(candidates[0], search_title)

        return "repair_failed", None

    def _finish_repair(self, best: dict, fallback_title: str) -> tuple[str, dict | None]:
        if not (best.get("abstract") or "").strip():
            enriched = fetch_abstract_for_level1(best.get("title", fallback_title))
            if enriched and (enriched.get("abstract") or "").strip():
                best["abstract"] = enriched["abstract"]
                best["citationCount"] = enriched.get(
                    "citationCount", best.get("citationCount")
                )
                best["_abstract_source"] = enriched.get("_source", "unknown")
                if not best.get("externalIds"):
                    best["externalIds"] = enriched.get("externalIds", {})
        print(f"  [Layer 2] Repaired: {best.get('title','?')[:60]} "
              f"(score={best.get('_fuzzy_score')})")
        return "repaired", best
    def _layer3_semantic(
        self,
        claim: str,
        verdict: str,
        effective_verdict: str,
        canonical_paper: dict | None,
        raw_title: str,
        raw_year: int | None
    ) -> tuple[str, float, str, dict | None]:
        """Run semantic support checking for the cited paper entity."""
        if verdict == "LEVEL_1_PERFECT":
            paper = fetch_abstract_for_level1(raw_title)
            if not paper:
                return "UNCERTAIN", 0.0, "Could not fetch abstract for L1 paper.", None
            sem_v, sem_c, sem_j = verify_one_candidate(
                claim, paper, self.client, is_route_a=False
            )
            return sem_v, sem_c, sem_j, paper

        if verdict == "LEVEL_2_FLAWED" and canonical_paper is not None:
            sem_v, sem_c, sem_j = verify_one_candidate(
                claim, canonical_paper, self.client, is_route_a=True
            )
            return sem_v, sem_c, sem_j, canonical_paper

        # Alternative papers are handled only in Layer 4, not counted as citation support.
        return "UNSUPPORTED", 1.0, (
            "Input citation is Level 3 or repair-failed; no cited paper entity "
            "is available for semantic verification. Alternative evidence is "
            "handled in Layer 4 retrieval."
        ), None
    def _layer4_retrieval(self, claim: str) -> tuple[str, list[dict]]:
        """Retrieve and rank alternative evidence candidates."""
        candidates, route = route_b_multi_source(claim)
        if not candidates:
            return "not_retrieved", []

        verifiable = [p for p in candidates if p.get("_has_abstract")]
        if not verifiable:
            for p in candidates:
                p["_verdict"] = "UNCERTAIN"
                p["_confidence"] = 0.0
                p["_justification"] = "Retrieved candidate, but no abstract was available for support verification."
            return "unverified", candidates[:5]

        scored = rank_candidates_batch(claim, verifiable, self.client)
        if not scored:
            return "not_retrieved", []

        best = scored[0]
        best_v    = best.get("_verdict", "UNCERTAIN")
        best_conf = best.get("_confidence", 0.0)

        if best_v == "SUPPORTED" and best_conf >= 0.7:
            status = "retrieved"
        elif best_v in ("SUPPORTED", "PARTIALLY_SUPPORTED") and best_conf >= 0.5:
            status = "partial"
        elif candidates:
            status = "unverified"
            for p in candidates:
                p.setdefault("_verdict", "UNCERTAIN")
                p.setdefault("_confidence", 0.0)
                p.setdefault("_justification", "Retrieved candidate, but support was not verified.")
            scored = candidates[:5]
        else:
            status = "not_retrieved"
            scored = []

        return status, scored

    def _final_status(
        self,
        verdict: str,
        layer2_status: str,
        sem_verdict: str,
        sem_conf: float,
        layer4_status: str
    ) -> str:
        supported = _is_supported(sem_verdict, sem_conf)

        if verdict == "LEVEL_1_PERFECT":
            return "L1_valid" if supported else (
                "L1_mismatch_retrieved" if layer4_status == "retrieved"
                else "L1_mismatch_partial" if layer4_status == "partial"
                else "L1_mismatch_unverified" if layer4_status == "unverified"
                else "L1_mismatch_no_alternative"
            )

        if verdict == "LEVEL_2_FLAWED":
            if layer2_status == "repaired":
                return "L2_repaired_valid" if supported else (
                    "L2_repaired_mismatch_retrieved" if layer4_status == "retrieved"
                    else "L2_repaired_mismatch_partial" if layer4_status == "partial"
                    else "L2_repaired_mismatch_unverified" if layer4_status == "unverified"
                    else "L2_repaired_mismatch_no_alternative"
                )
            else:  # repair_failed
                if supported:
                    return "L2_repair_failed_semantic_recovered"
                return (
                    "L2_repair_failed_retrieved" if layer4_status == "retrieved"
                    else "L2_repair_failed_partial" if layer4_status == "partial"
                    else "L2_repair_failed_unverified" if layer4_status == "unverified"
                    else "L2_repair_failed_no_alternative"
                )

        # LEVEL_3_FAKE
        if supported:
            return "L3_semantic_recovered"
        return (
            "L3_retrieved" if layer4_status == "retrieved"
            else "L3_partial" if layer4_status == "partial"
            else "L3_unverified" if layer4_status == "unverified"
            else "L3_not_retrieved"
        )

    def _build_report(
        self,
        title, verdict, claim,
        layer2_status, canonical_paper,
        sem_verdict, sem_conf, sem_just, paper_for_sem,
        layer4_status, alternative_papers,
        final_status
    ) -> str:
        lines = [
            f"[PIPELINE REPORT]",
            f"Title:         {title}",
            f"Input verdict: {verdict}",
            f"Claim:         {claim}",
            f"",
        ]

        # Layer 2
        if verdict == "LEVEL_2_FLAWED":
            if layer2_status == "repaired":
                doi = (canonical_paper or {}).get("externalIds", {}).get("DOI", "N/A")
                lines += [
                    f"Layer 2 - Repair: repaired",
                    f"  Canonical paper: {(canonical_paper or {}).get('title','?')[:70]}",
                    f"  DOI:             {doi}",
                ]
            else:
                lines += ["Layer 2 - Repair: failed -> treated as Level 3"]
            lines.append("")

        # Layer 3
        icon = "yes" if _is_supported(sem_verdict, sem_conf) else "no"
        lines += [
            f"Layer 3 - Semantic: {icon} {sem_verdict} ({sem_conf:.0%})",
            f"  {sem_just}",
        ]
        if paper_for_sem:
            lines.append(
                f"  Paper: {paper_for_sem.get('title','?')[:70]}"
            )
        lines.append("")

        # Layer 4
        if layer4_status == "skipped":
            lines.append("Layer 4 - Retrieval: skipped (citation is supported)")
        elif layer4_status == "not_retrieved" or not alternative_papers:
            lines.append("Layer 4 - Retrieval: ✗ no suitable alternative found")
        elif layer4_status == "unverified":
            lines.append(f"Layer 4 - Retrieval: ? unverified  ({len(alternative_papers)} candidates)")
            for rank, alt in enumerate(alternative_papers, 1):
                doi     = alt.get("externalIds", {}).get("DOI", "N/A")
                authors = ", ".join(a.get("name", "") for a in alt.get("authors", [])[:3])
                if len(alt.get("authors", [])) > 3:
                    authors += " et al."
                just = alt.get("_justification", "Retrieved candidate, but support was not verified.")
                lines += [
                    f"  [{rank}] {alt.get('title','?')[:70]}",
                    f"       Authors: {authors or 'N/A'}  |  Year: {alt.get('year','N/A')}  |  DOI: {doi}",
                    f"       UNCERTAIN - {just}",
                ]
        else:
            icon4 = "yes" if layer4_status == "retrieved" else "~"
            lines.append(f"Layer 4 - Retrieval: {icon4} {layer4_status}  ({len(alternative_papers)} candidates)")
            for rank, alt in enumerate(alternative_papers, 1):
                doi     = alt.get("externalIds", {}).get("DOI", "N/A")
                authors = ", ".join(a.get("name", "") for a in alt.get("authors", [])[:3])
                if len(alt.get("authors", [])) > 3:
                    authors += " et al."
                v    = alt.get("_verdict", "?")
                conf = alt.get("_confidence", 0.0)
                just = alt.get("_justification", "")
                lines += [
                    f"  [{rank}] {alt.get('title','?')[:70]}",
                    f"       Authors: {authors}  |  Year: {alt.get('year','N/A')}  |  DOI: {doi}",
                    f"       {v} ({conf:.0%}) - {just}",
                ]
        lines += ["", f"Final status: {final_status}"]
        return "\n".join(lines)

    def _make_failed(self, title: str, verdict: str, reason: str) -> dict:
        return asdict(PipelineResult(
            original_title=title, input_verdict=verdict,
            claim="", claim_confidence=0.0, context_used="",
            layer2_status="skipped", canonical_paper=None,
            semantic_verdict="UNCERTAIN", semantic_confidence=0.0,
            semantic_justification=reason, paper_used_for_semantic=None,
            layer4_status="skipped", alternative_papers=[],
            final_status="failed",
            report=f"[FAILED] {title}\nReason: {reason}"
        ))
