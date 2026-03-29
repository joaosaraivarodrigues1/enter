
-- ============================================================
-- CATÁLOGOS DE ATIVOS
-- ============================================================

-- Ativos precisam ser cadastrados aqui antes de aparecer em posições ou dados de mercado
create table ativos_acoes (
  ticker text primary key,
  nome text not null
);

create table ativos_fundos (
  cnpj text primary key,
  nome text not null
);

-- ============================================================
-- DADOS DE MERCADO
-- ============================================================

-- Um registro por mês. Índices globais usados em todos os cálculos de rendimento.
-- precos_acoes e cotas_fundos só aceitam meses que existam aqui.
create table dados_mercado (
  mes text primary key,                -- formato YYYY-MM
  cdi_mensal numeric,
  ipca_mensal numeric,
  selic_mensal numeric,
  ibovespa_retorno_mensal numeric,
  ima_b_retorno_mensal numeric
);

create table precos_acoes (
  id uuid primary key default gen_random_uuid(),
  ticker text not null references ativos_acoes(ticker),
  mes text not null,                   -- formato YYYY-MM (sem FK para dados_mercado)
  preco_fechamento numeric not null,
  dividendos_pagos numeric not null default 0,
  unique (ticker, mes)
);

create table cotas_fundos (
  id uuid primary key default gen_random_uuid(),
  cnpj text not null references ativos_fundos(cnpj),
  mes text not null,                   -- formato YYYY-MM (sem FK para dados_mercado)
  cota_fechamento numeric not null,
  unique (cnpj, mes)
);

-- ============================================================
-- CLIENTES E CARTEIRA
-- ============================================================

create table clientes (
  id uuid primary key default gen_random_uuid(),
  nome text not null
);

create table posicoes_acoes (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references clientes(id),
  ticker text not null references ativos_acoes(ticker),
  quantidade numeric not null,
  preco_medio_compra numeric not null,
  data_compra date not null
);

create table posicoes_fundos (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references clientes(id),
  cnpj text not null references ativos_fundos(cnpj),
  nome text not null,
  numero_cotas numeric not null,
  valor_aplicado numeric not null,
  data_investimento date not null
);

create table posicoes_renda_fixa (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references clientes(id),
  descricao text not null,
  instrumento text not null,           -- CDB, LCI, LCA, tesouro_direto, debenture
  indexacao text not null,             -- pos_fixado, prefixado, ipca_mais
  taxa_contratada numeric not null,
  unidade_taxa text not null,          -- percentual_cdi, percentual_selic, percentual_ao_ano, spread_ao_ano
  valor_aplicado numeric not null,
  data_inicio date not null,
  data_vencimento date not null,
  isento_ir boolean not null default false,
  emissor text                         -- preenchido apenas para debêntures
);

