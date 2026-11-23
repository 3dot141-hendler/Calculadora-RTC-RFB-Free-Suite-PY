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

CREATE TABLE IF NOT EXISTS redutor_compra_governamental (
    id INTEGER PRIMARY KEY,
    percentual_redutor TEXT NOT NULL,
    inicio_vigencia TEXT NOT NULL,
    fim_vigencia TEXT
);

CREATE TABLE IF NOT EXISTS transferencia_cbs_ente_gov (
    id INTEGER PRIMARY KEY,
    percentual_transferencia TEXT NOT NULL,
    inicio_vigencia TEXT NOT NULL,
    fim_vigencia TEXT
);

CREATE TABLE IF NOT EXISTS ncm_imposto_seletivo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ncm TEXT NOT NULL,
    descricao TEXT NOT NULL,
    aliquota_ad_valorem TEXT,
    aliquota_ad_rem TEXT,
    inicio_vigencia TEXT NOT NULL,
    fim_vigencia TEXT
);

CREATE INDEX IF NOT EXISTS idx_ncm_is_codigo
    ON ncm_imposto_seletivo (ncm, inicio_vigencia);

CREATE TABLE IF NOT EXISTS nbs_aplicavel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nbs TEXT NOT NULL,
    descricao TEXT NOT NULL,
    item_lc116 TEXT,
    c_class_trib TEXT,
    inicio_vigencia TEXT NOT NULL,
    fim_vigencia TEXT
);

CREATE INDEX IF NOT EXISTS idx_nbs_aplicavel_codigo
    ON nbs_aplicavel (nbs, inicio_vigencia);

CREATE TABLE IF NOT EXISTS tratamento_tributario (
    id INTEGER PRIMARY KEY,
    descricao TEXT NOT NULL,
    expressao_aliquota TEXT,
    expressao_aliquota_efetiva TEXT,
    expressao_base_calculo TEXT,
    expressao_tributo_calculado TEXT,
    expressao_tributo_devido TEXT,
    possui_reducao INTEGER NOT NULL DEFAULT 0,
    possui_monofasia INTEGER NOT NULL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS localidades_ibge (
    codigo_ibge INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    uf_codigo INTEGER NOT NULL,
    uf_sigla TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_localidades_uf_nome
    ON localidades_ibge (uf_sigla, nome);
