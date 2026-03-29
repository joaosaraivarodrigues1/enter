# Buy/Sell Recommendation Logic
## Fundamentos, Fontes e Algoritmo de Decisão

---

## Estrutura do documento

Cada decisão neste framework pertence a uma das quatro camadas abaixo. A camada determina o grau de autoridade da regra e o que pode ser customizado:

| Camada | Natureza | Pode alterar? |
|--------|----------|--------------|
| **1 — Regulação** | Obrigação legal (CVM, ANBIMA) | Não |
| **2 — Teoria acadêmica** | Princípios estabelecidos (Markowitz, CAPM) | Não |
| **3 — Prática de mercado** | Padrão da indústria brasileira | Com cuidado |
| **4 — Heurísticas configuráveis** | Thresholds operacionais do sistema | Sim |

---

## Camada 1 — Base Regulatória

### 1.1 Suitability — Adequação ao Perfil do Investidor

**Fonte primária:** ICVM 539/2013 — *Instrução CVM nº 539, de 13 de novembro de 2013*
> "Dispõe sobre o dever de verificação da adequação dos produtos, serviços e operações ao perfil do cliente."

**Fonte complementar:** Código ANBIMA de Regulação e Melhores Práticas para Distribuição de Produtos de Investimento (vigente)

**O que a regulação determina:**

A ICVM 539/2013 obriga toda instituição financeira a verificar, antes de qualquer recomendação, se o produto é adequado ao perfil do cliente em três dimensões:

```
Dimensão 1 — Perfil de risco
  Avalia: tolerância a perdas, experiência com investimentos, objetivos financeiros
  Resultado: classificação em conservador / moderado / arrojado / agressivo

Dimensão 2 — Horizonte de investimento
  Avalia: quando o cliente precisará dos recursos
  Resultado: curto prazo (até 2 anos) / médio (2–5 anos) / longo (> 5 anos)

Dimensão 3 — Situação financeira
  Avalia: renda, patrimônio, capacidade de absorver perdas
  Resultado: define o tamanho máximo de posições de risco
```

**Consequência regulatória direta para o sistema:**

```
REGRA HARD (não negociável):
  SE produto NOT IN categoria_permitida(perfil_cliente):
    → recomendação BLOQUEADA
    → sistema deve sugerir alternativa dentro do perfil
    → nunca recomendar ao cliente sem o aviso de inadequação

Produtos permitidos por perfil (baseado em ICVM 539 + prática XP):
  Conservador:  RF grau de investimento, fundos DI, Tesouro Direto
  Moderado:     + ações de empresas consolidadas, fundos multimercado moderados,
                  debêntures BB+ ou superior
  Arrojado:     + fundos de ações, FIIs, BDRs, derivativos com finalidade de hedge
  Agressivo:    + derivativos especulativos, fundos alavancados, ativos alternativos
```

> **Nota de atualização:** A CVM realizou reestruturação normativa em 2021–2022. Verificar no portal CVM (gov.br/cvm) se a ICVM 539/2013 foi consolidada ou substituída por resolução mais recente antes de citar em documentos formais.

---

### 1.2 Classificação de Fundos

**Fonte:** CVM Resolução 175/2022 (substituiu a ICVM 555/2014 para a maioria dos fundos)

Define as classes e subclasses de fundos e seus limites de concentração e alavancagem. Relevante para classificar corretamente cada fundo da carteira e determinar o benchmark obrigatório de comparação.

| Classe CVM 175 | Correspondência prática | Benchmark típico |
|----------------|------------------------|-----------------|
| Fundo Renda Fixa Simples | FIRF DI, Tesouro | CDI / Selic |
| Fundo Renda Fixa | FIRF com crédito privado | CDI / IMA-B |
| Fundo Multimercado | FIM livre, long/short, macro | CDI |
| Fundo de Ações | FIA, long biased | IBOVESPA / IBrA |

---

### 1.3 Tributação — IR sobre Investimentos

**Renda Fixa e Fundos RF/Multimercado:**
**Fonte:** Lei 11.033/2004 + Instrução Normativa RFB 1.585/2015

Tabela regressiva (quanto mais tempo, menos IR):

| Prazo desde a aplicação | Alíquota IR |
|------------------------|------------|
| Até 180 dias | 22,5% |
| 181 a 360 dias | 20,0% |
| 361 a 720 dias | 17,5% |
| Acima de 720 dias | 15,0% |

**Come-cotas (antecipação semestral de IR em fundos):**
**Fonte:** Lei 9.532/1997 Art. 33, modificada pela Lei 11.033/2004

```
Fundos de longo prazo (prazo médio da carteira > 365 dias):
  come-cotas = 15% sobre rendimento, em maio e novembro

Fundos de curto prazo (prazo médio ≤ 365 dias):
  come-cotas = 20% sobre rendimento, em maio e novembro

Fundos de Ações (FIA com mínimo 67% em ações):
  NÃO há come-cotas → tributação apenas no resgate, alíquota única 15%
```

**Ações — Ganho de Capital:**
**Fonte:** Lei 11.033/2004 Art. 3º + Lei 13.259/2016

```
Operações comuns (swing trade):
  Isenção: vendas totais no mês ≤ R$ 20.000
  Tributado: 15% sobre o lucro (vendas > R$ 20.000/mês)

Day trade:
  Sempre tributado: 20% sobre o lucro (sem isenção de R$ 20k)

Compensação de prejuízos:
  Prejuízo em ações pode compensar ganho em ações no mesmo mês ou meses futuros
  Prejuízo em day trade só compensa ganho em day trade
```

**Dividendos:**
**Fonte:** Lei 9.249/1995 Art. 10

```
Dividendos pagos por empresas brasileiras: ISENTOS de IR para pessoa física
JCP (Juros sobre Capital Próprio): tributados na fonte à alíquota de 15%
```

---

### 1.4 Liquidez mínima e prazos

**Fonte:** CVM Resolução 175/2022 + regulamentos específicos de cada fundo

A regulação não impõe prazos mínimos de resgate universais — cada fundo define em seu regulamento. O sistema deve respeitar os prazos declarados no regulamento do fundo (D+0 a D+360).

```
REGRA REGULATÓRIA:
  O regulamento do fundo prevalece sobre qualquer recomendação do sistema.
  Se o fundo tem liquidez D+30, a recomendação deve mencionar o prazo explicitamente.
  Não é permitido prometer liquidez imediata em ativo ilíquido.
```

---

## Camada 2 — Teoria Acadêmica

### 2.1 Teoria Moderna do Portfólio (Markowitz)

**Fonte:** Markowitz, H.M. (1952). *"Portfolio Selection."* Journal of Finance, 7(1), 77–91.

**Princípio fundamental:**

> O risco de um portfólio não é a média dos riscos individuais dos ativos — é função da correlação entre eles. Diversificar entre ativos não correlacionados reduz o risco total sem sacrificar retorno esperado.

**O que isso fundamenta no sistema:**

```
Regra de concentração:
  Um único ativo com peso muito alto aumenta o risco idiossincrático
  sem compensação em retorno esperado.
  → Base teórica para a regra: peso_ativo > 25% = flag de redução

Regra de diversificação setorial:
  LREN3 + ARZZ3 na mesma carteira (varejo de moda) = alta correlação
  → Duplica o risco sem diversificar
  → Base teórica para flag de concentração setorial

Fronteira eficiente:
  Para cada nível de risco, existe uma alocação ótima que maximiza retorno.
  O alvo de alocação por perfil (moderado = 30-50% RF, etc.) é uma
  aproximação prática da fronteira eficiente para o contexto brasileiro.
```

### 2.2 CAPM e Beta

**Fonte:** Sharpe, W.F. (1964). *"Capital Asset Prices: A Theory of Market Equilibrium under Conditions of Risk."* Journal of Finance, 19(3), 425–442.

**Princípio:**

> O retorno esperado de um ativo é função do seu beta (sensibilidade ao mercado) e do prêmio de risco de mercado. Ativo com beta > 1 amplifica movimentos do mercado.

```
retorno_esperado = taxa_livre_de_risco + beta × (retorno_mercado - taxa_livre_de_risco)

No Brasil:
  taxa_livre_de_risco = CDI (proxy da Selic)
  retorno_mercado     = retorno histórico do IBOVESPA

Implicação para o sistema:
  Fundos long biased em ciclo de Selic alta têm beta alto e taxa livre de risco alta
  → o custo de oportunidade (CDI a 15,5%) supera o prêmio esperado das ações
  → base teórica para recomendar redução de long biased quando Selic > 12%
```

### 2.3 Modelos de Fatores (Fama-French)

**Fonte:** Fama, E.F. & French, K.R. (1992). *"The Cross-Section of Expected Stock Returns."* Journal of Finance, 47(2), 427–465.

**Princípio:**

> Além do beta de mercado, retornos são explicados por fatores: tamanho da empresa (small vs. large cap), valor (book-to-market ratio) e, posteriormente, momentum, qualidade e volatilidade baixa.

```
Implicação para o sistema:
  Em ambiente de Selic alta e IPCA elevado:
    Fator valor > fator crescimento (growth stocks sofrem mais)
    → base para recomendar redução de small caps e growth em ciclo contracionista
    → favorece ações com dividendos sólidos (empresas maduras, fator valor)
```

### 2.4 Ciclos de mercado e rotação setorial

**Fonte:** Stovall, S. (1996). *"Standard & Poor's Guide to Sector Investing"* + adaptações para o mercado brasileiro (Relatórios ANBIMA, BCB Relatório de Estabilidade Financeira)

**Mapeamento ciclo de juros → setores:**

| Fase do ciclo | Selic | Setores favorecidos | Setores prejudicados |
|---------------|-------|--------------------|--------------------|
| Aperto monetário | Subindo | RF pós-fixada, bancos (spread maior), commodities exportadoras | Varejo, construção, saúde privada, crescimento |
| Pico de juros | Estável alto | RF, defensivos, dividendos | Growth, alavancados |
| Afrouxamento | Caindo | Ações em geral, imóveis, consumo | Fundos DI (rende menos) |
| Juros baixos | Estável baixo | Growth, small caps, FIIs | RF (retorno real baixo) |

> **Aplicação ao cenário atual (XP Research, fev/2025):**
> Brasil em fase de **aperto monetário** — Selic subindo para 15,5%.
> → RF pós-fixada, fundos DI e exportadores são favorecidos.
> → Varejo doméstico (LREN3, ARZZ3), saúde privada (HAPV3) e fundos long biased são prejudicados.

---

## Camada 3 — Prática de Mercado

### 3.1 Faixas de alocação por perfil

**Fonte:** ANBIMA — Segmentos de Atuação (Código de Distribuição, Anexo I) + práticas XP, BTG Pactual, Itaú Private

Estas faixas representam o padrão consolidado da indústria brasileira. Cada instituição tem sua tabela própria, mas convergem nestes intervalos:

| Classe de ativo | Conservador | Moderado | Arrojado | Agressivo |
|-----------------|-------------|---------|---------|----------|
| RF pós-fixada (CDI) | 50–80% | 20–40% | 5–15% | 0–10% |
| RF IPCA+ / prefixada | 10–30% | 10–20% | 5–10% | 0–10% |
| Multimercado baixo risco | 5–15% | 10–20% | 10–20% | 5–15% |
| Multimercado alto risco | 0% | 5–15% | 15–25% | 20–30% |
| Ações / FIA | 0–5% | 15–30% | 40–60% | 50–70% |
| Alternativos / internacionais | 0% | 0–5% | 0–10% | 0–15% |

**Como usar no sistema:**

```
Para cada classe:
  ponto_medio_alvo = (limite_inferior + limite_superior) / 2
  desvio = alocacao_atual - ponto_medio_alvo

  SE desvio > +10 p.p.: sobreallocação significativa → flag REDUZIR
  SE desvio > +5 p.p.:  sobreallocação moderada → flag ATENÇÃO
  SE desvio < -10 p.p.: suballocação significativa → flag AUMENTAR
  SE desvio < -5 p.p.:  suballocação moderada → flag ATENÇÃO
```

### 3.2 Benchmarks obrigatórios por categoria de fundo

**Fonte:** ANBIMA Código de Administração de Recursos de Terceiros + CVM Resolução 175/2022

| Categoria do fundo | Benchmark de comparação | Critério de underperformance |
|--------------------|------------------------|------------------------------|
| FIRF DI / RF Simples | CDI | Retorno < 95% do CDI no período |
| Multimercado (FIM) | CDI | Retorno < CDI no período |
| Long Biased / FIM macro | CDI ou IBOVESPA | Depende do regulamento |
| FIA (fundo de ações) | IBOVESPA ou IBrX-100 | Retorno < índice no período |
| IPCA+ / IMA-B | IMA-B (ANBIMA) | Retorno < IMA-B no período |

---

## Camada 4 — Heurísticas Configuráveis

Estes são os thresholds operacionais do sistema. São razoáveis e defensáveis, mas não têm fonte regulatória ou acadêmica única — são parâmetros que devem ser calibrados com o time de alocação da XP.

### 4.1 Thresholds de risco por ativo

```python
# Configurável — valores padrão do sistema

DRAWDOWN_CRITICO     = -0.40   # drawdown > 40% + peso > 1,5% → REDUZIR
DRAWDOWN_ALERTA      = -0.25   # drawdown > 25% + peso > 3% → ATENÇÃO
CONCENTRACAO_MAXIMA  = 0.25    # peso > 25% no portfólio total → REDUZIR
CONCENTRACAO_SETOR   = 0.35    # peso > 35% num mesmo setor → DIVERSIFICAR
POSICAO_RESIDUAL     = 0.005   # peso < 0,5% → candidato a consolidação
UNDERPERFORMANCE     = 0.80    # fundo rendendo < 80% do benchmark em 12m → AVALIAR
```

### 4.2 Thresholds de rebalanceamento

```python
# Baseado em: Vanguard Research (2015) "Best practices for portfolio rebalancing"
# + adaptação para mercado brasileiro (custo tributário mais alto)

DESVIO_REBALANCEAMENTO = 0.05  # desvio > 5 p.p. do alvo → rebalancear
FREQUENCIA_REVISAO     = 30    # dias — revisão mensal (alinhado ao relatório XP)
```

> **Referência externa:** Vanguard (2015). *"Best practices for portfolio rebalancing."*
> Demonstra que rebalanceamento por banda (threshold) supera rebalanceamento por calendário fixo,
> especialmente quando há custos de transação relevantes (como IR no Brasil).

### 4.3 Score de ação — pesos dos sinais

```python
# Pesos são configuráveis — refletem julgamento sobre importância relativa

PESO_SINAL_ALOCACAO  = 1  # desvio de alocação estratégica
PESO_SINAL_RISCO     = 2  # risco do ativo (drawdown, concentração) — peso maior
PESO_SINAL_MACRO     = 1  # alinhamento com cenário macroeconômico
```

---

## Algoritmo Completo de Decisão

### Visão geral do fluxo

```
[ENTRADA: dados do portfólio + perfil + macro + benchmarks]
        │
        ▼
[ETAPA 1: Filtro de suitability]
  → Verificar se todos os ativos são permitidos para o perfil
  → Ativos inadequados: flag imediata VENDER (regulatório)
        │
        ▼
[ETAPA 2: Cálculo de scores por ativo]
  → Sinal Tipo 1: desvio de alocação estratégica
  → Sinal Tipo 2: risco do ativo (drawdown, concentração, underperformance)
  → Sinal Tipo 3: alinhamento macro
  → Score final = Σ(peso × sinal)
        │
        ▼
[ETAPA 3: Geração de recomendações candidatas]
  → Score ≤ -2: candidato a REDUZIR ou VENDER
  → Score ≥ +2: candidato a AUMENTAR ou COMPRAR
        │
        ▼
[ETAPA 4: Validação de restrições práticas]
  → Liquidez: verificar prazo de resgate
  → IR: calcular custo tributário da operação
  → Benefício líquido: o ganho da realocação supera o custo do IR?
        │
        ▼
[ETAPA 5: Priorização e destino]
  → Ordenar por urgência (score + magnitude do desvio)
  → Para cada venda: definir ativo substituto dentro do perfil
  → Verificar se o substituto também passa no filtro de suitability
        │
        ▼
[SAÍDA: array JSON de recomendações estruturadas → LLM para narrativa]
```

---

### Etapa 1 — Filtro de suitability (regulatório)

```python
def filtro_suitability(ativo, perfil_cliente):
    """
    Base: ICVM 539/2013
    Retorna True se o ativo é adequado, False se não é.
    """
    matriz_suitability = {
        "conservador":  ["RF_grau_investimento", "fundo_DI", "tesouro_direto"],
        "moderado":     ["RF_grau_investimento", "fundo_DI", "tesouro_direto",
                         "acoes_consolidadas", "fundo_multimercado_moderado",
                         "debentures_BB_mais"],
        "arrojado":     [...todos_acima..., "FIA", "FII", "BDR",
                         "derivativos_hedge"],
        "agressivo":    [...todos_acima..., "derivativos_especulativos",
                         "fundos_alavancados", "alternativos"]
    }
    return ativo.categoria in matriz_suitability[perfil_cliente]

# Se False: recomendação automática de VENDER, independente de qualquer score
```

---

### Etapa 2 — Cálculo de score por ativo

```python
def calcular_score(ativo, portfolio, perfil, macro):
    score = 0

    # --- SINAL TIPO 1: Desvio de alocação (peso = 1) ---
    desvio_classe = portfolio.alocacao_atual[ativo.classe] - perfil.alvo_medio[ativo.classe]

    if desvio_classe > 0.10:    score -= 1  # classe sobreallocada
    elif desvio_classe < -0.10: score += 1  # classe suballocada
    # Entre -5% e +5%: neutro (sem sinal)

    # --- SINAL TIPO 2: Risco do ativo (peso = 2) ---

    # 2a. Drawdown profundo
    if ativo.drawdown_acumulado < -DRAWDOWN_CRITICO and ativo.peso > 0.015:
        score -= 2
    elif ativo.drawdown_acumulado < -DRAWDOWN_ALERTA and ativo.peso > 0.03:
        score -= 1

    # 2b. Performance positiva sólida
    if ativo.retorno_acumulado > 0.15 and ativo.drawdown_max > -0.10:
        score += 1

    # 2c. Concentração excessiva
    if ativo.peso > CONCENTRACAO_MAXIMA:
        score -= 1

    # 2d. Posição residual
    if ativo.peso < POSICAO_RESIDUAL:
        score -= 1  # candidato a consolidação

    # 2e. Fundo com underperformance sistemática
    if (ativo.tipo == "fundo"
        and ativo.retorno_12m < ativo.benchmark_12m * UNDERPERFORMANCE):
        score -= 1

    # --- SINAL TIPO 3: Alinhamento macro (peso = 1) ---
    macro_score = avaliar_macro(ativo, macro)  # ver Etapa 2a abaixo
    score += macro_score

    return score


def avaliar_macro(ativo, macro):
    """
    Base: teoria de ciclos de mercado (Stovall 1996) +
          mapeamento setorial (BCB Relatório de Estabilidade Financeira)
    """
    score = 0

    # Selic em alta
    if macro.selic_tendencia == "alta":
        if ativo.categoria in ["RF_posFixada", "fundo_DI", "RF_IPCA_mais"]:
            score += 1
        if ativo.categoria in ["acoes_varejo", "acoes_crescimento", "long_biased"]:
            score -= 1

    # IPCA alto
    if macro.ipca_anual > 0.05:
        if ativo.categoria == "RF_IPCA_mais":
            score += 1
        if ativo.setor in ["varejo_discricionario", "saude_privada"]:
            score -= 1

    # Câmbio depreciado (BRL fraco)
    if macro.usd_brl > 5.50:
        if ativo.perfil == "exportador":
            score += 1
        if ativo.perfil == "importador":
            score -= 1

    # PIB desacelerando
    if macro.pib_crescimento < 0.02:
        if ativo.setor in ["varejo_discricionario", "construcao_civil"]:
            score -= 1
        if ativo.categoria in ["RF_posFixada", "defensivos"]:
            score += 1

    return max(-1, min(1, score))  # limitado a -1/+1 por ativo
```

---

### Etapa 3 — Tabela de decisão

| Score | Ação | Urgência | Descrição |
|-------|------|----------|-----------|
| +3 | COMPRAR | Alta | Todos os sinais positivos — alocar imediatamente |
| +2 | AUMENTAR | Média | Forte sinal de compra — incrementar posição |
| +1 | MANTER (viés +) | Baixa | Ligeiramente favorável — monitorar oportunidade |
| 0 | MANTER | Nenhuma | Posição equilibrada — sem ação necessária |
| -1 | MANTER (viés −) | Baixa | Início de deterioração — atenção próximo mês |
| -2 | REDUZIR | Média | Sinal claro de redução — diminuir exposição |
| -3 | VENDER | Alta | Múltiplos sinais negativos — sair da posição |

---

### Etapa 4 — Validação de restrições práticas

```python
def validar_restricoes(recomendacao, ativo, portfolio):
    resultado = {
        "acao_validada": recomendacao.acao,
        "restricoes": [],
        "ajustes": []
    }

    # --- LIQUIDEZ ---
    if recomendacao.acao in ["VENDER", "REDUZIR"]:
        if ativo.prazo_resgate_dias > 0:
            resultado["restricoes"].append(
                f"Liquidez: resgate disponível em D+{ativo.prazo_resgate_dias}"
            )
            resultado["ajustes"].append(
                f"Iniciar processo de resgate hoje; valor disponível em ~{ativo.prazo_resgate_dias} dias"
            )

    # --- IMPOSTO DE RENDA ---
    if recomendacao.acao in ["VENDER", "REDUZIR"]:
        ganho = ativo.valor_atual - ativo.valor_aplicado

        if ganho > 0:
            aliquota = calcular_aliquota(ativo)  # tabela regressiva Lei 11.033/2004
            ir_estimado = ganho * aliquota

            # Custo de oportunidade: quanto tempo para o CDI recuperar o IR pago?
            meses_para_recuperar = ir_estimado / (portfolio.valor_total * macro.cdi_mes)

            resultado["restricoes"].append(
                f"IR estimado: R$ {ir_estimado:.2f} (alíquota {aliquota*100:.1f}%)"
            )
            resultado["ajustes"].append(
                f"CDI recupera o custo tributário em ~{meses_para_recuperar:.1f} meses"
            )

        elif ganho < 0:
            resultado["ajustes"].append(
                "Venda com prejuízo: sem IR + prejuízo pode compensar ganhos futuros"
            )

    # --- ISENÇÃO DE IR EM AÇÕES ---
    if ativo.tipo == "acao" and recomendacao.acao in ["VENDER", "REDUZIR"]:
        if portfolio.total_vendas_acoes_mes + ativo.valor_atual <= 20000:
            resultado["ajustes"].append(
                "Venda total de ações no mês ≤ R$20.000 → isento de IR (Lei 11.033/2004 Art. 3º)"
            )

    return resultado
```

---

### Etapa 5 — Destino sugerido (para cada venda, qual substituto)

```python
def sugerir_substituto(ativo_vendido, perfil, macro):
    """
    Regra: o substituto deve ter score ≥ +2 e passar no filtro de suitability.
    """
    # Mapeamento padrão de realocação por contexto macro + perfil
    mapa_substitutos = {
        # De: ativo com sinal negativo → Para: alternativa dentro do perfil
        ("acoes_varejo",    "moderado", "selic_alta"): "CDB_posFixado_ou_IPCA_mais",
        ("long_biased",     "moderado", "selic_alta"): "fundo_DI_credito_privado",
        ("acoes_saude",     "moderado", "selic_alta"): "Tesouro_IPCA_mais",
        ("FIA_qualquer",    "moderado", "selic_alta"): "fundo_DI_ou_RF_simples",
        ("posicao_residual","qualquer", "qualquer"):   "consolidar_em_maior_posicao_existente"
    }

    chave = (ativo_vendido.categoria, perfil.tipo, macro.regime_selic)
    substituto = mapa_substitutos.get(chave, "fundo_DI")  # default: fundo DI

    # Verificar suitability do substituto
    if not filtro_suitability(substituto, perfil):
        substituto = "CDB_grau_investimento"  # fallback conservador sempre permitido

    return substituto
```

---

## Cobertura de casos — Revisão completa

### Casos cobertos pelo algoritmo

| Caso | Como é tratado | Etapa |
|------|---------------|-------|
| Ativo fora do perfil regulatório | Flag VENDER obrigatório | Etapa 1 |
| Drawdown profundo (> 40%) | Score -2, candidato a vender | Etapa 2 |
| Drawdown moderado (> 25%) | Score -1, alerta | Etapa 2 |
| Concentração excessiva (> 25%) | Score -1, reduzir | Etapa 2 |
| Concentração setorial | Flag separado, verificação de correlação | Etapa 2 |
| Posição residual (< 0,5%) | Score -1, consolidar | Etapa 2 |
| Fundo com underperformance | Score -1, avaliar substituição | Etapa 2 |
| Classe suballocada | Score +1, candidato a compra | Etapa 2 |
| Classe sobreallocada | Score -1, candidato a redução | Etapa 2 |
| Macro desfavorável ao setor | Score -1 | Etapa 2 |
| Macro favorável ao setor | Score +1 | Etapa 2 |
| Ativo ilíquido (D+30+) | Ajuste de prazo na recomendação | Etapa 4 |
| Venda com ganho (IR) | Cálculo de custo e payback | Etapa 4 |
| Venda com prejuízo | Destaque de isenção + compensação futura | Etapa 4 |
| Isenção de IR < R$20k/mês em ações | Verificação automática | Etapa 4 |
| Substituição dentro do perfil | Mapa de substitutos + validação suitability | Etapa 5 |

### Casos não cobertos (limitações do MVP)

| Caso | Limitação | Como endereçar futuramente |
|------|-----------|---------------------------|
| **Ativos fora da XP** (imóveis, previdência externa) | Sistema só vê o que está no extrato XP | Input manual de patrimônio total |
| **VGBL / PGBL** (previdência privada) | Tributação diferente (tabela regressiva OU progressiva) | Módulo separado de previdência |
| **FIIs** (fundos imobiliários) | Lógica de dividendos mensais + isenção IR para PF | Adicionar categoria FII ao score |
| **BDRs e ações internacionais** | Tributação em dólar, variação cambial no retorno | Módulo de ativos dolarizados |
| **COEs** (Certificados de Operações Estruturadas) | Produto complexo com barreira de capital | Requer análise específica do payoff |
| **Eventos corporativos** (split, grupamento, bonificação) | Afeta preço médio e quantidade sem ser "retorno" | Ajuste automático ao detectar variação >50% de preço |
| **Mudança de perfil do cliente** | Sistema usa perfil fixo do extrato | Trigger manual ao atualizar perfil |
| **Come-cotas em maio/novembro** | Redução de cotas sem ser resgate | Aviso automático no mês do come-cotas |
| **Fundos em liquidação** | Fundo fechado para resgates | Flag de alerta + prazo estimado |
| **Circuit breaker** / halt de negociação | Preço inválido no dia | Fallback para último preço válido |

---

## Estrutura de saída para o LLM

```json
[
  {
    "ativo": "HAPV3",
    "acao": "VENDER",
    "urgencia": "ALTA",
    "score": -3,
    "score_detalhe": {
      "sinal_alocacao": 0,
      "sinal_risco": -2,
      "sinal_macro": -1
    },
    "gatilhos": [
      "Drawdown acumulado: -74,58% (limiar: -40%)",
      "Setor saúde desfavorecido por Selic 15,5% e controle ANS"
    ],
    "restricoes": {
      "liquidez": "D+2 — sem restrição",
      "ir": "Venda com prejuízo acumulado — sem incidência de IR",
      "suitability": "Aprovado para perfil moderado"
    },
    "substituto_sugerido": "Tesouro IPCA+ 2029 ou CDB IPCA+",
    "valor_envolvido_brl": 6143.14,
    "peso_portfolio": 0.0197
  }
]
```

**Prompt base para o LLM (Subgraph 4 — Recommendation Engine):**

```
You are a senior financial advisor at XP Investimentos writing a monthly report section in Brazilian Portuguese.

CLIENT PROFILE: [perfil]
MACRO CONTEXT: [resumo macro — XP Research + Itaú BBA]
RECOMMENDATIONS (generated by rules engine): [JSON acima]

Instructions:
- Write 2–3 paragraphs in Brazilian Portuguese, professional but warm tone
- Explain each recommendation in plain language
- Connect each recommendation to the macro context and the client's risk profile
- For sell recommendations: always explain what the proceeds will be invested in
- Quantify expected benefit where possible (e.g., "ao realocar para CDB com Selic a 15,5%...")
- Never invent data not present in the inputs
- Never recommend products outside the client's suitability profile
- Never make promises about future returns
- Mention tax implications only when material (IR > R$500 or IR = 0 when client might assume otherwise)
```

---

## Fontes consolidadas

| Elemento | Fonte | Tipo |
|----------|-------|------|
| Suitability obrigatória | ICVM 539/2013 (CVM) | Regulação |
| Classificação de fundos | CVM Resolução 175/2022 | Regulação |
| IR tabela regressiva RF | Lei 11.033/2004 + IN RFB 1.585/2015 | Legislação |
| Come-cotas | Lei 9.532/1997 Art. 33 | Legislação |
| IR ações — isenção R$20k | Lei 11.033/2004 Art. 3º | Legislação |
| Dividendos isentos | Lei 9.249/1995 Art. 10 | Legislação |
| IR ações — ganho de capital | Lei 13.259/2016 | Legislação |
| Teoria do portfólio | Markowitz (1952), Journal of Finance | Acadêmica |
| CAPM e beta | Sharpe (1964), Journal of Finance | Acadêmica |
| Modelos de fatores | Fama & French (1992), Journal of Finance | Acadêmica |
| Rotação setorial por ciclo | Stovall (1996), S&P Guide to Sector Investing | Acadêmica |
| Faixas de alocação por perfil | ANBIMA Código de Distribuição + prática de mercado | Indústria |
| Benchmarks por categoria | ANBIMA Código de Adm. de Recursos de Terceiros | Indústria |
| Rebalanceamento por banda | Vanguard Research (2015) | Indústria |
| Thresholds (drawdown, concentração) | Heurísticas configuráveis — calibrar com mesa XP | Sistema |
