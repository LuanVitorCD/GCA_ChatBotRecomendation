package br.com.seuprojeto.dataset;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

// IMPORTANTE: O código abaixo assume a existência de classes em um pacote 'lattes'
// que não foram fornecidas, como:
// import lattes.Pessoa;
// import lattes.PessoaBD;
// import lattes.Publicacao;
// import lattes.PublicacaoBD;
// import lattes.PublicacaoSC;
// import lattes.AreaConhecimento;
// import lattes.AreaConhecimentoBD;
// import lattes.AreaConhecimentoSC;
// Certifique-se de que essas classes e seus métodos (ex: PessoaBD.listAll())
// estejam disponíveis no seu projeto.

/**
 * Esta classe unifica todos os scripts relacionados à criação de datasets.
 * Ela centraliza a lógica para gerar dois tipos de datasets a partir dos dados do Lattes:
 *
 * 1. Dataset de Publicações: Baseado na frequência de palavras nos títulos das publicações.
 * 2. Dataset de Áreas de Conhecimento: Baseado nas áreas de conhecimento e especialidades dos pesquisadores.
 *
 * Para executar, chame o método 'main'.
 */
public class GeradorDeDatasets {

    /**
     * Ponto de entrada principal. Executa a geração de ambos os datasets.
     * Comente uma das chamadas de método se quiser gerar apenas um deles.
     */
    public static void main(String[] args) {
        try {
            ConnectionPostgres.startConnection();
            System.out.println("--- Conexão com o banco de dados estabelecida ---");

            // Passo 1: Gerar o dataset baseado em palavras de publicações
            gerarDatasetDePublicacoes();

            // Passo 2: Gerar o dataset baseado em áreas de conhecimento
            gerarDatasetDeAreasConhecimento();

        } catch (Exception e) {
            System.err.println("Ocorreu um erro fatal durante a geração do dataset: " + e.getMessage());
            e.printStackTrace();
        } finally {
            try {
                ConnectionPostgres.closeConnection();
                System.out.println("--- Conexão com o banco de dados fechada ---");
            } catch (SQLException e) {
                System.err.println("Erro ao fechar a conexão com o banco: " + e.getMessage());
            }
        }
    }

    // =================================================================================
    // --- GERAÇÃO DO DATASET DE PUBLICAÇÕES (PALAVRAS) ---
    // =ualiza a lógica de MontarDataset.java, ContarPalavras.java e seus BDs/POJOs.
    // =================================================================================
    public static void gerarDatasetDePublicacoes() throws SQLException {
        System.out.println("\n>>> INICIANDO GERAÇÃO DO DATASET DE PUBLICAÇÕES <<<");

        // Etapa 1: Concatenar publicações por pessoa (lógica de MontarDataset.java)
        System.out.println("[FASE 1/2] Concatenando publicações por pesquisador...");
        /*
        List<Pessoa> pessoas = PessoaBD.listAll();
        for (Pessoa pessoa : pessoas) {
            if (existePessoaPublicacao(pessoa)) {
                continue;
            }
            PublicacaoSC filtro = new PublicacaoSC();
            filtro.setPessoa(pessoa);
            filtro.setMenorAno(2015);
            filtro.setTipo("ARTIGO");
            
            List<Publicacao> publicacoes = PublicacaoBD.listAll(filtro);
            String publicacoesConcatenadas = publicacoes.stream()
                .map(Publicacao::getTituloSemStopword)
                .collect(Collectors.joining(" "));

            if (!publicacoesConcatenadas.isEmpty()) {
                PessoaPublicacao pp = new PessoaPublicacao();
                pp.setPessoa(pessoa);
                pp.setPublicacao(publicacoesConcatenadas);
                inserirPessoaPublicacao(pp);
            }
        }
        System.out.println("Concatenação finalizada.");
        */
        System.out.println("AVISO: A FASE 1 (Concatenação) foi comentada para acelerar a execução. Descomente se for a primeira vez rodando.");


        // Etapa 2: Contar palavras e montar o dataset (lógica de ContarPalavras.java)
        System.out.println("[FASE 2/2] Montando a matriz de palavras...");
        List<PessoaPublicacao> todasPublicacoes = getAllLemmedPublicactions();
        
        // Conta a frequência de todas as palavras para filtrar as menos relevantes
        Map<String, Integer> contagemGeral = new HashMap<>();
        for (PessoaPublicacao pp : todasPublicacoes) {
            for (String palavra : pp.getPublicacaoLemmed().split("\\s+")) {
                contagemGeral.put(palavra, contagemGeral.getOrDefault(palavra, 0) + 1);
            }
        }

        // Cria o cabeçalho do dataset com palavras que aparecem mais de 4 vezes
        List<String> header = new ArrayList<>();
        header.add("id_pessoa");
        for (Map.Entry<String, Integer> entry : contagemGeral.entrySet()) {
            if (entry.getValue() > 4) {
                header.add(entry.getKey());
            }
        }
        
        // Salva o cabeçalho no banco (id_pessoa = 0)
        DatasetLinha linhaHeader = new DatasetLinha(0, String.join(",", header));
        inserirLinhaDataset(linhaHeader);
        System.out.println("Cabeçalho do dataset de publicações criado com " + header.size() + " colunas.");

        // Cria uma linha para cada pessoa
        for (PessoaPublicacao pp : todasPublicacoes) {
            Map<String, Integer> contagemPessoa = new HashMap<>();
            for (String palavra : pp.getPublicacaoLemmed().split("\\s+")) {
                contagemPessoa.put(palavra, contagemPessoa.getOrDefault(palavra, 0) + 1);
            }

            List<String> linha = new ArrayList<>(Collections.nCopies(header.size(), "0"));
            linha.set(0, pp.getPessoa().getId().toString());

            for (int i = 1; i < header.size(); i++) {
                String palavraDoHeader = header.get(i);
                if (contagemPessoa.containsKey(palavraDoHeader)) {
                    linha.set(i, contagemPessoa.get(palavraDoHeader).toString());
                }
            }
            
            DatasetLinha linhaDs = new DatasetLinha(pp.getPessoa().getId(), String.join(",", linha));
            inserirLinhaDataset(linhaDs);
        }
        System.out.println("Matriz de palavras montada e salva para " + todasPublicacoes.size() + " pesquisadores.");
        System.out.println(">>> DATASET DE PUBLICAÇÕES FINALIZADO <<<\n");
    }


    // =================================================================================
    // --- GERAÇÃO DO DATASET DE ÁREAS DE CONHECIMENTO ---
    // Unifica a lógica de MontarDataset_AC.java e seus BDs/POJOs.
    // =================================================================================
    public static void gerarDatasetDeAreasConhecimento() throws SQLException {
        System.out.println("\n>>> INICIANDO GERAÇÃO DO DATASET DE ÁREAS DE CONHECIMENTO <<<");
        /*
        List<Pessoa> pessoas = PessoaBD.listAll();
        List<String> header = listAllAreaConhecimento();
        header.add(0, "id_pessoa");

        // Salva o cabeçalho no banco (id_pessoa = 0)
        DatasetLinha linhaHeader = new DatasetLinha(0, String.join(",", header));
        inserirLinhaDatasetArea(linhaHeader);
        System.out.println("Cabeçalho do dataset de áreas criado com " + header.size() + " colunas.");
        
        // Processa cada pessoa
        for (Pessoa pessoa : pessoas) {
            AreaConhecimentoSC filtro = new AreaConhecimentoSC();
            filtro.setPessoa(pessoa);
            List<AreaConhecimento> areas = AreaConhecimentoBD.listAll(filtro);
            
            Set<String> areasDaPessoa = new HashSet<>();
            for(AreaConhecimento area : areas) {
                if (area.getSubAreaConhecimento() != null && !area.getSubAreaConhecimento().isEmpty()) {
                    areasDaPessoa.add(formatarNomeArea(area.getSubAreaConhecimento()));
                }
                if (area.getEspecialidade() != null && !area.getEspecialidade().isEmpty()) {
                    areasDaPessoa.add(formatarNomeArea(area.getEspecialidade()));
                }
            }

            List<String> linha = new ArrayList<>(Collections.nCopies(header.size(), "0"));
            linha.set(0, pessoa.getId().toString());
            
            for (int i = 1; i < header.size(); i++) {
                if (areasDaPessoa.contains(header.get(i))) {
                    linha.set(i, "1"); // Marca 1 se a pessoa possui a área
                }
            }
            
            DatasetLinha linhaDs = new DatasetLinha(pessoa.getId(), String.join(",", linha));
            inserirLinhaDatasetArea(linhaDs);
        }
        System.out.println("Matriz de áreas montada e salva para " + pessoas.size() + " pesquisadores.");
        */
        System.out.println("AVISO: A geração do dataset de Áreas foi comentada. Descomente o bloco de código para executá-la.");
        System.out.println(">>> DATASET DE ÁREAS DE CONHECIMENTO FINALIZADO <<<");
    }

    private static String formatarNomeArea(String area) {
        return area.trim().replace(",", "_").replace(" ", "_").replace("__", "_").toLowerCase();
    }


    // =================================================================================
    // --- MÉTODOS DE ACESSO AO BANCO DE DADOS (DAO) ---
    // =================================================================================

    // --- Métodos para a tabela 'pessoa_publicacao' ---
    private static void inserirPessoaPublicacao(PessoaPublicacao pp) throws SQLException {
        String sql = String.format("INSERT INTO pessoa_publicacao (publicacoes, id_pessoa) VALUES ('%s', %d)",
                pp.getPublicacao().replace("'", "''"),
                pp.getPessoa().getId());
        ConnectionPostgres.executeInsert(sql);
    }

    private static boolean existePessoaPublicacao(Pessoa pessoa) throws SQLException {
        String query = "SELECT 1 FROM pessoa_publicacao WHERE id_pessoa = " + pessoa.getId();
        try (ResultSet rs = ConnectionPostgres.executeList(query)) {
            return rs.next();
        }
    }

    private static List<PessoaPublicacao> getAllLemmedPublicactions() throws SQLException {
        String query = "SELECT id, id_pessoa, publicacoes_lemmed FROM pessoa_publicacao WHERE publicacoes_lemmed IS NOT NULL";
        List<PessoaPublicacao> retorno = new ArrayList<>();
        try (ResultSet rs = ConnectionPostgres.executeList(query)) {
            while (rs.next()) {
                PessoaPublicacao pp = new PessoaPublicacao();
                pp.setId(rs.getInt("id"));
                // pp.setPessoa(new Pessoa(rs.getInt("id_pessoa"))); // Requer classe Pessoa
                pp.setPublicacaoLemmed(rs.getString("publicacoes_lemmed"));
                retorno.add(pp);
            }
        }
        return retorno;
    }

    // --- Métodos para a tabela 'dataset' (publicações) ---
    private static void inserirLinhaDataset(DatasetLinha linha) throws SQLException {
        String sql = String.format("INSERT INTO dataset (linha, id_pessoa) VALUES ('%s', %d)",
                linha.getTexto().replace("'", "''''"), // Escape extra para CSV
                linha.getIdPessoa());
        ConnectionPostgres.executeInsert(sql);
    }

    // --- Métodos para a tabela 'dataset_area' ---
    private static void inserirLinhaDatasetArea(DatasetLinha linha) throws SQLException {
        String sql = String.format("INSERT INTO dataset_area (linha, id_pessoa) VALUES ('%s', %d)",
                linha.getTexto().replace("'", "''''"),
                linha.getIdPessoa());
        ConnectionPostgres.executeInsert(sql);
    }

    private static List<String> listAllAreaConhecimento() throws SQLException {
        String query = "SELECT area FROM (" +
                       "  SELECT lower(especialidade) AS area FROM area_conhecimento " +
                       "  WHERE especialidade IS NOT NULL AND especialidade <> '' AND ano > 2010 " +
                       "  GROUP BY lower(especialidade) " +
                       "  HAVING count(especialidade) > 15 AND count(DISTINCT id_pessoa) > 15 " +
                       "  UNION " +
                       "  SELECT lower(sub_area_conhecimento) AS area FROM area_conhecimento " +
                       "  WHERE sub_area_conhecimento IS NOT NULL AND sub_area_conhecimento <> '' AND ano > 2010 " +
                       "  GROUP BY lower(sub_area_conhecimento) " +
                       "  HAVING count(sub_area_conhecimento) > 15 AND count(DISTINCT id_pessoa) > 15" +
                       ") AS areas_unidas ORDER BY area";
        
        List<String> palavras = new ArrayList<>();
        try (ResultSet rs = ConnectionPostgres.executeList(query)) {
            while (rs.next()) {
                palavras.add(formatarNomeArea(rs.getString("area")));
            }
        }
        return palavras;
    }

    // =================================================================================
    // --- CLASSES DE DADOS ANINHADAS (POJOs) ---
    // =================================================================================

    static class PessoaPublicacao {
        private int id;
        private Pessoa pessoa;
        private String publicacao;
        private String publicacaoLemmed;
        // Getters e Setters...
        public int getId() { return id; }
        public void setId(int id) { this.id = id; }
        public Pessoa getPessoa() { return pessoa; }
        public void setPessoa(Pessoa pessoa) { this.pessoa = pessoa; }
        public String getPublicacao() { return publicacao; }
        public void setPublicacao(String publicacao) { this.publicacao = publicacao; }
        public String getPublicacaoLemmed() { return publicacaoLemmed; }
        public void setPublicacaoLemmed(String publicacaoLemmed) { this.publicacaoLemmed = publicacaoLemmed; }
    }
    
    // Classe unificada para representar uma linha de qualquer dataset
    static class DatasetLinha {
        private String texto;
        private Integer idPessoa;
        public DatasetLinha(Integer idPessoa, String texto) {
            this.idPessoa = idPessoa;
            this.texto = texto;
        }
        // Getters e Setters...
        public String getTexto() { return texto; }
        public void setTexto(String texto) { this.texto = texto; }
        public Integer getIdPessoa() { return idPessoa; }
        public void setIdPessoa(Integer idPessoa) { this.idPessoa = idPessoa; }
    }
    
    // Classe placeholder para código compilar
    static class Pessoa {
        private Integer id;
        public Pessoa(Integer id) { this.id = id; }
        public Integer getId() { return id; }
    }
}


// =================================================================================
// --- CLASSE DE CONEXÃO (Exemplo) ---
// =================================================================================
/**
 * IMPORTANTE: Esta é uma classe de exemplo. Você deve ter a sua própria
 * implementação da classe 'ConnectionPostgres' no seu projeto.
 */
class ConnectionPostgres {
    private static Connection connection = null;
    public static void startConnection() throws SQLException {
        if (connection == null || connection.isClosed()) {
            String url = "jdbc:postgresql://localhost:5432/mestrado";
            String user = "postgres";
            String password = "admin";
            connection = DriverManager.getConnection(url, user, password);
        }
    }
    public static void closeConnection() throws SQLException {
        if (connection != null && !connection.isClosed()) {
            connection.close();
            connection = null;
        }
    }
    public static void executeInsert(String sql) throws SQLException {
        if (connection == null || connection.isClosed()) throw new SQLException("Conexão não iniciada.");
        try (Statement stmt = connection.createStatement()) {
            stmt.executeUpdate(sql);
        }
    }
    public static ResultSet executeList(String sql) throws SQLException {
        if (connection == null || connection.isClosed()) throw new SQLException("Conexão não iniciada.");
        Statement stmt = connection.createStatement();
        return stmt.executeQuery(sql);
    }
}
