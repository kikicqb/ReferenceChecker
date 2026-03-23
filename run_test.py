import json  
from verification import verify_citation

def run_benchmark():
    json_file_path = "experiment_datasets/exp5.json"  
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            TEST_DATASET = json.load(f)
    except FileNotFoundError:
        print(f" Can't find file {json_file_path}, please check the path!")
        return
    # ==========================================

    score = 0
    total = len(TEST_DATASET)
    results_log = []  
    
    for i, item in enumerate(TEST_DATASET):
        id = item.get('id', '')
        title = item.get('title', '')
        author = item.get('author', '')
        year = item.get('year', '') 
        link = item.get('link', '')
        is_real = item.get('is_real', False)
        group = item.get('group', 'Unknown')
        
        print(f"[{i+1}/{total}] Testing: {title}")
        print(f"  Group: {group}")
        print(f"  Expected: {'Real Paper' if is_real else 'Fake Paper'}")
        
        result = verify_citation(title, author, year, expected_doi=link)
        print(f" System: {result}")
        
        is_correct = False  
        
        if is_real and "Verified" in result:
            print("   -> ✅ Correct")
            score += 1
            is_correct = True
        elif not is_real and "Reject" in result:
            print("   -> ✅ Intercepted")
            score += 1
            is_correct = True
        else:
            print("   -> ❌ Wrong")
            
        print("-" * 50)
        
        # Append data to the log
        results_log.append({
            "id": id,
            "title": title,
            "group": group,
            "expected_real": is_real,
            "system_result": result,
            "is_correct": is_correct
        })
            
    accuracy = (score / total) * 100
    print(f"\n Final accuracy: {score}/{total} ({accuracy:.1f}%)")

    # Generate output path dynamically and save the JSON file
    output_file_path = json_file_path.replace(".json", "_script_results.json")
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(results_log, f, ensure_ascii=False, indent=4)
        
    print(f" Results safely saved to: {output_file_path}")

if __name__ == "__main__":
    run_benchmark()