# dataset_generator.py - Conversão de GeradorDeDatasets.java
import pandas as pd

def generate_mock_dataset():
    data = [
        {"id": 1, "name": "Prof. Ana Souza", "research": "Redes neurais, visão computacional"},
        {"id": 2, "name": "Prof. Bruno Lima", "research": "Aprendizado profundo, PLN"},
        {"id": 3, "name": "Prof. Carla Dias", "research": "Sistemas embarcados, IoT"},
    ]
    return pd.DataFrame(data)
