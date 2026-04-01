import json  
from verification import verify_citation

def run_benchmark():
    json_file_path = "grobid_datasets/test.json"  
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            TEST_DATASET = json.load(f)
    except FileNotFoundError:
        print(f" Can't find file {json_file_path}, please check the path!")
        return

    score = 0
    labeled_total = 0 
    total = len(TEST_DATASET)
    results_log = []  
    
    for i, item in enumerate(TEST_DATASET):
        id = item.get('id', '')
        title = item.get('title', '')
        author = item.get('author', '')
        year = item.get('year', '') 
        link = item.get('link', '')
        group = item.get('group', 'Unknown')
        
        has_label = "is_real" in item 
        is_real = item.get('is_real', False)
        
        print(f"[{i+1}/{total}] Testing: {title}")
        print(f"  Group: {group}")
        
        result = verify_citation(title, author, year, expected_doi=link)
        print(f"  System: {result}")
        
        is_correct = None 
        
        if has_label:
            labeled_total += 1
            print(f"  Expected: {'Real Paper' if is_real else 'Fake Paper'}")
            
            if is_real and ("LEVEL_1_PERFECT" in result or "LEVEL_2_FLAWED" in result):
                print("   -> ✅ Correct")
                score += 1
                is_correct = True
            elif not is_real and "LEVEL_3_FAKE" in result:
                print("   -> ✅ Intercepted")
                score += 1
                is_correct = True
            else:
                print("   -> ❌ Wrong")
                is_correct = False
        else:
            print("  -> [Inference Mode] No label found, skipping evaluation.")
            
        print("-" * 50)
        
        results_log.append({
            "id": id,
            "title": title,
            "group": group,
            "has_label": has_label,
            "expected_real": is_real if has_label else "N/A",
            "system_result": result,
            "is_correct": is_correct
        })
            
    if labeled_total > 0:
        accuracy = (score / labeled_total) * 100
        print(f"\n Final accuracy (on labeled data): {score}/{labeled_total} ({accuracy:.1f}%)")
    else:
        print("\n No labeled data found. All items processed in Inference Mode.")

    final_output = {
        "summary": {
            "total_papers": total,
            "labeled_papers": labeled_total,
            "correct_predictions": score,
            "accuracy": f"{accuracy:.2f}%" if labeled_total > 0 else "N/A"
        },
        "detailed_results": results_log 
    }

    output_file_path = json_file_path.replace(".json", "_script_results.json")
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=4)
        
    print(f" Results safely saved to: {output_file_path}")

if __name__ == "__main__":
    run_benchmark()