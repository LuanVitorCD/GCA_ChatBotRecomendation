CREATE SEQUENCE pessoa_id
    INCREMENT 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    START 1
    CACHE 1;

DROP TABLE pessoa;

CREATE TABLE pessoa (
	id integer PRIMARY KEY,
	titulacao VARCHAR ( 255 ) NOT NULL,
	universidade VARCHAR ( 255 ) NOT NULL,
	nome VARCHAR ( 255 ) NOT NULL
);

DELETE FROM pessoa


CREATE SEQUENCE publicacao_id
    INCREMENT 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    START 1
    CACHE 1;

DROP TABLE publicacao;

CREATE TABLE publicacao (
	id integer PRIMARY KEY DEFAULT nextval('publicacao_id'),
	tipo VARCHAR ( 255 ) NOT NULL,
	titulo TEXT NOT NULL,
	titulo_portugues TEXT,
	titulo_sem_stopword TEXT, 
	idioma VARCHAR ( 255 ),
	ano Integer,
	id_pessoa integer NOT NULL,
	CONSTRAINT fk_pessoa FOREIGN KEY(id_pessoa) REFERENCES pessoa(id)
);


CREATE TABLE stopwords (
	id integer PRIMARY KEY,
	word VARCHAR ( 255 ) NOT NULL
);

CREATE SEQUENCE word_id
    INCREMENT 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    START 1
    CACHE 1;

CREATE TABLE pessoa_publicacao(
	id integer PRIMARY KEY,
	publicacoes TEXT,
	id_pessoa integer NOT NULL, 
	publicacoes_lemmed text,
	CONSTRAINT fk_pessoa FOREIGN KEY(id_pessoa) REFERENCES pessoa(id)
);

CREATE SEQUENCE pessoa_publicacao_id
    INCREMENT 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    START 1
    CACHE 1;



CREATE SEQUENCE area_conhecimento_id
INCREMENT 1
MINVALUE 1
MAXVALUE 9223372036854775807
START 1
CACHE 1;


create table area_conhecimento (
	id integer PRIMARY KEY,
	grande_area_conhecimento text,
	area_conhecimento text,
	sub_area_conhecimento text,
	especialidade text,
	id_pessoa integer NOT NULL,
	CONSTRAINT fk_pessoa FOREIGN KEY(id_pessoa) REFERENCES pessoa(id)
);


alter table publicacao add column periodico text, add column ISSN text, add column volume integer, add column pagina_inicial integer, add column pagina_final integer;




CREATE TABLE ppg (
	id integer PRIMARY KEY,
	nome text not null,
	nome_universidade text,
	sigla_universidade varchar(20) not null
)

CREATE SEQUENCE ppg_id
    INCREMENT 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    START 1
    CACHE 1;


CREATE TABLE pessoa_ppg (
	id_ppg integer NOT NULL,
	id_pessoa integer NOT NULL,
	CONSTRAINT fk_pessoa FOREIGN KEY(id_pessoa) REFERENCES pessoa(id),
	CONSTRAINT fk_ppg FOREIGN KEY(id_ppg) REFERENCES ppg(id)
);

CREATE TABLE qualis (
	issn varchar(10) primary key, 
	estrato varchar(2) not null
);
