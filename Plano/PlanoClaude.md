# Plano — AI Financial Advisor para XP

---

## 1. Diagnóstico: O que está errado no MVP atual

### Problemas identificados na output_letter.md

| # | Problema | Evidência |
|---|----------|-----------|
| 1 | **Rentabilidade inventada** | A carta diz "retorno total de 3,5%" mas não há cálculo — o CSV de rentabilidade está marcado como WIP e incompleto |
| 2 | **Dados macro desatualizados** | A carta projeta Selic em 9% e cortes do Fed em julho. A análise macro real da XP (fev/2025) projeta Selic terminal em 15,50% |
| 3 | **Nenhuma recomendação de compra/venda** | A carta diz "não realizamos realocações significativas" sem justificativa baseada em dados |
| 4 | **Sem análise de risco vs. perfil** | Albert é moderado, mas tem 74,58% de queda em HAPV3 e 41,7% em LREN3 — isso não é discutido |
| 5 | **Formatação manual** | A carta é um Markdown simples, sem estrutura profissional, sem assinatura visual, não está pronta para envio |
| 6 | **Sem benchmark** | A performance não é comparada a CDI, IBOVESPA ou IPCA — impossível saber se 3,5% é bom ou ruim |

---

## 2. Dados — O que temos e o que precisamos gerar

### O que já temos (1 cliente)
- **Portfólio Albert**: 4 ações + 7 fundos + 1 CDB — R$312k investidos
- **Perfil de risco**: Moderado
- **Análise macro XP**: fev/2025 (Selic 15,5%, IPCA 6,1%, USD/BRL 6,20, PIB 2,0%)
- **CSV de rentabilidade**: preços atual e do mês anterior para 12 ações (incompleto — falta fundos e renda fixa)

### O que precisamos gerar (para demonstrar escala)

**3 clientes sintéticos adicionais** com perfis contrastantes:

| Cliente | Perfil | Foco do portfólio | Patrimônio |
|---------|--------|-------------------|------------|
| **Mariana Costa** | Conservador | 70% renda fixa (Tesouro IPCA+, CDBs), 20% fundos multimercado baixo risco, 10% ações defensivas | R$180k |
| **Rafael Mendes** | Arrojado | 60% ações (growth + small caps), 30% fundos long biased, 10% cripto/alternativos | R$450k |
| **Lucia Ferreira** | Moderado | Similar a Albert mas com mais renda fixa — útil para testar personalização dentro do mesmo perfil | R$220k |

**Dados de benchmark a incluir:**
- CDI do mês (via API Banco Central — endpoint: `/dadosSeriesTemporais/metadados/series/12`)
- IBOVESPA do mês (via `brapi.dev/api/quote/^BVSP`)
- IPCA acumulado 12 meses (via API IBGE SIDRA)

**Dados de fundos a completar:**
- O CSV atual tem apenas ações. Precisamos adicionar rentabilidade mensal dos 7 fundos de Albert. Fonte: informe mensal CVM (dados públicos) ou valor fixo sintético para o MVP.

---

## 3. Arquitetura Rivet — Visão geral do grafo

O workflow é composto por **5 subgraphs** conectados em sequência:

```
[INPUT: cliente_id]
        │
        ▼
[Subgraph 1: Data Loader]
   Carrega portfólio, perfil de risco e macro analysis do cliente
        │
        ▼
[Subgraph 2: Profitability Engine]
   Calcula rentabilidade real de cada posição, ponderada pela alocação
   Compara com CDI, IBOV, IPCA
        │
        ▼
[Subgraph 3: Risk & Fit Analyzer]
   Verifica se a carteira atual está alinhada com o perfil de risco
   Identifica posições problemáticas (drawdown excessivo, descasamento de perfil)
        │
        ▼
[Subgraph 4: Recommendation Engine]
   Gera recomendações específicas de compra/venda com justificativa macro
        │
        ▼
[Subgraph 5: Letter Generator]
   Monta a carta em português, formatada profissionalmente
        │
        ▼
[OUTPUT: carta_mensal.html / .pdf]
```

### Detalhamento de cada subgraph

#### Subgraph 1 — Data Loader
- **Input node**: recebe `cliente_id`
- **Extract node** (ou código JS): lê o arquivo de portfólio do cliente e o perfil de risco
- **HTTP Request node**: faz chamada às APIs (BCB, IBGE, brapi.dev) para pegar CDI, IPCA e IBOV do mês
- **Output**: objeto estruturado `{portfolio, risk_profile, macro, benchmarks}`

#### Subgraph 2 — Profitability Engine
- **Code node (JavaScript)**:
  ```javascript
  // Para cada posição:
  // retorno_posição = (preco_atual - preco_anterior) / preco_anterior
  // contribuição = retorno_posição × peso_alocação
  // retorno_carteira = Σ contribuições
  // excesso_retorno = retorno_carteira - CDI_mes
  ```
- Calcula rentabilidade ponderada real (não inventada)
- Identifica os 3 maiores contribuidores positivos e negativos
- Compara vs. CDI, IBOV e IPCA
- **Output**: objeto `{retorno_total, vs_cdi, vs_ibov, top_contrib, worst_contrib}`

#### Subgraph 3 — Risk & Fit Analyzer
- **LLM node** com prompt estruturado em inglês:
  ```
  You are a risk analyst. Given this portfolio and this risk profile:
  1. List positions that are misaligned with the risk profile
  2. Flag positions with drawdown > 30% that represent > 2% of the portfolio
  3. Assess if the current allocation (stocks/funds/fixed income %) matches
     the recommended range for a [PROFILE] investor
  Output JSON: {misaligned_positions, flagged_drawdowns, allocation_assessment}
  ```
- **Output**: diagnóstico estruturado de risco

#### Subgraph 4 — Recommendation Engine
- **LLM node** com contexto completo (rentabilidade + risco + macro):
  ```
  You are a financial advisor at XP. Based on:
  - Portfolio performance: [DATA]
  - Risk diagnostics: [DATA]
  - Macro outlook (XP Research, Feb 2025): [DATA]

  Generate 2-3 specific buy/sell recommendations. For each:
  - Asset name
  - Action: BUY / SELL / REDUCE / MAINTAIN
  - Rationale (2 sentences max, tied to macro or risk fit)
  - Urgency: HIGH / MEDIUM / LOW

  Output JSON array.
  ```
- **Output**: array de recomendações estruturadas

#### Subgraph 5 — Letter Generator
- **LLM node** que converte todos os dados em carta narrativa (português, tom consultivo)
- **Code node (JS ou Python)**: aplica template HTML com CSS inline para formatação profissional
- Template inclui: cabeçalho XP, seções nomeadas, tabela de performance, caixa de recomendações destacada, rodapé com assessor
- Exporta como HTML pronto para PDF via `wkhtmltopdf` ou Puppeteer (script externo chamado pelo Rivet via External Call node)

---

## 4. Implementação das 3 melhorias (abordagem combinada)

### Melhoria 1 — Cálculo de Rentabilidade Real
**O que fazer:**
1. Completar o CSV com colunas faltando: `quantity`, `weight`, `fund_monthly_return`
2. No Code node do Subgraph 2, calcular retorno ponderado por ativo
3. Buscar CDI e IBOV via API no mesmo nó ou em HTTP node separado
4. Apresentar como: retorno total + tabela por classe de ativo + gráfico de barras (SVG inline no HTML)

**Dado de entrada novo necessário:** preço/cota de fundos no mês anterior (gerar sintético para MVP, substituir por CVM nos próximos ciclos)

### Melhoria 2 — Lógica de Compra/Venda
**O que fazer:**
1. Criar regras baseadas em dados (não só LLM):
   - Se drawdown > 40% E peso > 1.5% → flag para redução
   - Se ação caiu mas setor macro favorável → flag para manutenção com alerta
   - Se posição em renda fixa < target do perfil → flag para aumento
2. Combinar essas regras com o LLM do Subgraph 4 para gerar texto justificado
3. Resultado: recomendações com lógica auditável, não apenas "intuição" do modelo

**Exemplo para Albert:**
- HAPV3: REDUZIR — queda de 74,58%, setor de saúde sob pressão com Selic alta. Peso atual (1.97%) próximo ao limiar.
- LREN3: MANTER com atenção — queda de 41,7% mas empresa sólida; macro sugere consumo fraco em 2025.
- Renda Fixa: AUMENTAR — Selic em 15,5% favorece CDBs e Tesouro IPCA+; perfil moderado suberepresentado em RF.

### Melhoria 3 — Formatação Automatizada
**O que fazer:**
1. Letter Generator produz HTML com template profissional (logo XP, fonte serifada, paleta azul/branco)
2. Script Python externo (`render_pdf.py`) usa Playwright ou WeasyPrint para converter HTML → PDF
3. Rivet chama o script via External Call node, passando o HTML como stdin
4. Output final: arquivo `carta_[cliente]_[mes_ano].pdf` pronto para envio

---

## 5. Automação e escala — Como roda sozinho no tempo

### Ciclo mensal automatizado

```
[Scheduler: 1º dia útil do mês]
        │
        ▼
[Script: data_refresh.py]
   Atualiza CSV de preços via API (brapi.dev)
   Atualiza macro analysis via scraping ou upload manual
        │
        ▼
[Rivet: batch_processor subgraph]
   Loop sobre lista de clientes (JSON array)
   Para cada cliente → executa o grafo principal → salva PDF
        │
        ▼
[Script: send_emails.py]
   Lê PDFs gerados
   Envia por e-mail via SendGrid ou SMTP com personalização por cliente
```

### Como processar múltiplos clientes no Rivet
- Criar um **Loop subgraph**: recebe array de `cliente_ids`, itera, chama o grafo principal, coleta outputs
- O Rivet suporta loops nativos com `Array node` + `Loop controller`
- Alternativa mais robusta: Python script que chama a Rivet API em batch (se Rivet expõe API de execução)

### Fontes de dados a integrar no futuro
| Dado | Fonte | Frequência |
|------|-------|------------|
| Preços de ações | brapi.dev (gratuito) ou B3 oficial | Diária |
| Cotas de fundos | CVM — informe diário de fundos (público) | Diária |
| CDI, IPCA, Selic | Banco Central do Brasil API (gratuito) | Mensal |
| IBOVESPA | brapi.dev | Mensal |
| Macro analysis XP | Upload manual pelo assessor (PDF) | Mensal |

---

## 6. Dados sintéticos — O que gerar agora

Para demonstrar que o sistema funciona com múltiplos clientes, criar os seguintes arquivos:

### `/Input/clients/mariana_portfolio.json`
```json
{
  "name": "Mariana Costa",
  "profile": "conservador",
  "total_invested": 180000,
  "allocation": {
    "renda_fixa": 0.70,
    "fundos_multimercado": 0.20,
    "acoes": 0.10
  },
  "positions": [
    {"asset": "Tesouro IPCA+ 2029", "value": 72000, "return_monthly": 0.012},
    {"asset": "CDB Itaú 120% CDI", "value": 54000, "return_monthly": 0.0098},
    {"asset": "Verde AM FIC FIM", "value": 36000, "return_monthly": 0.008},
    {"asset": "ITUB4", "value": 9000, "return_monthly": 0.033},
    {"asset": "BBAS3", "value": 9000, "return_monthly": 0.051}
  ]
}
```

### `/Input/clients/rafael_portfolio.json`
Perfil arrojado — 60% ações growth, 30% fundos long biased, 10% alternativos. Criar estrutura equivalente.

### `/Input/risk_profiles/conservador.txt`
Descrever: aversão a perdas, horizonte curto/médio, prioriza preservação de capital, produtos: Tesouro Selic, CDBs, fundos DI.

### `/Input/risk_profiles/arrojado.txt`
Descrever: tolerância alta a volatilidade, horizonte longo, busca retorno acima do mercado, produtos: ações, fundos de ações, derivativos simples.

### `/Input/macro/macro_conservador_scenario.txt`
Cenário alternativo para testar robustez: "E se o dólar subir para R$7,00?" — serve para demonstrar que o sistema pode adaptar recomendações por cenário.

---

## 7. Entregáveis finais

| Entregável | Formato | Status |
|------------|---------|--------|
| Rivet workflow revisado | `.rivet-project` | A fazer |
| 3 cartas mensais (Albert, Mariana, Rafael) | `.pdf` em português | A fazer |
| Relatório de análise do MVP | `.md` / `.pdf`, máx 2 páginas | A fazer |
| Scripts de suporte | `profitability.js`, `render_pdf.py`, `data_refresh.py` | A fazer |
| Dados sintéticos de input | JSONs + TXTs em `/Input/clients/` | A fazer |

### Estrutura de arquivos do projeto
```
Documentos/
├── README.md
├── enter_challenge.rivet-project   ← workflow revisado
├── Input/
│   ├── XP - Albert_s portfolio.txt
│   ├── XP - Albert_s risk profile.txt
│   ├── XP - Macro analysis.txt
│   ├── profitability_calc_wip.csv  ← completar
│   └── clients/
│       ├── mariana_portfolio.json  ← criar
│       └── rafael_portfolio.json   ← criar
├── Output/
│   ├── output_letter.md            ← versão original
│   ├── albert_carta_abril2025.pdf  ← nova versão
│   ├── mariana_carta_abril2025.pdf ← nova versão
│   └── rafael_carta_abril2025.pdf  ← nova versão
└── scripts/
    ├── profitability.js
    ├── render_pdf.py
    └── data_refresh.py
```

---

## 8. Respostas preparadas para a reunião com a XP

**P1: Quais são os principais problemas da primeira versão?**
Três críticos: (1) rentabilidade inventada — sem cálculo real; (2) dados macro errados — Selic a 9% quando está a 15,5%; (3) sem recomendações de compra/venda acionáveis — a carta não ajuda o cliente a tomar decisão alguma.

**P2: Como você decidiu sua abordagem?**
Priorizei as 3 áreas simultaneamente porque são interdependentes: sem cálculo correto de rentabilidade, não há base para recomendar compra/venda; sem formatação automatizada, o sistema não escala. A escolha de Python + Rivet segue a diretriz do desafio de combinar código e prompt engineering.

**P3: O que você faria com um mês inteiro?**
- Integração real com APIs da B3 e CVM para dados de cotas de fundos
- Painel web para o assessor: ver todas as cartas geradas, aprovar/editar antes do envio
- Módulo de backtesting: mostrar ao cliente como sua carteira teria performado em cenários históricos (ex: COVID-19, crise de 2015)
- Envio automático via WhatsApp Business API (preferência do cliente médio brasileiro)
- Fine-tuning de prompt por segmento: conservador vs. arrojado precisa de tom diferente
- Guardrails: validação automática para evitar que o modelo invente números ou recomende produtos fora do perfil regulatório

---

## Ordem de execução (sprint de 1 dia)

1. **[2h]** Gerar dados sintéticos (2 clientes + 2 perfis + 1 macro alternativo)
2. **[1h]** Completar CSV de rentabilidade (adicionar fundos e renda fixa com valores sintéticos)
3. **[3h]** Construir os 5 subgraphs no Rivet — começar pelo Data Loader e Profitability Engine
4. **[2h]** Implementar Recommendation Engine com regras + LLM
5. **[1h]** Criar template HTML e script render_pdf.py
6. **[1h]** Rodar para os 3 clientes, revisar outputs, ajustar prompts
7. **[1h]** Escrever relatório de análise (2 páginas)
