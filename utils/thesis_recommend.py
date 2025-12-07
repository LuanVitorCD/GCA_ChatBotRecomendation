# -*- coding: utf-8 -*-
# thesis_recommend.py - Implementação Fiel e Expandida da Tese
# Lógica: Filtro SQL -> Clusterização (Birch/KMeans) -> Ranking Multifatorial (6 Variáveis)

import spacy
import pandas as pd
import numpy as np
import datetime
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
        # Tenta ler dataset. Se falhar (tabela não existe), retorna vazio
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

        # Processamento de dados CSV-like no banco
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
        # Adaptação SQLite: GROUP_CONCAT
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
#             CLASSE Ranking (Expansão para 6 Variáveis da Tese)              #
# =========================================================================== #
class Ranking(object):
    def __init__(self, originalText):
        self.originalText = originalText

    def getRanking(self, whereClause, weights):
        if not whereClause: return []
        conn = get_db_connection()
        
        # Extração de Métricas Brutas para as 6 Dimensões (Adaptado para SQLite)
        sql = f"""
        SELECT 
            pe.id, pe.nome, pe.ano_doutorado,
            
            -- P_PROD: Volume de Produção (Livros peso 2, Outros 1)
            (SELECT COALESCE(SUM(CASE WHEN tipo='LIVRO' THEN 2.0 ELSE 1.0 END), 0) 
             FROM publicacao WHERE id_pessoa = pe.id) as raw_prod,

            -- P_EXP: Experiência (Contagem de Orientações Mestrado/Doutorado)
            (SELECT CAST(COUNT(*) AS FLOAT) FROM orientacao 
             WHERE id_pessoa = pe.id AND natureza IN ('MESTRADO', 'DOUTORADO')) as raw_exp,
            
            -- P_EFI: Eficiência (Orientações Concluídas Recentes como proxy)
            (SELECT CAST(COUNT(*) AS FLOAT) FROM orientacao 
             WHERE id_pessoa = pe.id AND ano < 2024) as raw_efi,

            -- P_QUAL: Qualidade (Qualis A1/A2)
            (SELECT COALESCE(SUM(CASE WHEN q.estrato IN ('A1','A2') THEN 1.0 ELSE 0.2 END), 0) 
             FROM publicacao p JOIN qualis q ON p.issn = q.issn 
             WHERE p.id_pessoa = pe.id) as raw_qual,
             
            -- P_COLAB: Colaboração (Proxy baseado em volume total de publicações, assumindo coautoria média)
            (SELECT CAST(COUNT(*) AS FLOAT) FROM publicacao WHERE id_pessoa = pe.id) * 0.15 as raw_colab

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
        
        # Recupera pesos (com valores default da Tese/Original)
        w_area = weights.get('area', 0.2)
        w_exp = weights.get('exp', 0.2)
        w_prod = weights.get('prod', 0.2)
        w_efi = weights.get('efi', 0.1)
        w_colab = weights.get('colab', 0.1)
        w_pesq = weights.get('pesq', 0.1) 
        w_qual = weights.get('qual', 0.1) 

        for _, row in df.iterrows():
            # Normalização pelo tempo de doutorado (evita divisão por zero)
            anos = max(1, current_year - (row['ano_doutorado'] or current_year))
            
            # Normalizações Simples
            s_prod = row['raw_prod'] / anos
            s_exp = row['raw_exp'] / anos
            
            # Eficiência: Razão Concluídas / (Total + 1)
            s_efi = row['raw_efi'] / (row['raw_exp'] + 1)
            
            s_qual = row['raw_qual'] / anos
            s_colab = row['raw_colab'] / anos
            
            # Pesquisa (Proxy: 50% da produção técnica/bibliográfica)
            s_pesq = s_prod * 0.5 
            
            # Área (Já filtrada, então é 1.0 para quem está aqui)
            s_area = 1.0

            # Fórmula Linear da Tese (Soma Ponderada)
            final_score = (s_area * w_area) + \
                          (s_exp * w_exp) + \
                          (s_prod * w_prod) + \
                          (s_efi * w_efi) + \
                          (s_colab * w_colab) + \
                          (s_pesq * w_pesq) + \
                          (s_qual * w_qual) 
            
            results.append({
                'nome': row['nome'],
                'id': str(row['id']),
                'hybrid_score': final_score,
                'details': {
                    'raw_prod': s_prod, 'raw_exp': s_exp, 'raw_qual': s_qual,
                    'raw_efi': s_efi, 'raw_colab': s_colab
                }
            })
            
        results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return results

# Orchestrator
clusterPalavras = ClusterPalavras()
clusterPalavrasChaves = ClusterPalavrasChaves()

def thesis_recommendation_engine(originalText, only_doctors=False, weights=None):
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

        # 4. Ranking (Com os 6 pesos da Tese)
        return Ranking(cleaned).getRanking(whereClause, weights)

    except Exception as e:
        print(f"Erro Engine: {e}")
        return []