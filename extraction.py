import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path

def extract_citations(pdf_path):
    print(f"Parsing PDF: {pdf_path}...")
    
    # GROBID 
    url = "http://localhost:8070/api/processReferences"
    
    try:
        # Send PDF
        files = {'input': open(pdf_path, 'rb')}
        resp = requests.post(url, files=files)
        
        # Parse XML result
        soup = BeautifulSoup(resp.text, 'xml')
        citations = []
        
        for bib in soup.find_all("biblStruct"):
            # 1. extract title
            title = bib.find("title", type="main")
            title_text = title.getText() if title else "Unknown Title"
            
            # 2. extract year
            date = bib.find("date", type="published")
            year = date["when"] if date and date.has_attr("when") else "Unknown Year"

            # 3. extract author
            authors = []
            for author_node in bib.find_all("author"):
                pers_name = author_node.find("persName")
                if pers_name:
                    surname = pers_name.find("surname")
                    forename = pers_name.find("forename")
                    
                    name_parts = []
                    if forename: name_parts.append(forename.get_text())
                    if surname: name_parts.append(surname.get_text())
                    
                    if name_parts:
                        authors.append(" ".join(name_parts))
            
            authors_text = ", ".join(authors) if authors else "Unknown Author"
            
            # 4. extract doi/link
            link = "N/A"
            doi_tag = bib.find("idno", type="DOI")
            if doi_tag:
                link = f"https://doi.org/{doi_tag.text.strip()}"
            else:
                ptr_tag = bib.find("ptr")
                if ptr_tag and ptr_tag.has_attr("target"):
                    link = ptr_tag["target"]
                else:
                    arxiv_tag = bib.find("idno", type="arXiv")
                    if arxiv_tag:
                        link = f"https://arxiv.org/abs/{arxiv_tag.text.strip()}"

            raw_text = bib.getText().strip()
            
            citations.append({
                "title": title_text,
                "author": authors_text, 
                "year": year,
                "link": link,          
                "raw_text": raw_text
            })
            
        print(f"✅ Sucessfully extracted {len(citations)} citations。")

        with open(output_name, 'w', encoding='utf-8') as f:
            json.dump(citations, f, ensure_ascii=False, indent=4)
            
        print(f"Results saved to: {output_name}")
        return citations

    except Exception as e:
        print(f"❌ Something went wrong with Grobid: {e}")
        return []

if __name__ == "__main__":
    target_pdf = "grobid/exp5.pdf" 
    
    path_obj = Path(target_pdf)
    output_name = str(path_obj.parent / f"{path_obj.stem}.json")
    
    extract_citations(target_pdf)