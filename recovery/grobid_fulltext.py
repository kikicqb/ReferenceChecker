"""Extract full text TEI from GROBID for semantic recovery."""
import httpx
import hashlib
import time
from pathlib import Path
from lxml import etree

GROBID_URL = "http://localhost:8070"
NAMESPACE = {"tei": "http://www.tei-c.org/ns/1.0"}
CACHE_DIR = Path(".grobid_cache")
TIMEOUT = httpx.Timeout(connect=10.0, read=300.0, write=300.0, pool=10.0)
MAX_RETRIES = 3


def _cache_path(pdf_path: str) -> Path:
    path = Path(pdf_path)
    digest = hashlib.sha1(path.read_bytes()).hexdigest()[:12]
    return CACHE_DIR / f"{path.stem}_{digest}.tei.xml"


def _load_or_request_xml(pdf_path: str) -> bytes:
    cache_path = _cache_path(pdf_path)
    if cache_path.exists():
        print(f"[GROBID] Using cached fulltext XML: {cache_path}")
        return cache_path.read_bytes()

    CACHE_DIR.mkdir(exist_ok=True)
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[GROBID] Processing PDF ({attempt}/{MAX_RETRIES})...")
            with open(pdf_path, "rb") as f:
                resp = httpx.post(
                    f"{GROBID_URL}/api/processFulltextDocument",
                    files={"input": f},
                    data={"consolidateReferences": "0"},
                    timeout=TIMEOUT
                )
            resp.raise_for_status()
            cache_path.write_bytes(resp.content)
            return resp.content
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                wait_seconds = 5 * attempt
                print(f"[GROBID] Request failed ({exc}). Retrying in {wait_seconds}s...")
                time.sleep(wait_seconds)

    raise RuntimeError(
        "GROBID fulltext extraction failed after retries. "
        "Check that the GROBID server is running at http://localhost:8070 "
        "and try again."
    ) from last_error


def extract_fulltext(pdf_path: str) -> tuple[str, etree._Element]:
    """Return plain body text and the parsed TEI XML root."""
    xml_bytes = _load_or_request_xml(pdf_path)
    root = etree.fromstring(xml_bytes)

    # Restrict extraction to the body so bibliography entries are not matched.
    body = root.find(".//tei:body", NAMESPACE)
    raw_text = " ".join(body.itertext()).strip() if body is not None else ""

    return raw_text, root
