# dataset_generator.py - Versão expandida com 60 professores mockados
import pandas as pd

def generate_mock_dataset():
    data = [
        # ----------- ÁREA DE COMPUTAÇÃO (1-30) -----------
        {"id": 1, "name": "Prof. Ana Souza", "research": "Redes neurais, visão computacional"},
        {"id": 2, "name": "Prof. Bruno Lima", "research": "Aprendizado profundo, PLN"},
        {"id": 3, "name": "Prof. Carla Dias", "research": "Sistemas embarcados, IoT"},
        {"id": 4, "name": "Prof. Daniel Oliveira", "research": "Engenharia de software, métodos ágeis"},
        {"id": 5, "name": "Prof. Elisa Martins", "research": "Ciência de dados, mineração de texto"},
        {"id": 6, "name": "Prof. Fernando Rocha", "research": "Computação gráfica, realidade aumentada"},
        {"id": 7, "name": "Prof. Gabriela Nunes", "research": "Bioinformática, genômica computacional"},
        {"id": 8, "name": "Prof. Henrique Castro", "research": "Segurança da informação, criptografia"},
        {"id": 9, "name": "Prof. Isabel Teixeira", "research": "Educação em computação, e-learning"},
        {"id": 10, "name": "Prof. João Almeida", "research": "Robótica, sistemas autônomos"},
        {"id": 11, "name": "Prof. Karla Mendes", "research": "Banco de dados, big data"},
        {"id": 12, "name": "Prof. Lucas Fernandes", "research": "Processamento de imagens, visão computacional"},
        {"id": 13, "name": "Prof. Mariana Silva", "research": "Interação humano-computador, acessibilidade"},
        {"id": 14, "name": "Prof. Nelson Ribeiro", "research": "Computação em nuvem, sistemas distribuídos"},
        {"id": 15, "name": "Prof. Olivia Pires", "research": "Simulação científica, modelagem matemática"},
        {"id": 16, "name": "Prof. Paulo Gomes", "research": "Engenharia elétrica, automação industrial"},
        {"id": 17, "name": "Prof. Queila Barbosa", "research": "Ciência de redes, análise de tráfego"},
        {"id": 18, "name": "Prof. Ricardo Tavares", "research": "Teoria da computação, algoritmos"},
        {"id": 19, "name": "Prof. Sabrina Costa", "research": "Computação quântica, criptografia pós-quântica"},
        {"id": 20, "name": "Prof. Tiago Moreira", "research": "Inteligência artificial aplicada à medicina"},
        {"id": 21, "name": "Prof. Ursula Andrade", "research": "Processamento de linguagem natural, chatbots"},
        {"id": 22, "name": "Prof. Victor Lima", "research": "Sistemas operacionais, kernel Linux"},
        {"id": 23, "name": "Prof. Wagner Duarte", "research": "Engenharia de software orientada a serviços"},
        {"id": 24, "name": "Prof. Xênia Carvalho", "research": "Aprendizado por reforço, agentes inteligentes"},
        {"id": 25, "name": "Prof. Yuri Campos", "research": "Redes sem fio, 5G e IoT"},
        {"id": 26, "name": "Prof. Zélia Furtado", "research": "Ciência de materiais, simulação computacional"},
        {"id": 27, "name": "Prof. Arthur Rezende", "research": "Visão computacional aplicada à agricultura"},
        {"id": 28, "name": "Prof. Beatriz Lopes", "research": "Deep learning para processamento de fala"},
        {"id": 29, "name": "Prof. Caio Pereira", "research": "Blockchain, contratos inteligentes"},
        {"id": 30, "name": "Prof. Diana Moura", "research": "Análise de sentimentos, mídias sociais"},

        # ----------- OUTRAS ÁREAS (31-60) -----------
        {"id": 31, "name": "Prof. Eduardo Ramos", "research": "Cardiologia, insuficiência cardíaca"},
        {"id": 32, "name": "Prof. Fernanda Azevedo", "research": "Oncologia, terapias experimentais"},
        {"id": 33, "name": "Prof. Gustavo Prado", "research": "Nutrição esportiva, metabolismo humano"},
        {"id": 34, "name": "Prof. Helena Duarte", "research": "Educação física, biomecânica do movimento"},
        {"id": 35, "name": "Prof. Igor Santos", "research": "Fisioterapia, reabilitação motora"},
        {"id": 36, "name": "Prof. Juliana Castro", "research": "Design de interação, experiência do usuário"},
        {"id": 37, "name": "Prof. Kleber Martins", "research": "Design gráfico, tipografia digital"},
        {"id": 38, "name": "Prof. Larissa Barbosa", "research": "Jornalismo investigativo, ética da comunicação"},
        {"id": 39, "name": "Prof. Marcelo Vieira", "research": "Comunicação digital, mídias sociais"},
        {"id": 40, "name": "Prof. Natália Ferreira", "research": "Direito constitucional, direitos humanos"},
        {"id": 41, "name": "Prof. Otávio Mendes", "research": "Direito penal, criminologia"},
        {"id": 42, "name": "Prof. Patrícia Nogueira", "research": "Direito ambiental, sustentabilidade"},
        {"id": 43, "name": "Prof. Rafael Almeida", "research": "Agronomia, cultivo sustentável"},
        {"id": 44, "name": "Prof. Simone Lopes", "research": "Engenharia agrícola, irrigação inteligente"},
        {"id": 45, "name": "Prof. Thiago Correia", "research": "Veterinária, saúde animal"},
        {"id": 46, "name": "Prof. Úrsula Carvalho", "research": "Psicologia clínica, saúde mental"},
        {"id": 47, "name": "Prof. Vitor Gomes", "research": "Psicologia social, comportamento de grupo"},
        {"id": 48, "name": "Prof. William Silva", "research": "Economia, mercado financeiro"},
        {"id": 49, "name": "Prof. Ximena Torres", "research": "Administração, empreendedorismo"},
        {"id": 50, "name": "Prof. Yara Souza", "research": "Ciência política, políticas públicas"},
        {"id": 51, "name": "Prof. Zacarias Pinto", "research": "História contemporânea, política internacional"},
        {"id": 52, "name": "Prof. Adriana Moura", "research": "Sociologia urbana, movimentos sociais"},
        {"id": 53, "name": "Prof. Bernardo Leite", "research": "Antropologia cultural, etnografia"},
        {"id": 54, "name": "Prof. Clarissa Fonseca", "research": "Letras, análise literária"},
        {"id": 55, "name": "Prof. Douglas Ribeiro", "research": "Linguística, variação e mudança"},
        {"id": 56, "name": "Prof. Estela Duarte", "research": "Pedagogia, metodologias ativas"},
        {"id": 57, "name": "Prof. Felipe Rocha", "research": "Biologia molecular, biotecnologia"},
        {"id": 58, "name": "Prof. Gabriela Lima", "research": "Ecologia, conservação ambiental"},
        {"id": 59, "name": "Prof. Hugo Moreira", "research": "Geografia, mudanças climáticas"},
        {"id": 60, "name": "Prof. Isabela Cardoso", "research": "Arqueologia, patrimônio cultural"},
    ]
    return pd.DataFrame(data)

if __name__ == "__main__":
    df = generate_mock_dataset()
    print(df.head(15))
    print(f"Total de professores mockados: {len(df)}")