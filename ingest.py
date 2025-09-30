# ingest.py - Conversão do ProcessadorLattesCompleto.java
import re
from bs4 import BeautifulSoup
from typing import Dict, List

# Regex para encontrar DOIs
DOI_REGEX = re.compile(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+')

def parse_lattes_html(html_content: str) -> Dict:
    """
    Processa o conteúdo HTML/XML de um Currículo Lattes para extrair
    informações estruturadas sobre o pesquisador e suas publicações.

    Args:
        html_content: O conteúdo HTML do currículo.

    Returns:
        Um dicionário com os dados extraídos, pronto para ser inserido no banco.
    """
    soup = BeautifulSoup(html_content, "lxml")
    
    profile = {
        "nome": "Nome não encontrado",
        "titulacao": "Titulação não encontrada",
        "universidade": "Universidade não encontrada", # Este campo é mais complexo de extrair de forma consistente
        "areas_conhecimento": [],
        "publicacoes": []
    }

    # --- Extração do Nome ---
    h1 = soup.find('h1', class_='nome')
    if h1:
        profile["nome"] = h1.get_text(strip=True)

    # --- Extração de Áreas de Atuação (Exemplo) ---
    # A estrutura do Lattes pode variar. Este é um seletor comum.
    # É preciso um tratamento mais robusto para capturar todos os níveis.
    areas_div = soup.find('div', id='areas-atuacao')
    if areas_div:
        # Extrai todas as linhas de área
        areas_raw = areas_div.find_all(class_='area-conhecimento-grande')
        for area_text in areas_raw:
             # O texto vem como "Grande Área: Ciências Exatas e da Terra / Área: Ciência da Computação."
             # É necessário um parser mais inteligente para separar cada nível.
             profile["areas_conhecimento"].append(area_text.get_text(strip=True))
    
    # --- Extração de Publicações (Exemplo melhorado) ---
    # O Lattes agrupa publicações por tipo. É preciso iterar em cada seção.
    # Exemplo para "Artigos completos publicados em periódicos"
    artigos_divs = soup.find_all('div', class_='artigo-completo')
    for div in artigos_divs:
        publication_data = {
            "tipo": "ARTIGO",
            "titulo": "Título não encontrado",
            "ano": None,
            "doi": None,
            "periodico": None,
            "issn": None
        }
        
        # Título
        titulo_element = div.find('span', class_='titulo-do-artigo-completo')
        if titulo_element:
            publication_data["titulo"] = titulo_element.get_text(strip=True)

        # Detalhes (Ano, Periódico, ISSN)
        detalhes_element = div.find('span', class_='detalhes-do-artigo-completo')
        if detalhes_element:
            detalhes_text = detalhes_element.get_text(" ", strip=True)
            # Extrair ano (geralmente o primeiro conjunto de 4 dígitos)
            year_match = re.search(r'\b(\d{4})\b', detalhes_text)
            if year_match:
                publication_data["ano"] = int(year_match.group(1))

            # Extrair ISSN
            issn_match = re.search(r'ISSN: (\d{4}-\d{3}[\dX])', detalhes_text)
            if issn_match:
                publication_data["issn"] = issn_match.group(1)

        # DOI
        doi_element = div.find('a', class_='link-doi')
        if doi_element:
             publication_data["doi"] = doi_element.get_text(strip=True)

        profile["publicacoes"].append(publication_data)

    # TODO: Implementar a extração para outros tipos de publicação:
    # - Livros e capítulos ('livro-publicado', 'capitulo-publicado')
    # - Trabalhos em anais de eventos ('trabalho-em-congresso')
    
    return profile

if __name__ == "__main__":
    # Exemplo de como usar a função
    # Você precisaria carregar um arquivo HTML de um Lattes real aqui.
    try:
        with open("exemplo_lattes.html", "r", encoding="utf-8") as f:
            html = f.read()
            dados_extraidos = parse_lattes_html(html)
            
            import json
            print("Dados extraídos do Lattes (exemplo):")
            print(json.dumps(dados_extraidos, indent=2, ensure_ascii=False))

    except FileNotFoundError:
        print("Arquivo 'exemplo_lattes.html' não encontrado.")
        print("Para testar, salve o HTML de um Currículo Lattes com este nome no diretório.")
