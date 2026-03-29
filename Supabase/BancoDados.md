# Schema do Banco de Dados — Supabase

## Visão geral

7 tabelas divididas em dois grupos: dados do cliente/carteira e dados de mercado.

```
clientes
  └── posicoes_acoes
  └── posicoes_fundos
  └── posicoes_renda_fixa

dados_mercado
precos_acoes
cotas_fundos
```

---

## Dados do Cliente e Carteira

### `clientes`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | Chave primária |
| `nome` | text | Nome do cliente |

---

### `posicoes_acoes`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | Chave primária |
| `cliente_id` | uuid | FK → clientes.id |
| `ticker` | text | Ex: PETR4, LREN3 |
| `quantidade` | numeric | Número de ações |
| `preco_medio_compra` | numeric | Preço médio pago por ação |
| `data_compra` | date | Data da compra |

---

### `posicoes_fundos`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | Chave primária |
| `cliente_id` | uuid | FK → clientes.id |
| `cnpj` | text | CNPJ do fundo |
| `nome` | text | Nome do fundo |
| `numero_cotas` | numeric | Quantidade de cotas do cliente |
| `valor_aplicado` | numeric | Valor original investido |
| `data_investimento` | date | Data da aplicação |

---

### `posicoes_renda_fixa`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | Chave primária |
| `cliente_id` | uuid | FK → clientes.id |
| `descricao` | text | Ex: CDB C6, Tesouro Selic 2029 |
| `instrumento` | text | CDB, LCI, LCA, tesouro_direto, debenture |
| `indexacao` | text | pos_fixado, prefixado, ipca_mais |
| `taxa_contratada` | numeric | Valor numérico da taxa |
| `unidade_taxa` | text | percentual_cdi, percentual_selic, percentual_ao_ano, spread_ao_ano |
| `valor_aplicado` | numeric | Valor original investido |
| `data_inicio` | date | Data da aplicação |
| `data_vencimento` | date | Data de vencimento |
| `isento_ir` | boolean | True para LCI, LCA, debêntures incentivadas |
| `emissor` | text | Preenchido apenas para debêntures |

---

## Dados de Mercado

### `dados_mercado`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `mes` | text | Chave primária. Formato YYYY-MM |
| `cdi_mensal` | numeric | CDI acumulado no mês (%) |
| `ipca_mensal` | numeric | IPCA do mês (%) |
| `selic_mensal` | numeric | Selic acumulada no mês (%) |
| `ibovespa_retorno_mensal` | numeric | Retorno do IBOVESPA no mês (%) |
| `ima_b_retorno_mensal` | numeric | Retorno do IMA-B no mês (%) |

---

### `precos_acoes`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | Chave primária |
| `ticker` | text | Ex: PETR4, LREN3, HGLG11 |
| `mes` | text | Formato YYYY-MM |
| `preco_fechamento` | numeric | Preço de fechamento do último dia do mês |
| `dividendos_pagos` | numeric | Total de dividendos pagos no mês por ação |

> Chave única composta: `ticker` + `mes`

---

### `cotas_fundos`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | Chave primária |
| `cnpj` | text | CNPJ do fundo |
| `mes` | text | Formato YYYY-MM |
| `cota_fechamento` | numeric | Cota do último dia útil do mês |

> Chave única composta: `cnpj` + `mes`

---

## Notas

- **Renda fixa não tem tabela de mercado própria** — o retorno é calculado cruzando `posicoes_renda_fixa` com a série histórica de `dados_mercado`.
- **`precos_acoes`** cobre tanto ações quanto FIIs (HGLG11) — o cálculo é idêntico para ambos.
- **`cotas_fundos`** é populada pela função local `extract_fund_data(cnpj)` que lê os ZIPs da CVM armazenados localmente.
- **`precos_acoes`** e **`dados_mercado`** são populados via Edge Functions do Supabase disparadas por chamadas à brapi.dev e BCB API.
- **`precos_acoes.mes`** e **`cotas_fundos.mes`** não têm FK para `dados_mercado` — ações e índices são carregados de forma independente e cruzados apenas na hora do cálculo.
