# Estudo de Mercado — AI Financial Advisor XP

Referência completa de conceitos necessários para construir o workflow de relatório mensal para clientes XP. Organizado em ordem de dependência: cada seção pressupõe a anterior.

---

## 1. Estrutura do Mercado Financeiro Brasileiro

### 1.1 Reguladores e self-reguladores

| Entidade | Papel | Relevância para o projeto |
|----------|-------|--------------------------|
| **CVM** (Comissão de Valores Mobiliários) | Regula o mercado de capitais (ações, fundos, derivativos) | Define regras de suitability — o que pode ser recomendado a cada perfil |
| **BCB** (Banco Central do Brasil) | Regula o sistema financeiro e define a Selic | Fonte oficial de CDI, Selic, câmbio |
| **ANBIMA** | Self-regulação da indústria de fundos e renda fixa | Padroniza classificação de fundos, define benchmarks obrigatórios |
| **B3** (Brasil, Bolsa, Balcão) | Opera a bolsa de valores e o mercado de derivativos | Onde ações e ETFs são negociados; publica dados de preços |

### 1.2 Como os ativos chegam ao cliente XP

O cliente não compra diretamente na B3. O fluxo é:

```
Cliente → Assessor XP → Plataforma XP → Corretora/Distribuidora → B3 / Gestor do fundo
```

- Para **ações**: a ordem passa pela corretora e é executada na B3
- Para **fundos**: o cliente aplica via plataforma XP, que transfere para o gestor do fundo
- Para **renda fixa**: o banco ou emissor vende diretamente via plataforma XP

### 1.3 Liquidez

**Liquidez** é a facilidade de converter um ativo em dinheiro sem perda de valor.

| Ativo | Liquidez | Impacto prático |
|-------|----------|-----------------|
| Ações (LREN3, MRFG3...) | Alta (D+2) | Pode vender hoje, recebe em 2 dias úteis |
| Fundos multimercado | Média (D+30 a D+60) | Resgate demora dias ou semanas |
| CDB com vencimento | Baixa (até o vencimento) | Não pode resgatar antes; ou resgata com deságio |
| Tesouro IPCA+ | Média (D+1 via Tesouro Direto) | Pode vender antes do vencimento, mas ao preço de mercado |

**Importância para recomendações:** nunca recomendar venda de ativo ilíquido sem verificar prazo de resgate. O CDB do Albert vence em set/2024 — se ainda estiver na carteira, a recomendação precisa considerar isso.

---

## 2. Classes de Ativos — O que é cada uma

### 2.1 Ações

**Definição:** Fração de propriedade de uma empresa listada na B3.

**Como funciona:**
- O preço oscila diariamente conforme oferta e demanda
- O investidor ganha de duas formas: **valorização** (preço sobe) e **dividendos** (distribuição de lucro)
- Tipos de ação: **ON (ordinária)** — tem direito a voto; **PN (preferencial)** — prioridade no dividendo, sem voto. Na B3, os sufixos são: `3` = ON, `4` = PN, `11` = unit

**Na carteira do Albert:**
| Ação | Tipo | Performance acumulada |
|------|------|----------------------|
| LREN3 | ON (Lojas Renner) | -41,7% desde compra |
| MRFG3 | ON (Marfrig) | +43,5% |
| ARZZ3 | ON (Arezzo) | -31,05% |
| HAPV3 | ON (Hapvida) | -74,58% |

**Peculiaridade:** a rentabilidade no portfólio do Albert é **acumulada desde a data de compra** (2021–2022), não do último mês. Para o cálculo de rentabilidade mensal, é preciso usar os preços do CSV (`current_price` vs `last_month_price`).

### 2.2 Fundos de Investimento

**Definição:** Veículo coletivo onde múltiplos investidores aplicam recursos que são geridos por um gestor profissional.

**Como funciona:**
- O investidor compra **cotas** do fundo — uma fração do patrimônio total
- O gestor investe o patrimônio conforme a política do fundo
- A rentabilidade é medida pela variação do **valor da cota** entre dois momentos
- O gestor cobra **taxa de administração** (% ao ano) e, em alguns fundos, **taxa de performance** (% do que exceder o benchmark)

**Tipos de fundo relevantes para o projeto:**

| Sigla | Nome completo | O que investe | Benchmark típico | Risco |
|-------|---------------|---------------|-----------------|-------|
| **FIRF DI** | Fundo de Inv. Renda Fixa referenciado DI | Títulos atrelados ao CDI | CDI | Baixo |
| **FIM** | Fundo de Inv. Multimercado | Qualquer ativo (ações, câmbio, juros, derivativos) | CDI ou IPCA+ | Médio-Alto |
| **FIA** | Fundo de Inv. em Ações | Mínimo 67% em ações | IBOVESPA | Alto |
| **FIC** | Fundo de Inv. em Cotas | Investe em cotas de outros fundos | Igual ao fundo-alvo | Varia |

**Lendo os nomes dos fundos do Albert:**
- `Riza Lotus Plus Advisory FIC FIRF REF DI CP` → é um FIC (investe em cotas) de FIRF referenciado DI → **benchmark: CDI**, risco baixo. O "CP" = crédito privado
- `Brave I FIC FIM CP` → FIC de multimercado crédito privado → **benchmark: CDI**, risco médio
- `Truxt Long Bias Advisory FIC FIM` → multimercado long biased (mais comprado que vendido em ações) → **benchmark: IBOVESPA ou CDI**, risco alto
- `STK Long Biased FIC FIA` → fundo de ações long biased → **benchmark: IBOVESPA**, risco alto
- `Constellation Institucional Advisory FIC FIA` → fundo de ações fundamentalista → **benchmark: IBOVESPA**, risco alto
- `Ibiuna Hedge ST Advisory FIC FIM` → multimercado hedge, curto prazo → **benchmark: CDI**, risco médio

**Come-cotas:** Fundos de renda fixa e multimercado têm tributação semestral (maio e novembro) — o IR é recolhido automaticamente reduzindo o número de cotas. Isso reduz a rentabilidade líquida e deve ser considerado na carta.

### 2.3 Renda Fixa

**Definição:** Títulos onde o emissor toma dinheiro emprestado e promete devolver com juros.

**Tipos de remuneração:**

| Tipo | Como funciona | Exemplo | Quando é melhor |
|------|---------------|---------|-----------------|
| **Pós-fixado** | Rende um % do CDI ou Selic | CDB 110% CDI | Selic/CDI alta e incerta |
| **Prefixado** | Taxa fixada no momento da compra | CDB 12% a.a. | Quando Selic vai cair |
| **IPCA+** (híbrido) | IPCA + taxa fixa | IPCA + 5,45% | Proteção contra inflação |

**Na carteira do Albert:**
- CDB C6 com taxa `IPC-A + 5,45%` → rende a inflação mais 5,45% ao ano → com IPCA em 6,1% em 2025, rende ~11,55% a.a. bruto

**Duration:** Mede a sensibilidade do preço de um título de renda fixa à variação das taxas de juros. Títulos com duration longa (Tesouro IPCA+ 2035+) perdem valor de mercado quando os juros sobem — mesmo que o investidor não venda. Isso explica por que a carteira de Albert mostra `Taxa a mercado` diferente do `Valor aplicado`.

**Marcação a mercado vs. marcação na curva:**
- **Marcação na curva:** mostra o valor original + juros acumulados. Nunca cai.
- **Marcação a mercado:** mostra o valor se o título fosse vendido hoje. Pode cair quando os juros sobem.
- A XP usa marcação a mercado — por isso o `Valor líquido` dos fundos e títulos pode ser menor que o `Valor aplicado` mesmo que o ativo esteja rendendo.

---

## 3. Portfólio e Alocação

### 3.1 O que é um portfólio

Conjunto de todos os investimentos de um cliente. O portfólio do Albert tem:

```
Total investido: R$312.186,20
├── Ações (19,32%): R$60.311,79
│   ├── LREN3: R$27.812 (8,91%)
│   ├── MRFG3: R$15.433 (4,94%)
│   ├── ARZZ3: R$10.924 (3,50%)
│   └── HAPV3: R$6.143 (1,97%)
├── Fundos (67,71%): R$211.395,66
│   ├── Riza Lotus Plus: R$96.179 (30,81%) ← maior posição
│   ├── Brave I: R$72.567 (23,24%)
│   ├── Ibiuna Hedge ST: R$11.601 (3,72%)
│   ├── Truxt Long Bias: R$12.522 (4,01%)
│   ├── STK Long Biased: R$9.746 (3,12%)
│   ├── Constellation: R$8.475 (2,71%)
│   └── Trend Investback: R$305 (0,10%)
└── Renda Fixa (12,97%): R$40.479
    └── CDB C6 IPCA+5,45%: R$40.479
```

### 3.2 Alocação estratégica por perfil de risco

A alocação é a distribuição do portfólio entre classes de ativo. Cada perfil tem um range recomendado:

| Classe de ativo | Conservador | Moderado | Arrojado |
|-----------------|-------------|---------|---------|
| Renda fixa | 70–90% | 30–50% | 10–20% |
| Fundos multimercado | 10–20% | 20–40% | 20–30% |
| Ações / fundos de ações | 0–5% | 15–30% | 50–70% |

**Diagnóstico da carteira do Albert (moderado):**
- Ações diretas: 19,32% → dentro do range
- Fundos multimercado (Riza, Brave, Ibiuna): ~57% → **acima** do range para moderado
- Fundos de ações (Truxt, STK, Constellation): ~10% → dentro
- Renda fixa: 12,97% → **abaixo** do range para moderado (deveria ser 30–50%)

Isso é um ponto importante para a recomendação: **Albert está suballocado em renda fixa para seu perfil**, especialmente relevante com Selic a 15,5%.

### 3.3 Diversificação

**Definição:** Distribuir investimentos entre ativos que não se movem juntos (baixa correlação).

**Correlação:** medida de -1 a +1.
- +1 = movem igual (sem benefício de diversificação)
- 0 = independentes (diversificação plena)
- -1 = movem oposto (hedge perfeito)

**Exemplos práticos:**
- LREN3 e ARZZ3 são ambas varejo de moda → alta correlação → concentração de risco setorial
- Riza Lotus (DI) e HAPV3 (ação de saúde) → baixa correlação → diversificação real

**Risco idiossincrático vs. risco sistêmico:**
- **Risco idiossincrático** (risco específico): risco da empresa (HAPV3 pode ter problemas de gestão). É diversificável.
- **Risco sistêmico** (risco de mercado): risco que afeta tudo (crise, Selic subindo). Não é diversificável.

---

## 4. Cálculo de Rentabilidade

### 4.1 Retorno simples de uma posição

Para ações (usando os dados do CSV):

```
retorno_mensal = (preco_atual - preco_mes_anterior) / preco_mes_anterior
```

**Exemplo com o CSV (Albert):**
- LREN3: `(16,94 - 15,55) / 15,55 = +8,94%` no mês
- MRFG3: `(10,26 - 12,27) / 12,27 = -16,38%` no mês
- HAPV3: `(3,97 - 2,25) / 2,25 = +76,44%` no mês (recuperação)

**Importante:** o retorno mensal pode ser positivo mesmo que o retorno acumulado seja negativo (HAPV3 caiu 74% mas recuperou 76% neste mês).

### 4.2 Retorno ponderado pela alocação (contribuição)

Para calcular o retorno total da carteira, cada ativo contribui proporcionalmente ao seu peso:

```
contribuição_ativo = retorno_mensal × peso_no_portfolio
retorno_carteira = Σ contribuições de todos os ativos
```

**Exemplo (apenas ações do Albert, peso total = 19,32%):**
```
LREN3: +8,94% × 8,91% = +0,797%
MRFG3: -16,38% × 4,94% = -0,809%
ARZZ3: (56,58 - 56,55) / 56,55 × 3,50% = +0,001%
HAPV3: +76,44% × 1,97% = +1,506%
→ Contribuição das ações = +1,495%
```

### 4.3 Retorno Total vs. Retorno desde a compra

O portfólio do Albert mostra duas rentabilidades diferentes:

| Coluna no portfólio | O que significa | Quando usar |
|---------------------|-----------------|-------------|
| `Rentabilidade (%)` na tabela de ações | Retorno **acumulado desde a data de compra** | Para avaliar a decisão de entrada |
| Variação entre `preco_atual` e `last_month_price` no CSV | Retorno **do último mês** | Para o relatório mensal |

**A carta deve usar o retorno do último mês** — não o acumulado. A confusão entre esses dois é um erro crítico.

### 4.4 Retorno ponderado pelo tempo (TWR) vs. pelo dinheiro (MWR)

| Método | O que mede | Quando usar |
|--------|-----------|-------------|
| **TWR** (Time-Weighted Return) | Performance do gestor, eliminando efeito de aportes/resgates | Para comparar com benchmarks |
| **MWR** (Money-Weighted Return / TIR) | Retorno efetivo para o investidor, considerando quando entrou/saiu | Para mostrar o resultado real do cliente |

**Para o MVP:** usar TWR simples (retorno da cota/preço no período). O MWR requer histórico de fluxos de caixa, que não temos no input atual.

### 4.5 Retorno de fundos

Para fundos, o retorno mensal é calculado pela variação da **cota**:

```
retorno_fundo = (cota_final - cota_inicial) / cota_inicial
```

O problema atual: o CSV só tem ações. Para os fundos, precisamos das cotas do mês atual e do anterior via CVM/brasa.

**Fallback para o MVP:** usar a rentabilidade acumulada do portfólio dividida pelo número de meses desde a compra como proxy mensal:
```
retorno_mensal_proxy = ((valor_liquido / valor_aplicado) ^ (1/n_meses)) - 1
```

### 4.6 Retorno de renda fixa

Para o CDB do Albert (`IPCA + 5,45%`):

```
retorno_mensal ≈ ((1 + IPCA_anual)^(1/12) - 1) + (5,45% / 12)
```

Com IPCA de 6,1% ao ano:
```
retorno_mensal ≈ ((1,061)^(1/12) - 1) + (0,0545/12)
               ≈ 0,495% + 0,454%
               ≈ 0,95% ao mês ≈ 11,55% a.a.
```

### 4.7 Retorno líquido (após IR)

O retorno bruto não é o que o cliente recebe. É necessário descontar o imposto de renda:

**Tributação por classe de ativo:**

| Ativo | Alíquota | Tipo | Detalhe |
|-------|----------|------|---------|
| Ações (ganho de capital) | 15% | Sobre lucro na venda | Isento se venda < R$20k/mês |
| Ações (day trade) | 20% | Sobre lucro | Sempre tributado |
| Dividendos de ações | 0% | Isento | No Brasil, dividendo é isento |
| Fundos de ações (FIA) | 15% | Sobre ganho no resgate | |
| Fundos multimercado (longo prazo >720d) | 15% | Come-cotas em maio/nov + resgate | |
| Fundos multimercado (curto prazo <360d) | 20% | Come-cotas | |
| CDB, LCI, LCA, Tesouro | 15–22,5% | Tabela regressiva por prazo | Quanto mais tempo, menos IR |

**Tabela regressiva de renda fixa:**
| Prazo | Alíquota |
|-------|----------|
| Até 180 dias | 22,5% |
| 181 a 360 dias | 20% |
| 361 a 720 dias | 17,5% |
| Acima de 720 dias | 15% |

**O CDB do Albert** foi aplicado em set/2021, resgatado em set/2024 → mais de 720 dias → alíquota de 15%.

**Para a carta:** apresentar rentabilidade bruta e líquida. A diferença é relevante, especialmente em renda fixa.

---

## 5. Benchmarks

### 5.1 CDI (Certificado de Depósito Interbancário)

**O que é:** Taxa que os bancos cobram para emprestar dinheiro entre si overnight. Na prática, anda colado à Selic (geralmente ~0,1% abaixo).

**Por que é o principal benchmark do Brasil:**
- Representa o custo de oportunidade do dinheiro: qualquer investimento que renda menos que o CDI está perdendo valor em termos relativos
- Quase toda renda fixa e fundo multimercado usa CDI como benchmark
- Com Selic a 15,5%, o CDI mensal é aproximadamente `((1,155)^(1/12)) - 1 ≈ 1,20%`

**Uso na carta:** mostrar se a carteira bateu ou perdeu para o CDI no mês:
```
alfa_carteira = retorno_carteira - retorno_CDI
```

### 5.2 IBOVESPA

**O que é:** Índice das ações mais negociadas da B3, ponderado por valor de mercado e liquidez. Composto por ~90 empresas.

**Por que usar:** Benchmark para a parcela de ações e fundos de ações. Se a carteira de ações caiu 5% e o IBOVESPA caiu 8%, o gestor/cliente performou bem.

**Uso na carta:** comparar retorno da parcela de ações vs. IBOVESPA.

### 5.3 IPCA (Índice de Preços ao Consumidor Amplo)

**O que é:** Medida oficial de inflação do Brasil, calculada pelo IBGE.

**Por que usar:** Retorno real = retorno nominal - IPCA. Mostra se o patrimônio cresceu em termos de poder de compra:
```
retorno_real = ((1 + retorno_nominal) / (1 + IPCA_mensal)) - 1
```

**Uso na carta:** mostrar se o portfólio preservou o poder de compra. Para o perfil moderado do Albert, isso é um objetivo explícito ("preservar poder de compra e incrementá-lo marginalmente").

### 5.4 Selic

**O que é:** Taxa básica de juros da economia brasileira, definida pelo Copom a cada 45 dias.

**Diferença Selic vs. CDI:**
- **Selic Over** = taxa das operações com títulos públicos
- **CDI** = taxa do mercado interbancário privado
- Na prática, CDI ≈ Selic - 0,10% a.a.

**Impacto da Selic na carteira:**
- Selic **sobe** → renda fixa pós-fixada rende mais; ações e fundos de ações tendem a cair (dinheiro migra para RF); títulos prefixados perdem valor de mercado
- Selic **cai** → o inverso; boa para ações e fundos de ações

---

## 6. Análise de Risco — Métricas

### 6.1 Volatilidade

**Definição:** Desvio padrão dos retornos ao longo do tempo. Mede o quanto os retornos oscilam.

```
volatilidade = desvio_padrão(retornos_diários) × √252   ← anualizada
```

- Volatilidade alta = retornos imprevisíveis = risco maior
- Uma ação como HAPV3 (caiu 74%) tem volatilidade altíssima
- Um fundo DI como Riza Lotus tem volatilidade quase zero

**Uso na carta:** não precisa aparecer explicitamente para o cliente leigo, mas deve guiar as recomendações.

### 6.2 Drawdown

**Definição:** Queda percentual do valor de um ativo desde o seu pico histórico até o ponto atual.

```
drawdown = (valor_atual - pico_histórico) / pico_histórico
```

**Na carteira do Albert:**
- HAPV3: drawdown de -74,58% — isso significa que quem comprou no pico perdeu 74,58%
- LREN3: drawdown de -41,7%

**Máximo Drawdown (Max DD):** a maior queda registrada em um período. Métrica de risco muito usada para fundos.

**Importância para recomendações:** uma posição com drawdown profundo pode estar em "armadilha de valor" (continue caindo) ou pode ser uma oportunidade de compra. A análise macro precisa decidir qual é o caso.

### 6.3 Sharpe Ratio

**Definição:** Retorno excedente por unidade de risco.

```
sharpe = (retorno_carteira - CDI) / volatilidade_carteira
```

- Sharpe > 1 = bom (retorno justifica o risco)
- Sharpe < 0 = o fundo rendeu menos que o CDI com risco adicional

**Uso:** comparar fundos da carteira entre si. Se o Truxt Long Bias (FIM) tem Sharpe negativo mas o Riza Lotus tem Sharpe alto, talvez valha realocar.

### 6.4 Beta

**Definição:** Sensibilidade do ativo em relação ao mercado (IBOVESPA).

```
beta = correlação(ativo, IBOVESPA) × (volatilidade_ativo / volatilidade_IBOVESPA)
```

- Beta = 1 → move igual ao mercado
- Beta > 1 → amplifica movimentos do mercado (ativo agressivo)
- Beta < 1 → se move menos que o mercado (defensivo)
- Beta < 0 → se move contra o mercado (hedge)

**Exemplo:** um fundo long biased como STK FIA provavelmente tem beta próximo de 1. Um fundo DI como Riza Lotus tem beta próximo de 0.

### 6.5 Correlação entre ativos (para diversificação)

Para o portfólio do Albert, as correlações relevantes:
- Riza Lotus (DI) × ações → correlação próxima de 0 → boa diversificação
- LREN3 × ARZZ3 → ambas varejo de moda, afetadas por consumo → correlação alta → concentração indesejada
- Fundos long biased × IBOVESPA → correlação alta → duplicidade de risco

---

## 7. Análise Macro e Impacto na Carteira

### 7.1 O que a análise macro informa

A análise macro da XP (fev/2025) traz:
- **Selic terminal projetada: 15,50%** (alta de 1,00% + 0,75% + 0,50% nas próximas reuniões)
- **IPCA 2025: 6,1%** (acima do teto da meta de 4,5%)
- **PIB 2025: +2,0%** (desacelerando de 3,6% em 2024)
- **USD/BRL final 2025: R$6,20**
- **Fed:** sem cortes de juros em 2025

### 7.2 Como cada indicador afeta as classes de ativo

**Selic subindo (para 15,5%):**

| Classe | Impacto | Razão |
|--------|---------|-------|
| CDB pós-fixado | **Positivo** | Rende mais CDI |
| Tesouro IPCA+ | **Negativo (curto prazo)** | Preço de mercado cai quando juros sobem |
| Fundos DI (Riza Lotus) | **Positivo** | Rende mais CDI |
| Ações (LREN3, HAPV3...) | **Negativo** | Custo de capital sobe; consumo cai; P/L contrai |
| Fundos long biased | **Negativo** | Exposição a ações |

**IPCA alto (6,1%):**
- Corrói retorno real de ativos pré-fixados
- Beneficia títulos IPCA+ (CDB do Albert) — rende mais
- Pressiona setores de varejo (LREN3, ARZZ3) — custo de vida alto reduz consumo

**PIB desacelerando (+2,0%):**
- Negativo para ações em geral (menos crescimento de lucros)
- Especialmente negativo para varejo e consumo discricionário (LREN3, ARZZ3)
- Marfrig (MRFG3) — frigorífico, parte da receita em dólar — menos sensível ao PIB doméstico

**USD/BRL em R$6,20:**
- Positivo para exportadores: MRFG3 (carne para exportação), VALE3, PETR4
- Negativo para importadores e varejo (custo de importação sobe)
- Positivo para fundos com exposição ao dólar

### 7.3 Setores e seu comportamento macro

| Setor | Empresas na carteira | Sensibilidade macro |
|-------|---------------------|---------------------|
| Varejo de moda | LREN3, ARZZ3 | Alta sensibilidade à Selic e consumo |
| Saúde | HAPV3 | Regulação de preços pela ANS; custos altos em inflação |
| Frigoríficos | MRFG3 | Beneficiado pelo dólar alto e demanda externa |
| Crédito privado (fundos DI) | Riza Lotus, Brave I | Beneficiado pela Selic alta |

### 7.4 Ciclo de juros e o que esperar

O Brasil está em ciclo de **aperto monetário** (Selic subindo). Historicamente:

```
Ciclo de aperto →
  Renda fixa pós-fixada rende mais
  Ações sofrem (especialmente crescimento e varejo)
  Fundos DI superam fundos de ações
  Consumo desacelera
  Câmbio pode se fortalecer (atrai capital externo)
```

Para a carteira do Albert, este cenário reforça a sugestão de aumentar renda fixa e reduzir ações com drawdown profundo.

---

## 8. Recomendação de Compra e Venda

### 8.1 Lógica de recomendação — o que considerar

Uma boa recomendação combina **quatro dimensões**:

```
Recomendação = f(perfil_de_risco, análise_macro, performance_recente, alocação_atual)
```

| Dimensão | Pergunta-chave | Fonte de dados |
|----------|---------------|----------------|
| Perfil de risco | Este ativo é adequado para o perfil do cliente? | Documento de perfil + regras CVM |
| Análise macro | O cenário favorece este ativo? | Relatório macro XP + Itaú BBA |
| Performance recente | O ativo está em tendência de recuperação ou piora? | CSV de preços + drawdown |
| Alocação atual | O cliente está sobrepeso ou subpeso neste ativo/classe? | Dados do portfólio |

### 8.2 Tipos de recomendação

| Ação | Significado | Quando recomendar |
|------|-------------|------------------|
| **COMPRAR** | Iniciar ou aumentar posição | Ativo subavaliado + macro favorável + dentro do perfil |
| **MANTER** | Não fazer nada | Posição adequada + sem sinal de reversão |
| **REDUZIR** | Diminuir posição sem zerar | Sobrepeso ou risco elevado, mas ainda tem valor |
| **VENDER** | Zerar posição | Macro desfavorável + ativo fora do perfil + drawdown profundo sem perspectiva |
| **REBALANCEAR** | Ajustar pesos sem alterar exposição total | Desvio em relação à alocação alvo |

### 8.3 Regras baseadas em dados (auditáveis)

As regras abaixo não dependem do LLM — são determinísticas e verificáveis:

**Regra 1 — Drawdown excessivo:**
```
SE drawdown_acumulado > 40%
E peso_no_portfolio > 1,5%
ENTÃO flag = REDUZIR
```
→ Afeta HAPV3 (-74%, 1,97%) e LREN3 (-41,7%, 8,91%)

**Regra 2 — Subalocação em renda fixa com Selic alta:**
```
SE perfil == "moderado"
E alocação_renda_fixa < 25%
E selic > 13%
ENTÃO flag = AUMENTAR renda fixa
```
→ Albert tem 12,97% em RF — abaixo do mínimo para moderado em ambiente de Selic alta

**Regra 3 — Concentração em um único ativo:**
```
SE peso_ativo > 25%
ENTÃO flag = REDUZIR (concentração)
```
→ Riza Lotus representa 30,81% — acima do threshold

**Regra 4 — Fundo com rentabilidade negativa e beta alto:**
```
SE retorno_acumulado_fundo < 0
E categoria IN ["long biased", "FIA"]
E selic_tendencia == "alta"
ENTÃO flag = AVALIAR SAÍDA
```
→ Truxt Long Bias (-12,13%), STK Long Biased (-14,51%), Constellation (-25,66%)

**Regra 5 — Fundo com rentabilidade muito positiva e perfil:**
```
SE retorno_fundo > 15%
E categoria == "FIRF DI"
E perfil_risco IN ["conservador", "moderado"]
ENTÃO flag = MANTER (alinhado com cenário)
```
→ Riza Lotus (+15,51%), Brave I (+19,08%) — manter

### 8.4 Rebalanceamento de carteira

**Definição:** Processo de ajustar os pesos dos ativos de volta à alocação-alvo.

**Quando rebalancear:**
- Desvio > 5% em relação ao peso-alvo em uma classe
- Mudança significativa no cenário macro
- Mudança no perfil de risco do cliente

**Custo do rebalanceamento:**
- Venda de ações → IR sobre ganho de capital
- Fundos → prazo de resgate (não é imediato)
- Corretagem e emolumentos da B3 (pequeno, mas existe)

**Para o portfólio do Albert:**
```
Alocação atual vs. alvo moderado:
  Ações: 19,32% → target 20% → OK
  Fundos: 67,71% → target 45% → ACIMA
  Renda Fixa: 12,97% → target 35% → ABAIXO

→ Recomendação estrutural: mover ~20% de fundos para renda fixa
  = resgatar ~R$62k de fundos e aplicar em CDB/Tesouro IPCA+
```

### 8.5 Suitability (adequação ao perfil)

**Definição:** Processo regulatório (Resolução CVM 30) que garante que os produtos recomendados são adequados ao perfil do cliente.

**Três dimensões do suitability:**
1. **Perfil de risco:** conservador / moderado / arrojado / agressivo
2. **Horizonte de investimento:** curto (até 2 anos) / médio (2–5 anos) / longo (>5 anos)
3. **Capacidade financeira:** reserva de emergência, renda, patrimônio total

**Para Albert (moderado):**
- Pode receber: ações de empresas consolidadas, renda fixa BB+ ou superior, fundos multimercado
- Não pode receber: derivativos alavancados, criptomoedas, fundos agressivos com leverage
- O LLM precisa de um guardrail: nunca recomendar produto fora do perfil regulatório

### 8.6 Aplicação das recomendações à carteira do Albert

Com base em todas as dimensões acima:

| Ativo | Ação | Razão |
|-------|------|-------|
| HAPV3 | REDUZIR | Drawdown -74,58%, setor de saúde sob pressão, Selic alta reduz consumo |
| LREN3 | MANTER com atenção | Drawdown -41,7% mas empresa sólida; esperar recuperação do consumo |
| MRFG3 | MANTER | +43,5%, beneficiado pelo câmbio alto, exportador |
| ARZZ3 | MANTER | Queda moderada, empresa de qualidade; avaliar em 1–2 meses |
| Riza Lotus Plus | MANTER | +15,51%, alinhado com Selic alta, maior posição mas defensiva |
| Brave I FIC FIM | MANTER | +19,08%, bom desempenho, crédito privado |
| Truxt Long Bias | AVALIAR SAÍDA | -12,13%, long biased em ambiente de Selic alta = vento contrário |
| STK Long Biased | AVALIAR SAÍDA | -14,51%, mesmo raciocínio |
| Constellation FIA | AVALIAR SAÍDA | -25,66%, fundo de ações em ambiente hostil |
| CDB C6 IPCA+ | MANTER | Rende IPCA+5,45%, excelente em cenário de inflação alta |
| **Nova alocação RF** | COMPRAR | Aumentar renda fixa para ~30–35% via CDB ou Tesouro IPCA+ |

---

## 9. Tributação (síntese operacional)

### 9.1 O que descontar no cálculo de retorno líquido

Para a carta do cliente, mostrar sempre **retorno bruto e líquido**:

```
retorno_liquido_ações = retorno_bruto × (1 - 0,15)  [se ganho de capital, acima de R$20k/mês]
retorno_liquido_RF = retorno_bruto × (1 - aliquota_tabela_regressiva)
retorno_liquido_fundos = retorno_bruto × (1 - aliquota_come_cotas)
```

### 9.2 IOF

Incide sobre renda fixa e fundos resgatados em menos de 30 dias — alíquota regressiva de 96% a 0%. Não relevante para o Albert se ele mantém posições por mais de 30 dias.

### 9.3 Come-cotas

Fundos multimercado e RF têm antecipação do IR em **maio e novembro**:
- Fundos de longo prazo (>720 dias): 15%
- Fundos de curto prazo: 20%

Isso reduz o número de cotas do fundo automaticamente — o cliente vê a cota menor sem ter feito resgate. A carta deve explicar isso quando o cliente perceber queda na posição.

---

## 10. Peculiaridades do Mercado Brasileiro

### 10.1 Alta concentração em CDI/Selic

Com Selic a 15,5%, o Brasil tem uma das maiores taxas reais do mundo. Isso cria uma **anomalia**: mesmo um perfil moderado deveria ter exposição relevante a renda fixa, porque o retorno é alto com risco baixo. Em países com juros próximos de zero (Europa, EUA até 2022), isso não acontecia.

**Implicação para o workflow:** a recomendação de "aumentar renda fixa" para Albert não é conservadorismo excessivo — é racional no contexto brasileiro de 2025.

### 10.2 Volatilidade cambial e risco político

O real (BRL) é uma das moedas emergentes mais voláteis. Com USD/BRL a R$6,20, ativos dolarizados ou fundos com hedge cambial ganham relevância mesmo para perfis moderados.

**Implicação:** mencionar exposição cambial da carteira na carta, especialmente se o cliente tiver fundos com derivativos de câmbio.

### 10.3 Fundos Advisory vs. Institucionais

No portfólio do Albert, vários fundos têm "Advisory" no nome (Riza Lotus **Advisory**, Truxt **Advisory**, Constellation **Advisory**):
- Fundos **Advisory** são distribuídos exclusivamente por assessores certificados (como a XP)
- Têm características diferenciadas de taxa e acesso — o cliente só pode acessar via XP
- Isso reforça o vínculo com o assessor

### 10.4 FIC (Fundo de Investimento em Cotas)

A maioria dos fundos da XP é do tipo FIC — um fundo que investe em cotas de outro fundo (o "master"). Isso significa:
- Há uma camada extra de taxa (FIC + master)
- A liquidez do FIC pode ser diferente da do master
- O CNPJ do FIC (o que o cliente vê) ≠ CNPJ do master (onde o dinheiro está de verdade)

**Implicação para o cálculo:** buscar a cota do FIC no CVM, não do master.

### 10.5 D+X (prazo de liquidação)

| Ativo | Prazo para receber o dinheiro após solicitação |
|-------|-----------------------------------------------|
| Ações | D+2 (2 dias úteis) |
| Fundos DI | D+1 a D+0 |
| Fundos multimercado | D+30 a D+60 |
| Fundos de ações | D+30 a D+60 |
| CDB com vencimento | Data do vencimento (ou deságio) |
| Tesouro Direto | D+1 |

**Implicação para recomendações:** se a recomendação é "resgatar Truxt Long Bias para comprar CDB", o assessor precisa avisar que o resgate pode demorar 30–60 dias.

### 10.6 Nota sobre os dados do Albert

O portfólio mostra `Conta: 792854 | 07/05/2025` — a data de extração do extrato. Os dados de rentabilidade acumulada refletem o período desde a compra (2021–2022 até mai/2025). O CSV de rentabilidade mensal usa preços de abril/2025 vs. março/2025, portanto **a carta é do ciclo de abril/2025**.

---

## Glossário de Termos-Chave

| Termo | Definição rápida |
|-------|-----------------|
| **Alocação** | Distribuição do portfólio entre classes de ativo |
| **Alpha** | Retorno excedente em relação ao benchmark |
| **Benchmark** | Índice de referência para comparar performance |
| **Beta** | Sensibilidade do ativo ao mercado |
| **CDI** | Taxa do mercado interbancário; proxy da Selic |
| **Come-cotas** | Antecipação semestral de IR em fundos |
| **Cota** | Fração de participação em um fundo |
| **Correlação** | Grau de relação entre movimentos de dois ativos |
| **Drawdown** | Queda desde o pico histórico |
| **Duration** | Sensibilidade do título de RF à variação de juros |
| **FIA** | Fundo de Investimento em Ações |
| **FIC** | Fundo de Investimento em Cotas (investe em outros fundos) |
| **FIM** | Fundo de Investimento Multimercado |
| **FIRF** | Fundo de Investimento em Renda Fixa |
| **HAPV3** | Código da ação da Hapvida na B3 |
| **IBOVESPA** | Índice das principais ações da B3 |
| **IOF** | Imposto sobre operações financeiras |
| **IPCA** | Índice de inflação oficial do Brasil |
| **Liquidez** | Facilidade de converter ativo em dinheiro |
| **Long Bias** | Estratégia com mais posições compradas que vendidas |
| **Marcação a mercado** | Valoração pelo preço atual de venda |
| **MWR** | Money-Weighted Return — retorno efetivo do investidor |
| **Perfil de risco** | Classificação do investidor: conservador/moderado/arrojado |
| **P/L** | Preço/Lucro — múltiplo de valuation de ações |
| **Rebalanceamento** | Ajuste dos pesos para a alocação-alvo |
| **Selic** | Taxa básica de juros do Brasil |
| **Sharpe** | Retorno por unidade de risco |
| **Suitability** | Adequação do produto ao perfil regulatório do cliente |
| **TWR** | Time-Weighted Return — performance eliminando efeito de aportes |
| **Volatilidade** | Desvio padrão dos retornos; medida de risco |
