# Ativos Disponíveis na Plataforma

## 1. Ações e FIIs — Albert

| Ticker | Empresa | Tipo | Setor | Perfil de risco |
|--------|---------|------|-------|-----------------|
| LREN3 | Lojas Renner | Ação | Varejo discricionário | Moderado/Arrojado |
| MRFG3 | Marfrig | Ação | Frigoríficos | Moderado/Arrojado |
| ARZZ3 | Arezzo | Ação | Varejo discricionário | Moderado/Arrojado |
| HAPV3 | Hapvida | Ação | Saúde privada | Moderado/Arrojado |

---

## 2. Ações e FIIs — Novos

| Ticker | Empresa | Tipo | Setor | Perfil de risco | Razão da adição |
|--------|---------|------|-------|-----------------|-----------------|
| ITUB4 | Itaú Unibanco | Ação | Banco | Moderado | Albert não tem nenhuma ação de banco. Bancos são favorecidos em Selic alta (spread maior) — perfil macro oposto ao varejo do Albert. Cobre o caso de ativo que se beneficia do mesmo ambiente que prejudica LREN3 e ARZZ3. |
| VALE3 | Vale | Ação | Mineração | Moderado/Arrojado | Cobre o perfil exportador e sensibilidade ao câmbio (BRL fraco favorece). Albert só tem MRFG3 como exportador. VALE3 adiciona exposição a commodity metálica e ciclo global, comportamento macro distinto. |
| PETR4 | Petrobras | Ação | Petróleo | Moderado/Arrojado | Segundo exportador com lógica de dividendos altos e recorrentes — exercita o cálculo de proventos com valores relevantes, diferente das ações do Albert onde dividendos são ocasionais. |
| EGIE3 | Engie Brasil | Ação | Energia elétrica | Conservador/Moderado | Cobre o perfil defensivo — setor de utilities com dividendos regulares e baixa volatilidade. Não representado na carteira do Albert. Funciona bem como ativo de menor risco dentro da classe de ações. |
| WEGE3 | WEG | Ação | Industrial / crescimento | Arrojado | Cobre o perfil growth — prejudicado em Selic alta por ter valuation baseado em crescimento futuro. Contraponto direto ao ITUB4 no algoritmo de recomendação macro. |
| CYRE3 | Cyrela | Ação | Construção civil | Arrojado | Setor citado explicitamente no algoritmo de recomendação como prejudicado em Selic alta e PIB baixo. Não representado no portfólio do Albert. Amplia os casos de recomendação de redução/venda. |
| HGLG11 | CSHG Logística | FII | Logística / Imobiliário | Moderado/Arrojado | Cobre Fundos de Investimento Imobiliário. Cálculo idêntico ao de ações (variação de preço + rendimentos mensais via brapi.dev), sem uso de cotas CVM. Armazenado em `ativos_acoes` com `tipo = FII`. |

> **MRFG3:** brapi.dev não possui dados históricos para este ticker. Ativo cadastrado no catálogo mas sem preços em `precos_acoes`.

---

## 3. Fundos — Albert

| Nome | CNPJ | Categoria | Benchmark derivado | Perfil de risco |
|------|------|-----------|--------------------|-----------------|
| Riza Lotus Plus | `43.917.493/0001-31` ⚠️ | Multimercado RF | CDI | Moderado |
| Brave I FIC FIM CP | `35.726.300/0001-37` | Multimercado | CDI | Moderado |
| Trend Investback | `37.910.132/0001-60` | RF Simples | CDI | Conservador |
| Truxt Long Bias | `30.830.162/0001-18` | Long Biased | CDI / IBOVESPA | Arrojado |
| STK Long Biased | `12.282.747/0001-69` ⚠️ | Long Biased | CDI / IBOVESPA | Arrojado |
| Constellation FIA | `18.872.811/0001-48` ⚠️ | FIA | IBOVESPA | Arrojado |
| Ibiuna Hedge ST | `15.799.713/0001-34` ⚠️ | Multimercado | CDI | Moderado/Arrojado |

> ⚠️ **CNPJs pendentes de confirmação:**
> - **Riza Lotus Plus** `43.917.493/0001-31` é a versão Advisory. Confirmar se Albert acessa essa versão ou a versão retail.
> - **STK Long Biased** `12.282.747/0001-69` — a CVM classifica este fundo como **FIA**, não FIM. Avaliar se `categoria` deve ser corrigida de `Long Biased` para `FIA`.
> - **Constellation FIA** `18.872.811/0001-48` é o fundo principal (Compounders). Alternativas: `38.948.507/0001-44` (retail Access) ou `34.462.109/0001-62` (Advisory institucional).
> - **Ibiuna Hedge ST** `15.799.713/0001-34` é a versão STH retail. Alternativa Advisory: `30.493.349/0001-73`.

---

## 4. Fundos — Novos

| Nome | CNPJ | Categoria | Benchmark derivado | Perfil de risco | Razão da adição |
|------|------|-----------|--------------------|-----------------|-----------------|
| Trend DI | `45.278.833/0001-57` | RF DI | CDI | Conservador | Albert não tem fundo DI puro. É o fundo mais simples — 100% CDI, favorecido em Selic alta, indicado para perfil conservador no suitability. Mesma família do Trend Investback já na carteira do Albert. Amplia a cobertura do algoritmo para recomendação de alocação defensiva. |

> **Benchmark derivado:** não é armazenado no banco — é derivado da `categoria` em tempo de exibição (FIA → IBOVESPA; Long Biased → CDI/IBOVESPA; demais → CDI).

---

## 5. Renda Fixa — Albert

> Campos do catálogo (`ativos_renda_fixa`): `nome`, `instrumento`, `indexacao`, `isento_ir`, `emissor`.
> `taxa_contratada`, `valor_aplicado`, `data_inicio` e `data_vencimento` pertencem à posição do cliente (`posicoes_renda_fixa`).

| Nome | Instrumento | Indexação | Isento IR | Emissor |
|------|-------------|-----------|-----------|---------|
| CDB C6 Bank IPCA+ | CDB | ipca_mais | Não | C6 Bank |

---

## 6. Renda Fixa — Novos

| Nome | Instrumento | Indexação | Isento IR | Emissor | Razão da adição |
|------|-------------|-----------|-----------|---------|-----------------|
| CDB BTG Pactual Pós-fixado CDI | CDB | pos_fixado_cdi | Não | BTG Pactual | Tipo de cálculo ausente na carteira do Albert. Pós-fixado CDI é o mais comum no mercado. Cobre o caso de ativo favorecido diretamente por Selic alta. |
| LCA Banco do Brasil Pós-fixado CDI | LCA | pos_fixado_cdi | Sim | Banco do Brasil | Mesmo cálculo que o CDB CDI, mas com isenção de IR. Exercita a lógica de `isento_ir` no retorno líquido. Cobre o instrumento LCA. |
| Tesouro Selic 2029 | Tesouro Direto | pos_fixado_selic | Não | Tesouro Nacional | Cobre o cálculo pós-fixado Selic e o instrumento Tesouro Direto. Ativo de menor risco da plataforma, referência para perfil conservador. |
| Tesouro Prefixado 2027 | Tesouro Direto | prefixado | Não | Tesouro Nacional | Único tipo de cálculo que não depende de nenhum dado de mercado — retorno determinado apenas pela taxa contratada. Exercita a lógica de marcação a mercado. |
| Debênture Incentivada CPFL | Debênture | ipca_mais | Sim | CPFL Energia | Mesmo cálculo IPCA+ do CDB C6, mas com isenção de IR e emissor corporativo. Cobre o instrumento debênture e amplia os casos de análise de custo tributário. |

> **Indexação — valores válidos no banco:** `pos_fixado_cdi`, `pos_fixado_selic`, `prefixado`, `ipca_mais`

---

## Módulo — Obtenção de Dados

### 1. Ações e FIIs (incluindo HGLG11)

**Ativos:** LREN3, MRFG3, ARZZ3, HAPV3, ITUB4, VALE3, PETR4, EGIE3, WEGE3, CYRE3, HGLG11

**Fonte:** brapi.dev (PRO) — token armazenado como secret `BRAPI_TOKEN` no Supabase

**Tabela de destino:** `precos_acoes` — colunas `ticker`, `mes`, `preco_fechamento`, `dividendos_pagos`

**Edge Function:** `fetch-acoes` (Supabase Edge Functions, Deno)

**Passo a passo:**

1. Chamada 1 — preços mensais (janela de 5 anos):
```
GET https://brapi.dev/api/quote/{ticker}?range=5y&interval=1mo&token={BRAPI_TOKEN}
```
2. Chamada 2 — dividendos pagos:
```
GET https://brapi.dev/api/quote/{ticker}?dividends=true&token={BRAPI_TOKEN}
```
3. Agrupar dividendos por mês (`paymentDate`).
4. Fazer upsert em `precos_acoes` com conflito em `(ticker, mes)`.
5. Retry automático: 6 tentativas com 2s de espera entre cada.

**Acionamento:** chamada HTTP via Streamlit (formulário "Adicionar ativo") ou diretamente via POST à Edge Function.

---

### 2. Fundos de Investimento

**Ativos:** Riza Lotus Plus, Brave I FIC FIM CP, Trend Investback, Trend DI, Truxt Long Bias, STK Long Biased, Constellation FIA, Ibiuna Hedge ST

**Fonte:** CVM — Informe Diário (arquivos ZIP armazenados localmente)

**Tabela de destino:** `cotas_fundos` — colunas `cnpj`, `mes`, `cota_fechamento`

#### Setup inicial — feito uma única vez

1. Levantar o CNPJ de cada fundo no portal CVM (dados.cvm.gov.br).
2. Baixar os ZIPs do informe diário e salvar localmente em `/data/cvm/`:
```
https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_AAAAMM.zip
```
3. Os ZIPs ficam armazenados localmente e reutilizados para qualquer fundo novo.

#### Função local — `extract_fund_data(cnpj)`

Roda na máquina local. Lê os ZIPs locais e exporta diretamente para o Supabase.

```python
def extract_fund_data(cnpj: str, zip_folder: str, supabase_client):
    registros = []

    for zip_filename in sorted(os.listdir(zip_folder)):
        zip_path = os.path.join(zip_folder, zip_filename)

        with zipfile.ZipFile(zip_path) as z:
            csv_filename = z.namelist()[0]
            with z.open(csv_filename) as f:
                df = pd.read_csv(f, sep=';', dtype=str)

        df_fundo = df[df['CNPJ_FUNDO'] == cnpj]
        df_fundo['DT_COMPTC'] = pd.to_datetime(df_fundo['DT_COMPTC'])
        ultimo_dia = df_fundo['DT_COMPTC'].max()
        linha = df_fundo[df_fundo['DT_COMPTC'] == ultimo_dia].iloc[0]

        registros.append({
            'cnpj': cnpj,
            'mes': ultimo_dia.strftime('%Y-%m'),
            'cota_fechamento': float(linha['VL_QUOTA'].replace(',', '.'))
        })

    supabase_client.table('cotas_fundos').upsert(registros).execute()
```

#### Como usar

- **Carga histórica inicial:** chamar `extract_fund_data` para cada CNPJ.
- **Novo fundo adicionado:** chamar `extract_fund_data` com o novo CNPJ — os ZIPs já estão locais.

> Os ZIPs nunca precisam ser baixados novamente enquanto o período histórico não mudar.

---

### 3. Índices Globais

**Dados:** CDI mensal, IPCA mensal, Selic mensal, IBOVESPA mensal

**Tabela de destino:** `dados_mercado` — colunas `mes`, `cdi_mensal`, `ipca_mensal`, `selic_mensal`, `ibovespa_retorno_mensal`

**Edge Function:** `fetch-indices` (Supabase Edge Functions, Deno)

#### CDI mensal
**Fonte:** BCB API — Série 4389 (CDI acumulado no mês)
```
GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.4389/dados?dataInicial=01/MM/AAAA&dataFinal=31/MM/AAAA&formato=json
```

#### IPCA mensal
**Fonte:** BCB API — Série 433
```
GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?dataInicial=01/MM/AAAA&dataFinal=31/MM/AAAA&formato=json
```

#### Selic mensal
**Fonte:** BCB API — Série 4390 (Selic acumulada no mês)
```
GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?dataInicial=01/MM/AAAA&dataFinal=31/MM/AAAA&formato=json
```

#### IBOVESPA mensal
**Fonte:** brapi.dev
```
GET https://brapi.dev/api/quote/%5EBVSP?range=5y&interval=1mo&token={BRAPI_TOKEN}
```

---

### 4. Renda Fixa

**Ativos:** CDB C6, CDB 110% CDI, LCA 92% CDI, Tesouro Selic 2029, Tesouro Prefixado 2027, Debênture Incentivada XYZ

**Não há dados de mercado a buscar por ativo.** O retorno é calculado a partir dos dados da posição do cliente (`posicoes_renda_fixa`) combinados com os índices já coletados em `dados_mercado`:

| Indexação | Dado de mercado usado | Origem |
|-----------|-----------------------|--------|
| `pos_fixado_cdi` (CDB, LCA) | CDI mensal | BCB API série 4389 |
| `pos_fixado_selic` (Tesouro Selic) | Selic mensal | BCB API série 4390 |
| `ipca_mais` (CDB C6, Debênture) | IPCA mensal | BCB API série 433 |
| `prefixado` (Tesouro Prefixado) | Nenhum | — |

> Nenhuma chamada adicional de API é necessária para renda fixa além dos índices globais já coletados.
