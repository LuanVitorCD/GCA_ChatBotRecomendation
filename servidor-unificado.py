# -*- coding: utf-8 -*-

# --------------------------------------------------------------------------- #
#                                   IMPORTS                                   #
# --------------------------------------------------------------------------- #
# Framework web
from flask import Flask, request

# Processamento de linguagem natural
import spacy

# Banco de dados e manipulação de dados
import psycopg2
import pandas as pd
import numpy as np

# Machine Learning e Clustering
from sklearn.cluster import Birch, KMeans
from sklearn.preprocessing import Normalizer
from sklearn.feature_extraction.text import TfidfVectorizer

# Outros
import datetime

# --------------------------------------------------------------------------- #
#                                 CLASSE Areas                                #
#             (Originalmente em sqls/areas.py)                                #
# --------------------------------------------------------------------------- #
class Areas(object):
    """
    Busca orientadores no banco de dados com base nas áreas de pesquisa
    fornecidas no texto original.
    """
    def __init__(self, originalText):
        self.originalText = originalText

    def getPossibleAdvisors(self):
        con = psycopg2.connect(host='localhost', database='mestrado', user='postgres', password='admin')
        cur = con.cursor()
        sql_data =  "select id_pessoa from ppg "
        sql_data += "inner join pessoa_ppg on ppg.id = pessoa_ppg.id_ppg "
        sql_data += "where lower(area1) in ( "
        for word in self.originalText.split(" "):
          sql_data += "'" + word.lower() + "'"+ ", "
        sql_data = sql_data[:-2]
        sql_data += ")"
        sql_data += "or lower(area2) in ( "
        for word in self.originalText.split(" "):
          sql_data += "'" + word.lower() + "'"+ ", "
        sql_data = sql_data[:-2]
        sql_data += ")"
        sql_data += "or lower(area3) in ( "
        for word in self.originalText.split(" "):
          sql_data += "'" + word.lower() + "'"+ ", "
        sql_data = sql_data[:-2]
        sql_data += ")"

        cur.execute(sql_data)
        data = cur.fetchall()
        con.close()
        
        ids = pd.DataFrame(data, columns = ['id_pessoa'])
        return ', '.join(ids.id_pessoa.astype(str).values)

# --------------------------------------------------------------------------- #
#                          CLASSE ClusterPalavras                             #
#         (Originalmente em clustering/cluster_palavras.py)                   #
# --------------------------------------------------------------------------- #
class ClusterPalavras(object):
    """
    Realiza o primeiro nível de clustering com base na frequência de palavras
    do dataset de publicações.
    """
    kmeans = None
    headerDs = None
    finalDataFrame = None

    def generateCluster(self, ids, clustersAmount, export=False): 
        start = datetime.datetime.now()
        con = psycopg2.connect(host='localhost', database='mestrado', user='postgres', password='admin')
        cur = con.cursor()
        sql_data = "select * from dataset where linha not like 'id_pessoa%' and id_pessoa in ("+ids+")"
        sql_header = 'select * from dataset where id_pessoa = 0'
        cur.execute(sql_data)
        data = cur.fetchall()
        cur.execute(sql_header)
        header = cur.fetchall()
        con.close()

        dataFrame = pd.DataFrame(data)
        dataFrameHeader = pd.DataFrame(header)
        dataFrame = pd.DataFrame(dataFrame[0].str.split(',').tolist(), columns=dataFrameHeader[0].str.split(',').tolist())
        dataFrameWithoutID = dataFrame.drop(axis=1, columns = ['id_pessoa'])

        transformer = Normalizer().fit(dataFrameWithoutID)

        self.kmeans = Birch(n_clusters=clustersAmount).fit(transformer.transform(dataFrameWithoutID))
        dataFrame['classe'] = self.kmeans.labels_

        con2 = psycopg2.connect(host='localhost', database='mestrado', user='postgres', password='admin')
        cur2 = con2.cursor()
        self.finalDataFrame = pd.DataFrame(columns = ['id_pessoa', 'nome_pessoa', 'classe'])
        for index, row in dataFrame[['id_pessoa', 'classe']].iterrows():
            sql_pessoa = "select nome from pessoa where id = " + row['id_pessoa'];
            cur2.execute(sql_pessoa)
            data_pessoa = cur2.fetchall()
            nome = data_pessoa[0][0]
            self.finalDataFrame = pd.concat([self.finalDataFrame, pd.DataFrame([[row['id_pessoa'], nome, row['classe']]],columns=['id_pessoa', 'nome_pessoa', 'classe'])])

        cur2.close()
        if export:
            self.finalDataFrame.to_csv('cluster1.csv', sep=',', index=False)
        
        self.headerDs = dataFrameHeader
        end = datetime.datetime.now()
        print(f"ClusterPalavras.generateCluster took: {end - start}")

    def createDatasetHeader(self, dataset):
        newDataset = ''
        headerAsVector = self.headerDs.values.tolist()[0][0].split(',')
        for word in dataset.split(' '):
            for wordHeader in headerAsVector:
                if word == wordHeader:
                    newDataset += word + ','
        return newDataset
    
    def countWords(self, dataset):
        retorno = dict()
        for value in dataset.split(','):
            if not value:
                continue
            if value not in retorno:
                retorno[value] = 1
            else:
                retorno[value] +=1
        return retorno

    def predict(self, dataset):
        dataFrameHeader = pd.DataFrame(self.headerDs)[0].str.split(',').tolist()
        dataFrame = pd.DataFrame(np.zeros((1, len(dataFrameHeader[0]))), columns=dataFrameHeader)
        for idx, value in dataset.items():
            if idx in dataFrame.columns:
                dataFrame[idx] = value
        
        dataFrameWithoutID = dataFrame.drop(axis=1, columns = ['id_pessoa'])
        transformer = Normalizer().fit(dataFrameWithoutID)
        classe = self.kmeans.predict(transformer.transform(dataFrameWithoutID))
        return classe[0]
    
    def getAllPeopleIDFromCluster(self, classe):
        return self.finalDataFrame.loc[self.finalDataFrame['classe'] == classe].id_pessoa

# --------------------------------------------------------------------------- #
#                       CLASSE ClusterPalavrasChaves                          #
#      (Originalmente em clustering/cluster_palavras_chaves.py)               #
# --------------------------------------------------------------------------- #
class ClusterPalavrasChaves(object):
    """
    Realiza o segundo nível de clustering com base nas palavras-chave
    mais frequentes dos orientadores.
    """
    kmeans = None
    tfidf = None
    finalDataFrame = None

    def generateCluster(self, whereClause, export=False): 
        con = psycopg2.connect(host='localhost', database='mestrado', user='postgres', password='admin')
        cur = con.cursor()
        sql_data =  " SELECT array_to_string(array_agg(upper(palavra)), ', ') as palavras, id_pessoa FROM ("
        sql_data += " SELECT"
        sql_data += " ROW_NUMBER() OVER (PARTITION BY T.id_pessoa ORDER BY t.qtd desc) AS r, t.*"
        sql_data += " FROM ("
        sql_data += "     select count(*) qtd, palavra, id_pessoa"
        sql_data += "     from palavra_chave"
        sql_data += "     where ano > 2010"
        sql_data += "     group by id_pessoa, palavra"
        sql_data += "     order by count(*) desc"
        sql_data += " ) t"
        sql_data += " order by t.qtd desc"
        sql_data += " ) x"
        sql_data += " WHERE x.r <= 3"
        sql_data += " AND id_pessoa IN (" + whereClause +")"
        sql_data += " group by id_pessoa"
        sql_data += " order by x.id_pessoa;"

        cur.execute(sql_data)
        data = cur.fetchall()
        con.close()

        dataFrame = pd.DataFrame(data, columns = ['palavras', 'id_pessoa'])

        self.tfidf = TfidfVectorizer(
            min_df = 1,
            max_df = 0.95,
            max_features = 8000
        )
        self.tfidf.fit(dataFrame.palavras)
        text = self.tfidf.transform(dataFrame.palavras)
        self.kmeans = KMeans(n_clusters=2).fit(text)

        dataFrame['classe'] = self.kmeans.labels_
        con2 = psycopg2.connect(host='localhost', database='mestrado', user='postgres', password='admin')
        cur2 = con2.cursor()
        self.finalDataFrame = pd.DataFrame(columns = ['id_pessoa', 'nome_pessoa', 'classe'])
        for index, row in dataFrame[['id_pessoa', 'classe']].iterrows():
            sql_pessoa = "select nome from pessoa where id = " + str(row['id_pessoa'])
            cur2.execute(sql_pessoa)
            data_pessoa = cur2.fetchall()
            nome = data_pessoa[0][0]
            self.finalDataFrame = pd.concat([self.finalDataFrame, pd.DataFrame([[row['id_pessoa'], nome, row['classe']]],columns=['id_pessoa', 'nome_pessoa', 'classe'])])

        cur2.close()
        if export:
            self.finalDataFrame.to_csv('cluster2.csv', sep=',', index=False)
        
    def predict(self, text):
        dataFrame = pd.DataFrame(columns = ['palavras'])
        dataFrame.loc[0] = [text]
        transformed = self.tfidf.transform(dataFrame.palavras)
        classe = self.kmeans.predict(transformed)
        return str(classe[0])

    def getAllPeopleIDFromCluster(self, classe):
        return self.finalDataFrame.loc[self.finalDataFrame['classe'] == int(classe)].id_pessoa.astype(str)

# --------------------------------------------------------------------------- #
#                               CLASSE Ranking                                #
#             (Originalmente em sqls/ranking.py)                              #
# --------------------------------------------------------------------------- #
class Ranking(object):
    """
    Calcula o ranking final dos orientadores com base em uma métrica
    que envolve publicações, orientações e qualis.
    """
    def __init__(self, originalText):
        self.originalText = originalText

    def getRanking(self, whereClause, onlyDoctoral):
        if not whereClause:
            return "Nenhum orientador encontrado para os critérios."

        con = psycopg2.connect(host='localhost', database='mestrado', user='postgres', password='admin')
        cur = con.cursor()
        sql_data =  " select pessoa.id, pessoa.nome, COALESCE(publicacoes, 0) + COALESCE(orientacoes, 0) + COALESCE(qualis, 0) as result from "
        sql_data += " 	(select publicacao.id_pessoa, publicacao.valor_publicacao * 0.3 publicacoes, "
        sql_data += " 	orientacao.valor_orientacao * 0.3 orientacoes, qualis.valor_qualis * 0.4 qualis"
        sql_data += " 	from ("
        sql_data += " 		select sum(valor_publicacao) valor_publicacao, id_pessoa from("
        sql_data += " 			SELECT id_pessoa,"
        sql_data += " 			COUNT(pu.id) *"
        sql_data += " 			(CASE"
        sql_data += " 				WHEN TIPO = 'ARTIGO' OR TIPO = 'CAPITULO' THEN 1"
        sql_data += " 				WHEN TIPO = 'LIVRO' THEN 2"
        sql_data += " 				WHEN TIPO = 'TRABALHOS' THEN 0.5"
        sql_data += " 			END) / ( CASE "
        sql_data += " 					WHEN EXTRACT(YEAR from NOW()) = pe.ano_doutorado THEN 1"
        sql_data += " 					ELSE EXTRACT(YEAR from NOW()) - pe.ano_doutorado"
        sql_data += " 				END)"
        sql_data += " 			valor_publicacao"
        sql_data += " 			FROM publicacao pu"
        sql_data += " 			inner join pessoa pe on pe.id = pu.id_pessoa"
        sql_data += " 			WHERE	(TIPO = 'TRABALHOS' AND classificacao_evento IN ('INTERNACIONAL', 'NACIONAL'))"
        sql_data += " 					OR (TIPO = 'LIVRO' AND TIPO_LIVRO = 'LIVRO_PUBLICADO' AND (meio_divulgacao like '%IMPRESSO%' OR meio_divulgacao = 'VARIOS'))"
        sql_data += " 					OR (TIPO = 'CAPITULO' AND (meio_divulgacao like '%IMPRESSO%' OR meio_divulgacao = 'VARIOS'))"
        sql_data += " 					OR (TIPO = 'ARTIGO')"
        sql_data += " 			GROUP BY tipo, pe.id, pu.id_pessoa"
        sql_data += " 		) publicacao"
        sql_data += " 		group by id_pessoa"
        sql_data += " 	) publicacao"
        sql_data += " 	left join ("
        sql_data += " 		select p.id id_pessoa, "
        sql_data += " 		(count(o.*) / (select count(*) from pessoa_ppg where id_pessoa = p.id) )/ (EXTRACT(YEAR from NOW()) - ano_doutorado) valor_orientacao"
        sql_data += " 		from orientacao o"
        sql_data += " 		inner join pessoa p on p.id = o.id_pessoa"
        sql_data += " 		where natureza IN ('MESTRADO', 'DOUTORADO') "
        sql_data += " 		and o.ano >= ano_doutorado"
        sql_data += " 		group by p.id"
        sql_data += " 	) orientacao on orientacao.id_pessoa = publicacao.id_pessoa"
        sql_data += " 	left join ("
        sql_data += " 		select id_pessoa, sum(valor_qualis) valor_qualis from ("
        sql_data += " 			select (count(p.issn) * CASE"
        sql_data += " 					WHEN q.estrato = 'A1' THEN 1"
        sql_data += " 					WHEN q.estrato = 'A2' THEN 0.875"
        sql_data += " 					WHEN q.estrato = 'A3' THEN 0.75"
        sql_data += " 					WHEN q.estrato = 'A4' THEN 0.625"
        sql_data += " 					WHEN q.estrato = 'B1' THEN 0.5"
        sql_data += " 					WHEN q.estrato = 'B2' THEN 0.375"
        sql_data += " 					WHEN q.estrato = 'B3' THEN 0.25"
        sql_data += " 					WHEN q.estrato = 'B4' THEN 0.125"
        sql_data += " 					ELSE 0 "
        sql_data += " 				END / CASE "
        sql_data += " 						WHEN EXTRACT(YEAR from NOW()) = pe.ano_doutorado THEN 1"
        sql_data += " 						ELSE EXTRACT(YEAR from NOW()) - pe.ano_doutorado"
        sql_data += " 					END"
        sql_data += " 			) valor_qualis, p.id_pessoa"
        sql_data += " 			from publicacao p"
        sql_data += " 			inner join pessoa pe on pe.id = p.id_pessoa"
        sql_data += " 			inner join qualis q on REPLACE(q.issn, '-', '') = REPLACE(p.issn, '-', '')"
        sql_data += " 			where REPLACE(p.issn, '-', '') not in (select REPLACE(issn, '-', '') from preda_qualis)"
        sql_data += " 			group by p.id_pessoa, q.estrato, pe.id"
        sql_data += " 		) qualis group by id_pessoa"
        sql_data += " 	) qualis on qualis.id_pessoa = publicacao.id_pessoa) resultados"
        sql_data += " inner join pessoa on pessoa.id = resultados.id_pessoa"
        sql_data += " WHERE pessoa.id in (" + whereClause + ")"
        sql_data += " ORDER BY RESULT DESC"

        cur.execute(sql_data)
        data = cur.fetchall()
        con.close()

        dataFrame = pd.DataFrame(data, columns = ['id', 'nome', 'resultado'])
        # A função getPPGs não foi incluída pois o retorno não estava sendo usado.
        # Se precisar dela, me avise.
        retorno = ""
        for idx in dataFrame.index:
            retorno += str(dataFrame['nome'][idx]) + " - Rating: " + str(float("{:.2f}".format(dataFrame['resultado'][idx]))) + "\n\n"
        
        return retorno if retorno else "Nenhum orientador encontrado após o ranking final."

    def getRankingOnlyDoctors(self, whereClause):
        if not whereClause:
            return "Nenhum orientador encontrado para os critérios."
        
        con = psycopg2.connect(host='localhost', database='mestrado', user='postgres', password='admin')
        cur = con.cursor()
        sql_data =  "select id_pessoa from ppg "
        sql_data += "inner join pessoa_ppg on id_ppg = ppg.id "
        sql_data += "where ppg.doutorado is true "
        sql_data += "and id_pessoa in (" + whereClause + ") "
        sql_data += "group by id_pessoa "

        cur.execute(sql_data)
        data = cur.fetchall()
        con.close()
        
        if not data:
            return "Nenhum orientador com programa de doutorado encontrado no grupo filtrado."

        ids = pd.DataFrame(data, columns = ['id_pessoa'])['id_pessoa'].values
        string_ints = [str(int_val) for int_val in list(ids)]
        
        return self.getRanking(', '.join(string_ints), True)

# --------------------------------------------------------------------------- #
#                             CONFIGURAÇÃO DO SERVIDOR                          #
#                    (Originalmente em server.py)                             #
# --------------------------------------------------------------------------- #
server = Flask(__name__)
nlp = spacy.load('pt_core_news_md')
clusterPalavras = ClusterPalavras()
clusterPalavrasChaves = ClusterPalavrasChaves()

# --------------------------------------------------------------------------- #
#                               ROTAS DA API                                  #
# --------------------------------------------------------------------------- #
@server.route('/predict/', methods=['POST'])
def predict():
    try:
        # 1. Pré-processamento do texto de entrada
        dataset = ''
        originalText = request.data.decode('utf-8').replace(',', '').replace('.', '')
        for token in nlp(originalText):
            dataset += token.lemma_.strip() + ' '
        
        # 2. Filtro inicial por áreas de pesquisa
        ids = Areas(dataset).getPossibleAdvisors()
        if not ids:
            return "Nenhum orientador encontrado para as áreas de pesquisa especificadas."
        
        quantityOfAdvisors = len(ids.split(','))
        clustersAmount = round(quantityOfAdvisors / 6)
        if clustersAmount < 2:
            clustersAmount = 2
        
        # 3. Primeiro clustering (Publicações)
        clusterPalavras.generateCluster(ids, clustersAmount, True)
        retorno = clusterPalavras.createDatasetHeader(dataset)
        counted = clusterPalavras.countWords(retorno)
        result = clusterPalavras.predict(counted)
        ids_df = clusterPalavras.getAllPeopleIDFromCluster(result)
        
        if ids_df.empty:
            return "Não foi possível refinar a busca com o primeiro cluster."
        whereClause = ', '.join(ids_df.values.astype(str))
        
        # 4. Segundo clustering (Palavras-chave)
        clusterPalavrasChaves.generateCluster(whereClause)
        result = clusterPalavrasChaves.predict(originalText)
        ids_df = clusterPalavrasChaves.getAllPeopleIDFromCluster(result)
        
        if ids_df.empty:
            return "Não foi possível refinar a busca com o segundo cluster."
        whereClause = ', '.join(ids_df.values)

        # 5. Ranking final
        return Ranking(originalText).getRanking(whereClause, False)
    except Exception as e:
        print(f"Ocorreu um erro em /predict/: {e}")
        return "Ocorreu um erro interno no servidor.", 500

@server.route('/predict_doutorado/', methods=['POST'])
def predict_doutorado():
    try:
        # 1. Pré-processamento do texto de entrada
        dataset = ''
        originalText = request.data.decode('utf-8').replace(',', '').replace('.', '')
        for token in nlp(originalText):
            dataset += token.lemma_.strip() + ' '
        
        # 2. Filtro inicial por áreas de pesquisa
        ids = Areas(dataset).getPossibleAdvisors()
        if not ids:
            return "Nenhum orientador encontrado para as áreas de pesquisa especificadas."
            
        quantityOfAdvisors = len(ids.split(','))
        clustersAmount = round(quantityOfAdvisors/6)
        if clustersAmount < 2:
            clustersAmount = 2

        # 3. Primeiro clustering (Publicações)
        clusterPalavras.generateCluster(ids, clustersAmount, True)
        retorno = clusterPalavras.createDatasetHeader(dataset)
        counted = clusterPalavras.countWords(retorno)
        result = clusterPalavras.predict(counted)
        ids_df = clusterPalavras.getAllPeopleIDFromCluster(result)

        if ids_df.empty:
            return "Não foi possível refinar a busca com o primeiro cluster."
        whereClause = ', '.join(ids_df.values.astype(str))
        
        # 4. Segundo clustering (Palavras-chave)
        clusterPalavrasChaves.generateCluster(whereClause)
        result = clusterPalavrasChaves.predict(originalText)
        ids_df = clusterPalavrasChaves.getAllPeopleIDFromCluster(result)

        if ids_df.empty:
            return "Não foi possível refinar a busca com o segundo cluster."
        whereClause = ', '.join(ids_df.values)

        # 5. Ranking final (apenas doutores)
        return Ranking(originalText).getRankingOnlyDoctors(whereClause)
    except Exception as e:
        print(f"Ocorreu um erro em /predict_doutorado/: {e}")
        return "Ocorreu um erro interno no servidor.", 500

# --------------------------------------------------------------------------- #
#                             EXECUÇÃO DO SERVIDOR                              #
# --------------------------------------------------------------------------- #
if __name__ == '__main__':
    # O ideal é usar um servidor de produção como Gunicorn ou Waitress
    # Em desenvolvimento, pode usar host='0.0.0.0' para acessar de outros dispositivos na rede
    server.run(host='localhost', port=8080, debug=True)
