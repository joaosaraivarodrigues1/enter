# Prompts de Extração Macro — Pipeline Rivet

## Contexto

O objetivo deste pipeline é extrair, a partir de um relatório macro (XP Research, fev/2025), os argumentos econômicos relevantes para avaliar cada ativo do portfólio de Albert da Silva (perfil moderado, R$386.858).

O texto do relatório é particionado em parágrafos. Cada parágrafo passa por 7 prompts em paralelo — um por indicador econômico. Cada prompt retorna uma síntese de uma ou duas linhas se o parágrafo for relevante para aquele indicador, ou vazio se não for. Os resumos não-vazios coletados formam o conjunto de argumentos que alimenta o scoring engine de buy/sell.

---

## Indicadores monitorados

| # | Indicador | Por que monitorar | Ativos diretamente impactados |
|---|-----------|-------------------|-------------------------------|
| 1 | **Selic** | Driver principal de toda a carteira: define atratividade relativa entre RF e renda variável, custo de capital das empresas e apetite por risco | LREN3, ARZZ3, HAPV3, Truxt, STK, Constellation, Riza Lotus |
| 2 | **IPCA** | Indexa o CDB (principal ativo de RF) e é o driver de custos do setor de saúde privada (ANS limita repasse) | HAPV3, CDB IPCA+, LREN3, ARZZ3 |
| 3 | **Câmbio (USD/BRL)** | MRFG3 é exportadora — BRL fraco aumenta sua margem em reais. LREN3 e ARZZ3 importam insumos — BRL fraco comprime margens | MRFG3, LREN3, ARZZ3 |
| 4 | **PIB** | Desaceleração reduz consumo das famílias, comprimindo faturamento do varejo e resultado dos fundos de ações | LREN3, ARZZ3, Truxt, STK, Constellation |
| 5 | **Crédito Privado** | Brave I FIM CP (23% do portfólio) investe em títulos de crédito privado — spread alto sinaliza risco de inadimplência corporativa e piora do fundo | Brave I FIM CP |
| 6 | **Risco Fiscal** | Dívida pública crescendo deteriora o prêmio de risco soberano, pressionando a curva longa de juros — afeta a atratividade de títulos IPCA+ como substitutos | CDB IPCA+, Brave I, Constellation |
| 7 | **Cenário Externo** | Fed hawkish reduz fluxo de capital para emergentes, pressiona câmbio e apetite por risco global — amplifica os efeitos dos outros indicadores | Constellation, Truxt, STK, Ibiuna |

---

## Dependências dos indicadores

| Indicador | Depende de |
|-----------|------------|
| **Selic** | Expectativas de inflação (Focus) · IPCA acima da meta · Câmbio depreciado (pass-through) · Hiato do produto positivo · Risco fiscal (dificulta cortes) · Fed hawkish (via BRL → inflação importada) |
| **IPCA** | Câmbio depreciado (alimentos e bens industriais) · Demanda doméstica aquecida (inflação de serviços) · Preços administrados (energia, transporte, combustível) · Inércia e expectativas desancoradas · Mercado de trabalho apertado (salários) · Fiscal expansionário (transferências, salário mínimo) · Choques agrícolas (clima, seca) |
| **Câmbio** | Risco fiscal (driver dominante) · Fed hawkish (carry trade, fluxo de capital) · Aversão a risco global · Preços de commodities (suporte estrutural) · Selic alta (carry trade — efeito condicionado à credibilidade fiscal) · Incerteza política doméstica |
| **PIB** | Selic alta (crédito caro) · Inflação (poder de compra) · Fiscal (transferências, salário mínimo) · Mercado de trabalho · Setor agrícola (safra) · Demanda chinesa por commodities · Investimento público (PAC) |
| **Crédito Privado** | Selic alta (custo de rolagem) · Desaceleração do PIB (receitas corporativas) · BRL depreciado (passivos em USD sem hedge) · Risco fiscal (alarga spreads) · Mercado de trabalho (inadimplência de famílias) |
| **Risco Fiscal** | Juros nominais altos (bola de neve da dívida) · Despesas obrigatórias crescentes (>93% do gasto federal) · PIB fraco (receita tributária menor) · Ano eleitoral (pressão por gastos) · Passivos de estatais e governos subnacionais |
| **Cenário Externo** | Decisões do Fed · Política comercial dos EUA (tarifas) · Atividade da China (demanda por commodities) · Aversão a risco global (VIX) · Preço do petróleo (efeito duplo: exportação vs. inflação doméstica) |

### Indicador excluído após revisão

**Commodities** foi considerado e descartado. Seu impacto direto se limitaria a MRFG3 (4.94% do portfólio), e o essencial desse efeito já é capturado pelo prompt de Câmbio (exportadores se beneficiam do BRL fraco) e pelo de Cenário Externo (demanda global). Manter um prompt com alcance tão estreito aumentaria o ruído sem ganho proporcional.

---

## Mapa ativo × indicador

| Ativo | Peso | Selic | IPCA | Câmbio | PIB | Crédito Privado | Fiscal | Externo |
|-------|------|:-----:|:----:|:------:|:---:|:---------------:|:------:|:-------:|
| LREN3 | 8.91% | ●● | ●● | ● | ●● | — | — | — |
| ARZZ3 | 3.50% | ●● | ● | ● | ●● | — | — | — |
| HAPV3 | 1.97% | ● | ●● | — | ● | — | — | — |
| MRFG3 | 4.94% | — | — | ●● | — | — | — | ● |
| Riza Lotus DI | 30.81% | ●● | — | — | — | — | — | — |
| Brave I CP | 23.24% | ● | ● | — | ● | ●● | ● | — |
| CDB IPCA+ | 12.97% | — | ●● | — | — | — | ●● | — |
| Truxt Long Bias | 4.01% | ●● | — | — | ● | — | — | ● |
| STK Long Biased | 3.12% | ●● | — | — | ● | — | — | ● |
| Constellation FIA | 2.71% | ●● | — | — | ●● | — | ● | ●● |
| Ibiuna Hedge ST | 3.72% | ● | — | ● | — | — | — | ● |
| Trend (residual) | 0.10% | — | — | — | — | — | — | — |

*●● impacto direto e significativo · ● impacto indireto ou moderado · — sem correlação relevante*

---

## Arquitetura

```
[texto XP particionado em array de parágrafos]
        │
        ▼ Split
[parágrafo 1] → [Prompt Selic]     → resumo ou vazio
[parágrafo 1] → [Prompt IPCA]      → resumo ou vazio
[parágrafo 1] → [Prompt Câmbio]    → resumo ou vazio
...
[parágrafo N] → [Prompt Externo]   → resumo ou vazio
        │
        ▼ Collect (filtrar vazios)
[array de resumos preenchidos → argumentos do scoring]
```

Cada prompt recebe um argumento (parágrafo) e retorna:
- **Vazio** se o argumento não tem correlação com o indicador do prompt
- **Até duas frases** resumindo o que o argumento diz sobre aquele indicador

---

## Prompt 1 — Selic

```
You are analyzing a financial paragraph.

GOAL:
Identify whether the paragraph contains information relevant to the Selic rate, either directly or indirectly.

RELEVANT INFORMATION includes:

(A) Direct references:
- Current Selic rate
- Expected direction of Selic
- Copom decisions or expectations

(B) Indirect signals (only if clearly connected to monetary policy):
- Inflation expectations or IPCA above target
- Exchange rate depreciation (pass-through to inflation)
- Positive output gap (overheated economy)
- Fiscal risk (constrains rate cuts)
- Fed hawkish stance (via BRL depreciation → imported inflation)

INTERPRETATION RULES:
- Only consider indirect signals if they clearly imply pressure on monetary policy.
- Do NOT treat generic economic commentary as relevant.
- Do NOT speculate beyond the text.

OUTPUT RULES:
- If no relevant information: return exactly empty text.
- If relevant: return up to 2 concise sentences summarizing ONLY the Selic-related implications.
- Focus on direction, drivers, and policy expectations.

ARGUMENT: {{argument}}
```

---

## Prompt 2 — IPCA

```
You are analyzing a financial paragraph.

GOAL:
Identify whether the paragraph contains information relevant to inflation in Brazil, either directly or indirectly.

RELEVANT INFORMATION includes:

(A) Direct references:
- Current or projected IPCA
- Inflation trend (accelerating, decelerating, persistent)
- Inflation target compliance or deviation

(B) Indirect signals (only if clearly connected to inflation dynamics):
- Exchange rate depreciation (food and industrial goods)
- Strong domestic demand (services inflation)
- Administered prices (energy, transport, fuel)
- Anchoring of inflation expectations
- Tight labor market (wage pressure)
- Expansionary fiscal policy (transfers, minimum wage)
- Agricultural shocks (weather, drought)

INTERPRETATION RULES:
- Only consider indirect signals if they clearly imply inflationary or disinflationary pressure.
- Do NOT treat generic economic commentary as relevant.
- Do NOT speculate beyond the text.

OUTPUT RULES:
- If no relevant information: return exactly empty text.
- If relevant: return up to 2 concise sentences summarizing ONLY the inflation-related implications.
- Focus on direction, drivers, and deviation from target.

ARGUMENT: {{argument}}
```

---

## Prompt 3 — Câmbio

```
You are analyzing a financial paragraph.

GOAL:
Identify whether the paragraph contains information relevant to the Brazilian exchange rate (USD/BRL), either directly or indirectly.

RELEVANT INFORMATION includes:

(A) Direct references:
- Current or projected USD/BRL rate
- BRL appreciation or depreciation trend
- Central bank intervention in FX markets

(B) Indirect signals (only if clearly connected to exchange rate dynamics):
- Fiscal risk (dominant driver of BRL weakness)
- Fed hawkish stance (carry trade, capital flows out of Brazil)
- Global risk aversion (flight to safety)
- Commodity prices (structural support for BRL)
- Selic rate (carry trade — conditional on fiscal credibility)
- Domestic political uncertainty

INTERPRETATION RULES:
- Only consider indirect signals if they clearly imply appreciation or depreciation pressure on BRL.
- Do NOT treat generic economic commentary as relevant.
- Do NOT speculate beyond the text.

OUTPUT RULES:
- If no relevant information: return exactly empty text.
- If relevant: return up to 2 concise sentences summarizing ONLY the exchange rate implications.
- Focus on direction, drivers, and BRL outlook.

ARGUMENT: {{argument}}
```

---

## Prompt 4 — PIB

```
You are analyzing a financial paragraph.

GOAL:
Identify whether the paragraph contains information relevant to Brazilian economic growth (GDP), either directly or indirectly.

RELEVANT INFORMATION includes:

(A) Direct references:
- Current or projected GDP growth
- Economic activity indicators (industrial output, retail sales, services)
- Recession or expansion signals

(B) Indirect signals (only if clearly connected to economic activity):
- High Selic rate (expensive credit, investment slowdown)
- Inflation eroding purchasing power
- Fiscal policy (transfers, minimum wage increases)
- Labor market conditions (employment, wages)
- Agricultural sector performance (harvest)
- Chinese demand for Brazilian commodities
- Public investment programs (PAC)

INTERPRETATION RULES:
- Only consider indirect signals if they clearly imply acceleration or deceleration of economic activity.
- Do NOT treat generic economic commentary as relevant.
- Do NOT speculate beyond the text.

OUTPUT RULES:
- If no relevant information: return exactly empty text.
- If relevant: return up to 2 concise sentences summarizing ONLY the GDP-related implications.
- Focus on growth direction, drivers, and sector-level effects.

ARGUMENT: {{argument}}
```

---

## Prompt 5 — Crédito Privado

```
You are analyzing a financial paragraph.

GOAL:
Identify whether the paragraph contains information relevant to the Brazilian private credit market, either directly or indirectly.

RELEVANT INFORMATION includes:

(A) Direct references:
- Corporate credit spreads
- Debenture, CRI, or CRA market conditions
- Corporate default events or credit risk signals

(B) Indirect signals (only if clearly connected to private credit conditions):
- High Selic rate (increases rollover cost for corporate debt)
- GDP slowdown (compresses corporate revenues)
- BRL depreciation (pressures companies with USD liabilities and no hedge)
- Fiscal risk (widens sovereign spreads, pulling corporate spreads up)
- Labor market deterioration (household default, reduced consumption)

INTERPRETATION RULES:
- Only consider indirect signals if they clearly imply tightening or easing of corporate credit conditions.
- Do NOT treat generic economic commentary as relevant.
- Do NOT speculate beyond the text.

OUTPUT RULES:
- If no relevant information: return exactly empty text.
- If relevant: return up to 2 concise sentences summarizing ONLY the private credit implications.
- Focus on spread direction, default risk, and fund exposure.

ARGUMENT: {{argument}}
```

---

## Prompt 6 — Risco Fiscal

```
You are analyzing a financial paragraph.

GOAL:
Identify whether the paragraph contains information relevant to Brazil's fiscal situation, either directly or indirectly.

RELEVANT INFORMATION includes:

(A) Direct references:
- Primary surplus or deficit
- Public debt trajectory
- Fiscal framework compliance (spending cap, fiscal anchor)

(B) Indirect signals (only if clearly connected to fiscal dynamics):
- High nominal interest rates (debt snowball effect)
- Growing mandatory expenditures (structural rigidity of the budget)
- Weak GDP growth (lower tax revenue)
- Electoral cycle (spending pressure)
- Liabilities from state-owned enterprises or subnational governments

INTERPRETATION RULES:
- Only consider indirect signals if they clearly imply deterioration or improvement of fiscal conditions.
- Do NOT treat generic economic commentary as relevant.
- Do NOT speculate beyond the text.

OUTPUT RULES:
- If no relevant information: return exactly empty text.
- If relevant: return up to 2 concise sentences summarizing ONLY the fiscal implications.
- Focus on debt trajectory, credibility, and risk premium.

ARGUMENT: {{argument}}
```

---

## Prompt 7 — Cenário Externo (Extraction)

```
You are analyzing a financial paragraph.

GOAL:
Identify whether the paragraph contains information relevant to the global economic environment and its impact on Brazil, either directly or indirectly.

RELEVANT INFORMATION includes:

(A) Direct references:
- Fed decisions or expectations
- Global risk appetite (risk-on / risk-off)
- Capital flows to emerging markets

(B) Indirect signals (only if clearly connected to the external scenario):
- US trade policy and tariffs (impact on Brazilian exports)
- China's economic activity (demand for Brazilian commodities)
- Global risk aversion indicators (VIX, credit spreads)
- Oil prices (dual effect: export revenue vs. domestic inflation)

INTERPRETATION RULES:
- Only consider indirect signals if they clearly imply changes in external conditions relevant to Brazil.
- Do NOT treat generic economic commentary as relevant.
- Do NOT speculate beyond the text.

OUTPUT RULES:
- If no relevant information: return exactly empty text.
- If relevant: return up to 2 concise sentences summarizing ONLY the external scenario implications.
- Focus on Fed direction, risk appetite, and impact on Brazilian assets and currency.

ARGUMENT: {{argument}}
```

---

## Summary Prompt 1 — Selic

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Synthesize the findings below into a single conclusive paragraph about the current state of the Selic rate.

CONTEXT — WHAT DRIVES THE SELIC:
The Selic is influenced by: inflation expectations and IPCA above target, exchange rate depreciation (pass-through to domestic prices), positive output gap, fiscal risk (constrains rate cuts), and Fed hawkish stance (via BRL depreciation leading to imported inflation).

OUTPUT RULES:
- Write exactly one paragraph.
- Be conclusive — state what the evidence suggests about the current direction and level of the Selic.
- Integrate the findings with the drivers listed above where clearly supported.
- Do not repeat individual findings verbatim — synthesize.
- Do not speculate beyond what the findings support.

FINDINGS:
{{findings}}
```

---

## Summary Prompt 2 — IPCA

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Synthesize the findings below into a single conclusive paragraph about the current state of inflation in Brazil.

CONTEXT — WHAT DRIVES THE IPCA:
Inflation in Brazil is influenced by: exchange rate depreciation (food and industrial goods), strong domestic demand (services inflation), administered prices (energy, transport, fuel), anchoring of inflation expectations, tight labor market (wage pressure), expansionary fiscal policy (transfers, minimum wage), and agricultural shocks (weather, drought).

OUTPUT RULES:
- Write exactly one paragraph.
- Be conclusive — state what the evidence suggests about the current level, trend, and persistence of inflation.
- Integrate the findings with the drivers listed above where clearly supported.
- Do not repeat individual findings verbatim — synthesize.
- Do not speculate beyond what the findings support.

FINDINGS:
{{findings}}
```

---

## Summary Prompt 3 — Câmbio

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Synthesize the findings below into a single conclusive paragraph about the current state of the Brazilian exchange rate (USD/BRL).

CONTEXT — WHAT DRIVES THE EXCHANGE RATE:
The BRL is influenced by: fiscal risk (dominant driver of depreciation), Fed hawkish stance (carry trade and capital flows out of Brazil), global risk aversion, commodity prices (structural support for BRL), Selic rate (carry trade — conditional on fiscal credibility), and domestic political uncertainty.

OUTPUT RULES:
- Write exactly one paragraph.
- Be conclusive — state what the evidence suggests about the current BRL trajectory and the dominant drivers.
- Integrate the findings with the drivers listed above where clearly supported.
- Do not repeat individual findings verbatim — synthesize.
- Do not speculate beyond what the findings support.

FINDINGS:
{{findings}}
```

---

## Summary Prompt 4 — PIB

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Synthesize the findings below into a single conclusive paragraph about the current state of Brazilian economic growth.

CONTEXT — WHAT DRIVES GDP:
Brazilian GDP is influenced by: high Selic rate (expensive credit, investment slowdown), inflation eroding purchasing power, fiscal policy (transfers, minimum wage), labor market conditions, agricultural sector performance (harvest), Chinese demand for Brazilian commodities, and public investment programs (PAC).

OUTPUT RULES:
- Write exactly one paragraph.
- Be conclusive — state what the evidence suggests about the current growth trajectory and the key drivers of acceleration or deceleration.
- Integrate the findings with the drivers listed above where clearly supported.
- Do not repeat individual findings verbatim — synthesize.
- Do not speculate beyond what the findings support.

FINDINGS:
{{findings}}
```

---

## Summary Prompt 5 — Crédito Privado

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Synthesize the findings below into a single conclusive paragraph about the current state of the Brazilian private credit market.

CONTEXT — WHAT DRIVES PRIVATE CREDIT CONDITIONS:
Private credit conditions are influenced by: high Selic rate (increases rollover cost for corporate debt), GDP slowdown (compresses corporate revenues), BRL depreciation (pressures companies with USD liabilities and no hedge), fiscal risk (widens sovereign spreads, pulling corporate spreads up), and labor market deterioration (household default, reduced consumption).

OUTPUT RULES:
- Write exactly one paragraph.
- Be conclusive — state what the evidence suggests about the current direction of corporate credit spreads and default risk.
- Integrate the findings with the drivers listed above where clearly supported.
- Do not repeat individual findings verbatim — synthesize.
- Do not speculate beyond what the findings support.

FINDINGS:
{{findings}}
```

---

## Summary Prompt 6 — Risco Fiscal

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Synthesize the findings below into a single conclusive paragraph about the current state of Brazil's fiscal situation.

CONTEXT — WHAT DRIVES FISCAL RISK:
Brazil's fiscal risk is influenced by: high nominal interest rates (debt snowball effect), growing mandatory expenditures (structural rigidity exceeding 93% of federal spending), weak GDP growth (lower tax revenue), electoral cycle pressures (spending demands), and liabilities from state-owned enterprises and subnational governments.

OUTPUT RULES:
- Write exactly one paragraph.
- Be conclusive — state what the evidence suggests about the current fiscal trajectory, debt sustainability, and sovereign risk premium.
- Integrate the findings with the drivers listed above where clearly supported.
- Do not repeat individual findings verbatim — synthesize.
- Do not speculate beyond what the findings support.

FINDINGS:
{{findings}}
```

---

## Summary Prompt 7 — Cenário Externo

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Synthesize the findings below into a single conclusive paragraph about the current state of the global economic environment and its implications for Brazil.

CONTEXT — WHAT DRIVES THE EXTERNAL SCENARIO:
The external scenario for Brazil is shaped by: Fed decisions and the direction of US interest rates, US trade policy and tariffs (impact on Brazilian exports), China's economic activity (demand for Brazilian commodities), global risk aversion indicators (VIX, credit spreads), and oil prices (dual effect: export revenue vs. domestic inflation).

OUTPUT RULES:
- Write exactly one paragraph.
- Be conclusive — state what the evidence suggests about global risk appetite, capital flows to Brazil, and the dominant external pressures.
- Integrate the findings with the drivers listed above where clearly supported.
- Do not repeat individual findings verbatim — synthesize.
- Do not speculate beyond what the findings support.

FINDINGS:
{{findings}}
```

---

## Ranking Prompt

```
You are a financial analyst specialized in the Brazilian market.

GOAL:
Based on the current macro scenario, produce a two-level ranking of asset classes and the specific assets within each class — from most to least favored by the current economic environment.

MACRO SCENARIO:
{{macro_scenario}}

ASSETS:
{{assets}}

Each asset in the list contains: name, class, sector, and macro profile (exporter / importer / domestic).

RANKING RULES:

Class ranking:
- Rank each class based on how the macro scenario affects it as a whole.
- Consider all 7 indicators: Selic, IPCA, exchange rate, GDP, private credit, fiscal risk, and external scenario.
- A class is more favored when the majority of macro indicators point positively to it.
- A class is less favored when the majority of macro indicators point negatively to it.

Intra-class ranking:
- Within each class, rank assets using only macro signals.
- Use the asset's sector and macro profile to determine how each indicator applies specifically to it.
- Do not use performance, drawdown, or portfolio weight.
- Assets with identical macro exposure may share the same rank position.

OUTPUT FORMAT:
Return a JSON array. Each element represents one class block, ordered from most to least favored.

[
  {
    "class_rank": 1,
    "class": "<class name>",
    "class_rationale": "<one sentence explaining why this class is ranked here>",
    "assets": [
      {
        "asset_rank": 1,
        "name": "<asset name>",
        "rationale": "<one sentence explaining the macro signal for this asset>"
      }
    ]
  }
]

RULES:
- Every asset from the input must appear in the output exactly once.
- Do not invent assets not present in the input.
- Do not speculate beyond what the macro scenario supports.
- If two assets within the same class have identical macro exposure, assign them the same asset_rank.
```
