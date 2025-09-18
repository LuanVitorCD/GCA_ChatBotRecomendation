# ingest.py - Conversão inicial do ProcessadorLattesCompleto.java
import re
from bs4 import BeautifulSoup

DOI_REGEX = re.compile(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+')

def parse_lattes_html(html: str):
    soup = BeautifulSoup(html, "lxml")
    profile = {"name": None, "publications": []}
    h1 = soup.find('h1')
    if h1:
        profile["name"] = h1.get_text(strip=True)
    else:
        profile["name"] = "Nome não encontrado"
    for li in soup.find_all('li'):
        text = li.get_text(" ", strip=True)
        dois = DOI_REGEX.findall(text)
        if dois:
            profile["publications"].append({"text": text, "dois": dois})
    return profile
