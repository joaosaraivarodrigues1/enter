# Recomendação de Rebalanceamento

## Resumo

Pipeline determinístico que recebe dados brutos de carteira, mercado e perfil do cliente e produz recomendações estruturadas de compra e venda para rebalancear a alocação por classe de ativo. O LLM atua apenas na extração de scores macro e na geração da narrativa final — todas as decisões de rebalanceamento são calculadas por regras.

---

## Entradas

### Dados brutos — Supabase (HTTP Calls)

**Cadastro de ativos** — estáticos, sem filtro de cliente
```
ativos_renda_fixa  →  { id, nome, instrumento, indexacao }
ativos_acoes       →  { ticker, nome, tipo, setor }
ativos_fundos      →  { cnpj, nome, categoria }
```

**Séries históricas** — filtradas por janela de 12 meses
```
precos_acoes   →  { mes, ticker, preco_fechamento }
cotas_fundos   →  { mes, cnpj, cota_fechamento }
dados_mercado  →  { mes, cdi_mensal, selic_mensal, ipca_mensal,
                       ibovespa_retorno_mensal, usd_brl_fechamento,
                       pib_crescimento_anual }
```

**Carteira do cliente** — filtradas por `cliente_id`
```
posicoes_acoes   →  { ticker, quantidade, preco_medio_compra, data_compra }
posicoes_fundos  →  { cnpj, numero_cotas, valor_aplicado, data_investimento }
posicoes_rf      →  { ativo_id, taxa_contratada, valor_aplicado,
                        data_inicio, data_vencimento }
```

**Contexto do cliente**
```
cliente    →  { id, nome, perfil_de_risco }
relatorio  →  { conteudo_txt }
```

---

### Dados estáticos — hardcoded nos nodes

```
ClassesDeAtivos   →  mapeamento indexacao/categoria/tipo → id de classe
PerfisDeRisco     →  suitability + alocacao (min/alvo/max) por perfil
Pesos macro       →  matriz de pesos por indicador por classe (RankingClassesAtivos)
```

---

### Dado externo — produzido pelo LLM

```
scores_macro  →  { selic, ipca, cambio, pib, credito, fiscal, externo }
                 inteiros de -2 a +2, extraídos do conteudo_txt do relatório
```

---

## Saídas intermediárias expostas

```
ranking_ativos         →  { caixa: [...], renda_fixa: [...],
                             multimercado: [...], renda_variavel: [...] }
                            ativos ordenados por sharpe_proxy dentro de cada classe

ranking_classes        →  ["caixa", "renda_fixa", "multimercado", "renda_variavel"]
                            classes ordenadas por score macro, da mais à menos atraente

classes_permitidas     →  ["caixa", "renda_fixa", "multimercado"]
                            classes que o perfil do cliente permite possuir

ranking_global         →  { caixa: [...], renda_fixa: [...], multimercado: [...] }
                            interseção dos três acima: só classes permitidas,
                            na ordem macro, ativos na ordem interna

posicoes_valorizadas   →  [{ id, nome, classe, valor_atual, tipo }]
                            cada posição da carteira com valor atual calculado

percentual_por_classe  →  { total_carteira,
                             por_classe: { [classe]: { valor, percentual } } }
                            fotografia da alocação atual em % e R$

desvios_por_classe     →  { [classe]: { alvo, atual, desvio_pp,
                                         desvio_brl, status } }
                            status: "excesso" | "ok" | "deficit"
```

---

## Saídas finais

```
recomendacoes_venda   →  [{ ativo, classe, valor_sugerido, motivo }]
                          uma entrada por classe em "excesso"

recomendacoes_compra  →  [{ ativo, classe, valor_sugerido,
                              ja_na_carteira, motivo }]
                          uma entrada por classe em "deficit"

narrativa             →  texto em português
                          escrito pelo LLM com base em todos os estados expostos
```

---

## Pipeline — nodes e dependências

```
dados_mercado + relatorio ──────────────────────────────────→ scores_macro
                                                                    ↓
ativos_rf/acoes/fundos                                      ranking_classes
precos_acoes                 → ranking_ativos ──────────────────────↓
cotas_fundos                                                ranking_global ←── classes_permitidas
dados_mercado                                                       ↓               ↑
                                                         (usado em 4a e 4b)    perfil_de_risco
                                                                                    ↑
posicoes_acoes ──┐                                                                  │
posicoes_fundos ─┤→ posicoes_valorizadas → percentual_por_classe → desvios ────────┘
posicoes_rf ─────┘                                                      ↓
                                                            recomendacoes_venda
                                                            recomendacoes_compra
                                                                        ↓
                                                                   narrativa
```

---

## Detalhamento dos nodes

### Node 1 — Valorizar Posições

**Propósito:** calcular valor atual de cada posição e atribuir sua classe.

**Inputs:** `posicoes_acoes`, `posicoes_fundos`, `posicoes_rf`, `precos_acoes`, `cotas_fundos`, `ativos_rf`, `ativos_fundos`

**Regras:**
```
Ações:  valor_atual = quantidade × ultimo_preco_fechamento(ticker)
Fundos: valor_atual = numero_cotas × ultima_cota_fechamento(cnpj)
RF:     valor_atual = valor_aplicado  ← sem histórico de preço disponível

Classe de cada posição:
  Ação / FII                                              → renda_variavel
  FIA                                                     → renda_variavel
  Multimercado / Long Biased                              → multimercado
  RF DI / RF Simples / pos_fixado_cdi / pos_fixado_selic → caixa
  Multimercado RF / ipca_mais / prefixado                → renda_fixa
```

**Output:**
```json
[
  { "id": "LREN3",   "nome": "Lojas Renner", "classe": "renda_variavel", "valor_atual": 47699.10, "tipo": "acao"  },
  { "id": "0bdc21…", "nome": "Tesouro Selic","classe": "caixa",         "valor_atual": 59000.00, "tipo": "rf"    },
  { "id": "15.799…", "nome": "Ibiuna Hedge", "classe": "multimercado",  "valor_atual": 18450.00, "tipo": "fundo" }
]
```

---

### Node 2 — Percentuais por Classe

**Propósito:** agregar valor por classe e calcular percentual sobre o total.

**Input:** `posicoes_valorizadas`

**Regras:**
```
total_carteira = soma de todos os valor_atual
valor_classe   = soma dos valor_atual da classe
percentual     = (valor_classe / total_carteira) × 100
```

**Output:**
```json
{
  "total_carteira": 187331.50,
  "por_classe": {
    "caixa":          { "valor": 59000.00, "percentual": 31.5 },
    "renda_fixa":     { "valor": 50000.00, "percentual": 26.7 },
    "multimercado":   { "valor": 50450.00, "percentual": 26.9 },
    "renda_variavel": { "valor": 27881.50, "percentual": 14.9 }
  }
}
```

---

### Node 3 — Desvios vs Alvo

**Propósito:** comparar alocação atual com os alvos do perfil e calcular quanto falta ou sobra.

**Inputs:** `por_classe`, `perfil_de_risco`

**Regras:**
```
Para cada classe:
  alvo_pct  = perfil.alocacao[classe].alvo
  min_pct   = perfil.alocacao[classe].min
  max_pct   = perfil.alocacao[classe].max
  atual_pct = por_classe[classe].percentual

  desvio_pp  = atual_pct - alvo_pct
  desvio_brl = desvio_pp / 100 × total_carteira
               positivo = excesso → candidato a venda
               negativo = deficit → candidato a compra

  status = atual_pct > max_pct ? "excesso"
         : atual_pct < min_pct ? "deficit"
         : "ok"
```

**Output:**
```json
{
  "total_carteira": 187331.50,
  "desvios": {
    "caixa":          { "alvo": 30, "atual": 31.5, "desvio_pp": +1.5, "desvio_brl": +2809.97, "status": "ok"      },
    "renda_fixa":     { "alvo": 35, "atual": 26.7, "desvio_pp": -8.3, "desvio_brl": -15548.51,"status": "deficit" },
    "multimercado":   { "alvo": 25, "atual": 26.9, "desvio_pp": +1.9, "desvio_brl": +3559.30, "status": "ok"      },
    "renda_variavel": { "alvo": 10, "atual": 14.9, "desvio_pp": +4.9, "desvio_brl": +9179.44, "status": "excesso" }
  }
}
```

---

### Node 4a — Recomendações de Venda

**Propósito:** para cada classe em `excesso`, identificar qual ativo vender e quanto.

**Inputs:** `posicoes_valorizadas`, `desvios`, `ranking_global`

**Regras:**
```
Para cada classe com status = "excesso":
  valor_a_reduzir = desvio_brl da classe

  Ordenar posições da classe por prioridade de venda:
    1º: ativos que NÃO aparecem no ranking_global (não recomendados)
    2º: ativos que aparecem no ranking_global, do último para o primeiro

  Percorrer essa ordem até cobrir valor_a_reduzir:
    Se valor_atual_posicao <= saldo_restante → vender posição inteira
    Caso contrário → vender parcialmente
```

**Output:**
```json
[
  {
    "ativo": "MRFG3",
    "classe": "renda_variavel",
    "acao": "VENDER",
    "valor_sugerido": 9179.44,
    "motivo": "classe em excesso — posição com menor prioridade no ranking"
  }
]
```

---

### Node 4b — Recomendações de Compra

**Propósito:** para cada classe em `deficit`, identificar qual ativo comprar e quanto.

**Inputs:** `posicoes_valorizadas`, `desvios`, `ranking_global`

**Regras:**
```
Para cada classe com status = "deficit":
  valor_a_aportar = |desvio_brl| da classe

  Ordenar candidatos por prioridade de compra:
    1º: ativos já na carteira que estão no topo do ranking_global
    2º: ativos do ranking_global que o cliente ainda não possui

  Recomendar o primeiro da lista pelo valor_a_aportar completo
```

**Output:**
```json
[
  {
    "ativo": "CDB C6 Bank IPCA+",
    "classe": "renda_fixa",
    "acao": "COMPRAR",
    "valor_sugerido": 15548.51,
    "ja_na_carteira": true,
    "motivo": "classe em deficit — ativo com maior prioridade no ranking"
  }
]
```

---

## Comportamentos especiais

| Situação | Comportamento |
|----------|--------------|
| Todas as classes dentro do corredor | nodes 4a e 4b retornam `[]` — nenhuma recomendação |
| Classe não permitida pelo perfil com posição existente | `status = "excesso"` forçado — recomendação de venda sempre gerada |
| Fundo sem `categoria` | excluído de todas as etapas silenciosamente |
| Valor da venda menor que o excesso necessário | recomendação cobre parcialmente — sem escalar para próximo ativo |
| Venda e compra simultâneas | tratadas de forma independente — cruzamento de fluxos fica para a narrativa |

---

## Limitações conhecidas

1. **RF valorizada pelo custo** — `valor_aplicado` ignora juros acumulados. Distorce os percentuais da carteira.
2. **Sem IR** — recomendações de venda não consideram imposto sobre ganho de capital nem isenção de R$20k em ações.
3. **Sem liquidez** — `prazo_resgate_dias` ausente dos dados. Fundos com resgate longo recebem o mesmo tratamento que ações.
4. **Sharpe com 11 pontos** — base estatística fraca para o ranking de ativos.
5. **`setor` null em todas as ações** — sinal de câmbio por tipo de empresa não aplicável.
6. **Corredor estático** — `min/max` do perfil não se ajustam ao cenário macro.
7. **Uma recomendação por classe** — não escala automaticamente se o primeiro ativo não cobre o desvio inteiro.
