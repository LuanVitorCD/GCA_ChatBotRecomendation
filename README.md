# 🎓 RecomendaProf

**RecomendaProf** é um sistema de **recomendação inteligente de orientadores de mestrado/doutorado** que auxilia estudantes de pós-graduação a encontrarem o orientador ideal. Diferente de buscas simples por palavras-chave, ele utiliza um **algoritmo híbrido** que combina:

1.  **Semântica:** Processamento de Linguagem Natural (NLP) e Clusterização para afinidade temática;
2.  **Métricas Acadêmicas:** Um modelo matemático com 6 dimensões (Produção, Experiência, Eficiência, etc.);
3.  **Inteligência Artificial Generativa:** Uso de LLMs (Gemini/Ollama) para explicar recomendações e resumir perfis.

---

## 💡 Visão Geral

O sistema processa dados brutos do **Currículo Lattes (XML)**, aplicando normalização estatística para gerar indicadores de desempenho relativo. 

A aplicação foi reimplementada com **Streamlit** para interface gráfica, **SQLite** como banco de dados (para facilidade de distribuição) e integração com LLMs para refinamento de busca.

---

## 📸 Interface

### 1. Página de Pequisa
![Exemplo do projeto rodando com dados reais no motor moderno](assets/example_fullpage.png)

<details>
<summary>Clique para ver mais imagens</summary>

### 2. Painel de Métricas Multidimensionais
O sistema calcula e normaliza dados do Lattes para gerar um *Score Híbrido*. A visualização permite entender rapidamente os pontos fortes do orientador (ex: alta produção vs. alta disponibilidade para orientação).

![Painel de Métricas](assets/metrics_view.png)

---

### 3. Perfil Inteligente (Resumo via IA)
As informações cruas do banco de dados são processadas e, opcionalmente, refinadas por IA para gerar um resumo legível das áreas de atuação, eliminando a "sopa de letrinhas" de palavras-chave.

![Detalhes do Pesquisador](assets/profile_view.png)

</details>

---

## 🧠 Como Funciona a Recomendação

A recomendação segue o pipeline definido na Tese, processando o *Score de Afinidade* ($IR$) através de 3 estágios:

1. **Filtragem e Clusterização (IA)**
   - O texto do projeto do aluno é refinado e lematizado;
   - Algoritmos (Birch/KMeans) filtram docentes no mesmo cluster semântico.

2. **Cálculo Multifatorial (6 variáveis)**
   Para os candidatos filtrados, o sistema calcula scores normalizados. Para garantir a execução independente de APIs externas (como Google Scholar), as definições matemáticas foram adaptadas para utilizar exclusivamente a riqueza de dados do **Currículo Lattes (XML)**:

   | Dimensão | Definição Teórica | Implementação (Proxy) | Justificativa Técnica |
   | :--- | :--- | :--- | :--- |
   | 🎯 **Área** ($P_{Area}$) | Hierarquia CNPq | **Coincidência Hierárquica** | Cálculo exato de sobreposição (Grande Área > Área > Subárea). |
   | 🎓 **Experiência** ($P_{Exp}$) | Orientações Ponderadas | **Volume Normalizado** | A contagem total de orientações (Mestrado/Doutorado) reflete a senioridade na formação de RH. |
   | 📚 **Produção** ($P_{Prod}$) | Impacto Bibliométrico | **Volume Ponderado** | A densidade de produção (Artigos/Livros) é um forte indicativo de *output* científico em bases locais. |
   | ⚡ **Eficiência** ($P_{Efi}$) | Taxa de Sucesso | **Taxa de Conclusão** | Razão entre orientações concluídas e totais, inferindo a capacidade de fluxo do orientador. |
   | 🤝 **Colaboração** ($P_{Colab}$) | Grafos de Coautoria | **Densidade de Rede** | O volume de produção colaborativa é utilizado como proxy para a inserção do pesquisador na comunidade. |
   | 🔬 **Pesquisa** ($P_{Pesq}$) | Projetos Financiados | **Recência (Pesquisa Ativa)** | Mede a produção nos últimos 4 anos. Garante que o sistema recomende pesquisadores ativos atualmente, diferenciando-os de perfis inativos. |

   > **Nota:** Todas as métricas são normalizadas dinamicamente ($Score \in [0, 1]$) com base no máximo valor encontrado no cluster de candidatos da busca atual.

![Variáveis usadas na recomendação](assets/variables_used.png)

3. **Ranking Ponderado**
- O usuário pode ajustar os pesos ($\alpha$) de cada variável, permitindo buscas focadas (ex: "Quero alguém com muita produção", ou "Prefiro alguém com muita experiência em orientar").


---

## 📘 Relação com a Tese de Doutorado

Este sistema é uma **implementação aplicada e validável** do modelo proposto na tese:

> *Modelagem Matemática para Recomendação de Orientadores em Programas de Pós-Graduação Stricto Sensu*  
> Radi Melo Martins, 2025.

O núcleo matemático do Índice de Recomendação (IR), suas variáveis e forma de ponderação seguem fielmente o modelo descrito na tese.

### Adaptações para Uso Prático
Algumas adaptações foram realizadas para viabilizar:
- Uso por alunos de graduação e pós;
- Distribuição simples;
- Independência de APIs externas.

Essas adaptações incluem:
- Uso exclusivo de dados do Currículo Lattes (XML);
- Proxies matemáticos para métricas bibliométricas externas;
- Integração de NLP e LLMs **SOMENTE** como camada de interface e explicabilidade, **sem interferir no cálculo do IR (ele não mexe no cálculo matemático do score)**.

Essas decisões **não alteram o modelo conceitual**, apenas sua operacionalização.


---

## 🚀 Funcionalidades

- Extração e processamento de dados do Currículo Lattes;
- Chatbot Inteligente que refina a busca do aluno usando LLMs (Local ou Nuvem);
- Pesos Personalizáveis: O aluno define o que é mais importante (ex: focar em produção ou em experiência);
- Explicabilidade: Cada recomendação vem com uma justificativa gerada por IA;
- Sistema de Favoritos e Ocultação de candidatos;
- Banco de dados SQLite portátil, sem necessidade de instalação de servidores complexos.

---

## 🧩 Estrutura do Projeto

```bash
.
├── streamlit_app.py        # Interface principal em Streamlit  
├── requirements.txt        # Dependências do projeto
├── .gitignore              # Arquivo git que diz quais arquivos ignorar enviar para versionamento
├── data.zip                # Pasta com os dados, basta extrair
│
├── data/
│   └── base_recomendacao.db   # Aparecerá pós extração do ".zip", é um arquivo banco de dados SQLite com dados já inseridos
│
├── utils/
│   ├── db_utils.py             # Conexão e utilidades do banco SQLite
│   └── thesis_recommend.py    # Motor de recomendação (SQLite + k-means + clustering)
│
└── assets/
    ├── legacy-versions/    # Pasta com prints de versões mais antigas
    └── example.png         # Pasta para guardar prints de versões do projeto (facilita na hora de mostra-los no README)
```

---

## 💾 Estrutura de Dados
O projeto utiliza um banco de dados **SQLite** portável, estruturado para relacionar produções, orientações e áreas de conhecimento de forma eficiente.

![Schema do Banco de Dados](assets/db_schema.png)

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+** — linguagem de programação;
- **Streamlit** — interface web interativa;
- **SQLite** — banco relacional principal;
- **spaCy** — processamento de linguagem natural;
- **Pandas** — manipulação de dados;
- **Scikit-learn** — cálculo de métricas e pontuações;
- **SQLite3** — conexão com SQLite.

---

## ⚙️ Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/LuanVitorCD/GCA_ChatBotRecomendation.git
cd GCA_ChatBotRecomendation
```

### 2. Crie um ambiente virtual
- Windows
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

- Linux/Mac
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Baixar modelo de linguagem
```bash
python -m spacy download pt_core_news_md
```

---

## ▶️ Execução

### Modo Real (SQLite)
1. Extraia a pasta zipada com o .db `data.zip`;
2. Configure na sidebar:
   - (se selecionado no provedor `Nuvem (Gemini)`) as credenciais de API Gemini que utilizará;
     
   ![Credenciais API](assets/example_geminiapi_key.png)

   - (se selecionado no provedor `Local (Ollama)`) qual o modelo LLM rodando no Ollama que utilizará.
     
   ![Credenciais API](assets/example_ollamalocal_model.png)
   
3. Rode a aplicação:
   ```bash
   streamlit run streamlit_app.py
   ```
4. Digite um prompt com sua área e interesses (ex: “Graduado em Ciência da Computação com interesse em pós focando em Modelagem Matemática e Machine Learning”) e clique em **Recomendar**.

---

## 👩‍💻 Autoria

Desenvolvido como parte do grupo de pesquisa GCA (Grupo de Computação Aplicada).

A lógica do modelo da tese em **Scikit-learn** é fixa, enquanto os módulos auxiliares são reimplementados em Python para maior flexibilidade e integração moderna.
