import requests
import re
import unicodedata
from difflib import SequenceMatcher

# ==========================================
# 1. Basic Text and Logic Cleaning Tools
# ==========================================
def calculate_similarity(a, b):
    if not a or not b: return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def clean_text(text):
    if not text:
        return ""
    text = unicodedata.normalize('NFKD', str(text).lower()).encode('ASCII', 'ignore').decode('utf-8')
    return re.sub(r'[^a-z0-9\s]', ' ', text)

def clean_doi(doi_str):
    """remove prefix"""
    if not doi_str:
        return ""
    doi_str = str(doi_str).lower().strip()
    prefixes = [
        "https://doi.org/", "http://dx.doi.org/", "doi:", 
        "https://www.semanticscholar.org/paper/", 
        "https://openalex.org/"
    ]
    for p in prefixes:
        doi_str = doi_str.replace(p, "")
    return doi_str.strip()

def check_author_match(expected_author, found_authors_str):
    try:
        if not expected_author or not found_authors_str.strip(): 
            return True
            
        expected_clean = clean_text(expected_author)
        found_clean = clean_text(found_authors_str)
        
        expected_words = set(expected_clean.split())
        found_words = set(found_clean.split())
        
        stop_words = {"et", "al", "and", "with", "de", "van", "der", "von"}

        valid_expected = {w for w in expected_words if len(w) > 1 and w not in stop_words}
        valid_found = {w for w in found_words if len(w) > 1 and w not in stop_words}
        
        if not valid_expected or not valid_found: 
            return True 
        
        overlap = valid_expected.intersection(valid_found)
        min_length = min(len(valid_expected), len(valid_found))
        
        if min_length == 0:
            return False
            
        overlap_ratio = len(overlap) / min_length
        return overlap_ratio >= 0.6
        
    except Exception as e:
        print(f"\n  check_author_match break: {e}")
        return False

def check_year_match(expected_year, found_year):
    if not expected_year or not found_year: return True
    try:
        return abs(int(expected_year) - int(found_year)) <= 1
    except ValueError:
        return str(expected_year) == str(found_year)


# ========================
# 2. Database Requests
# ========================

def check_crossref(title, author, year, expected_doi=None):
    url = "https://api.crossref.org/works"
    params = {"query.title": title, "rows": 5, "select": "title,author,issued,DOI"} 
    headers = {"User-Agent": "ThesisProject/1.5 (mailto:test@student.liu.se)"}
    
    best_status = "TITLE_NOT_FOUND"
    msg = " Reject: Title Not Found in CrossRef"
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        items = resp.json().get('message', {}).get('items', [])
        
        for item in items:
            try: 
                found_title = item.get('title', [''])[0]
                if calculate_similarity(title, found_title) > 0.9:
                    best_status = "AUTHOR_MISMATCH"
                    
                    raw_authors = item.get('author', [])
                    authors = " ".join([f"{a.get('given', '')} {a.get('family', '')}" for a in raw_authors if isinstance(a, dict)])
                    msg = f" Reject: Author Mismatch (Found title in CrossRef, but author '{author}' not matched)"
                    
                    if check_author_match(author, authors):
                        best_status = "YEAR_MISMATCH"
                        date_parts = item.get('issued', {}).get('date-parts', [[None]])
                        found_year = str(date_parts[0][0]) if date_parts and date_parts[0] and date_parts[0][0] else ""
                        msg = f" Reject: Year Mismatch (Found in CrossRef, but year is {found_year}, expected {year})"
                        
                        if check_year_match(year, found_year):
                            if expected_doi:
                                found_doi = item.get('DOI', '')
                                if found_doi and clean_doi(expected_doi) != clean_doi(found_doi):
                                    best_status = "DOI_MISMATCH"
                                    msg = f" Reject: FAKE DOI (Title/Author match, but official CrossRef DOI is {found_doi})"
                                    continue # Link mismatch, check next possible record
                            
                            return "VERIFIED", " Verified (Source: CrossRef)"
            except Exception:
                continue 
    except Exception: 
        pass
    return best_status, msg


def check_semantic_scholar(title, author, year, expected_doi=None):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {"query": title, "limit": 5, "fields": "title,authors,year,externalIds,url"} 
    
    best_status = "TITLE_NOT_FOUND"
    msg = "Reject: Title Not Found in Semantic Scholar"
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        items = resp.json().get('data', [])
        
        for item in items:
            try: 
                found_title = item.get('title', '')
                if calculate_similarity(title, found_title) > 0.9:
                    best_status = "AUTHOR_MISMATCH"
                    
                    raw_authors = item.get('authors') or []
                    authors = " ".join([a.get('name', '') for a in raw_authors if isinstance(a, dict)])
                    msg = f"Reject: Author Mismatch (Found title in Semantic Scholar, but author '{author}' not matched)"
                    
                    if check_author_match(author, authors):
                        best_status = "YEAR_MISMATCH"
                        found_year = str(item.get('year', ''))
                        msg = f"Reject: Year Mismatch (Found in Semantic Scholar, but year is {found_year}, expected {year})"
                        
                        if check_year_match(year, found_year):
                            if expected_doi:
                                external_ids = item.get('externalIds') or {}
                                found_doi = external_ids.get('DOI', '')
                                if not found_doi: 
                                    found_doi = item.get('url', '')
                                    
                                if found_doi and clean_doi(expected_doi) != clean_doi(found_doi):
                                    best_status = "DOI_MISMATCH"
                                    msg = f"Reject: FAKE DOI (Title/Author match, but official Link is {found_doi})"
                                    continue 
                            
                            return "VERIFIED", "Verified (Source: Semantic Scholar)"
            except Exception:
                continue
    except Exception: 
        pass
    return best_status, msg


def check_openalex(title, author, year, expected_doi=None):
    url = "https://api.openalex.org/works"
    params = {"search": title, "per-page": 5} 
    
    best_status = "TITLE_NOT_FOUND"
    msg = "Reject: Title Not Found in OpenAlex"
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        items = resp.json().get('results', [])
        
        for item in items:
            try: 
                found_title = item.get('title', '')
                if not found_title: continue
                if calculate_similarity(title, found_title) > 0.9:
                    best_status = "AUTHOR_MISMATCH"
                    
                    authorships = item.get('authorships', [])
                    authors = " ".join([a.get('author', {}).get('display_name', '') for a in authorships if isinstance(a, dict)])
                    msg = f"Reject: Author Mismatch (Found title in OpenAlex, but author '{author}' not matched)"
                    
                    if check_author_match(author, authors):
                        best_status = "YEAR_MISMATCH"
                        found_year = str(item.get('publication_year', ''))
                        msg = f"Reject: Year Mismatch (Found in OpenAlex, but year is {found_year}, expected {year})"
                        
                        if check_year_match(year, found_year):
                            if expected_doi:
                                found_doi = item.get('doi', '') 
                                if found_doi and clean_doi(expected_doi) != clean_doi(found_doi):
                                    best_status = "DOI_MISMATCH"
                                    msg = f"Reject: FAKE DOI (Title/Author match, but official DOI is {found_doi})"
                                    continue
                            
                            return "VERIFIED", "Verified (Source: OpenAlex)"
            except Exception:
                continue
    except Exception: 
        pass
    return best_status, msg


def check_dblp(title, author, year, expected_doi=None):
    url = "https://dblp.org/search/publ/api"
    params = {"q": f"{title} {author}", "format": "json", "h": 5} 
    
    best_status = "TITLE_NOT_FOUND"
    msg = "Reject: Title Not Found in DBLP"
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        items = resp.json().get('result', {}).get('hits', {}).get('hit', [])

        # --- Debug logs ---
        print(f"\n[Debug] Actual requested URL: {resp.url}") 
        
        items = resp.json().get('result', {}).get('hits', {}).get('hit', [])
        print(f"[Debug] DBLP API returned {len(items)} records")
        # -----------------------------
        
        for item in items:
            try: 
                info = item.get('info', {})
                found_title = info.get('title', '')
                
                if calculate_similarity(title, found_title) > 0.9:
                    best_status = "AUTHOR_MISMATCH"
                    
                    raw_authors = info.get('authors', {}).get('author', [])
                    if isinstance(raw_authors, dict):
                        raw_authors = [raw_authors]
                    elif not isinstance(raw_authors, list):
                        raw_authors = []
                        
                    authors = " ".join([a.get('text', '') for a in raw_authors if isinstance(a, dict)])
                    msg = f"Reject: Author Mismatch"
                    
                    if check_author_match(author, authors):
                        best_status = "YEAR_MISMATCH"
                        found_year = str(info.get('year', ''))
                        msg = f"Reject: Year Mismatch"
                        
                        if check_year_match(year, found_year):
                            
                            if expected_doi:
                                found_doi = info.get('doi', '')
                                if not found_doi: 
                                    found_doi = info.get('ee', '')
                                    
                                if found_doi and clean_doi(expected_doi) != clean_doi(found_doi):
                                    best_status = "DOI_MISMATCH"
                                    msg = f"Reject: FAKE DOI"
                                    print(f"      [Failure Cause -> DOI] Expected: {expected_doi} | Found: {found_doi}")
                                    continue 
                            
                            return "VERIFIED", "Verified (Source: DBLP)"
                        else:
                            print(f"      [Failure Cause -> Year] Expected: {year} | Found: {found_year}")
                    else:
                        print(f"      [Failure Cause -> Author] Expected: {author} | Found: {authors}")
                else:
                    sim_score = calculate_similarity(title, found_title)
                    print(f"      [Failure Cause -> Title Similarity {sim_score:.2f}] Expected: '{title}' | Found: '{found_title}'")
                    
            except Exception:
                continue
    except Exception: 
        pass
        
    return best_status, msg


# ======================
# 3. Main Control Logic 
# ======================
def verify_citation(title, author=None, year=None, expected_doi=None):
   
    results = []
    
    for check_func in [check_crossref, check_semantic_scholar, check_openalex, check_dblp]:
        status, msg = check_func(title, author, year, expected_doi)
        results.append((status, msg))
        
    statuses = [r[0] for r in results]
    

    if "DOI_MISMATCH" in statuses:
        msg = next(r[1] for r in results if r[0] == "DOI_MISMATCH")
        return msg
        
    elif "YEAR_MISMATCH" in statuses:
        msg = next(r[1] for r in results if r[0] == "YEAR_MISMATCH")
        return msg
        
    elif "AUTHOR_MISMATCH" in statuses:
        msg = next(r[1] for r in results if r[0] == "AUTHOR_MISMATCH")
        return msg
    
    elif "VERIFIED" in statuses:
        msg = next(r[1] for r in results if r[0] == "VERIFIED")
        return msg
        
    else:
        return "Reject: Title Not Found in any database"