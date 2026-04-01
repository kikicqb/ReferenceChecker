import os
import json
import requests
import time
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=GEMINI_API_KEY,
)
MODEL_NAME = "gemini-3.1-flash-lite-preview"

# =======================================================
# 1. Tool：Cascading Search
# =======================================================
def search_all_databases(title, first_author, year):
    print(f"   [Super Tool Execution] Starting Waterfall Search for: '{title[:20]}...'")
    
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', ' ', title)
    strict_query = f"{clean_title} {first_author}"
    
    report = f"--- DATABASE SEARCH INTELLIGENCE REPORT ---\nTarget: {title} | Author: {first_author}\n\n"
    headers = {"User-Agent": "ThesisProject/1.5 (mailto:test@student.liu.se)"}
    
    dblp_found_something = False

    # DBLP strict match
    print("     -> [Step 1] Querying DBLP (Strict Match)...")
    try:
        resp = requests.get("https://dblp.org/search/publ/api", params={"q": strict_query, "format": "json", "h": 3}, timeout=5)
        if resp.status_code == 200:
            items = resp.json().get('result', {}).get('hits', {}).get('hit', [])
            report += "[1. DBLP Results (Strict Match)]:\n"
            if items:
                dblp_found_something = True
                for item in items:
                    info = item.get('info', {})
                    authors = info.get('authors', {}).get('author', [])
                    authors = [authors] if isinstance(authors, dict) else (authors if isinstance(authors, list) else [])
                    author_str = ", ".join([a.get('text', '') for a in authors if isinstance(a, dict)])
                    report += f"  - Title: {info.get('title', '')} | Authors: {author_str} | Year: {info.get('year', '')} | DOI: {info.get('doi', '') or info.get('ee', '')}\n"
            else:
                report += "  - No strict matches found.\n"
        else:
            report += f"[1. DBLP Results]: API Error HTTP {resp.status_code}\n"
    except Exception as e:
        report += f"[1. DBLP Results]: Exception - {str(e)}\n"

    # AI Fuzzy Search
    if not dblp_found_something:
        print("     -> [Step 2] Strict match failed. Triggering AI Fuzzy Search ...")
        
        clean_title_for_fuzzy = re.sub(r'[^a-zA-Z0-9\s]', ' ', title)
        core_words = [w for w in clean_title_for_fuzzy.split() if len(w) > 3]
        fuzzy_query = f"{' '.join(core_words)} {first_author}"
        
        SEARCH_LIMIT = 10 
        
        # --- Check Semantic Scholar ---
        try:
            resp = requests.get("https://api.semanticscholar.org/graph/v1/paper/search", params={"query": fuzzy_query, "limit": SEARCH_LIMIT, "fields": "title,authors,year,externalIds,url"}, timeout=5)
            if resp.status_code == 200:
                items = resp.json().get('data', [])
                report += f"\n[2. Semantic Scholar Results (Fuzzy Match - Top {SEARCH_LIMIT})]:\n"
                if not items: report += "  - No results found.\n"
                for item in items:
                    author_str = ", ".join([a.get('name', '') for a in item.get('authors', []) if isinstance(a, dict)])
                    doi = item.get('externalIds', {}).get('DOI', '') or item.get('url', '')
                    report += f"  - Title: {item.get('title', '')} | Authors: {author_str} | Year: {item.get('year', '')} | DOI: {doi}\n"
            else:
                report += f"\n[2. Semantic Scholar Results]: API Error HTTP {resp.status_code}\n"
        except Exception as e:
            report += f"\n[2. Semantic Scholar Results]: Exception - {str(e)}\n"

        # --- Check CrossRef ---
        try:
            resp = requests.get("https://api.crossref.org/works", params={"query.bibliographic": fuzzy_query, "rows": SEARCH_LIMIT, "select": "title,author,issued,DOI"}, headers=headers, timeout=5)
            if resp.status_code == 200:
                items = resp.json().get('message', {}).get('items', [])
                report += f"\n[3. CrossRef Results (Fuzzy Match - Top {SEARCH_LIMIT})]:\n"
                if not items: report += "  - No results found.\n"
                for item in items:
                    author_str = ", ".join([f"{a.get('given', '')} {a.get('family', '')}" for a in item.get('author', []) if isinstance(a, dict)])
                    date_parts = item.get('issued', {}).get('date-parts', [[None]])
                    y = str(date_parts[0][0]) if date_parts and date_parts[0] and date_parts[0][0] else ""
                    report += f"  - Title: {item.get('title', [''])[0]} | Authors: {author_str} | Year: {y} | DOI: {item.get('DOI', '')}\n"
            else:
                report += f"\n[3. CrossRef Results]: API Error HTTP {resp.status_code}\n"
        except Exception as e:
            report += f"\n[3. CrossRef Results]: Exception - {str(e)}\n"

        # --- Check OpenAlex ---
        try:
            resp = requests.get("https://api.openalex.org/works", params={"search": fuzzy_query, "per-page": SEARCH_LIMIT}, timeout=5)
            if resp.status_code == 200:
                items = resp.json().get('results', [])
                report += f"\n[4. OpenAlex Results (Fuzzy Match - Top {SEARCH_LIMIT})]:\n"
                if not items: report += "  - No results found.\n"
                for item in items:
                    author_str = ", ".join([a.get('author', {}).get('display_name', '') for a in item.get('authorships', []) if isinstance(a, dict)])
                    report += f"  - Title: {item.get('title', '')} | Authors: {author_str} | Year: {item.get('publication_year', '')} | DOI: {item.get('doi', '')}\n"
            else:
                report += f"\n[4. OpenAlex Results]: API Error HTTP {resp.status_code}\n"
        except Exception as e:
            report += f"\n[4. OpenAlex Results]: Exception - {str(e)}\n"
            
    else:
        report += "\n[2, 3 & 4. Semantic Scholar, CrossRef, OpenAlex]: Skipped to save resources (Perfect match found in DBLP).\n"

    time.sleep(2)
    return report

# ================================
# 2. Core Agent Verification 
# ================================
def run_agent_verification(raw_citation):
    print(f"\n Starting test for citation: {raw_citation[:30]}...")
    
    system_prompt = (
    "You are an expert academic fact-checking agent. Your job is to verify if a cited paper exists using the 'search_all_databases' tool. "
    "The tool searches DBLP, CrossRef, Semantic Scholar, and OpenAlex simultaneously.\n\n"
    
    "### STRATEGY FOR NOISY DATA (CRITICAL):\n"
    "1. **Analyze Input Quality**: Before searching, check if the 'title' is 'Unknown', 'Unknown Title', or suspiciously short. "
    "Check if the 'author' is missing or looks like garbled text (e.g., 'TJoachims').\n"
    "2. **Mine Raw Text**: If the metadata is poor, carefully scan the 'raw_text' field. Look for sequences that resemble paper titles "
    "(usually longer phrases between the author names and the year/venue). Extract potential titles and clean author names (e.g., 'TJoachims' -> 'Joachims').\n"
    "3. **Refined Search**: Use the *best available* information. If the title is unknown, search using 'Author + Key Keywords from Raw Text + Year'.\n\n"
    
    "### CLASSIFICATION LEVELS:\n"
    """
    - LEVEL 1 (Perfect Match): The provided metadata EXACTLY matches the official database records. The title must be complete (including subtitles), the author list must be highly accurate, and the year must match. If an expected DOI is provided in the input, it MUST perfectly match the official DOI. (Exception: If Grobid failed and output 'Unknown Title', but you found the flawless, exact title/authors in the 'raw_text', you may classify it as LEVEL 1).

    - LEVEL 2 (Minor Flaw / Real Entity): The academic paper exists in reality, BUT the provided input data contains errors. 
    **STRICT TRIGGERS FOR LEVEL 2:**
    1. DOI Mismatch: An expected DOI is provided, but it is fake, broken, or points to a different paper.
    2. Title Flaws: Missing subtitles, typos, slightly altered words, or incomplete titles.
    3. Author Flaws: Missing co-authors, severely misspelled names.
    4. Year Mismatch: The year is incorrect (e.g., off by 1-2 years).
    *Rule of thumb: If you had to mentally "fix", "guess", or "ignore" an error in the input to find the real paper in the database, it MUST be classified as LEVEL 2.*

    - LEVEL 3 (Completely Fake): No convincing match is found in ANY of the databases after trying multiple search variations. The entity appears to be hallucinated or completely fabricated.
    """

    "### OUTPUT INSTRUCTIONS:\n"
    "Provide a brief reasoning explaining your discovery process (especially if you recovered a title from raw text). "
    "Your final response MUST end with exactly ONE of the following labels on a new line:\n"
    "[VERDICT: LEVEL_1_PERFECT]\n[VERDICT: LEVEL_2_FLAWED]\n[VERDICT: LEVEL_3_FAKE]"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please verify this citation: {raw_citation}"}
    ]

    tools = [{
        "type": "function",
        "function": {
            "name": "search_all_databases",
            "description": "Searches 4 major academic databases simultaneously. Returns a consolidated report of the top 3 matches from each.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The full title of the paper"},
                    "first_author": {"type": "string", "description": "ONLY the surname (last name) of the FIRST author (e.g., 'Schmidt')"},
                    "year": {"type": "string", "description": "The 4-digit publication year (e.g., '2025')"}
                },
                "required": ["title", "first_author", "year"]
            }
        }
    }]

    response = client.chat.completions.create(
        model=MODEL_NAME, messages=messages, tools=tools, tool_choice="auto", temperature=0.0
    )
    response_msg = response.choices[0].message

    if response_msg.tool_calls:
        tool_call = response_msg.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        
        db_report = search_all_databases(args.get('title', ''), args.get('first_author', ''), args.get('year', ''))
        #print(f"  [Intelligence Report] \n{db_report}") 
        
        messages.append(response_msg)
        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": db_report})
        messages.append({"role": "user", "content": "Now analyze the database report and provide your final reasoning and VERDICT label."})
        
        print(" Analyzing cross-database intelligence for final verdict...")
        final_response = client.chat.completions.create(
            model=MODEL_NAME, messages=messages, temperature=0.0
        )
        content = final_response.choices[0].message.content
        if not content: content = "[VERDICT: LEVEL_3_FAKE] (Fallback: Model blanked out)"
        
        print(f"\n Final Conclusion:\n{content}")
        return content
    else:
        content = response_msg.content
        if not content: content = "[VERDICT: LEVEL_3_FAKE] (Fallback: Model blanked out)"
        print("\n Final Conclusion (No database called):\n" + content)
        return content


# =====================
# 3. Main Testing Loop
# =====================
if __name__ == "__main__":
    
    input_file_path = "grobid_datasets/test.json"  
    
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            TEST_DATASET = json.load(f)
    except FileNotFoundError:
        print(f" Cannot find file {input_file_path}, please check the path!")
        exit()

    total = len(TEST_DATASET)
    score = 0  
    labeled_total = 0 
    results_log = []

    print(f" Starting automated multi-database Agent testing, total {total} papers...\n")
    
    for index, paper in enumerate(TEST_DATASET):
        id = paper.get("id", "")
        title = paper.get("title", "")
        author = paper.get("author", "")
        year = paper.get("year", "")
        link = paper.get("link", "") 
        group = paper.get('group', 'Unknown')
        raw_text = paper.get('raw_text', '')

        has_label = "is_real" in paper
        is_real = paper.get("is_real", False) 
        
        print(f"==================================================")
        print(f"[{index + 1}/{total}] Testing: {title}")
        print(f"   Group: {group}")
        
        try:
            raw_citation_text = f"Title: {title}\nAuthor: {author}\nYear: {year}\nLink: {link}\nRaw Text: {raw_text}"
            
            raw_agent_verdict = run_agent_verification(raw_citation_text)
            
            clean_verdict = "UNKNOWN"
            upper_verdict = str(raw_agent_verdict).upper() 
            if "LEVEL_1" in upper_verdict or "LEVEL 1" in upper_verdict:
                clean_verdict = "LEVEL_1_PERFECT"
            elif "LEVEL_2" in upper_verdict or "LEVEL 2" in upper_verdict:
                clean_verdict = "LEVEL_2_FLAWED"
            elif "LEVEL_3" in upper_verdict or "LEVEL 3" in upper_verdict:
                clean_verdict = "LEVEL_3_FAKE"
            
            is_correct = None
            
            if has_label:
                labeled_total += 1
                print(f"   Expected: {'Real Paper' if is_real else 'Fake Paper'}")
                if is_real and clean_verdict in ["LEVEL_1_PERFECT", "LEVEL_2_FLAWED"]:
                    is_correct = True
                    print(f"   -> ✅ Agent Correct!")
                    score += 1
                elif not is_real and clean_verdict == "LEVEL_3_FAKE":
                    is_correct = True
                    print("   -> ✅ Agent Intercepted!")
                    score += 1
                else:
                    is_correct = False
                    print(f"   -> ❌ Agent Failed!")
            else:
                print(f"   -> [Inference Mode] No label, Result: {clean_verdict}")
            
            results_log.append({
                "id": id, 
                "title": title, 
                "has_label": has_label,
                "expected_real": is_real if has_label else "N/A",
                "clean_verdict": clean_verdict,            
                "is_correct": is_correct,
                "raw_agent_response": raw_agent_verdict
            })
            
        except Exception as e:
            print(f"❌ Error testing this paper: {e}")
            
        time.sleep(2) 
        
    if labeled_total > 0:
        accuracy = (score / labeled_total) * 100
        print(f"\n==================================================")
        print(f"Agent Final Accuracy: {score}/{labeled_total} ({accuracy:.1f}%)")
    else:
        print(f"\n==================================================")
        print("All tests completed in Inference Mode (No labeled data).")
    print(f"==================================================\n")

    final_output = {
        "summary": {
            "total_papers": total,
            "labeled_papers": labeled_total,
            "correct_predictions": score,
            "accuracy": f"{accuracy:.2f}%" if labeled_total > 0 else "N/A"
        },
        "detailed_results": results_log 
    }

    output_file = input_file_path.replace(".json", "_agent_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=4)
        
    print(f" Results safely saved to: {output_file}")