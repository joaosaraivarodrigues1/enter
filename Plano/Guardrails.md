# Guard Rails — AI Financial Advisor (Rivet + OpenAI)

> Escopo: fluxo Rivet com LLM (OpenAI) para leitura e extração de três tipos de documento —
> **portfólio**, **perfil de risco** e **análise de mercado**. Sem escopo de contratos ou outros documentos.

---

## 1. Contexto de uso de LLM no fluxo Rivet

O workflow possui três pontos onde a LLM opera sobre dados extraídos dos documentos:

| Subgraph | Entrada principal | O que a LLM faz | Risco central |
|---|---|---|---|
| **3 — Risk & Fit Analyzer** | Portfólio + Perfil de risco | Identifica desalinhamentos e flags de drawdown | Ignorar dado crítico; misclassificar produto |
| **4 — Recommendation Engine** | Output do SG3 + Análise de mercado | Gera recomendações BUY/SELL/REDUCE com justificativa | Inventar números; violar suitability |
| **5 — Letter Generator** | Todos os outputs anteriores | Redige a carta em português | Citar número sem fonte; tom inadequado |

Os Subgraphs 1 e 2 (Data Loader e Profitability Engine) são **determinísticos** (código JavaScript no Rivet) — não passam por LLM e não precisam de guardrails de modelo.

---

## 2. Tipologia dos documentos de entrada

### 2.1 Portfólio

**Formato atual:** `.txt` (extrato XP)

**Campos críticos para extração:**

```
total_investido        → número monetário (R$)
saldo_disponivel       → número monetário (R$)
posicoes[]
  └── ativo            → ticker ou nome do fundo
  └── valor_posicao    → R$
  └── peso_alocacao    → % do portfólio
  └── rentabilidade    → % acumulada desde entrada
  └── data_investimento → data
  └── quantidade        → número inteiro (apenas ações)
  └── preco_medio       → R$ (apenas ações)
codigo_assessor        → string alfanumérica
```

**Riscos específicos de extração:**
- Confundir rentabilidade acumulada com rentabilidade mensal
- Somar incorretamente os pesos (devem totalizar ~100%)
- Tratar o saldo disponível como posição investida

### 2.2 Perfil de Risco

**Formato atual:** `.txt` (documento narrativo)

**Campos críticos para extração:**

```
classificacao_perfil   → enum: conservador | moderado | arrojado | agressivo
produtos_permitidos[]  → lista derivada do perfil (não inventar — usar tabela regulatória)
horizonte              → curto | medio | longo
tolerancia_perda       → descrição qualitativa
```

**Riscos específicos de extração:**
- LLM inferir produtos permitidos além do que a regulação (ICVM 539) autoriza
- Subir o perfil de risco (ex: tratar moderado como arrojado) para permitir mais recomendações

### 2.3 Análise de Mercado

**Formato atual:** `.txt` (relatório XP Research)

**Campos críticos para extração:**

```
data_referencia        → mês/ano do relatório
selic_atual            → % ao ano
selic_projetada        → % ao ano + horizonte
ipca_projetado         → % (ano corrente)
cambio_projetado       → R$/USD
pib_projetado          → % (ano corrente)
cenario_geral          → bullish | neutral | bearish (inferido)
fonte                  → "XP Research" + data
```

**Riscos específicos de extração:**
- Confundir projeção com valor realizado (Selic "está em" vs "deverá chegar em")
- Usar dados de relatório desatualizado sem sinalizar

---

## 3. Guardrails por camada

### Camada 1 — Input Guard (antes de chamar a LLM)

Implementado como **Code node JavaScript** no início de cada subgraph que usa LLM.

#### 1A — Validação do portfólio

```javascript
function validatePortfolio(portfolio) {
  const errors = []

  // Pesos devem somar 100% (tolerância ±1%)
  const totalWeight = portfolio.posicoes.reduce((sum, p) => sum + p.peso_alocacao, 0)
  if (Math.abs(totalWeight - 100) > 1) {
    errors.push(`PESO_INVALIDO: soma = ${totalWeight.toFixed(2)}% (esperado: ~100%)`)
  }

  // Nenhuma posição com peso ou valor negativo
  portfolio.posicoes.forEach(p => {
    if (p.peso_alocacao < 0) errors.push(`PESO_NEGATIVO: ${p.ativo}`)
    if (p.valor_posicao < 0) errors.push(`VALOR_NEGATIVO: ${p.ativo}`)
  })

  // total_investido deve ser coerente com soma das posições (±5%)
  const somaPositions = portfolio.posicoes.reduce((sum, p) => sum + p.valor_posicao, 0)
  const diff = Math.abs(somaPositions - portfolio.total_investido) / portfolio.total_investido
  if (diff > 0.05) {
    errors.push(`TOTAL_INCOERENTE: soma posições R$${somaPositions.toFixed(2)} ≠ total R$${portfolio.total_investido.toFixed(2)}`)
  }

  return { valid: errors.length === 0, errors }
}
```

#### 1B — Validação do perfil de risco

```javascript
const PERFIS_VALIDOS = ["conservador", "moderado", "arrojado", "agressivo"]

function validateRiskProfile(profile) {
  if (!PERFIS_VALIDOS.includes(profile.classificacao_perfil.toLowerCase())) {
    return { valid: false, errors: [`PERFIL_INVALIDO: "${profile.classificacao_perfil}"`] }
  }
  return { valid: true, errors: [] }
}
```

#### 1C — Validação da análise de mercado

```javascript
function validateMacro(macro) {
  const errors = []
  const now = new Date()
  const reportDate = new Date(macro.data_referencia)
  const monthsDiff = (now - reportDate) / (1000 * 60 * 60 * 24 * 30)

  // Relatório com mais de 45 dias: avisar (não bloquear)
  if (monthsDiff > 1.5) {
    errors.push(`MACRO_DESATUALIZADO: relatório de ${macro.data_referencia} (${monthsDiff.toFixed(0)} meses atrás)`)
  }

  // Selic deve estar em intervalo plausível para o Brasil
  if (macro.selic_atual < 2 || macro.selic_atual > 30) {
    errors.push(`SELIC_IMPROVAVEL: ${macro.selic_atual}% (intervalo esperado: 2–30%)`)
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings: errors.filter(e => e.startsWith("MACRO_DESATUALIZADO"))
  }
}
```

---

### Camada 2 — Prompt Guard (estrutura do prompt que entra na LLM)

#### Princípio: Chain-of-Custody de dados

Todo número que aparece no prompt deve ter uma **tag de origem** explícita. A LLM é instruída a nunca usar números sem esta tag.

**Estrutura de prompt para o Subgraph 4 (Recommendation Engine):**

```
SYSTEM:
You are a financial advisor at XP Investimentos. Your role is to generate
buy/sell recommendations strictly based on the data provided below.

RULES:
1. Only use numbers that appear in the tagged data sections below.
   If a number you need is not present, write DATA_UNAVAILABLE — never estimate.
2. Never recommend a product outside the client's allowed_products list.
   This rule is non-negotiable (ICVM 539/2013 compliance).
3. Every recommendation must cite the specific data point that justifies it.

PORTFOLIO DATA [source: XP extrato, {portfolio.data_extracao}]:
{portfolio_json}

RISK PROFILE DATA [source: XP perfil, {perfil.data_classificacao}]:
{perfil_json}

MACRO DATA [source: {macro.fonte}, {macro.data_referencia}]:
{macro_json}

RISK DIAGNOSTICS [source: Subgraph 3 output, calculated]:
{risk_diagnostics_json}

OUTPUT FORMAT:
Return a JSON array. Each item:
{
  "ativo": string,
  "acao": "BUY" | "SELL" | "REDUCE" | "MAINTAIN",
  "justificativa": string (max 2 sentences, must reference tagged data),
  "urgencia": "HIGH" | "MEDIUM" | "LOW",
  "dado_base": string (which specific data point triggered this recommendation)
}
```

---

### Camada 3 — Output Guard (validação do que a LLM retornou)

#### 3A — Suitability Check (HARD BLOCK — não negociável)

Regra derivada da ICVM 539/2013. Se a LLM recomendar produto fora do perfil, o output é **bloqueado** e nunca chega ao cliente.

```javascript
const PRODUTOS_PERMITIDOS = {
  conservador: ["rf_grau_investimento", "fundo_di", "tesouro_direto", "cdb"],
  moderado:    ["rf_grau_investimento", "fundo_di", "tesouro_direto", "cdb",
                "acoes_dividendos", "fundo_multimercado_moderado", "debentures_bb_plus"],
  arrojado:    ["rf_grau_investimento", "fundo_di", "tesouro_direto", "cdb",
                "acoes_dividendos", "fundo_multimercado_moderado", "debentures_bb_plus",
                "fundo_acoes", "fii", "bdr", "derivativo_hedge"],
  agressivo:   ["*arrojado", "derivativo_especulativo", "fundo_alavancado", "alternativo"]
}

function checkSuitability(recommendations, perfil) {
  const permitidos = PRODUTOS_PERMITIDOS[perfil]
  // SELL e MAINTAIN nunca são bloqueados — cliente pode sair de qualquer posição
  const bloqueadas = recommendations.filter(rec => {
    if (rec.acao === "SELL" || rec.acao === "MAINTAIN") return false
    return !isAllowed(rec.ativo, permitidos)
  })
  return { passed: bloqueadas.length === 0, blocked: bloqueadas }
}
```

#### 3B — Schema Validation

```javascript
const ACOES_VALIDAS    = ["BUY", "SELL", "REDUCE", "MAINTAIN"]
const URGENCIAS_VALIDAS = ["HIGH", "MEDIUM", "LOW"]

function validateRecommendations(recs) {
  const errors = []
  if (!Array.isArray(recs)) return { valid: false, errors: ["OUTPUT_NAO_ARRAY"] }

  recs.forEach((rec, i) => {
    if (!rec.ativo)                                errors.push(`[${i}] ativo ausente`)
    if (!ACOES_VALIDAS.includes(rec.acao))         errors.push(`[${i}] acao inválida: "${rec.acao}"`)
    if (!URGENCIAS_VALIDAS.includes(rec.urgencia)) errors.push(`[${i}] urgencia inválida: "${rec.urgencia}"`)
    if (!rec.justificativa || rec.justificativa.length < 10)
                                                   errors.push(`[${i}] justificativa ausente`)
    if (!rec.dado_base)    errors.push(`[${i}] dado_base ausente — rastreabilidade quebrada`)
  })

  return { valid: errors.length === 0, errors }
}
```

#### 3C — Hallucination Check (números na carta)

Aplicado no **Subgraph 5 (Letter Generator)**: após a carta ser gerada, um segundo prompt verifica se os números na carta existem nos dados de entrada.

```
SYSTEM: You are a fact-checker. Given a financial letter and the original data,
identify any number in the letter that cannot be traced back to the data.

LETTER:
{carta_gerada}

SOURCE DATA:
{todos_os_dados_de_entrada}

OUTPUT (JSON):
{
  "all_facts_verified": boolean,
  "unverified_claims": [{ "claim": string, "reason": string }]
}
```

Se `all_facts_verified == false` → carta entra em fila de revisão humana, não é liberada.

---

### Camada 4 — Retry & Escalation

```
FALHA DE VALIDAÇÃO
       │
  É HARD BLOCK? (suitability ou input inválido)
  ├── SIM → BLOQUEAR + LOG + alertar assessor → parar
  └── NÃO
       │
  É erro de schema ou hallucination?
  ├── SIM → RETRY (max 2x com prompt corrigido)
  │         Ainda falhou? → status: needs_review → fila humana
  └── NÃO (apenas warning de dado desatualizado)
       └── Prosseguir + inserir disclaimer automático na carta
```

**Disclaimer automático para macro desatualizado** (inserido pelo Letter Generator):

> *"Esta análise é baseada no relatório XP Research de [data]. Recomendamos consultar o material mais recente antes de tomar decisões."*

---

## 4. Implementação no Rivet

### Onde cada guardrail vive no grafo

```
[Subgraph 1: Data Loader]
    └── Code node: validatePortfolio() + validateRiskProfile() + validateMacro()
        → Se HARD error: Output node "ERROR" com mensagem estruturada → para o fluxo
        → Se WARNING: Output node "WARNING" → fluxo continua com flag

[Subgraph 3: Risk & Fit Analyzer]
    ├── Code node: calcula flags determinísticos (drawdown, peso, suitability)
    ├── Text node: monta prompt com chain-of-custody + flags pré-calculados
    ├── LLM node (OpenAI): executa análise de risco contextual
    └── Code node: checkSuitability() no output — bloqueia se necessário

[Subgraph 4: Recommendation Engine]
    ├── Text node: monta prompt com allowed_products injetados explicitamente
    ├── LLM node (OpenAI): gera recomendações JSON
    ├── Code node: validateRecommendations() + checkSuitability()
    └── If node: retry se inválido (contador ≤ 2) → needs_review se esgotado

[Subgraph 5: Letter Generator]
    ├── LLM node (OpenAI): gera carta narrativa em português
    ├── LLM node (OpenAI gpt-4o-mini): hallucination check
    └── If node: liberar (VALID) ou → needs_review
```

### Configuração OpenAI recomendada por subgraph

| Subgraph | Model | Temperature | Response format |
|---|---|---|---|
| Risk & Fit Analyzer | gpt-4o | 0.2 | `json_object` |
| Recommendation Engine | gpt-4o | 0.1 | `json_object` |
| Letter Generator (carta) | gpt-4o | 0.6 | text |
| Letter Generator (fact-check) | gpt-4o-mini | 0.0 | `json_object` |

- Temperature baixa nos subgraphs analíticos: reduz criatividade indesejada nos números
- `response_format: { type: "json_object" }` nos subgraphs 3 e 4: elimina markdown wrapping no JSON
- Fact-check com `gpt-4o-mini`: operação simples de verificação — reduz custo

---

## 5. Regras determinísticas do Subgraph 3 (não delegadas à LLM)

Estas regras são calculadas em **Code node antes** da chamada LLM. A LLM recebe apenas os flags já resolvidos.

| Regra | Condição | Flag gerado |
|---|---|---|
| 2.1 Drawdown profundo | drawdown < -30% E peso > 1.5% | `REDUZIR_OU_VENDER` |
| 2.2 Concentração excessiva | peso_ativo > 25% | `REDUZIR_CONCENTRACAO` |
| 2.3 Fora do perfil | produto NOT IN permitidos | `VENDER_SUITABILITY` (hard) |
| 2.4 Fundo abaixo benchmark | retorno < benchmark × 0.80 E período ≥ 12m | `AVALIAR_SAIDA` |
| 2.5 Posição residual | peso < 0.5% | `CONSOLIDAR` |

**Exemplo com Albert (portfólio real):**
- HAPV3: drawdown -74.58%, peso 1.97% → Regra 2.1 dispara → `REDUZIR_OU_VENDER`
- Trend Investback: peso 0.10% → Regra 2.5 dispara → `CONSOLIDAR`
- Nenhum ativo excede 25% → Regra 2.2 não dispara
- Todos os ativos são compatíveis com perfil Moderado → Regra 2.3 não dispara

---

## 6. O que NÃO delegar à LLM

| Decisão | Por quê não LLM | Onde fica |
|---|---|---|
| Cálculo de rentabilidade ponderada | Exige precisão aritmética | Subgraph 2, Code node JS |
| Verificação de suitability (ICVM 539) | Risco regulatório — resultado binário | Code node, pré e pós LLM |
| Comparação com benchmarks (CDI, IBOV) | Requer dados de API, não julgamento | Subgraph 2, Code node JS |
| Cálculo de drawdown por posição | Aritmético | Code node no SG3, antes da LLM |
| Aplicação de flags das Regras 2.1–2.5 | Lógica determinística com threshold | Code node no SG3, antes da LLM |

A LLM recebe os **resultados** desses cálculos como input estruturado. Sua função é transformar dados calculados em linguagem natural e julgamento contextual — não fazer a matemática.

---

## 7. Glossário de status de output

| Status | Significado | Ação no Rivet |
|---|---|---|
| `VALID` | Passou todos os guardrails | Carta liberada para revisão do assessor |
| `WARNING` | Dado desatualizado ou posição borderline | Carta gerada com disclaimer automático |
| `NEEDS_REVIEW` | Hallucination detectada ou retry esgotado | Fila humana — não enviada |
| `BLOCKED_SUITABILITY` | Produto fora do perfil recomendado | Fluxo interrompido — assessor alertado |
| `BLOCKED_INPUT` | Portfólio ou perfil inválido na entrada | Fluxo não inicia — dados precisam de correção |
