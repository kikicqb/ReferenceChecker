"""
Step 1: 引用定位 + Claim 提取

你的验证系统没有 ref_marker 字段，只有 title。
所以定位策略是：用 title 的关键词在正文里找到引用上下文。

Grobid XML 里每个引用长这样：
  <ref type="bibr" target="#b11">[12]</ref>
而 #b11 对应 reference list 里：
  <biblStruct xml:id="b11">
    <title>Learning to combine trained distance metrics...</title>

所以我们用 title → 找到 xml:id → 再找正文里的 <ref target="#bXX">
"""

import re
from google import genai
from lxml import etree

NAMESPACE = {"tei": "http://www.tei-c.org/ns/1.0"}

# ── 1. 用 title 在 XML reference list 里找到 Grobid 分配的内部 ID ──────────
def find_ref_id_by_title(xml_root: etree._Element, title: str) -> str | None:
    """
    在 <listBibl> 里搜索与 title 最匹配的条目，返回其 xml:id（如 "b11"）
    用 lower() 做大小写不敏感匹配，再用关键词子集匹配处理截断标题
    """
    from rapidfuzz import fuzz

    bib_structs = xml_root.findall(".//tei:listBibl/tei:biblStruct", NAMESPACE)
    best_id = None
    best_score = 0

    for bib in bib_structs:
        # Grobid 把标题放在 <title level="a"> 或 <title level="m">
        title_els = bib.findall(".//tei:title", NAMESPACE)
        for t_el in title_els:
            bib_title = "".join(t_el.itertext()).strip()
            score = fuzz.ratio(title.lower(), bib_title.lower())
            if score > best_score:
                best_score = score
                xml_id = bib.get("{http://www.w3.org/XML/1998/namespace}id")
                best_id = xml_id

    # 相似度阈值85（处理 Grobid 提取不完整的情况）
    if best_score >= 85:
        return best_id

    return None


# ── 2. 用内部 ID 在正文里定位引用，提取上下文窗口 ─────────────────────────
def locate_context_by_ref_id(
    xml_root: etree._Element,
    ref_id: str,
    before_sentences: int = 2,
    after_sentences: int = 1
) -> str | None:
    target = f"#{ref_id}"

    # 优先找 <s> 级别（句子级，最精准）
    for s_el in xml_root.findall(".//tei:body//tei:s", NAMESPACE):
        refs_in_s = s_el.findall(".//tei:ref[@type='bibr']", NAMESPACE)
        targets_in_s = [r.get("target", "") for r in refs_in_s]
        if target in targets_in_s:
            return " ".join(s_el.itertext()).strip()

    # fallback：找 <p> 级别，但只取包含引用的那一句
    for p_el in xml_root.findall(".//tei:body//tei:p", NAMESPACE):
        refs_in_p = p_el.findall(".//tei:ref[@type='bibr']", NAMESPACE)
        targets_in_p = [r.get("target", "") for r in refs_in_p]
        if target in targets_in_p:
            # 段落里分句，只取含引用标记的那句及前后
            full_text = " ".join(p_el.itertext()).strip()
            sentences = re.split(r'(?<=[.!?])\s+', full_text)
            for i, sent in enumerate(sentences):
                # 找到含引用序号的句子
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
            # 实在找不到就返回整段
            return full_text

    return None


def _trim_paragraph(paragraph: str, before: int, after: int) -> str:
    """从段落中截取引用附近的句子窗口"""
    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
    # 段落级别找不到精确位置时，直接返回前几句（通常引用在段末）
    total = before + after + 1
    if len(sentences) <= total:
        return paragraph
    return " ".join(sentences[:total])


# ── 3. Fallback：纯文本正则定位（XML 失败时使用）─────────────────────────
def locate_context_from_text(
    raw_text: str,
    title: str,
    before: int = 2,
    after: int = 1
) -> str | None:
    """
    用 title 的前几个关键词在纯文本中搜索，找引用标记附近的上下文
    这是最后的 fallback，精度较低
    """
    # 取 title 前 4 个词作为搜索关键词（避免截断问题）
    keywords = title.split()[:4]
    pattern = re.compile(re.escape(" ".join(keywords)), re.IGNORECASE)

    sentences = re.split(r'(?<=[.!?])\s+', raw_text)
    for i, sent in enumerate(sentences):
        if pattern.search(sent):
            start = max(0, i - before)
            end = min(len(sentences), i + after + 1)
            return " ".join(sentences[start:end])

    return None


# ── 4. Gemini Claim 提取 ─────────────────────────────────────────────────
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
    """
    返回 (claim, confidence)
    confidence: 1.0=正常, 0.5=UNCERTAIN, 0.0=API失败
    """
    try:
        prompt = CLAIM_PROMPT.format(ref_marker=ref_marker, title=title, context=context[:2000])
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt
        )
        claim = response.text.strip()

        if not claim or claim == "UNCERTAIN":
            return "UNCERTAIN", 0.5

        # 过短说明提取失败
        if len(claim.split()) < 4:
            return claim, 0.4

        # LLM 把标题塞进去了（没有遵循指令）
        if title[:20].lower() in claim.lower():
            # 尝试清理，但降低置信度
            return claim, 0.6

        return claim, 1.0

    except Exception as e:
        print(f"  [Claim extraction ERROR] {e}")
        return "", 0.0


# ── 组合入口（供 recovery_module.py 调用）────────────────────────────────
def get_claim_for_citation(title, xml_root, raw_text, client):
    ref_id = find_ref_id_by_title(xml_root, title)
    
    # 查出对应的引用序号（比如 "[18]"）
    ref_marker = None
    if ref_id:
        target = f"#{ref_id}"
        for r in xml_root.findall(".//tei:body//tei:ref[@type='bibr']", NAMESPACE):
            if r.get("target") == target:
                ref_marker = "".join(r.itertext()).strip()
                break
    
    ref_marker = ref_marker or title[:20]  # fallback 用 title 前几个词
    
    context = locate_context_by_ref_id(xml_root, ref_id) if ref_id else None
    if not context:
        context = locate_context_from_text(raw_text, title)
    if not context:
        return "", 0.0, ""

    claim, confidence = extract_claim(context, title, ref_marker, client)
    return claim, confidence, context