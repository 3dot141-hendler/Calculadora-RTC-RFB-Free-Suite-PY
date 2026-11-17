-- =============================================================================
-- Schema SQLite de Tabelas Oficiais da Reforma Tributária (RTC)
-- Baseado na arquitetura ADR004 (banco somente-leitura em runtime)
-- =============================================================================

CREATE TABLE IF NOT EXISTS cst_classificacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cst TEXT NOT NULL,
    c_class_trib TEXT NOT NULL,
    descricao TEXT NOT NULL,
    aliquota_reducao_ibs TEXT NOT NULL DEFAULT '0.00',
    aliquota_reducao_cbs TEXT NOT NULL DEFAULT '0.00',
    inicio_vigencia TEXT NOT NULL,
    fim_vigencia TEXT
);

CREATE INDEX IF NOT EXISTS idx_cst_cclasstrib
    ON cst_classificacao (cst, c_class_trib, inicio_vigencia);

CREATE TABLE IF NOT EXISTS atividade_simples (
    codigo TEXT PRIMARY KEY,
    descricao TEXT NOT NULL,
    anexo_sem_fator_r TEXT,
    anexo_com_fator_r TEXT,
    inicio_vigencia TEXT NOT NULL,
    fim_vigencia TEXT
);

CREATE TABLE IF NOT EXISTS transicao_compra_gov_simples (
    id INTEGER PRIMARY KEY,
    fator TEXT NOT NULL,
    inicio_vigencia TEXT NOT NULL,
    fim_vigencia TEXT
);

CREATE TABLE IF NOT EXISTS uf_aliquota_referencia (
    uf TEXT NOT NULL,
    nome TEXT NOT NULL,
    aliquota_ibs_uf TEXT NOT NULL,
    aliquota_cbs TEXT NOT NULL,
    inicio_vigencia TEXT NOT NULL,
    fim_vigencia TEXT,
    PRIMARY KEY (uf, inicio_vigencia)
);
