# recommend.py - Adaptado de ProcessadorQualis.java
import numpy as np

def profile_to_feature_vector(profile):
    total_pubs = len(profile.get("publications", []))
    return np.array([total_pubs]).reshape(1, -1)

def recommend_mock(student_area, professors):
    ranked = sorted(professors, key=lambda p: student_area.lower() in p['research'].lower(), reverse=True)
    return ranked[:5]
