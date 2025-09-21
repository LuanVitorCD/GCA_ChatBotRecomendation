# recommend.py - Recomendação com TF-IDF + Cosine Similarity
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def recommend_with_tfidf(student_area, professors, top_k=5, threshold=0.4):
    df = pd.DataFrame(professors)
    if df.empty:
        return []

    texts = df['research'].tolist()
    vectorizer = TfidfVectorizer().fit([student_area] + texts)
    student_vec = vectorizer.transform([student_area])
    prof_vecs = vectorizer.transform(texts)

    similarities = cosine_similarity(student_vec, prof_vecs).flatten()
    df['score'] = similarities

    # Normalizar em relação ao top1
    max_score = df['score'].max()
    if max_score > 0:
        df['percent'] = (df['score'] / max_score * 100).round(2)
    else:
        df['percent'] = 0

    # Filtrar pelo threshold relativo ao top1
    df = df[df['score'] >= max_score * threshold]

    # Ordenar por score decrescente e limitar top_k
    df = df.sort_values(by='score', ascending=False).head(top_k)

    return df.to_dict(orient='records')
