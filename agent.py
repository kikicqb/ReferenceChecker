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

MODEL_NAME = "gemini-2.5-flash"

# ========================================
# 1. Tool Function: DBLP Search 
# ========================================
def search_dblp_api(title, author):
    print(f"   [Tool Execution] Querying DBLP for the Agent: {title} ...")
    
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', ' ', title)
    short_title = " ".join(clean_title.split()[:4])

    query = f"{short_title} {author}"
    url = "https://dblp.org/search/publ/api"
    
    params = {
        "q": query,
        "format": "json",
        "h": 3  
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code in [500, 502, 503, 504, 429]:
                print(f"  [DEBUG] DBLP server issue (Status code: {response.status_code}). Waiting 5 seconds before retry {attempt + 1}...")
                time.sleep(5)
                continue
                
            if response.status_code != 200:
                return f"Error: DBLP server returned HTTP {response.status_code}."
                
            data = response.json()
            
            hits = data.get("result", {}).get("hits", {}).get("hit", [])
            if not hits:
                return "DBLP database returned no results for this query."
                
            results_text = "Found the following papers in DBLP:\n"
            for hit in hits:
                info = hit.get("info", {})
                found_title = info.get("title", "No title")
                found_year = info.get("year", "Unknown year")
                
                found_doi = info.get("doi", "")
                if not found_doi:
                    found_doi = info.get("ee", "No link available")
                    
                authors = info.get("authors", {}).get("author", [])
                if isinstance(authors, dict):
                    author_names = authors.get("text", "")
                elif isinstance(authors, list):
                    author_names = ", ".join([a.get("text", "") for a in authors if isinstance(a, dict)])
                else:
                    author_names = "Unknown authors"
                    
                results_text += f"- Title: {found_title} | Authors: {author_names} | Year: {found_year} | Link: {found_doi}\n"
                
            time.sleep(2)
            return results_text
            
        except requests.exceptions.Timeout:
            print("  [DEBUG] Request timed out! Waiting 3 seconds before retry...")
            time.sleep(3)
            continue
        except json.JSONDecodeError:
            return "Error connecting to DBLP: Server returned HTML instead of JSON. You might be temporarily blocked."
        except Exception as e:
            return f"Error connecting to DBLP database: {str(e)}"
            
    return "DBLP database is currently down or unresponsive after multiple retries."


# ===========================
# 2. Core Agent Verification 
# ===========================
def run_agent_verification(paper_title, paper_author, paper_year, paper_doi):
    print(f"\n Starting test for paper: {paper_title}")
    
    system_prompt = (
        "You are an expert academic fact-checking agent. Your job is to verify if a cited paper exists using the DBLP database tool. "
        "Based on the tool's returned evidence, you MUST classify the citation into one of THREE levels:\n\n"
        "- LEVEL 1 (Perfect Match): The paper exists and all core metadata (Title, Author, Year) perfectly or near-perfectly match the database.\n"
        "- LEVEL 2 (Minor Flaw / Real Entity): The core paper exists in the real world, but the provided citation has noticeable hallucinations or errors (e.g., misspelled authors, wrong year, slightly altered title, or wrong venue). It is a real concept with flawed details.\n"
        "- LEVEL 3 (Completely Fake): No convincing match is found in the database. The core entity is a pure AI hallucination.\n\n"
        "Provide a brief, step-by-step reasoning for your decision. \n"
        "CRITICAL INSTRUCTION: Your final response MUST end with exactly ONE of the following labels on a new line:\n"
        "[VERDICT: LEVEL_1_PERFECT]\n"
        "[VERDICT: LEVEL_2_FLAWED]\n"
        "[VERDICT: LEVEL_3_FAKE]"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please verify this paper:\nTitle: {paper_title}\nAuthor: {paper_author}\nYear: {paper_year}\nExpected Link: {paper_doi}"}
    ]

    tools = [{
        "type": "function",
        "function": {
            "name": "search_dblp_api",
            "description": "Search the DBLP computer science database to verify paper existence and metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the paper"},
                    "author": {"type": "string", "description": "The surname of the first author"}
                },
                "required": ["title", "author"]
            }
        }
    }]

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.0
    )
    
    response_msg = response.choices[0].message

    if response_msg.tool_calls:
        tool_call = response_msg.tool_calls[0]
        arguments = json.loads(tool_call.function.arguments)
        
        db_result = search_dblp_api(arguments.get('title', paper_title), arguments.get('author', paper_author))
        print(f"  [Database Response] \n{db_result}")
        
        messages.append(response_msg)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": db_result
        })
        
        print(" Analyzing data for final verdict...")
        final_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.0
        )
        
        content = final_response.choices[0].message.content
        if not content:
            content = "[VERDICT: LEVEL_3_FAKE] (Fallback: Model blanked out)"
        
        print(f"\n Final Conclusion:\n{content}")
        return content

    else:
        content = response_msg.content
        if not content:
            content = "[VERDICT: LEVEL_3_FAKE] (Fallback: Model blanked out)"
            
        print("\n Final Conclusion (No database called):\n" + content)
        return content


# =====================
# 3. Main Testing 
# =====================
if __name__ == "__main__":
    
    input_file_path = "experiment_datasets/test35.json"  
    
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            TEST_DATASET = json.load(f)
    except FileNotFoundError:
        print(f" Cannot find file {input_file_path}, please check the path!")
        exit()

    total = len(TEST_DATASET)
    print(f" Starting automated Agent testing, total {total} papers...\n")
    
    results_log = []
    score = 0  

    for index, paper in enumerate(TEST_DATASET):
        id = paper.get("id", "")
        title = paper.get("title", "")
        author = paper.get("author", "")
        year = paper.get("year", "")
        link = paper.get("link", "") 
        group = paper.get("group", "Unknown") 
        expected_real = paper.get("is_real", False) 
        
        print(f"==================================================")
        print(f"[{index + 1}/{total}] Testing: {title}")
        print(f"   Expected: {'Real Paper' if expected_real else 'Fake Paper'}")
        
        try:
            # Run the Agent
            raw_agent_verdict = run_agent_verification(title, author, year, link)
            
            clean_verdict = "UNKNOWN"
            upper_verdict = str(raw_agent_verdict).upper() 
            
            if "LEVEL 1" in upper_verdict or "LEVEL_1" in upper_verdict:
                clean_verdict = "LEVEL_1_PERFECT"
            elif "LEVEL 2" in upper_verdict or "LEVEL_2" in upper_verdict:
                clean_verdict = "LEVEL_2_FLAWED"
            elif "LEVEL 3" in upper_verdict or "LEVEL_3" in upper_verdict:
                clean_verdict = "LEVEL_3_FAKE"
            
            print(f"   Agent Extracted Conclusion: {clean_verdict}")
            
            is_correct = False
            if expected_real and clean_verdict in ["LEVEL_1_PERFECT", "LEVEL_2_FLAWED"]:
                is_correct = True
                print(f"   -> ✅ Agent Correct! (Real entity successfully caught as {clean_verdict})")
                score += 1
            elif not expected_real and clean_verdict == "LEVEL_3_FAKE":
                is_correct = True
                print("   -> ✅ Agent Intercepted! (Fake paper ruthlessly destroyed as LEVEL_3_FAKE)")
                score += 1
            else:
                print(f"   -> ❌ Agent Failed! (Expected Real: {expected_real}, but got {clean_verdict})")
            
            # Save results
            results_log.append({
                "id": id,
                "title": title,
                "group": group,
                "expected_real": expected_real,
                "clean_verdict": clean_verdict,          
                "is_correct": is_correct,             
                "raw_agent_response": raw_agent_verdict 
            })
            
        except Exception as e:
            print(f"❌ Error testing this paper: {e}")
            
        time.sleep(5) 
        
    # Print final score
    accuracy = (score / total) * 100
    print(f"\n==================================================")
    print(f"Agent Final Accuracy: {score}/{total} ({accuracy:.1f}%)")
    print(f"==================================================\n")

    output_file_path = input_file_path.replace(".json", "_agent_results.json")
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(results_log, f, ensure_ascii=False, indent=4)
        
    print(f"Testing completely finished! All results saved to: {output_file_path}")