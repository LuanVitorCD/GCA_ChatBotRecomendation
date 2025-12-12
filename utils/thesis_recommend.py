# -*- coding: utf-8 -*-
# thesis_recommend.py - Implementação Fiel e Expandida da Tese
# Lógica: Filtro SQL -> Clusterização (Birch/KMeans) -> Ranking Multifatorial (6 Variáveis)

import spacy
import pandas as pd
import numpy as np
import datetime
import re
from sklearn.cluster import Birch, KMeans
from sklearn.preprocessing import Normalizer
from sklearn.feature_extraction.text import TfidfVectorizer
from utils.db_utils import get_db_connection

try:
    nlp = spacy.load('pt_core_news_md')
except IOError:
    nlp = None

# =========================================================================== #
#                                 CLASSE Areas                                #
# =========================================================================== #
class Areas(object):
    def __init__(self, originalText):
        self.originalText = originalText

    def getPossibleAdvisors(self):
        conn = get_db_connection()
        cur = conn.cursor()
        words = self.originalText.split(" ")
        conditions = []
        params = []
        for word in words:
            term = word.lower()
            conditions.append(f"(LOWER(area1) LIKE ? OR LOWER(area2) LIKE ? OR LOWER(area3) LIKE ?)")
            params.extend([f"%{term}%", f"%{term}%", f"%{term}%"])
        where_clause = " OR ".join(conditions)
        sql = f"SELECT DISTINCT p.id_pessoa FROM ppg INNER JOIN pessoa_ppg p ON ppg.id = p.id_ppg WHERE {where_clause}"
        try:
            cur.execute(sql, params)
            data = cur.fetchall()
            ids = [str(row['id_pessoa']) for row in data]
            return ', '.join(ids)
        finally:
            conn.close()

# =========================================================================== #
#                          CLASSE ClusterPalavras                             #
# =========================================================================== #
class ClusterPalavras(object):
    kmeans = None
    headerDs = None
    finalDataFrame = None

    def generateCluster(self, ids, clustersAmount): 
        if not ids: return
        conn = get_db_connection()
        try:
            sql_data = f"select * from dataset where linha not like 'id_pessoa%' and id_pessoa in ({ids})"
            sql_header = "select * from dataset where id_pessoa = 0"
            df_data = pd.read_sql_query(sql_data, conn)
            df_header = pd.read_sql_query(sql_header, conn)
        except:
            conn.close()
            return
        conn.close()

        if df_data.empty: return

        if not df_header.empty:
            cols = df_header.iloc[0]['linha'].split(',')
        else:
            return 

        data_expanded = df_data['linha'].str.split(',', expand=True)
        if data_expanded.shape[1] == len(cols):
            data_expanded.columns = cols
        
        data_expanded['id_pessoa'] = df_data['id_pessoa']
        df_clustering = data_expanded.drop(columns=['id_pessoa'], errors='ignore')
        df_clustering = df_clustering.apply(pd.to_numeric, errors='coerce').fillna(0)

        transformer = Normalizer().fit(df_clustering)
        transformed_data = transformer.transform(df_clustering)
        self.kmeans = Birch(n_clusters=clustersAmount).fit(transformed_data)
        
        self.finalDataFrame = pd.DataFrame()
        self.finalDataFrame['id_pessoa'] = df_data['id_pessoa']
        self.finalDataFrame['classe'] = self.kmeans.labels_
        self.headerDs = cols

    def createDatasetHeader(self, dataset):
        newDataset = ''
        if not self.headerDs: return ""
        for word in dataset.split(' '):
            if word in self.headerDs: newDataset += word + ','
        return newDataset
    
    def countWords(self, dataset):
        retorno = dict()
        for value in dataset.split(','):
            if not value: continue
            retorno[value] = retorno.get(value, 0) + 1
        return retorno

    def predict(self, dataset_dict):
        if not self.headerDs: return 0
        vector = np.zeros((1, len(self.headerDs)))
        df_vec = pd.DataFrame(vector, columns=self.headerDs)
        for word, count in dataset_dict.items():
            if word in df_vec.columns: df_vec.at[0, word] = count
        if 'id_pessoa' in df_vec.columns: df_vec = df_vec.drop(columns=['id_pessoa'])
        transformer = Normalizer().fit(df_vec)
        classe = self.kmeans.predict(transformer.transform(df_vec))
        return classe[0]
    
    def getAllPeopleIDFromCluster(self, classe):
        if self.finalDataFrame is None: return pd.Series()
        return self.finalDataFrame.loc[self.finalDataFrame['classe'] == classe]['id_pessoa']

# =========================================================================== #
#                       CLASSE ClusterPalavrasChaves                          #
# =========================================================================== #
class ClusterPalavrasChaves(object):
    kmeans = None
    tfidf = None
    finalDataFrame = None

    def generateCluster(self, whereClause): 
        conn = get_db_connection()
        sql = f"""
         SELECT GROUP_CONCAT(UPPER(palavra), ', ') as palavras, id_pessoa 
         FROM (SELECT palavra, id_pessoa FROM palavra_chave WHERE ano > 2010 AND id_pessoa IN ({whereClause}) ORDER BY id_pessoa) 
         GROUP BY id_pessoa
        """
        try:
            df = pd.read_sql_query(sql, conn)
        except:
            df = pd.DataFrame()
        finally:
            conn.close()

        if df.empty: return

        self.tfidf = TfidfVectorizer(min_df=1, max_df=0.95, max_features=8000)
        text_matrix = self.tfidf.fit_transform(df['palavras'].fillna(''))
        
        true_k = min(2, len(df))
        if true_k < 2: true_k = 1
            
        self.kmeans = KMeans(n_clusters=true_k).fit(text_matrix)
        self.finalDataFrame = df.copy()
        self.finalDataFrame['classe'] = self.kmeans.labels_
        
        conn = get_db_connection()
        names_df = pd.read_sql_query(f"SELECT id, nome FROM pessoa WHERE id IN ({whereClause})", conn)
        conn.close()
        self.finalDataFrame = self.finalDataFrame.merge(names_df, left_on='id_pessoa', right_on='id', how='left')

    def predict(self, text):
        if not self.tfidf: return "0"
        transformed = self.tfidf.transform([text])
        classe = self.kmeans.predict(transformed)
        return str(classe[0])

    def getAllPeopleIDFromCluster(self, classe):
        if self.finalDataFrame is None: return pd.Series()
        return self.finalDataFrame.loc[self.finalDataFrame['classe'] == int(classe)]['id_pessoa'].astype(str)

# =========================================================================== #
#             CLASSE Ranking (Adaptada para P_Area da Tese)                   #
# =========================================================================== #
class Ranking(object):
    def __init__(self, originalText, student_area_struct=None):
        self.originalText = originalText
        # Estrutura vinda do LLM: {'grande_area': '...', 'area': '...', 'sub_area': '...'}
        self.student_area_struct = student_area_struct or {}

    def _calculate_hierarchical_score(self, prof_hierarchy_str):
        """
        Calcula P_Area conforme Eq 5.2 da Tese:
        GA (1pt) + A (2pts) + SA (3pts) + E (4pts).
        Normaliza dividindo por 10.
        """
        if not prof_hierarchy_str or not self.student_area_struct:
            return 0.0

        best_score = 0.0
        
        # O banco retorna várias áreas concatenadas por ' | '
        # Formato esperado da string: "GA#A#SA#E | GA#A#SA#E..."
        areas_prof = prof_hierarchy_str.split(' | ')
        
        # Normalização dos termos do aluno para comparação
        s_ga = str(self.student_area_struct.get('grande_area', '')).lower().strip()
        s_a  = str(self.student_area_struct.get('area', '')).lower().strip()
        s_sa = str(self.student_area_struct.get('sub_area', '')).lower().strip()
        s_e  = str(self.student_area_struct.get('especialidade', '')).lower().strip()

        for area_str in areas_prof:
            parts = area_str.split('#')
            # Garante que temos 4 partes (preenche com vazio se faltar)
            parts += [''] * (4 - len(parts))
            p_ga, p_a, p_sa, p_e = [p.lower().strip() for p in parts[:4]]
            
            current_score = 0.0
            
            # Comparação Hierárquica Estrita
            # 1. Grande Área (Peso 1)
            if s_ga and (s_ga in p_ga or p_ga in s_ga): 
                current_score += 1.0
                
                # 2. Área (Peso 2) - Só pontua se GA bateu
                if s_a and (s_a in p_a or p_a in s_a):
                    current_score += 2.0
                    
                    # 3. Subárea (Peso 3) - Só pontua se A bateu
                    if s_sa and (s_sa in p_sa or p_sa in s_sa):
                        current_score += 3.0
                        
                        # 4. Especialidade (Peso 4) - Só pontua se SA bateu
                        if s_e and (s_e in p_e or p_e in s_e):
                            current_score += 4.0
            
            if current_score > best_score:
                best_score = current_score
        
        # Normalização (Máximo possível é 10)
        return min(1.0, best_score / 10.0)

    def _calculate_semantic_fallback(self, user_text, prof_text):
        """Fallback: Jaccard simples se a hierarquia CNPq estiver vazia"""
        if not prof_text: return 0.0
        def tokenize(text): return set(re.findall(r'\w+', str(text).lower()))
        u_tok = tokenize(user_text)
        p_tok = tokenize(prof_text)
        if not u_tok: return 0.0
        intersection = u_tok.intersection(p_tok)
        return min(1.0, 0.2 + (0.8 * (len(intersection) / len(u_tok))))

    def getRanking(self, whereClause, weights):
        if not whereClause: return []
        conn = get_db_connection()
        
        # SQL Modificado para buscar a Hierarquia CNPq concatenada e remover dependência de status
        sql = f"""
        SELECT 
            pe.id, pe.nome, pe.ano_doutorado, pe.titulacao, pe.universidade,
            
            (SELECT sigla_universidade FROM ppg JOIN pessoa_ppg pp ON ppg.id = pp.id_ppg WHERE pp.id_pessoa = pe.id LIMIT 1) as sigla_inst,

            -- Áreas de Conhecimento Estruturadas (Formato: GA#A#SA#E)
            (SELECT GROUP_CONCAT(
                COALESCE(grande_area_conhecimento, '') || '#' || 
                COALESCE(area_conhecimento, '') || '#' || 
                COALESCE(sub_area_conhecimento, '') || '#' || 
                COALESCE(especialidade, ''), 
                ' | ') 
             FROM area_conhecimento WHERE id_pessoa = pe.id
            ) as hierarquia_cnpq,

            -- Títulos de Publicações (Para Fallback de Área se hierarquia for nula)
            (SELECT GROUP_CONCAT(titulo, ' ') FROM publicacao WHERE id_pessoa = pe.id LIMIT 10) as fallback_text,

            (SELECT GROUP_CONCAT(idioma, ', ') FROM (SELECT DISTINCT idioma FROM publicacao WHERE id_pessoa = pe.id AND idioma IS NOT NULL AND idioma != '')) as idiomas_publicacao,

            -- P_PROD: Volume de Produção (Livros peso 2, Outros 1)
            (SELECT COALESCE(SUM(CASE WHEN tipo='LIVRO' THEN 2.0 ELSE 1.0 END), 0) FROM publicacao WHERE id_pessoa = pe.id) as raw_prod,

            -- P_EXP: Experiência
            -- Total de Orientações (Mestrado + Doutorado)
            (SELECT CAST(COUNT(*) AS FLOAT) FROM orientacao WHERE id_pessoa = pe.id AND natureza IN ('MESTRADO', 'DOUTORADO')) as total_orientacoes,
            
            -- P_EFI: Eficiência
            -- Como não temos status 'CONCLUIDA', usamos o ano como proxy: orientações com ano < 2024 são assumidas concluídas
            (SELECT CAST(COUNT(*) AS FLOAT) FROM orientacao WHERE id_pessoa = pe.id AND natureza IN ('MESTRADO', 'DOUTORADO') AND ano < 2024) as orientacoes_concluidas_est,
            
            -- P_QUAL: Qualidade (Qualis A1/A2) - Base para Produção/Pesquisa
            (SELECT COALESCE(SUM(CASE WHEN q.estrato IN ('A1','A2') THEN 1.0 ELSE 0.2 END), 0) FROM publicacao p JOIN qualis q ON p.issn = q.issn WHERE p.id_pessoa = pe.id) as raw_qual,
             
            -- P_COLAB: Colaboração
            -- Contagem simples de publicações como proxy de rede, ajustado
            (SELECT CAST(COUNT(*) AS FLOAT) FROM publicacao WHERE id_pessoa = pe.id) as total_pubs

        FROM pessoa pe WHERE pe.id IN ({whereClause})
        """
        
        try:
            df = pd.read_sql_query(sql, conn)
        except Exception as e:
            print(f"Erro Ranking SQL: {e}")
            return []
        finally:
            conn.close()
            
        if df.empty: return []

        results = []
        current_year = datetime.datetime.now().year
        
        w_area = weights.get('area', 0.2)
        w_exp = weights.get('exp', 0.2)
        w_prod = weights.get('prod', 0.2)
        w_efi = weights.get('efi', 0.1)
        w_colab = weights.get('colab', 0.1)
        w_pesq = weights.get('pesq', 0.1) 
        w_qual = weights.get('qual', 0.1) 

        # --- NORMALIZAÇÃO RELATIVA AO GRUPO (Tese) ---
        # Encontra os máximos do dataset atual para normalizar (Eq. 3, 5, 8)
        max_prod = df['raw_prod'].max() or 1.0
        max_orientacoes = df['total_orientacoes'].max() or 1.0
        max_qual = df['raw_qual'].max() or 1.0
        max_pubs_total = df['total_pubs'].max() or 1.0

        for _, row in df.iterrows():
            anos = max(1, current_year - (row['ano_doutorado'] or current_year))
            
            # 1. P_AREA (Híbrido)
            hierarquia = row['hierarquia_cnpq']
            s_area = 0.0
            if hierarquia and len(hierarquia) > 5:
                s_area = self._calculate_hierarchical_score(hierarquia)
            if s_area == 0.0:
                prof_context = str(row['fallback_text'])
                s_area = self._calculate_semantic_fallback(self.originalText, prof_context)

            # 2. P_EXPERIENCIA (Tese Eq. 3 simplificada para o Artigo)
            # Normalização pelo máximo do grupo (Volume Relativo)
            s_exp = row['total_orientacoes'] / max_orientacoes

            # 3. P_EFICIENCIA (Tese Eq. 6)
            # Como não temos status explícito, usamos a razão de orientações 'antigas' (provavelmente concluídas) sobre o total
            # Isso é uma aproximação válida dada a limitação do banco
            if row['total_orientacoes'] > 0:
                s_efi = row['orientacoes_concluidas_est'] / row['total_orientacoes']
            else:
                s_efi = 0.0

            # 4. P_PRODUCAO (Tese Eq. 7 adaptada)
            # Normalização pelo máximo de produção ponderada
            s_prod = row['raw_prod'] / max_prod

            # 5. P_COLABORACAO (Tese Eq. 8)
            # Proxy: Volume de publicações normalizado (indicativo de rede de coautoria ativa)
            # Na falta de dados de grafos, quem publica mais tende a colaborar mais.
            s_colab = row['total_pubs'] / max_pubs_total

            # 6. P_PESQUISA
            # Proxy: Qualidade da produção (A1/A2) normalizada
            s_pesq = row['raw_qual'] / max_qual
            
            # Qualidade usada para cálculo
            s_qual = row['raw_qual'] / max_qual

            # --- SCORE FINAL (Soma Ponderada) ---
            final_score = (s_area * w_area) + \
                          (s_exp * w_exp) + \
                          (s_prod * w_prod) + \
                          (s_efi * w_efi) + \
                          (s_colab * w_colab) + \
                          (s_pesq * w_pesq)
            
            # Formatação para exibição
            areas_display = row['hierarquia_cnpq'].replace('#', ' > ').split(' | ')[0] if row['hierarquia_cnpq'] else "Inferido por Publicações"

            results.append({
                'nome': row['nome'],
                'id': str(row['id']),
                'hybrid_score': final_score,
                'info': {
                    'titulacao': row['titulacao'],
                    'universidade': row['universidade'],
                    'sigla': row['sigla_inst'],
                    'areas': areas_display[:100] + "...",
                    'raw_hierarchy': row['hierarquia_cnpq'], # IMPORTANTE: Envia a string bruta para o frontend fazer o split correto
                    'ano_doutorado': row['ano_doutorado'],
                    'idiomas': row['idiomas_publicacao']
                },
                'details': {
                    'raw_area': s_area,
                    'raw_prod': s_prod, 'raw_exp': s_exp, 'raw_qual': s_qual,
                    'raw_efi': s_efi, 'raw_colab': s_colab, 'raw_pesq': s_pesq,
                    'abs_prod': row['raw_prod'],
                    'abs_exp': row['total_orientacoes'],
                    'abs_qual': row['raw_qual']
                }
            })
            
        results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return results

# Orchestrator
clusterPalavras = ClusterPalavras()
clusterPalavrasChaves = ClusterPalavrasChaves()

def thesis_recommendation_engine(originalText, only_doctors=False, weights=None, student_area_struct=None):
    if weights is None: weights = {}
    if nlp is None: raise ImportError("Spacy não carregado.")

    try:
        # 1. Pré-processamento
        dataset = ''
        cleaned = originalText.replace(',', '').replace('.', '')
        for token in nlp(cleaned):
            if not token.is_stop: dataset += token.lemma_.strip() + ' '
        
        # 2. Filtro de Área
        ids = Areas(dataset).getPossibleAdvisors()
        if not ids: return []
        
        # 3. Clusterização
        id_list = ids.split(', ')
        # Birch
        clusterPalavras.generateCluster(ids, max(2, round(len(id_list)/6)))
        
        if clusterPalavras.finalDataFrame is None or clusterPalavras.finalDataFrame.empty:
             ids_df = pd.Series(id_list)
        else:
            header = clusterPalavras.createDatasetHeader(dataset)
            counted = clusterPalavras.countWords(header)
            result = clusterPalavras.predict(counted)
            ids_df = clusterPalavras.getAllPeopleIDFromCluster(result)
        
        if ids_df.empty: return []
        whereClause = ', '.join(ids_df.values.astype(str))
        
        # KMeans Keywords
        clusterPalavrasChaves.generateCluster(whereClause)
        if clusterPalavrasChaves.finalDataFrame is not None and not clusterPalavrasChaves.finalDataFrame.empty:
            result = clusterPalavrasChaves.predict(cleaned)
            ids_df = clusterPalavrasChaves.getAllPeopleIDFromCluster(result)
            if not ids_df.empty: whereClause = ', '.join(ids_df.values)

        # 4. Ranking (Passando a estrutura de área do aluno)
        return Ranking(cleaned, student_area_struct).getRanking(whereClause, weights)

    except Exception as e:
        print(f"Erro Engine: {e}")
        return []