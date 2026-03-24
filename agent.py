import os
import json
import requests
import time
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

MODEL_NAME = "nvidia/nemotron-3-nano-30b-a3b:free"

# ==========================================
# 1. Tool Function: DBLP Search
# ==========================================
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
    
    try:
        response = requests.get(url, params=params, timeout=10)
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
            
        return results_text
        
    except Exception as e:
        return f"Error connecting to DBLP database: {str(e)}"


# ===========================
# 2. Core Agent Verification 
# ===========================
def run_agent_verification(paper_title, paper_author, paper_year, paper_doi):
    print(f"\n Starting test for paper: {paper_title}")
    
    system_prompt = (
        "You are a strict academic fact-checking agent. Your job is to verify if a paper exists using the DBLP search tool. "
        "You MUST verify Title, Author, Year, and DOI/Link. "
        "CRITICAL RULE: If the returned database results show a paper that strongly matches the intended entity, you must consider the paper to exist (REAL). You MUST tolerate minor mismatches, slight wording differences, missing punctuation, or typos in the Title, Author, Year, or Link. "
        "Only declare it as FAKE if the tool finds no results at all, or if the core entity (Title/Author) is completely fabricated. \n\n"
        "CRITICAL INSTRUCTION: Your final response MUST end with exactly ONE of the following two labels on a new line:\n"
        "[VERDICT: REAL]\n"
        "[VERDICT: FAKE]"
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
        print(f"\n Final Conclusion:\n{final_response.choices[0].message.content}")
        return final_response.choices[0].message.content

    else:
        print("\n Final Conclusion (No database called):\n" + response_msg.content)
        return response_msg.content


# =====================
# 3. Main Testing 
# =====================
if __name__ == "__main__":
    
    input_file_path = "experiment_datasets/test.json"  
    
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
            
            # --- Extract binary verdict ---
            clean_verdict = "UNKNOWN"
            upper_verdict = raw_agent_verdict.upper().replace(" ", "") 
            
            if "[VERDICT:REAL]" in upper_verdict:
                clean_verdict = "REAL"
            elif "[VERDICT:FAKE]" in upper_verdict:
                clean_verdict = "FAKE"
            
            print(f"   Agent Extracted Conclusion: {clean_verdict}")
            
            # --- Binary Scoring Logic ---
            is_correct = False
            if expected_real and clean_verdict == "REAL":
                is_correct = True
                print("   -> ✅ Agent Correct! (Successfully identified a REAL paper)")
                score += 1
            elif not expected_real and clean_verdict == "FAKE":
                is_correct = True
                print("   -> ✅ Agent Intercepted! (Successfully identified a FAKE paper)")
                score += 1
            else:
                print("   -> ❌ Agent Failed! (Misclassification)")
            
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