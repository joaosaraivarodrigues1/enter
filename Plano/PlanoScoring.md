# Plano de Implementação — Engine de Scoring Buy/Sell

## Objetivo

Transformar o grafo atual (que manda dados brutos para o LLM interpretar) em um **engine determinístico de scoring** que aplica as regras do BuySellRecomendation.md antes do LLM — entregando para o Chat node um JSON estruturado de recomendações já calculadas, não dados brutos.

```
ANTES:  dados brutos → LLM "interpreta tudo"  → narrativa (inconsistente)
DEPOIS: dados brutos → engine de scoring → JSON estruturado → LLM "escreve narrativa" → relatório
```

---

## Arquitetura de Subgrafos

O projeto Rivet passa a ter múltiplos grafos especializados:

```
Rivet.rivet-project
├── gerar_recomendacao      ← grafo principal (orquestrador) — JÁ EXISTE
├── scoring_engine          ← NOVO: recebe portfolio completo → JSON de recomendações
├── score_por_ativo         ← NOVO: calcula score de 1 ativo (usado com Splitting)
├── validar_restricoes      ← NOVO: IR + liquidez por recomendação
└── narrativa_recomendacao  ← NOVO: Chat node isolado (recebe JSON → escreve relatório)
```

### Por que subgrafos?

- `score_por_ativo` é executado **N vezes em paralelo** via Splitting (1 execução por ativo)
- `validar_restricoes` idem — validação de IR/liquidez por ativo em paralelo
- `narrativa_recomendacao` isolado permite testar o Chat node independente do scoring
- Cada subgrafo tem inputs/outputs claros → testável individualmente

---

## Paralelização

### Nível 1 — HTTP Calls (já existe, nativo)
O Rivet executa todos os nodes sem dependência em paralelo automaticamente.
As 11 HTTP Calls atuais já rodam em paralelo. Adicionamos mais 1:

```
HTTP Call atual (11 paralelos):   cliente, posicoes_acoes, ativos_acoes,
                                   precos_acoes, posicoes_fundos, ativos_fundos,
                                   cotas_fundos, posicoes_rf, ativos_rf,
                                   macro_atual, relatorio

HTTP Call novo (roda em paralelo com os demais):
  macro_historico  →  /rest/v1/dados_mercado?mes=gte.2025-03&mes=lte.2026-03
                       &select=mes,selic_mensal,cdi_mensal,ibovespa_retorno_mensal
                       &order=mes.asc
```

O `macro_historico` serve para:
- Derivar `selic_tendencia` (selic atual > média 3 meses → "alta")
- Calcular CDI acumulado 12m e Ibovespa acumulado 12m (benchmark de fundos)

### Nível 2 — Splitting por ativo
O subgrafo `score_por_ativo` recebe **um ativo por vez**, mas é chamado com **Split ativado**.

```
[Code node: monta array de ativos enriquecidos]
        ↓ array de N objetos
[Subgraph Node: score_por_ativo]  ← Split ON, max = 50
        ↓ array de N scores (paralelo)
[Code node: filtra score ≠ 0, ordena, adiciona substitutos]
        ↓ JSON final de recomendações
[narrativa_recomendacao]
```

Resultado: todos os ativos do portfólio são avaliados simultaneamente, não um por um.

### Nível 3 — Dois Chat nodes em paralelo (opcional fase 2)
Para portfólios grandes, dividir o relatório em seções:

```
[JSON de recomendações]
        ├── [Chat node: "Seção Ações + Fundos"]
        └── [Chat node: "Seção RF + Conclusão"]
                ↓ (ambos rodam em paralelo)
[Text node: junta as duas seções]
```

---

## Dados: O que adicionar no Supabase

### 1. Nova coluna `ativos_acoes.perfil_macro`

```sql
ALTER TABLE ativos_acoes ADD COLUMN perfil_macro text;
-- Valores: 'exportador' | 'importador' | 'domestico'
```

Necessária para o sinal macro de câmbio (USD/BRL > 5,50 favorece exportadores).
Preencher para todos os tickers existentes.

### 2. Nenhuma outra migração

- `selic_tendencia` → derivado no Code node a partir de `macro_historico`
- `retorno_12m` de fundos → derivado de `cotas_fundos` histórico (dados já existem no schema)
- `ipca_anual` → `SUM(ipca_mensal)` dos últimos 12 meses via `macro_historico`

---

## Engine de Scoring — Subgrafo `score_por_ativo`

### Input
```json
{
  "ativo": { objeto enriquecido com todos os campos },
  "portfolio_context": { valor_total, alocacao_atual_por_classe, perfil_cliente },
  "macro": { cdi, selic, selic_tendencia, ipca_anual, usd_brl, pib, ibovespa_acumulado_12m }
}
```

### Lógica interna (Code node)

```
ETAPA 1 — Suitability (ICVM 539/2013)
  Matriz hardcoded por perfil
  Se inadequado → score = -99, acao = "VENDER", urgencia = "REGULATORIO"
  → retorno imediato (sem calcular mais nada)

ETAPA 2 — Três sinais

  Sinal 1: Desvio de alocação (peso 1)
    desvio = alocacao_atual_classe - alvo_medio_classe
    > +10pp → -1 | < -10pp → +1 | entre -5 e +5pp → 0

  Sinal 2: Risco do ativo (peso 2)
    2a. Drawdown vs PM:
        < -40% e peso > 1,5% → -2
        < -25% e peso >   3% → -1
    2b. Retorno positivo sólido:
        retorno > +15% → +1
    2c. Concentração:
        peso > 25% → -1
    2d. Posição residual:
        peso < 0,5% → -1
    2e. Underperformance de fundo (se historico disponível):
        retorno_12m < benchmark_12m * 0,80 → -1

  Sinal 3: Macro (peso 1, limitado a -1/+1)
    Selic em alta:
      RF pós-fixada, fundo DI → +1
      ações varejo/crescimento, long biased → -1
    IPCA > 5% ao ano:
      RF IPCA+ → +1
      varejo discricionário, saúde privada → -1
    USD/BRL > 5,50:
      exportador → +1 | importador → -1
    PIB < 2%:
      varejo discricionário, construção → -1
      RF pós-fixada → +1

  score_total = sinal_1 + sinal_2 + sinal_3

ETAPA 3 — Decisão
  +3       → COMPRAR   (urgência ALTA)
  +2       → AUMENTAR  (urgência MÉDIA)
  +1       → MANTER+   (urgência BAIXA)
   0       → MANTER    (sem ação)
  -1       → MANTER-   (urgência BAIXA)
  -2       → REDUZIR   (urgência MÉDIA)
  ≤ -3     → VENDER    (urgência ALTA)

ETAPA 4 — Restrições (só se ação = VENDER ou REDUZIR)
  Liquidez: prazo_resgate_dias
  IR:
    ganho = valor_atual - valor_aplicado (ou quantidade * preco_medio)
    Se ganho > 0: calcular alíquota regressiva → ir_estimado
    meses_payback = ir_estimado / (valor_total * cdi_mensal)
  Isenção ações: flag se valor_atual ≤ R$20k (verificar no Code node principal)

ETAPA 5 — Substituto (só se ação = VENDER ou REDUZIR)
  Mapa hardcoded: (categoria_ativo, perfil, regime_selic) → substituto
  Default fallback: "fundo_DI" (sempre dentro do suitability)
```

### Output por ativo
```json
{
  "ticker_ou_nome": "HAPV3",
  "classe": "acoes",
  "acao": "VENDER",
  "urgencia": "ALTA",
  "score": -3,
  "score_detalhe": { "sinal_alocacao": 0, "sinal_risco": -2, "sinal_macro": -1 },
  "gatilhos": ["Drawdown: -74,6% (limiar: -40%)", "Setor saúde: Selic alta + controle ANS"],
  "restricoes": { "liquidez": "D+2", "ir": "Venda com prejuízo — sem IR", "suitability": "OK" },
  "substituto_sugerido": "Tesouro IPCA+ 2029",
  "valor_envolvido_brl": 6143.14,
  "peso_portfolio": 0.0197
}
```

---

## Subgrafo `validar_restricoes`

Recebe o array de recomendações com ação VENDER/REDUZIR e:
- Ordena por urgência (regulatório > alta > média > baixa)
- Calcula `total_vendas_acoes` para verificar isenção de R$20k
- Ajusta flag de isenção IR para ações

Rodado com **Split ON** — cada recomendação validada em paralelo.

---

## Subgrafo `narrativa_recomendacao`

**Input:** JSON de recomendações validadas + resumo macro + perfil cliente

**Prompt base:**
```
Você é um assessor sênior da XP Investimentos escrevendo a seção de recomendações
do relatório mensal em português brasileiro.

PERFIL DO CLIENTE: {perfil}
CONTEXTO MACRO: {resumo_macro}
RECOMENDAÇÕES (calculadas pelo engine): {json_recomendacoes}

Instruções:
- 2 a 3 parágrafos por grupo de recomendação (vender, manter, comprar)
- Tom profissional mas acessível
- Para cada VENDER: explicar destino do recurso liberado
- Para MANTER: reforçar o porquê da posição atual
- Para COMPRAR/AUMENTAR: mencionar catalisador macro
- Quantificar benefício esperado onde possível ("ao realocar para CDB a Selic 15,5%...")
- Nunca inventar dados além do JSON recebido
- Nunca prometer retornos futuros
- Mencionar IR só se material (> R$500 ou = R$0 quando esperado)
- Mencionar liquidez apenas se prazo_resgate > 15 dias
```

---

## Otimizações Inteligentes

### 1. Skip de ativos neutros
O Code node de scoring filtra `score = 0` antes de passar ao LLM.
Portfólio bem alocado = JSON menor = prompt menor = custo menor.

### 2. Selic tendência derivada (sem nova coluna)
```javascript
const selic_series = macro_historico.map(m => m.selic_mensal);
const selic_atual = selic_series[selic_series.length - 1];
const selic_media_3m = selic_series.slice(-4, -1).reduce((a,b) => a+b, 0) / 3;
const selic_tendencia = selic_atual > selic_media_3m * 1.005 ? 'alta'
                      : selic_atual < selic_media_3m * 0.995 ? 'baixa'
                      : 'estavel';
```

### 3. CDI e Ibovespa acumulados 12m (benchmark de fundos)
```javascript
const cdi_12m = macro_historico.reduce((acc, m) => acc * (1 + m.cdi_mensal/100), 1) - 1;
const ibov_12m = macro_historico.reduce((acc, m) => acc * (1 + m.ibovespa_retorno_mensal/100), 1) - 1;
```

### 4. Prompt versionado no Code node
O prompt do Chat node não fica hardcoded no nó visual — vem como string do Code node.
Facilita versionamento em Git e comparação de variações de prompt.

### 5. Insights comparativos entre clientes (fase 2)
Adicionar `recomendacoes_historico` ou comparar JSONs de scoring entre meses:
- "Este mês LREN3 aparece como VENDER para 5 dos 8 clientes" → sinal sistêmico
- Diferença de score entre meses para o mesmo ativo → tendência

---

## Fluxo Completo do Grafo Principal (pós-implementação)

```
[graphInput "job"]
        ↓
[Extract: job_id, cliente_id, mes_referencia]

── PARALELO (12 HTTP Calls) ──────────────────────────────────────
| cliente | posicoes_acoes | ativos_acoes | precos_acoes          |
| posicoes_fundos | ativos_fundos | cotas_fundos                  |
| posicoes_rf | ativos_rf | macro_atual | macro_historico         |
| relatorio                                                        |
──────────────────────────────────────────────────────────────────
        ↓
[Code node: enriquece ativos, computa campos derivados,
            deriva selic_tendencia, CDI/Ibov 12m,
            monta array de ativos + portfolio_context + macro]
        ↓
[Subgraph: score_por_ativo] ← Split ON (paralelo por ativo)
        ↓ array de scores
[Subgraph: validar_restricoes] ← Split ON (paralelo)
        ↓ JSON de recomendações validadas
[Subgraph: narrativa_recomendacao]
        ↓
[graphOutput "recomendacao"]
```

---

## Ordem de Implementação

| Passo | O que fazer | Onde | Esforço |
|-------|-------------|------|---------|
| 1 | Migration: `ALTER TABLE ativos_acoes ADD COLUMN perfil_macro text` | Supabase | 10 min |
| 2 | Preencher `perfil_macro` para todos os tickers | Supabase SQL | 15 min |
| 3 | Adicionar HTTP Call `macro_historico` no grafo principal | Rivet IDE | 10 min |
| 4 | Criar subgrafo `score_por_ativo` com Code node (Etapas 1-5) | Rivet IDE | 2-3h |
| 5 | Testar subgrafo isolado com um ativo via Remote Debugger | Rivet IDE | 30 min |
| 6 | Criar subgrafo `validar_restricoes` | Rivet IDE | 30 min |
| 7 | Criar subgrafo `narrativa_recomendacao` com Chat node | Rivet IDE | 20 min |
| 8 | Recompor grafo principal: conectar subgrafos com Split | Rivet IDE | 1h |
| 9 | Testar ponta a ponta com `albert-2026-03` via dev.ps1 | PowerShell | 30 min |
| 10 | Testar os 8 clientes e comparar JSONs de scoring | PowerShell | 1h |

---

## O Que Não Muda

- `server.mjs` — nenhuma alteração
- Edge Function — nenhuma alteração
- Streamlit — nenhuma alteração
- `graphInput "job"` e os 3 Extract Object Path — permanecem iguais
- Context nodes `supabase_url` e `supabase_key` — permanecem iguais
- As 11 HTTP Calls existentes — permanecem, adicionar só `macro_historico`
