# Rendimento de Portfólio — Cálculo Completo

Guia estruturado para calcular o rendimento real da carteira de cada cliente para um mês selecionado. Todos os dados são lidos diretamente do banco Supabase — não há chamadas a APIs externas durante o cálculo. As APIs externas (BCB, brapi, CVM) alimentam o DB em um fluxo separado de atualização.

---

## Visão geral: os dois níveis de cálculo

```
Nível 1: Rendimento individual de cada ativo
    ↓ (multiplica pelo peso na carteira)
Nível 2: Rendimento total ponderado do portfólio
```

Os tipos de ativo presentes no banco e seus métodos de cálculo:

| Tipo de ativo | Tabela de posição | Tabela de preço/cota | Método |
|---|---|---|---|
| **Ação / FII** | `posicoes_acoes` | `precos_acoes` | Variação de preço + dividendos |
| **Fundo** | `posicoes_fundos` | `cotas_fundos` | Variação da cota |
| **Renda Fixa** | `posicoes_renda_fixa` | `dados_mercado` | Indexador + spread/taxa |

Os indexadores de mercado (CDI, IPCA, Selic, IBOVESPA, IMA-B) estão em `dados_mercado`, filtrados por `mes`.

---

## Parâmetro global: mês selecionado

Todas as consultas usam o parâmetro `mes_ref` (formato `YYYY-MM`, ex: `2025-04`) e `mes_anterior` (`mes_ref` - 1 mês).

---

## Módulo 1 — Ações e FIIs

### Conceito

Ações e FIIs geram retorno de duas formas:
1. **Ganho de capital**: variação do preço de fechamento entre dois meses
2. **Proventos**: dividendos ou JCP pagos no mês (já registrados em `precos_acoes.dividendos_pagos`)

> `ativos_acoes.tipo` pode ser `'Ação'` ou `'FII'`. As fórmulas de retorno são idênticas. A diferença está no **Módulo 6 (IR)**: dividendos de FII são isentos de IR para pessoa física.

---

### Inputs do banco

```sql
-- Posição do cliente
SELECT pa.ticker, pa.quantidade, pa.preco_medio_compra, pa.data_compra
FROM posicoes_acoes pa
WHERE pa.cliente_id = :cliente_id;

-- Preço do mês atual e do mês anterior
SELECT ticker, mes, preco_fechamento, dividendos_pagos
FROM precos_acoes
WHERE ticker = :ticker
  AND mes IN (:mes_ref, :mes_anterior);
```

| Variável | Origem |
|---|---|
| `quantidade` | `posicoes_acoes.quantidade` |
| `preco_fechamento_atual` | `precos_acoes.preco_fechamento` onde `mes = mes_ref` |
| `preco_fechamento_anterior` | `precos_acoes.preco_fechamento` onde `mes = mes_anterior` |
| `dividendos_pagos` | `precos_acoes.dividendos_pagos` onde `mes = mes_ref` (0 se não houve) |
| `preco_medio_compra` | `posicoes_acoes.preco_medio_compra` |
| `data_compra` | `posicoes_acoes.data_compra` |

---

### Passo a passo — Retorno mensal de uma ação/FII

**Passo 1.1 — Retorno de preço do mês:**
```
retorno_preco = (preco_fechamento_atual - preco_fechamento_anterior) / preco_fechamento_anterior
```

**Passo 1.2 — Retorno de proventos:**
```
retorno_proventos = dividendos_pagos / preco_fechamento_anterior
```
> Se `dividendos_pagos = 0`, `retorno_proventos = 0`.

**Passo 1.3 — Retorno total do ativo no mês:**
```
retorno_mes = retorno_preco + retorno_proventos
```

**Passo 1.4 — Valor atual da posição:**
```
valor_posicao = preco_fechamento_atual × quantidade
```

**Passo 1.5 — Variação monetária no mês:**
```
variacao_R$ = (preco_fechamento_atual - preco_fechamento_anterior) × quantidade
            + dividendos_pagos × quantidade
```

**Passo 1.6 — Retorno acumulado desde a compra:**
```
retorno_acumulado = (preco_fechamento_atual - preco_medio_compra) / preco_medio_compra
```

---

### Tabela-resumo das ações (exemplo Albert — mês de referência)

| Ação | Qtd | Preço ant. | Preço atual | Dividendos | Retorno mês | Valor posição | Variação R$ |
|---|---|---|---|---|---|---|---|
| LREN3 | 1.642 | R$ 15,55 | R$ 16,94 | R$ 0,00 | +8,94% | R$ 27.810 | +R$ 2.282 |
| MRFG3 | 1.504 | R$ 12,27 | R$ 10,26 | R$ 0,00 | -16,38% | R$ 15.431 | -R$ 3.023 |
| ARZZ3 | 193 | R$ 56,55 | R$ 56,58 | R$ 0,00 | +0,05% | R$ 10.920 | +R$ 6 |
| HAPV3 | 1.547 | R$ 2,25 | R$ 3,97 | R$ 0,00 | +76,44% | R$ 6.142 | +R$ 2.661 |
| **Total** | — | — | — | — | — | **R$ 60.303** | **+R$ 1.926** |

---

## Módulo 2 — Fundos de Investimento

### Conceito

Fundos não têm preço — têm **cota**. O retorno mensal é a variação da cota entre o último dia útil do mês anterior e o último dia útil do mês de referência.

As cotas já estão armazenadas por mês em `cotas_fundos`. **Não há necessidade de fallback por proxy** — se a cota do mês não estiver no banco, o dado de mercado ainda não foi inserido.

O `valor_liquido_atual` não é armazenado como campo separado. Ele é sempre calculado:
```
valor_liquido = numero_cotas × cota_fechamento
```

---

### Inputs do banco

```sql
-- Posição do cliente no fundo
SELECT pf.cnpj, pf.numero_cotas, pf.valor_aplicado, pf.data_investimento,
       af.nome, af.categoria
FROM posicoes_fundos pf
JOIN ativos_fundos af ON af.cnpj = pf.cnpj
WHERE pf.cliente_id = :cliente_id;

-- Cota do mês atual e do mês anterior
SELECT cnpj, mes, cota_fechamento
FROM cotas_fundos
WHERE cnpj = :cnpj
  AND mes IN (:mes_ref, :mes_anterior);
```

| Variável | Origem |
|---|---|
| `numero_cotas` | `posicoes_fundos.numero_cotas` |
| `valor_aplicado` | `posicoes_fundos.valor_aplicado` |
| `data_investimento` | `posicoes_fundos.data_investimento` |
| `cota_atual` | `cotas_fundos.cota_fechamento` onde `mes = mes_ref` |
| `cota_anterior` | `cotas_fundos.cota_fechamento` onde `mes = mes_anterior` |

---

### Passo a passo — Retorno mensal de um fundo

**Passo 2.1 — Retorno do mês:**
```
retorno_mes = (cota_atual / cota_anterior) - 1
```
> As cotas publicadas pelo gestor já são líquidas de taxa de administração e performance. O retorno calculado é líquido dessas taxas.

**Passo 2.2 — Valor líquido atual:**
```
valor_liquido = numero_cotas × cota_atual
```

**Passo 2.3 — Variação monetária no mês:**
```
variacao_R$ = numero_cotas × (cota_atual - cota_anterior)
```
Equivalente a:
```
variacao_R$ = valor_liquido × retorno_mes
```

**Passo 2.4 — Retorno acumulado desde a aplicação:**
```
retorno_acumulado = (valor_liquido / valor_aplicado) - 1
```

---

### Tabela-resumo dos fundos (exemplo Albert)

| Fundo | Nº cotas | Cota ant. | Cota atual | Retorno mês | Valor líquido | Variação R$ |
|---|---|---|---|---|---|---|
| Riza Lotus Plus | calcular | buscar DB | buscar DB | (cota_atual/cota_ant)-1 | ncotas × cota_atual | ncotas × Δcota |
| Brave I FIC FIM | calcular | buscar DB | buscar DB | (cota_atual/cota_ant)-1 | ncotas × cota_atual | ncotas × Δcota |
| ... | | | | | | |

> Exemplo Albert: para o mês de referência, preencher com os valores reais de `cotas_fundos`. Dados brutos do extrato de 04/04/2024 são defasados — usar sempre `cotas_fundos` do DB.

---

## Módulo 3 — Renda Fixa

### Conceito

O retorno de renda fixa depende do tipo de indexação registrado em `ativos_renda_fixa.indexacao`. Existem quatro tipos:

| `indexacao` | Tipo | Dado de mercado necessário |
|---|---|---|
| `pos_fixado_cdi` | Pós-fixado CDI | `dados_mercado.cdi_mensal` |
| `pos_fixado_selic` | Pós-fixado Selic | `dados_mercado.selic_mensal` |
| `prefixado` | Prefixado | Nenhum (taxa fixa contratada) |
| `ipca_mais` | Híbrido IPCA+ | `dados_mercado.ipca_mensal` |

O campo `posicoes_renda_fixa.unidade_taxa` determina como interpretar `taxa_contratada`:

| `unidade_taxa` | Significado | Exemplo |
|---|---|---|
| `%CDI` ou `%Selic` | Percentual do indexador | `taxa_contratada = 110` → 110% do CDI |
| `%a.a.` | Taxa anual fixa (spread ou prefixada) | `taxa_contratada = 12.5` → 12,5% a.a. |

---

### Inputs do banco

```sql
-- Posição do cliente em RF
SELECT prf.id, prf.taxa_contratada, prf.unidade_taxa, prf.valor_aplicado,
       prf.data_inicio, prf.data_vencimento,
       arf.nome, arf.indexacao, arf.isento_ir
FROM posicoes_renda_fixa prf
JOIN ativos_renda_fixa arf ON arf.id = prf.ativo_id
WHERE prf.cliente_id = :cliente_id;

-- Indexadores do mês de referência
SELECT mes, cdi_mensal, ipca_mensal, selic_mensal
FROM dados_mercado
WHERE mes = :mes_ref;
```

---

### 3A — Pós-fixado CDI (`pos_fixado_cdi`)

Onde `unidade_taxa = '%CDI'` e `taxa_contratada` é o percentual (ex: 110 para 110% CDI).

**Passo 3A.1:**
```
retorno_mes = cdi_mensal × (taxa_contratada / 100)

Exemplo CDB 110% CDI com CDI = 1,07%:
  retorno_mes = 1,07% × 1,10 = 1,177%
```

**Passo 3A.2 — Variação monetária:**
```
variacao_R$ = valor_aplicado × retorno_mes
```

---

### 3B — Pós-fixado Selic (`pos_fixado_selic`)

Onde `unidade_taxa = '%Selic'` e `taxa_contratada` é o percentual (ex: 100 para 100% Selic).

**Passo 3B.1:**
```
retorno_mes = selic_mensal × (taxa_contratada / 100)

Exemplo Tesouro Selic 100% com Selic = 1,08%:
  retorno_mes = 1,08% × 1,00 = 1,08%
```

**Passo 3B.2 — Variação monetária:**
```
variacao_R$ = valor_aplicado × retorno_mes
```

---

### 3C — Prefixado (`prefixado`)

Onde `unidade_taxa = '%a.a.'` e `taxa_contratada` é a taxa anual (ex: 12,5 para 12,5% a.a.).

**Passo 3C.1 — Converter taxa anual para mensal:**
```
retorno_mes = (1 + taxa_contratada / 100) ^ (1/12) - 1

Exemplo CDB 12,5% a.a.:
  retorno_mes = (1,125) ^ (1/12) - 1 = 0,9843% ao mês
```

**Passo 3C.2 — Variação monetária:**
```
variacao_R$ = valor_aplicado × retorno_mes
```

> **Marcação a mercado:** para o relatório mensal de carteiras mantidas até o vencimento, usar o retorno na curva (passo 3C.1). Se o cliente pretende vender antes do vencimento, o cálculo envolve a taxa de juros de mercado atual — fora do escopo deste módulo.

---

### 3D — Híbrido IPCA+ (`ipca_mais`)

Onde `unidade_taxa = '%a.a.'` e `taxa_contratada` é o spread anual (ex: 5,45 para IPCA+5,45% a.a.).

**Passo 3D.1 — Converter spread anual para mensal:**
```
spread_mes = (1 + taxa_contratada / 100) ^ (1/12) - 1

Exemplo spread 5,45% a.a.:
  spread_mes = (1,0545) ^ (1/12) - 1 = 0,4435%
```

**Passo 3D.2 — Compor IPCA do mês + spread:**
```
retorno_mes = (1 + ipca_mensal) × (1 + spread_mes) - 1

Exemplo com IPCA = 0,56%:
  retorno_mes = (1,0056) × (1,004435) - 1 = 1,006%
```

**Passo 3D.3 — Variação monetária:**
```
variacao_R$ = valor_aplicado × retorno_mes

Exemplo Albert (CDB IPCA+5,45%):
  variacao_R$ = R$ 40.478,75 × 1,006% = +R$ 407,22
```

> **Nota sobre `valor_aplicado` vs. valor de mercado:** o banco armazena `valor_aplicado` (valor inicial), não o valor de mercado corrente do título. Para renda fixa prefixada e IPCA+ de longo prazo, o valor de mercado pode diferir (marcação a mercado). Para o cálculo do **retorno percentual do mês**, isso não impacta — a fórmula usa apenas a taxa. Para o cálculo do **peso na carteira** (Módulo 4), usar `valor_aplicado` como proxy é uma simplificação conservadora e aceitável para relatórios mensais.

---

## Módulo 4 — Cálculo do Retorno Total do Portfólio

### Conceito

O retorno total é a **média ponderada** dos retornos individuais, onde o peso de cada ativo é sua participação no valor total da carteira no mês de referência.

```
retorno_portfolio = Σ (peso_i × retorno_mes_i)
```

---

### Inputs consolidados

| Ativo | `valor_posicao` (para calcular peso) |
|---|---|
| Ação / FII | `quantidade × preco_fechamento_atual` (de `precos_acoes`) |
| Fundo | `numero_cotas × cota_atual` (de `cotas_fundos`) |
| Renda Fixa | `valor_aplicado` (proxy — ver nota no Módulo 3) |

---

### Passo a passo

**Passo 4.1 — Calcular `valor_posicao` de cada ativo** (conforme tabela acima).

**Passo 4.2 — Calcular valor total da carteira:**
```
valor_total = Σ valor_posicao_i  (todos os ativos do cliente)
```

**Passo 4.3 — Calcular peso de cada ativo:**
```
peso_i = valor_posicao_i / valor_total
```

**Passo 4.4 — Calcular contribuição de cada ativo:**
```
contribuicao_i = peso_i × retorno_mes_i
```

**Passo 4.5 — Retorno total do portfólio:**
```
retorno_portfolio = Σ contribuicao_i
```

**Passo 4.6 — Variação monetária total:**
```
variacao_total_R$ = Σ variacao_R$_i
```
> Equivalente a: `variacao_total_R$ = valor_total × retorno_portfolio`

---

### Exemplo — Portfólio do Albert (mês de referência)

**Valor total investido: R$ 312.186,20**

#### Ações:
| Ativo | Valor posição | Peso | Retorno mês | Contribuição |
|---|---|---|---|---|
| LREN3 | R$ 27.810 | 8,91% | +8,94% | +0,797% |
| MRFG3 | R$ 15.431 | 4,94% | -16,38% | -0,809% |
| ARZZ3 | R$ 10.920 | 3,50% | +0,05% | +0,002% |
| HAPV3 | R$ 6.142 | 1,97% | +76,44% | +1,506% |
| **Subtotal** | **R$ 60.303** | **19,32%** | — | **+1,496%** |

#### Fundos:
| Ativo | Valor posição | Peso | Retorno mês | Contribuição |
|---|---|---|---|---|
| Riza Lotus Plus | `ncotas × cota_atual` | calc. | `(cota_atual/cota_ant)-1` | calc. |
| Brave I FIC FIM | `ncotas × cota_atual` | calc. | `(cota_atual/cota_ant)-1` | calc. |
| ... | | | | |
| **Subtotal** | **R$ ~209.655** | **~67,15%** | — | calc. |

#### Renda Fixa:
| Ativo | Valor posição | Peso | Retorno mês | Contribuição |
|---|---|---|---|---|
| CDB C6 IPCA+5,45% | R$ 40.479 (valor_aplicado) | 12,97% | +1,006% | +0,130% |
| **Subtotal** | **R$ 40.479** | **12,97%** | — | **+0,130%** |

#### Consolidação:
```
retorno_portfolio = contribuição_ações + contribuição_fundos + contribuição_RF
variacao_total_R$ = Σ variacao_R$_i
```

---

## Módulo 5 — Comparação com Benchmarks

### Conceito

O retorno isolado não informa se a carteira foi bem ou mal. Os benchmarks já estão em `dados_mercado` para cada mês.

---

### Inputs do banco

```sql
SELECT mes, cdi_mensal, ipca_mensal, selic_mensal,
       ibovespa_retorno_mensal, ima_b_retorno_mensal
FROM dados_mercado
WHERE mes = :mes_ref;
```

---

### Passo a passo

**Passo 5.1 — Alfa vs. CDI:**
```
alfa_CDI = retorno_portfolio - cdi_mensal
```
> Referência principal para carteiras conservadoras e multimercados.

**Passo 5.2 — Retorno real vs. IPCA:**
```
retorno_real = ((1 + retorno_portfolio) / (1 + ipca_mensal)) - 1
```

**Passo 5.3 — Alfa vs. IBOVESPA (parcela de ações):**

5.3.1 — Peso de cada ação dentro da classe:
```
peso_na_classe_i = valor_posicao_acao_i / valor_total_acoes
```

5.3.2 — Retorno ponderado da classe de ações:
```
retorno_acoes = Σ (peso_na_classe_i × retorno_mes_i)
```

5.3.3 — Alfa da classe de ações:
```
alfa_acoes = retorno_acoes - ibovespa_retorno_mensal
```

**Passo 5.4 — Alfa vs. IMA-B (para carteiras com IPCA+):**
```
alfa_ima_b = retorno_rf_ipca_mais - ima_b_retorno_mensal
```
> Relevante quando o cliente tem posições expressivas em IPCA+. O IMA-B é o benchmark natural para esse tipo de ativo.

---

## Módulo 6 — Retorno Líquido (IR)

### Conceito

Taxas de administração e performance já estão descontadas nas cotas dos fundos. O único desconto explícito a calcular é o **Imposto de Renda**, cobrado no resgate.

Para o relatório mensal, o IR não é cobrado mês a mês (exceto come-cotas). O cálculo aqui serve para estimar o retorno líquido hipotético em caso de resgate no mês de referência.

---

### Regras de tributação por tipo de ativo

```
SE tipo == 'Ação':
  SE vendas_no_mes > R$ 20.000:
    aliquota = 15%  (20% para day trade)
  SENÃO:
    aliquota = 0%   (isento)

SE tipo == 'FII':
  dividendos_pagos → aliquota = 0%  (sempre isento para PF)
  ganho_de_capital → aplicar regra igual à de ações acima

SE tipo == fundo (RF DI, Multimercado RF, Multimercado):
  dias = (data_resgate - data_investimento).dias
  SE dias <= 180:  aliquota = 22,5%
  SE dias <= 360:  aliquota = 20,0%
  SE dias <= 720:  aliquota = 17,5%
  SE dias > 720:   aliquota = 15,0%
  # Come-cotas: antecipa 15% (fundos LP) ou 20% (fundos CP) em maio e novembro

SE tipo == 'FIA' (Fundo de Ações):
  aliquota = 15%  (sem come-cotas)

SE tipo == renda_fixa:
  SE isento_ir == true:   # LCI, LCA, CRI, CRA
    aliquota = 0%
  SENÃO:                  # CDB, Tesouro
    dias = (data_resgate - data_inicio).dias
    Aplicar tabela regressiva acima (22,5% → 15%)
```

**Passo 6.1 — Ganho em R$:**
```
ganho_R$ = variacao_total_R$_do_ativo  (apenas a parte de ganho, não o principal)
```

**Passo 6.2 — IR estimado:**
```
ir_estimado = ganho_R$ × aliquota
```

**Passo 6.3 — Retorno líquido:**
```
retorno_liquido = retorno_bruto × (1 - aliquota)
```

> O campo `ativos_renda_fixa.isento_ir` sinaliza automaticamente os ativos isentos. Não é necessário inferir isso pelo nome do ativo.

---

## Módulo 7 — Queries consolidadas por cliente e mês

### Query completa — Ações

```sql
SELECT
  pa.ticker,
  aa.nome,
  aa.tipo,
  pa.quantidade,
  pa.preco_medio_compra,
  pa.data_compra,
  p_atual.preco_fechamento AS preco_atual,
  p_anterior.preco_fechamento AS preco_anterior,
  p_atual.dividendos_pagos,
  -- Retorno mensal
  (p_atual.preco_fechamento - p_anterior.preco_fechamento) / p_anterior.preco_fechamento
    + p_atual.dividendos_pagos / p_anterior.preco_fechamento AS retorno_mes,
  -- Valor da posição
  pa.quantidade * p_atual.preco_fechamento AS valor_posicao,
  -- Variação em R$
  (p_atual.preco_fechamento - p_anterior.preco_fechamento) * pa.quantidade
    + p_atual.dividendos_pagos * pa.quantidade AS variacao_R$,
  -- Retorno acumulado
  (p_atual.preco_fechamento - pa.preco_medio_compra) / pa.preco_medio_compra AS retorno_acumulado
FROM posicoes_acoes pa
JOIN ativos_acoes aa ON aa.ticker = pa.ticker
JOIN precos_acoes p_atual ON p_atual.ticker = pa.ticker AND p_atual.mes = :mes_ref
JOIN precos_acoes p_anterior ON p_anterior.ticker = pa.ticker AND p_anterior.mes = :mes_anterior
WHERE pa.cliente_id = :cliente_id;
```

### Query completa — Fundos

```sql
SELECT
  pf.cnpj,
  af.nome,
  af.categoria,
  pf.numero_cotas,
  pf.valor_aplicado,
  pf.data_investimento,
  c_atual.cota_fechamento AS cota_atual,
  c_anterior.cota_fechamento AS cota_anterior,
  -- Retorno mensal
  (c_atual.cota_fechamento / c_anterior.cota_fechamento) - 1 AS retorno_mes,
  -- Valor líquido atual
  pf.numero_cotas * c_atual.cota_fechamento AS valor_liquido,
  -- Variação em R$
  pf.numero_cotas * (c_atual.cota_fechamento - c_anterior.cota_fechamento) AS variacao_R$,
  -- Retorno acumulado
  (pf.numero_cotas * c_atual.cota_fechamento / pf.valor_aplicado) - 1 AS retorno_acumulado
FROM posicoes_fundos pf
JOIN ativos_fundos af ON af.cnpj = pf.cnpj
JOIN cotas_fundos c_atual ON c_atual.cnpj = pf.cnpj AND c_atual.mes = :mes_ref
JOIN cotas_fundos c_anterior ON c_anterior.cnpj = pf.cnpj AND c_anterior.mes = :mes_anterior
WHERE pf.cliente_id = :cliente_id;
```

### Query completa — Renda Fixa

```sql
SELECT
  prf.id,
  arf.nome,
  arf.indexacao,
  arf.isento_ir,
  prf.taxa_contratada,
  prf.unidade_taxa,
  prf.valor_aplicado,
  prf.data_inicio,
  prf.data_vencimento,
  dm.cdi_mensal,
  dm.ipca_mensal,
  dm.selic_mensal,
  -- Retorno mensal calculado via CASE no app (ver Módulos 3A-3D)
  CASE arf.indexacao
    WHEN 'pos_fixado_cdi'   THEN dm.cdi_mensal   * (prf.taxa_contratada / 100)
    WHEN 'pos_fixado_selic' THEN dm.selic_mensal  * (prf.taxa_contratada / 100)
    WHEN 'prefixado'        THEN POWER(1 + prf.taxa_contratada / 100, 1.0/12) - 1
    WHEN 'ipca_mais'        THEN (1 + dm.ipca_mensal) * POWER(1 + prf.taxa_contratada / 100, 1.0/12) - 1
  END AS retorno_mes,
  -- Variação em R$
  prf.valor_aplicado *
  CASE arf.indexacao
    WHEN 'pos_fixado_cdi'   THEN dm.cdi_mensal   * (prf.taxa_contratada / 100)
    WHEN 'pos_fixado_selic' THEN dm.selic_mensal  * (prf.taxa_contratada / 100)
    WHEN 'prefixado'        THEN POWER(1 + prf.taxa_contratada / 100, 1.0/12) - 1
    WHEN 'ipca_mais'        THEN (1 + dm.ipca_mensal) * POWER(1 + prf.taxa_contratada / 100, 1.0/12) - 1
  END AS variacao_R$
FROM posicoes_renda_fixa prf
JOIN ativos_renda_fixa arf ON arf.id = prf.ativo_id
JOIN dados_mercado dm ON dm.mes = :mes_ref
WHERE prf.cliente_id = :cliente_id;
```

> **Atenção:** para `ipca_mais`, a fórmula acima usa `(1 + ipca_mensal) × (1 + spread_mes) - 1` onde `spread_mes = (1 + taxa_contratada/100)^(1/12) - 1`. A query SQL simplifica para `(1 + ipca_mensal) × POWER(1 + taxa_contratada/100, 1.0/12) - 1`, que é equivalente.

---

## Módulo 8 — Dois fluxos distintos: Atualização vs. Cálculo

O processo mensal é composto de **dois fluxos independentes**:

### Fluxo A — Atualização do banco (alimenta APIs externas → Supabase)

```
[ ] A1. Inserir preços e dividendos em precos_acoes
    → Fonte: brapi.dev (por ticker, por mês)
    → Formato: (ticker, mes, preco_fechamento, dividendos_pagos)

[ ] A2. Inserir cotas dos fundos em cotas_fundos
    → Fonte: CVM informe diário (inf_diario_fi_AAAAMM.zip)
    → Filtrar por CNPJ dos fundos cadastrados em ativos_fundos
    → Formato: (cnpj, mes, cota_fechamento) — último dia útil do mês

[ ] A3. Inserir dados de mercado em dados_mercado
    → CDI: BCB API série 12
    → IPCA: BCB API série 433
    → Selic: BCB API série 11
    → IBOVESPA: brapi.dev ticker ^BVSP
    → IMA-B: ANBIMA API
    → Formato: (mes, cdi_mensal, ipca_mensal, selic_mensal, ibovespa_retorno_mensal, ima_b_retorno_mensal)
```

### Fluxo B — Cálculo do rendimento (consulta o Supabase)

```
[ ] B1. Receber parâmetro: cliente_id + mes_ref
[ ] B2. Calcular mes_anterior = mes_ref - 1 mês
[ ] B3. Executar queries dos Módulos 7 (ações, fundos, RF)
[ ] B4. Calcular valor_posicao de cada ativo e valor_total
[ ] B5. Calcular peso e contribuição de cada ativo (Módulo 4)
[ ] B6. Calcular retorno_portfolio = Σ contribuições
[ ] B7. Buscar benchmarks em dados_mercado (Módulo 5)
[ ] B8. Calcular alfa_CDI, retorno_real, alfa_acoes, alfa_ima_b
[ ] B9. Calcular retorno líquido estimado (Módulo 6)
[ ] B10. Montar JSON de saída para o LLM
```

### JSON de saída para o LLM

```json
{
  "cliente_id": "uuid",
  "cliente_nome": "Alberto...",
  "mes_ref": "2025-04",
  "retorno_portfolio_bruto": 0.01793,
  "variacao_R$": 5598.30,
  "valor_total": 312186.20,
  "benchmarks": {
    "cdi_mensal": 0.0107,
    "ipca_mensal": 0.0056,
    "ibovespa_mensal": 0.035,
    "ima_b_mensal": 0.012
  },
  "alfas": {
    "vs_cdi": 0.00723,
    "retorno_real": 0.01228,
    "acoes_vs_ibovespa": 0.04228
  },
  "ativos": [
    {
      "tipo": "acao",
      "ticker": "LREN3",
      "nome": "Lojas Renner",
      "retorno_mes": 0.0894,
      "valor_posicao": 27810.08,
      "variacao_R$": 2282.38,
      "peso": 0.0891,
      "contribuicao": 0.00797,
      "retorno_acumulado": -0.4169
    }
  ],
  "top_contributors": [],
  "top_detractors": []
}
```

---

## Apêndice — Fórmulas de referência rápida

```
// Ações e FIIs
retorno_mes = (preco_atual - preco_anterior + dividendos) / preco_anterior
valor_posicao = quantidade × preco_atual
variacao_R$ = (preco_atual - preco_anterior) × quantidade + dividendos × quantidade

// Fundos
retorno_mes = (cota_atual / cota_anterior) - 1
valor_liquido = numero_cotas × cota_atual
variacao_R$ = numero_cotas × (cota_atual - cota_anterior)

// RF pós-fixado CDI
retorno_mes = cdi_mensal × (taxa_contratada / 100)

// RF pós-fixado Selic
retorno_mes = selic_mensal × (taxa_contratada / 100)

// RF prefixado
retorno_mes = (1 + taxa_contratada/100) ^ (1/12) - 1

// RF IPCA+
spread_mes = (1 + taxa_contratada/100) ^ (1/12) - 1
retorno_mes = (1 + ipca_mensal) × (1 + spread_mes) - 1

// Portfólio
peso_i = valor_posicao_i / valor_total
contribuicao_i = peso_i × retorno_mes_i
retorno_portfolio = Σ contribuicao_i

// Benchmarks
alfa_CDI = retorno_portfolio - cdi_mensal
retorno_real = (1 + retorno_portfolio) / (1 + ipca_mensal) - 1
alfa_acoes = retorno_acoes_ponderado - ibovespa_mensal

// IR (retorno líquido estimado no resgate)
retorno_liquido = retorno_bruto × (1 - aliquota_IR)
```
