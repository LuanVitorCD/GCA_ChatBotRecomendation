package br.com.seuprojeto.qualis;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

/**
 * Esta classe unifica todas as funcionalidades relacionadas ao processamento
 * e importação de dados do Qualis para o banco de dados.
 * * Ela lê um arquivo CSV, monta os objetos de dados e os insere nas tabelas
 * 'qualis' e 'preda_qualis'.
 *
 * Para executar, certifique-se de que o arquivo "qualis.csv" está na pasta raiz
 * do projeto e que a classe ConnectionPostgres está configurada corretamente.
 */
public class ProcessadorQualis {

    // --- CLASSE PRINCIPAL COM A LÓGICA DE IMPORTAÇÃO ---

    public static void main(String[] args) {
        System.out.println("Iniciando a importação de dados do Qualis...");
        
        try {
            // Lê o arquivo CSV e cria uma lista de objetos Qualis
            List<Qualis> todosQualis = lerArquivoQualis("qualis.csv");
            
            System.out.println(todosQualis.size() + " registros encontrados no arquivo CSV.");

            // Inicia a conexão com o banco de dados
            ConnectionPostgres.startConnection();
            System.out.println("Conexão com o banco de dados estabelecida.");

            // Itera sobre a lista e insere cada registro no banco
            int contador = 0;
            for (Qualis qualis : todosQualis) {
                inserirQualis(qualis);
                contador++;
                if (contador % 100 == 0) {
                    System.out.println(contador + " registros inseridos...");
                }
            }
            
            System.out.println("Importação finalizada com sucesso!");

        } catch (IOException e) {
            System.err.println("Erro ao ler o arquivo 'qualis.csv': " + e.getMessage());
        } catch (SQLException e) {
            System.err.println("Erro de SQL durante a importação: " + e.getMessage());
        } catch (Exception e) {
            System.err.println("Ocorreu um erro inesperado: " + e.getMessage());
        } finally {
            // Garante que a conexão com o banco seja sempre fechada
            try {
                ConnectionPostgres.closeConnection();
                System.out.println("Conexão com o banco de dados fechada.");
            } catch (SQLException e) {
                System.err.println("Erro ao fechar a conexão com o banco: " + e.getMessage());
            }
        }
    }

    /**
     * Lê um arquivo CSV e o converte para uma lista de objetos Qualis.
     * @param caminhoArquivo O caminho para o arquivo "qualis.csv".
     * @return Uma lista de objetos Qualis.
     * @throws IOException Se houver um erro de leitura do arquivo.
     */
    public static List<Qualis> lerArquivoQualis(String caminhoArquivo) throws IOException {
        List<Qualis> listaQualis = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new FileReader(caminhoArquivo))) {
            String linha;
            br.readLine(); // Pula o cabeçalho, se houver
            
            while ((linha = br.readLine()) != null) {
                if (linha.trim().isEmpty()) {
                    continue; // Pula linhas em branco
                }
                String[] attributes = linha.split(",");
                if (attributes.length >= 2) {
                    Qualis qualis = new Qualis();
                    qualis.setEstrato(attributes[0].trim());
                    qualis.setISSN(attributes[1].trim());
                    listaQualis.add(qualis);
                }
            }
        }
        return listaQualis;
    }

    // --- MÉTODOS DE ACESSO AO BANCO DE DADOS (DAO) ---

    /**
     * Insere um objeto Qualis na tabela 'qualis'.
     * (Lógica de QualisBD.java)
     * @param qualis O objeto a ser inserido.
     * @throws SQLException Se ocorrer um erro de SQL.
     */
    public static void inserirQualis(Qualis qualis) throws SQLException {
        // Usar PreparedStatement é mais seguro contra SQL Injection
        String sql = String.format("INSERT INTO qualis (issn, estrato) VALUES ('%s', '%s')",
                qualis.getISSN().replace("'", "''"), // Simples escape para aspas
                qualis.getEstrato().replace("'", "''"));
        ConnectionPostgres.executeInsert(sql);
    }

    /**
     * Insere um objeto PredaQualis na tabela 'preda_qualis'.
     * (Lógica de PredaQualisBD.java)
     * @param qualis O objeto a ser inserido.
     * @throws SQLException Se ocorrer um erro de SQL.
     */
    public static void inserirPredaQualis(PredaQualis qualis) throws SQLException {
        String sql = String.format("INSERT INTO preda_qualis (issn) VALUES ('%s')",
                qualis.getIssn().replace("'", "''"));
        ConnectionPostgres.executeInsert(sql);
    }

    // --- CLASSES DE DADOS ANINHADAS (POJOs) ---

    /**
     * Representa a entidade 'Qualis' com ISSN e Estrato.
     * (Conteúdo de Qualis.java)
     */
    static class Qualis {
        private String ISSN;
        private String estrato;

        public String getISSN() {
            return ISSN;
        }

        public void setISSN(String ISSN) {
            this.ISSN = ISSN;
        }

        public String getEstrato() {
            return estrato;
        }

        public void setEstrato(String estrato) {
            this.estrato = estrato;
        }
    }

    /**
     * Representa a entidade 'PredaQualis' apenas com ISSN.
     * (Conteúdo de PredaQualis.java)
     */
    static class PredaQualis {
        private String issn;

        public PredaQualis(String issn) {
            this.issn = issn;
        }

        public String getIssn() {
            return issn;
        }

        public void setIssn(String issn) {
            this.issn = issn;
        }
    }
}


// ----------------------------------------------------------------------------------
// --- CLASSE DE CONEXÃO (Exemplo) ---
// ----------------------------------------------------------------------------------
/**
 * IMPORTANTE: Esta é uma classe de exemplo. Você deve ter a sua própria
 * implementação da classe 'ConnectionPostgres' no seu projeto, em um pacote 'bd'.
 * Certifique-se de que ela está configurada com suas credenciais do banco.
 */
class ConnectionPostgres {

    private static Connection connection = null;

    public static void startConnection() throws SQLException {
        if (connection == null) {
            // Substitua com seus dados de conexão
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
        if (connection == null) {
            throw new SQLException("A conexão com o banco de dados não foi iniciada.");
        }
        try (Statement stmt = connection.createStatement()) {
            stmt.executeUpdate(sql);
        }
    }
}
