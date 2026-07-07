import argparse
from pathlib import Path

from extraction import extract_citations
from verification import verify_citation

def main():
    parser = argparse.ArgumentParser(description="Extract and verify references from a PDF.")
    parser.add_argument("pdf", nargs="?", default="grobid_datasets/exp1.pdf", help="PDF file to process")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of citations to verify")
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf)
    output_path = pdf_path.with_suffix(".json")
    citations = extract_citations(str(pdf_path), str(output_path))
    
    if not citations:
        print("No citations extracted. Please check if the PDF path is correct.")
        return

    for i, cite in enumerate(citations[:args.limit]):
        print(f"\n[Citation {i+1}] {cite['title']}")
        
        result = verify_citation(
            cite.get("title", ""),
            cite.get("author"),
            cite.get("year"),
            cite.get("link"),
        )
        print(f"Result: {result}")

if __name__ == "__main__":
    main()
