import requests
from bs4 import BeautifulSoup

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
            # extract title
            title = bib.find("title", type="main")
            title_text = title.getText() if title else "Unknown Title"
            
            # extract year
            date = bib.find("date", type="published")
            year = date["when"] if date and date.has_attr("when") else "Unknown Year"
            
            # extract orginal text
            raw_text = bib.getText().strip()
            
            citations.append({
                "title": title_text,
                "year": year,
                "raw_text": raw_text
            })
            
        print(f"✅ Sucessfully extracted {len(citations)} citations。")
        return citations

    except Exception as e:
        print(f"❌ Something went wrong with Grobid: {e}")
        return []