# Report Prompts — Paragraphs by Indicator

## Asset variables used in prompts

All variables follow the canonical 4-class asset system defined in `RegrasDeNegocio/ClassesDeAtivos.md`:

| Variable | Included classes |
|----------|-----------------|
| `{{ativos_caixa}}` | pos_fixado_cdi · pos_fixado_selic · RF DI · RF Simples |
| `{{ativos_renda_fixa}}` | ipca_mais · prefixado · Multimercado RF |
| `{{ativos_multimercado}}` | Multimercado · Long Biased |
| `{{ativos_renda_variavel}}` | FIA · Ação · FII |

---

## Indicator 1 — Selic

### Classifier

```
You will receive a summary of the economic scenario for the Selic rate.

Classify the scenario into exactly one of the options below:
- rising
- falling

Return only the word. No explanations.

SCENARIO:
{{cenario_selic}}
```

---

### Prompt — Selic RISING

```
{{trigger}}

The Selic scenario is as follows:
{{cenario_selic}}

---

CONTEXT — SELIC RISING OR AT HIGH LEVEL:

When the Selic is rising or at an elevated level:
- Caixa e Liquidez: directly benefited — CDI/Selic remuneration rises immediately with the rate, with no additional risk
- Renda Fixa Estruturada: pressured — rising rates deteriorate mark-to-market of bonds with duration; required real premium increases, depressing prices
- Multimercado: slightly pressured — higher carry cost of leveraged positions reduces return
- Renda Variável: strongly pressured — discount rate rises, valuations fall, consumption recedes with tighter credit

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an alert tone that:
1. Describes the current Selic trajectory and what the scenario signals
2. Highlights the client's assets under pressure and explains why
3. Highlights the client's assets that benefit in this scenario
4. Recommends caution or protection where applicable
5. Mentions the client's specific assets by name
6. Write in Brazilian Portuguese.
```

---

### Prompt — Selic FALLING

```
{{trigger}}

The Selic scenario is as follows:
{{cenario_selic}}

---

CONTEXT — SELIC FALLING OR IN A DOWNWARD TRAJECTORY:

When the Selic is falling:
- Caixa e Liquidez: loses attractiveness — absolute return falls directly with the rate
- Renda Fixa Estruturada: benefited — required real premium falls, bonds with duration appreciate in mark-to-market
- Multimercado: slight improvement — lower carry cost on leveraged positions improves return
- Renda Variável: strongly benefited — lower discount rate raises valuations, consumption recovers with cheaper credit

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an opportunity tone that:
1. Describes the Selic downward trajectory and what the scenario signals
2. Highlights the client's assets that benefit and explains why
3. Points out where current exposure can be maintained or increased
4. Mentions the client's specific assets by name
5. Write in Brazilian Portuguese.
```

---
---

## Indicator 2 — IPCA

### Classifier

```
You will receive a summary of the economic scenario for inflation in Brazil (IPCA).

Classify the scenario into exactly one of the options below:
- accelerating
- decelerating

Return only the word. No explanations.

SCENARIO:
{{cenario_ipca}}
```

---

### Prompt — IPCA ACCELERATING

```
{{trigger}}

The IPCA scenario is as follows:
{{cenario_ipca}}

---

CONTEXT — IPCA ACCELERATING OR AT HIGH LEVEL:

When inflation is accelerating or above target:
- Caixa e Liquidez: neutral in carry — nominal return rises with Selic, but real return above inflation falls if the central bank does not react at the same pace
- Renda Fixa Estruturada: benefited in carry for IPCA-linked bonds — indexed return rises with inflation; note: mark-to-market can deteriorate if the required real premium also rises
- Multimercado: neutral — result depends on positioning in real assets and interest rates
- Renda Variável: pressured — household purchasing power falls, consumer-facing company margins are compressed

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an alert tone that:
1. Describes the current level and trend of inflation
2. Highlights the client's assets under pressure and explains why
3. Highlights the assets that benefit in this scenario
4. Recommends caution or protection where applicable
5. Mentions the client's specific assets by name
6. Write in Brazilian Portuguese.
```

---

### Prompt — IPCA DECELERATING

```
{{trigger}}

The IPCA scenario is as follows:
{{cenario_ipca}}

---

CONTEXT — IPCA DECELERATING OR FALLING:

When inflation is decelerating:
- Caixa e Liquidez: slight improvement in real return — stable CDI with falling inflation increases the gain above inflation
- Renda Fixa Estruturada: mixed — IPCA-linked carry falls alongside inflation; fixed-rate bonds gain real return as inflation recedes
- Multimercado: neutral — no material directional impact at class level
- Renda Variável: benefited — household purchasing power recovers, demand improves, company margins expand

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an opportunity tone that:
1. Describes the inflation downward trend and what the scenario signals
2. Highlights the client's assets that benefit and explains why
3. Points out where current exposure can be maintained or increased
4. Mentions the client's specific assets by name
5. Write in Brazilian Portuguese.
```

---
---

## Indicator 3 — Exchange Rate

### Classifier

```
You will receive a summary of the economic scenario for the Brazilian exchange rate (USD/BRL).

Classify the scenario into exactly one of the options below:
- depreciating
- appreciating

Return only the word. No explanations.

SCENARIO:
{{cenario_cambio}}
```

---

### Prompt — BRL DEPRECIATING

```
{{trigger}}

The exchange rate scenario is as follows:
{{cenario_cambio}}

---

CONTEXT — BRL DEPRECIATING (DOLLAR RISING):

When the real is depreciating:
- Caixa e Liquidez: neutral — BRL-denominated asset with no direct FX exposure
- Renda Fixa Estruturada: partially protected — imported inflation raises IPCA and increases carry on IPCA-linked bonds; fixed-rate bonds suffer if currency depreciation feeds into inflation expectations
- Multimercado: benefited — depreciation opens opportunities in exporters and dollarized assets within the fund
- Renda Variável: mixed — exporting companies benefit from higher USD revenue in BRL; consumer-facing companies with imported inputs suffer margin compression

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an alert tone that:
1. Describes the current exchange rate direction and main drivers
2. Highlights the client's assets under pressure and explains why
3. Highlights the assets that benefit in this scenario
4. Recommends caution or protection where applicable
5. Mentions the client's specific assets by name
6. Write in Brazilian Portuguese.
```

---

### Prompt — BRL APPRECIATING

```
{{trigger}}

The exchange rate scenario is as follows:
{{cenario_cambio}}

---

CONTEXT — BRL APPRECIATING (DOLLAR FALLING):

When the real is appreciating:
- Caixa e Liquidez: neutral — BRL-denominated asset with no direct FX exposure
- Renda Fixa Estruturada: slight reduction in IPCA+ carry — imported inflation recedes, lowering IPCA-linked bond income
- Multimercado: slightly pressured — reduces opportunity in exporters and currency positions
- Renda Variável: mixed — consumer-facing companies benefit from lower input costs; exporting companies suffer as USD revenue is worth less in BRL

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an opportunity tone that:
1. Describes the BRL appreciation and what the scenario signals
2. Highlights the client's assets that benefit and explains why
3. Points out the assets that may face pressure and how to position
4. Mentions the client's specific assets by name
5. Write in Brazilian Portuguese.
```

---
---

## Indicator 4 — GDP

### Classifier

```
You will receive a summary of the economic scenario for Brazilian GDP growth.

Classify the scenario into exactly one of the options below:
- accelerating
- decelerating

Return only the word. No explanations.

SCENARIO:
{{cenario_pib}}
```

---

### Prompt — GDP ACCELERATING

```
{{trigger}}

The GDP scenario is as follows:
{{cenario_pib}}

---

CONTEXT — GDP ACCELERATING:

When the economy is accelerating:
- Caixa e Liquidez: loses relative attractiveness — risk appetite shifts toward growth assets, reducing the appeal of stable low-risk return
- Renda Fixa Estruturada: neutral — no material directional impact; fixed income inflows may decline as risk appetite improves
- Multimercado: benefited — expanding economy widens the universe of directional opportunities and cyclical positions
- Renda Variável: strongly benefited — strong demand drives revenue growth, earnings expansion, and asset appreciation

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an opportunity tone that:
1. Describes the growth trajectory and its main drivers
2. Highlights the client's assets that benefit and explains why
3. Points out where current exposure can be maintained or increased
4. Mentions the client's specific assets by name
5. Write in Brazilian Portuguese.
```

---

### Prompt — GDP DECELERATING

```
{{trigger}}

The GDP scenario is as follows:
{{cenario_pib}}

---

CONTEXT — GDP DECELERATING:

When the economy is slowing down:
- Caixa e Liquidez: benefited relatively — stable and predictable return gains appeal in a higher risk-aversion environment
- Renda Fixa Estruturada: relatively protected — fixed income inflows increase as investors reduce risk
- Multimercado: slightly pressured — fewer directional opportunities; result depends on positioning
- Renda Variável: strongly pressured — corporate revenues fall with weaker demand, dividends decline, asset valuations compress

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an alert tone that:
1. Describes the deceleration trajectory and its main drivers
2. Highlights the client's assets under pressure and explains why
3. Highlights the assets that benefit in this scenario
4. Recommends caution or protection where applicable
5. Mentions the client's specific assets by name
6. Write in Brazilian Portuguese.
```

---
---

## Indicator 5 — Private Credit

### Classifier

```
You will receive a summary of the economic scenario for the Brazilian private credit market.

Classify the scenario into exactly one of the options below:
- deteriorating
- improving

Return only the word. No explanations.

SCENARIO:
{{cenario_credito}}
```

---

### Prompt — Private Credit DETERIORATING

```
{{trigger}}

The private credit scenario is as follows:
{{cenario_credito}}

---

CONTEXT — PRIVATE CREDIT DETERIORATING:

When the private credit market is under stress:
- Caixa e Liquidez: benefited — flight to quality increases demand for sovereign floating-rate assets; CDI/Selic spread over private credit becomes more attractive
- Renda Fixa Estruturada: pressured — credit spreads widen, Multimercado RF funds suffer mark-to-market deterioration, IPCA+ debentures face increased default risk
- Multimercado: neutral — result depends on positioning; funds with credit exposure suffer, those without are unaffected
- Renda Variável: pressured — corporate cost of capital rises, business environment worsens, earnings outlook deteriorates

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an alert tone that:
1. Describes the current conditions of the private credit market
2. Highlights the impact on the client's credit assets
3. Points out the assets that provide protection in this scenario
4. Recommends caution where applicable
5. Mentions the client's specific assets by name
6. Write in Brazilian Portuguese.
```

---

### Prompt — Private Credit IMPROVING

```
{{trigger}}

The private credit scenario is as follows:
{{cenario_credito}}

---

CONTEXT — PRIVATE CREDIT IMPROVING:

When the private credit market is healthy:
- Caixa e Liquidez: loses relative attractiveness — risk appetite shifts to private credit with additional spread over CDI
- Renda Fixa Estruturada: benefited — compressed spreads favor returns on Multimercado RF and IPCA+ debentures; high carry with controlled risk
- Multimercado: neutral — no material directional impact at class level
- Renda Variável: slight improvement — lower corporate cost of capital supports earnings and valuations

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an opportunity tone that:
1. Describes the favorable conditions in the private credit market
2. Highlights the positive impact on the client's credit assets
3. Points out where current exposure can be maintained or increased
4. Mentions the client's specific assets by name
5. Write in Brazilian Portuguese.
```

---
---

## Indicator 6 — Fiscal Risk

### Classifier

```
You will receive a summary of the economic scenario for Brazil's fiscal situation.

Classify the scenario into exactly one of the options below:
- deteriorating
- improving

Return only the word. No explanations.

SCENARIO:
{{cenario_fiscal}}
```

---

### Prompt — Fiscal Risk DETERIORATING

```
{{trigger}}

The fiscal risk scenario is as follows:
{{cenario_fiscal}}

---

CONTEXT — FISCAL RISK DETERIORATING:

When fiscal risk is elevated or deteriorating:
- Caixa e Liquidez: slightly pressured — severe fiscal deterioration may anticipate premature rate cuts, shortening the period of high Selic remuneration
- Renda Fixa Estruturada: strongly pressured — rising sovereign risk premium opens long bond spreads, deflating mark-to-market of IPCA+ and fixed-rate bonds; this is the primary risk for the class
- Multimercado: pressured — elevated fiscal risk limits long duration positions and increases volatility
- Renda Variável: pressured — cost of capital rises, multiples compress, foreign capital retreats from the local market

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an alert tone that:
1. Describes the current state of public finances and the debt trajectory
2. Highlights the client's assets under pressure and explains why
3. Points out the assets offering the most protection in this scenario
4. Recommends caution where applicable
5. Mentions the client's specific assets by name
6. Write in Brazilian Portuguese.
```

---

### Prompt — Fiscal Risk IMPROVING

```
{{trigger}}

The fiscal risk scenario is as follows:
{{cenario_fiscal}}

---

CONTEXT — FISCAL RISK IMPROVING:

When fiscal risk is being controlled or consolidated:
- Caixa e Liquidez: slight improvement — risk of premature rate cuts recedes, sustaining the period of high Selic remuneration
- Renda Fixa Estruturada: strongly benefited — required real premium falls, long bonds appreciate in mark-to-market; fiscal consolidation is the primary driver of fixed income recovery
- Multimercado: improvement — fiscal stability opens long duration positions and reduces directional risk
- Renda Variável: benefited — cost of capital falls, multiples expand, business confidence improves and foreign capital returns

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an opportunity tone that:
1. Describes the improvement in public finances and what the scenario signals
2. Highlights the client's assets that benefit and explains why
3. Points out where current exposure can be maintained or increased
4. Mentions the client's specific assets by name
5. Write in Brazilian Portuguese.
```

---
---

## Indicator 7 — External Scenario

### Classifier

```
You will receive a summary of the external economic scenario and its impact on Brazil.

Classify the scenario into exactly one of the options below:
- deteriorating
- improving

Return only the word. No explanations.

SCENARIO:
{{cenario_externo}}
```

---

### Prompt — External Scenario DETERIORATING

```
{{trigger}}

The external scenario is as follows:
{{cenario_externo}}

---

CONTEXT — EXTERNAL SCENARIO DETERIORATING:

When the global environment is adverse for emerging markets:
- Caixa e Liquidez: neutral — Selic interest rate differential sustains attractiveness; not a safe haven, but the carry premium remains
- Renda Fixa Estruturada: pressured — rising country risk increases the required real premium, deteriorating mark-to-market of long bonds
- Multimercado: neutral — result depends entirely on positioning; can benefit from volatility or currency positions
- Renda Variável: strongly pressured — global risk-off reduces appetite for emerging markets, capital flight depresses valuations and depreciates BRL

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an alert tone that:
1. Describes the current state of the global scenario and its main drivers
2. Highlights the client's assets under pressure and explains why
3. Highlights the assets offering the most stability in this scenario
4. Recommends caution where applicable
5. Mentions the client's specific assets by name
6. Write in Brazilian Portuguese.
```

---

### Prompt — External Scenario IMPROVING

```
{{trigger}}

The external scenario is as follows:
{{cenario_externo}}

---

CONTEXT — EXTERNAL SCENARIO IMPROVING:

When the global environment is favorable for emerging markets:
- Caixa e Liquidez: loses relative attractiveness — risk appetite shifts toward growth assets as global conditions improve
- Renda Fixa Estruturada: benefited — country risk recedes, required real premium falls, long bonds appreciate in mark-to-market
- Multimercado: benefited — can capture long positions in equities and emerging market currencies in a risk-on environment
- Renda Variável: strongly benefited — capital flows to emerging markets increase, BRL appreciates, valuations expand

---

CLIENT ASSETS BY CLASS:

Caixa e Liquidez: {{ativos_caixa}}
Renda Fixa Estruturada: {{ativos_renda_fixa}}
Multimercado: {{ativos_multimercado}}
Renda Variável: {{ativos_renda_variavel}}

---

INSTRUCTION:

Write an objective paragraph of 4 to 6 lines with an opportunity tone that:
1. Describes the improvement in the global scenario and what it signals for Brazil
2. Highlights the client's assets that benefit and explains why
3. Points out where current exposure can be maintained or increased
4. Mentions the client's specific assets by name
5. Write in Brazilian Portuguese.
```

---
---

## Report Assembly

### Title Generator Prompt

```
You will receive the current classification of 7 Brazilian economic indicators.

Based on these classifications, write a one-line title that summarizes
the current economic scenario. The title should be direct, informative,
and reflect the overall tone (adverse, favorable, or mixed).

Format examples:
- "Adverse scenario: rising rates, pressured inflation and slowing activity"
- "Window of opportunity: Selic falling and activity recovering"
- "Mixed scenario: controlled inflation but fiscal risk still elevated"

CLASSIFICATIONS:
Selic: {{classificacao_selic}}
IPCA: {{classificacao_ipca}}
Exchange Rate: {{classificacao_cambio}}
GDP: {{classificacao_pib}}
Private Credit: {{classificacao_credito}}
Fiscal Risk: {{classificacao_fiscal}}
External Scenario: {{classificacao_externo}}

Return only the title. No explanations.
```

---

### Report Assembly Prompt

```
Assemble the report below exactly as structured.
Do not rewrite, summarize or alter the received paragraphs.
Insert each block in the indicated space.

---

PORTFOLIO ANALYSIS REPORT
{{mes}}

Client: {{nome_cliente}}
Risk Profile: {{perfil_risco}}

---

{{titulo}}

---

{{titulo_selic}}

{{paragrafo_selic}}

---

{{titulo_ipca}}

{{paragrafo_ipca}}

---

{{titulo_cambio}}

{{paragrafo_cambio}}

---

{{titulo_pib}}

{{paragrafo_pib}}

---

{{titulo_credito}}

{{paragrafo_credito}}

---

{{titulo_fiscal}}

{{paragrafo_fiscal}}

---

{{titulo_externo}}

{{paragrafo_externo}}

---

This report was automatically generated based on the macro reference
report for the month of {{mes}} and the positions recorded in the
client's portfolio.
```
