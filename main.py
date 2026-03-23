from extraction import extract_citations
from verification import verify_with_crossref

def main():
    pdf_file = "test.pdf" 
    
    citations = extract_citations(pdf_file)
    
    if not citations:
        print("No citations extracted. Please check if the PDF path is correct.")
        return

    for i, cite in enumerate(citations[:10]):
        print(f"\n[Citation {i+1}] {cite['title']}")
        
        result = verify_with_crossref(cite['title'])
        print(f"Result: {result}")

if __name__ == "__main__":
    main()