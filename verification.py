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
def generic_verify_logic(db_name, items, extractor_func, exp_title, exp_author, exp_year, exp_doi):

    best_status = "TITLE_NOT_FOUND"
    msg = f" Reject: Title Not Found in {db_name}"
    
    for item in items:
        try:
            found_title, found_authors, found_year, found_doi = extractor_func(item)
            
            if not found_title: continue
            
            # 1. Check title
            if calculate_similarity(exp_title, found_title) > 0.9:
                best_status = "AUTHOR_MISMATCH"
                msg = f" Reject: Author Mismatch (Found in {db_name}, but author '{exp_author}' not matched)"
                
                # 2. Check author
                if check_author_match(exp_author, found_authors):
                    best_status = "YEAR_MISMATCH"
                    msg = f" Reject: Year Mismatch (Found in {db_name}, but year is {found_year}, expected {exp_year})"
                    
                    # 3. Check year
                    if check_year_match(exp_year, found_year):
                        # 4. Check DOI
                        if exp_doi:
                            if found_doi and clean_doi(exp_doi) != clean_doi(found_doi):
                                best_status = "DOI_MISMATCH"
                                msg = f" Reject: FAKE DOI (Title/Author match, but official DOI is {found_doi})"
                                continue 
                        
                        return "VERIFIED", f" Verified (Source: {db_name})"
        except Exception:
            continue
            
    return best_status, msg

def check_crossref(title, author, year, expected_doi=None):
    url = "https://api.crossref.org/works"
    params = {"query.title": title, "rows": 5, "select": "title,author,issued,DOI"} 
    headers = {"User-Agent": "ThesisProject/1.5 (mailto:test@student.liu.se)"}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        items = resp.json().get('message', {}).get('items', [])
        
        def extract(item):
            f_title = item.get('title', [''])[0]
            f_authors = " ".join([f"{a.get('given', '')} {a.get('family', '')}" for a in item.get('author', []) if isinstance(a, dict)])
            date_parts = item.get('issued', {}).get('date-parts', [[None]])
            f_year = str(date_parts[0][0]) if date_parts and date_parts[0] and date_parts[0][0] else ""
            f_doi = item.get('DOI', '')
            return f_title, f_authors, f_year, f_doi
            
        return generic_verify_logic("CrossRef", items, extract, title, author, year, expected_doi)
    except Exception:
        return "TITLE_NOT_FOUND", " Error connecting to CrossRef"

def check_semantic_scholar(title, author, year, expected_doi=None):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {"query": title, "limit": 5, "fields": "title,authors,year,externalIds,url"} 
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        items = resp.json().get('data', [])
        
        def extract(item):
            f_title = item.get('title', '')
            f_authors = " ".join([a.get('name', '') for a in item.get('authors', []) if isinstance(a, dict)])
            f_year = str(item.get('year', ''))
            f_doi = item.get('externalIds', {}).get('DOI', '') or item.get('url', '')
            return f_title, f_authors, f_year, f_doi
            
        return generic_verify_logic("Semantic Scholar", items, extract, title, author, year, expected_doi)
    except Exception:
        return "TITLE_NOT_FOUND", " Error connecting to Semantic Scholar"

def check_openalex(title, author, year, expected_doi=None):
    url = "https://api.openalex.org/works"
    params = {"search": title, "per-page": 5} 
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        items = resp.json().get('results', [])
        
        def extract(item):
            f_title = item.get('title', '') or ''
            f_authors = " ".join([a.get('author', {}).get('display_name', '') for a in item.get('authorships', []) if isinstance(a, dict)])
            f_year = str(item.get('publication_year', ''))
            f_doi = item.get('doi', '')
            return f_title, f_authors, f_year, f_doi
            
        return generic_verify_logic("OpenAlex", items, extract, title, author, year, expected_doi)
    except Exception:
        return "TITLE_NOT_FOUND", " Error connecting to OpenAlex"

def check_dblp(title, author, year, expected_doi=None):
    url = "https://dblp.org/search/publ/api"
    params = {"q": f"{title} {author}", "format": "json", "h": 5} 
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        items = resp.json().get('result', {}).get('hits', {}).get('hit', [])
        
        def extract(item):
            info = item.get('info', {})
            f_title = info.get('title', '')
            raw_authors = info.get('authors', {}).get('author', [])
            raw_authors = [raw_authors] if isinstance(raw_authors, dict) else (raw_authors if isinstance(raw_authors, list) else [])
            f_authors = " ".join([a.get('text', '') for a in raw_authors if isinstance(a, dict)])
            f_year = str(info.get('year', ''))
            f_doi = info.get('doi', '') or info.get('ee', '')
            return f_title, f_authors, f_year, f_doi
            
        return generic_verify_logic("DBLP", items, extract, title, author, year, expected_doi)
    except Exception:
        return "TITLE_NOT_FOUND", " Error connecting to DBLP"

# ======================
# 3. Main Control Logic 
# ======================
def verify_citation(title, author=None, year=None, expected_doi=None):
   
    results = []
    
    for check_func in [check_crossref, check_semantic_scholar, check_openalex, check_dblp]:
        status, msg = check_func(title, author, year, expected_doi)
        
        # Level 1: Perfect match
        if status == "VERIFIED":
            return "LEVEL_1_PERFECT", msg  
            
        results.append((status, msg))
        
    statuses = [r[0] for r in results]
    
    # Level 2: Exists but has minor flaws
    if "DOI_MISMATCH" in statuses:
        msg = next(r[1] for r in results if r[0] == "DOI_MISMATCH")
        return "LEVEL_2_FLAWED", msg
        
    elif "YEAR_MISMATCH" in statuses:
        msg = next(r[1] for r in results if r[0] == "YEAR_MISMATCH")
        return "LEVEL_2_FLAWED", msg
        
    elif "AUTHOR_MISMATCH" in statuses:
        msg = next(r[1] for r in results if r[0] == "AUTHOR_MISMATCH")
        return "LEVEL_2_FLAWED", msg
        
    # Level 3: Fabricated
    else:
        return "LEVEL_3_FAKE", "Reject: Title Not Found in any database"