# Ordenação de Classes — Lógica e Prompts

## Objetivo

Produzir um ranking de classes de ativos ordenado do mais favorecido ao menos favorecido pelo cenário macroeconômico atual.

A ordenação é híbrida: a IA lê os parágrafos macro e atribui pontuações numéricas por indicador; um algoritmo determinístico aplica uma matriz de pesos e calcula o score final de cada classe.

---

## Arquitetura

```
7 parágrafos macro (um por indicador)
        ↓ em paralelo
7 scoring prompts → 7 scores numéricos (-2 a +2)
        ↓
código: score_classe = Σ (indicator_score × weight)
        ↓
ranking de classes ordenado por score_classe
```

---

## Escala de pontuação

Cada indicador é pontuado de -2 a +2. O sinal é definido pela direção do indicador em si — não pelo impacto em uma classe específica. O impacto direcional por classe é tratado pelos pesos na matriz.

| Score | Significado geral |
|-------|-------------------|
| +2 | Cenário muito favorável para o indicador (ex: Selic caindo agressivamente) |
| +1 | Cenário moderadamente favorável |
|  0 | Neutro ou inconclusivo |
| -1 | Cenário moderadamente desfavorável |
| -2 | Cenário muito desfavorável (ex: Selic subindo agressivamente) |

---

## Matriz de pesos

Cada célula representa o peso do indicador para aquela classe.

**Positivo** = o indicador subindo (score positivo) beneficia a classe.
**Negativo** = o indicador subindo (score positivo) prejudica a classe.

| Classe | Selic | IPCA | Câmbio | PIB | Crédito | Fiscal | Externo |
|--------|:-----:|:----:|:------:|:---:|:-------:|:------:|:-------:|
| RF Pós-fixada | +2 | 0 | 0 | 0 | 0 | -1 | 0 |
| RF IPCA+ | +1 | +2 | 0 | 0 | 0 | -2 | 0 |
| Multimercado Macro | 0 | 0 | +1 | 0 | 0 | -1 | +1 |
| Multimercado Crédito | -1 | 0 | 0 | -1 | -2 | -1 | 0 |
| Long Biased | -2 | 0 | 0 | -1 | 0 | 0 | -1 |
| FIA Ações | -2 | 0 | 0 | -2 | 0 | -1 | -2 |
| Ações Varejo | -2 | -2 | -1 | -2 | 0 | 0 | 0 |
| Ações Saúde | -1 | -2 | 0 | -1 | 0 | 0 | 0 |
| Ações Exportador | 0 | 0 | +2 | 0 | 0 | 0 | -1 |

### Leitura da matriz

- **RF Pós-fixada × Selic = +2**: quando a Selic está em ciclo de alta (score negativo para o indicador), o produto é negativo... mas RF Pós-fixada se beneficia. Isso parece contradição?

  Não — a escala do indicador Selic é definida como: **+2 = Selic caindo (afrouxamento), -2 = Selic subindo (aperto)**. Portanto:
  - Selic subindo = score Selic = -2
  - Peso RF Pós-fixada × Selic = +2
  - Produto = -2 × +2 = **-4** ← isso está errado

  **Correção:** a escala do indicador Selic precisa ser definida como **positiva = aperto** para que os pesos façam sentido intuitivo:
  - **+2 = Selic subindo agressivamente (aperto forte)**
  - **-2 = Selic caindo agressivamente (afrouxamento)**

  Com essa convenção:
  - Selic subindo = score = +2
  - Peso RF Pós-fixada = +2 → produto = **+4** ✓ (RF se beneficia)
  - Peso FIA Ações = -2 → produto = **-4** ✓ (ações sofrem)

  Cada indicador tem sua própria convenção de direção. Ver seção de prompts abaixo.

---

## Convenções de direção por indicador

| Indicador | Score +2 significa | Score -2 significa |
|-----------|-------------------|-------------------|
| Selic | Aperto forte — Selic subindo agressivamente | Afrouxamento forte — Selic caindo |
| IPCA | Inflação muito alta, acelerando | Inflação controlada, desacelerando |
| Câmbio | BRL muito depreciado (USD/BRL alto) | BRL muito apreciado (USD/BRL baixo) |
| PIB | Crescimento forte, economia aquecida | Recessão ou desaceleração severa |
| Crédito Privado | Spreads muito altos, risco de default elevado | Spreads comprimidos, crédito farto |
| Fiscal | Risco fiscal muito elevado, dívida descontrolada | Fiscal equilibrado, dívida sustentável |
| Externo | Cenário externo adverso — Fed hawkish, risk-off | Cenário externo favorável — Fed dovish, risk-on |

---

## Fórmula de scoring

```javascript
const weights = {
  "RF Pós-fixada":        { selic: +2, ipca:  0, cambio:  0, pib:  0, credito:  0, fiscal: -1, externo:  0 },
  "RF IPCA+":             { selic: +1, ipca: +2, cambio:  0, pib:  0, credito:  0, fiscal: -2, externo:  0 },
  "Multimercado Macro":   { selic:  0, ipca:  0, cambio: +1, pib:  0, credito:  0, fiscal: -1, externo: +1 },
  "Multimercado Crédito": { selic: -1, ipca:  0, cambio:  0, pib: -1, credito: -2, fiscal: -1, externo:  0 },
  "Long Biased":          { selic: -2, ipca:  0, cambio:  0, pib: -1, credito:  0, fiscal:  0, externo: -1 },
  "FIA Ações":            { selic: -2, ipca:  0, cambio:  0, pib: -2, credito:  0, fiscal: -1, externo: -2 },
  "Ações Varejo":         { selic: -2, ipca: -2, cambio: -1, pib: -2, credito:  0, fiscal:  0, externo:  0 },
  "Ações Saúde":          { selic: -1, ipca: -2, cambio:  0, pib: -1, credito:  0, fiscal:  0, externo:  0 },
  "Ações Exportador":     { selic:  0, ipca:  0, cambio: +2, pib:  0, credito:  0, fiscal:  0, externo: -1 },
};

function rankClasses(scores) {
  // scores = { selic, ipca, cambio, pib, credito, fiscal, externo }
  const results = Object.entries(weights).map(([classe, w]) => {
    const score =
      scores.selic   * w.selic   +
      scores.ipca    * w.ipca    +
      scores.cambio  * w.cambio  +
      scores.pib     * w.pib     +
      scores.credito * w.credito +
      scores.fiscal  * w.fiscal  +
      scores.externo * w.externo;
    return { classe, score };
  });

  return results.sort((a, b) => b.score - a.score);
}
```

---

## Scoring Prompts (×7)

### Prompt 1 — Selic

**Convenção:** +2 = aperto monetário forte / -2 = afrouxamento forte

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Read the macro paragraph below and assign a score from -2 to +2 representing the current state of the Selic rate and monetary policy.

SCORING SCALE:
+2 = The Copom is in an aggressive tightening cycle. Selic rising sharply with no sign of pause.
+1 = Selic is rising at a moderate pace, or a pause is approaching but not yet signaled.
 0 = Selic is stable. Direction is unclear or mixed signals.
-1 = Selic is falling gradually, or a rate cut cycle is beginning.
-2 = The Copom is in an aggressive easing cycle. Selic falling sharply.

OUTPUT:
Return only a JSON object with a single field. No explanation.
{ "score": <integer from -2 to +2> }

ARGUMENT: {{argument}}
```

---

### Prompt 2 — IPCA

**Convenção:** +2 = inflação muito alta / -2 = inflação muito controlada

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Read the macro paragraph below and assign a score from -2 to +2 representing the current state of inflation in Brazil.

SCORING SCALE:
+2 = Inflation is very high, widespread, and accelerating. Well above target with no near-term relief.
+1 = Inflation is elevated and persistent, but showing early signs of stabilization.
 0 = Inflation is near target or direction is unclear.
-1 = Inflation is decelerating and moving toward target.
-2 = Inflation is well controlled, at or below target, and trending down.

OUTPUT:
Return only a JSON object with a single field. No explanation.
{ "score": <integer from -2 to +2> }

ARGUMENT: {{argument}}
```

---

### Prompt 3 — Câmbio

**Convenção:** +2 = BRL muito depreciado / -2 = BRL muito apreciado

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Read the macro paragraph below and assign a score from -2 to +2 representing the current state of the Brazilian exchange rate (USD/BRL).

SCORING SCALE:
+2 = BRL is severely depreciated. USD/BRL is very high and rising, with strong depreciation pressure.
+1 = BRL is moderately weak. USD/BRL elevated but relatively stable.
 0 = Exchange rate is near equilibrium or direction is unclear.
-1 = BRL is moderately appreciating. USD/BRL declining gradually.
-2 = BRL is strongly appreciated. USD/BRL falling sharply.

OUTPUT:
Return only a JSON object with a single field. No explanation.
{ "score": <integer from -2 to +2> }

ARGUMENT: {{argument}}
```

---

### Prompt 4 — PIB

**Convenção:** +2 = crescimento forte / -2 = recessão ou desaceleração severa

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Read the macro paragraph below and assign a score from -2 to +2 representing the current state of Brazilian economic growth.

SCORING SCALE:
+2 = Economy is growing strongly. GDP well above potential, demand robust.
+1 = Economy growing at a moderate pace, above trend.
 0 = Growth near potential or mixed signals.
-1 = Economy decelerating. Growth below trend, consumption softening.
-2 = Economy in recession or severe contraction. Demand collapsing.

OUTPUT:
Return only a JSON object with a single field. No explanation.
{ "score": <integer from -2 to +2> }

ARGUMENT: {{argument}}
```

---

### Prompt 5 — Crédito Privado

**Convenção:** +2 = spreads muito altos, risco elevado / -2 = spreads comprimidos, crédito farto

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Read the macro paragraph below and assign a score from -2 to +2 representing the current state of the Brazilian private credit market.

SCORING SCALE:
+2 = Credit spreads are very wide. Corporate default risk is high. Private credit funds under significant stress.
+1 = Spreads elevated and widening. Early signs of credit stress in the corporate sector.
 0 = Credit conditions are neutral. Spreads near historical averages.
-1 = Spreads tightening. Credit conditions improving for corporate borrowers.
-2 = Spreads very compressed. Credit is abundant and cheap for corporations.

OUTPUT:
Return only a JSON object with a single field. No explanation.
{ "score": <integer from -2 to +2> }

ARGUMENT: {{argument}}
```

---

### Prompt 6 — Risco Fiscal

**Convenção:** +2 = risco fiscal muito alto / -2 = fiscal equilibrado

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Read the macro paragraph below and assign a score from -2 to +2 representing the current state of Brazil's fiscal risk.

SCORING SCALE:
+2 = Fiscal risk is very high. Public debt on an unsustainable trajectory. Markets pricing significant sovereign risk premium.
+1 = Fiscal risk elevated. Budget pressures persist, debt growing above GDP.
 0 = Fiscal situation neutral or mixed. Debt stable relative to GDP.
-1 = Fiscal conditions improving. Primary surplus on track, debt trajectory stabilizing.
-2 = Fiscal risk very low. Budget balanced, debt clearly sustainable.

OUTPUT:
Return only a JSON object with a single field. No explanation.
{ "score": <integer from -2 to +2> }

ARGUMENT: {{argument}}
```

---

### Prompt 7 — Cenário Externo

**Convenção:** +2 = cenário externo adverso para emergentes / -2 = cenário externo favorável

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Read the macro paragraph below and assign a score from -2 to +2 representing the current state of the global economic environment and its impact on Brazil.

SCORING SCALE:
+2 = External scenario very adverse. Fed aggressively hawkish, strong risk-off, capital fleeing emerging markets.
+1 = External scenario moderately adverse. Fed on hold at high rates, global uncertainty elevated.
 0 = External scenario neutral. Mixed signals, no clear directional pressure on Brazil.
-1 = External scenario moderately favorable. Fed signaling cuts, risk appetite improving.
-2 = External scenario very favorable. Fed in easing cycle, strong risk-on, capital flowing to emerging markets.

OUTPUT:
Return only a JSON object with a single field. No explanation.
{ "score": <integer from -2 to +2> }

ARGUMENT: {{argument}}
```
