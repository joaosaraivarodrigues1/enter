# Fontes de Mercado — AI Financial Advisor XP

---

## Resumo de Implementação

O README pede um workflow que processe, para cada cliente:
1. Performance da carteira no mês
2. Impacto do cenário macro na carteira
3. Recomendações alinhadas ao perfil de risco e ao research da XP

O input atual cobre apenas um cliente (Albert) com dados parciais. Para o sistema funcionar com múltiplos clientes e de forma autônoma, as fontes abaixo preenchem três lacunas concretas:

| Lacuna | Impacto no output atual | Fonte que resolve |
|--------|------------------------|-------------------|
| Rentabilidade inventada (3,5% sem cálculo) | Carta não tem credibilidade | brapi.dev + CVM via brasa |
| Macro desatualizada (Selic 9% vs. real 15,5%) | Análise e recomendações erradas | BCB API + Itaú BBA / BBVA Research |
| Sem benchmark para comparar performance | Cliente não sabe se foi bem ou mal | BCB API (CDI) + brapi.dev (IBOV) |
| Recomendações genéricas sem base | Não ajuda o cliente a decidir | ANBIMA Boletim + contexto macro dos bancos |

**Estratégia de implementação:**
- Fontes com API → integrar como HTTP Request nodes no Rivet (automático)
- Fontes em PDF → alimentar como documentos de input para o LLM node (manual mensal)
- Fontes com scraping complexo → usar scripts Python externos chamados pelo Rivet via External Call node

**Prioridade de implementação:**

| Prioridade | Fonte | Razão |
|------------|-------|-------|
| 1 — Crítico | BCB API | Selic e CDI são benchmark obrigatório para qualquer carta de performance |
| 2 — Crítico | brapi.dev | Sem preços reais não há cálculo de rentabilidade |
| 3 — Alta | CVM via brasa | Cotas dos fundos da carteira do Albert estão faltando no CSV |
| 4 — Alta | ANBIMA Boletim PDF | Contextualiza performance dos fundos dentro da indústria |
| 5 — Média | Itaú BBA / BBVA Research PDF | Segundo relatório macro para triangular visão da XP Research |
| 6 — Baixa | Alpha Vantage / Twelve Data | Fallback para o brapi.dev |

---

## Fontes — Catálogo Completo

---

### Categoria 1 — Macro Brasileira

---

#### Banco Central do Brasil (BCB API)

**O que fornece:** Selic, IPCA, câmbio (USD/BRL), expectativas de mercado (Focus), histórico de política monetária
**Formato:** REST API JSON, gratuita, sem chave de autenticação necessária
**Custo:** Gratuito
**URL base:** `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados`

**Séries mais relevantes para o projeto:**

| Código | Série | Uso na carta |
|--------|-------|--------------|
| 12 | CDI acumulado mensal | Benchmark de performance da carteira |
| 433 | IPCA mensal | Contexto inflacionário; comparar com retorno real |
| 1 | Taxa Selic diária | Cenário macro; impacto em renda fixa |
| 10813 | USD/BRL (câmbio) | Impacto em ativos dolarizados |
| 13522 | Expectativas Focus — Selic | Forward guidance para recomendações |

**Por que usar:** É a fonte oficial. Qualquer número de Selic ou CDI citado na carta precisa vir daqui para ter credibilidade perante um assessor XP. Não exige cadastro, responde em JSON limpo.

**Plano de implementação:**
1. Criar HTTP Request node no Rivet (Subgraph 1 — Data Loader) para cada série necessária
2. Parâmetros: `dataInicial=01/MM/AAAA&dataFinal=31/MM/AAAA&formato=json`
3. Code node JS extrai o último valor do array retornado
4. Output: objeto `{cdi_mes, ipca_mes, selic_atual, usd_brl}`
5. Esse objeto alimenta o Subgraph 2 (Profitability Engine) e o Subgraph 4 (Recommendation Engine)

**Exemplo de chamada:**
```
GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?dataInicial=01/03/2025&dataFinal=31/03/2025&formato=json
```

---

#### Trading Economics

**O que fornece:** Projeções de consenso de mercado (onde analistas esperam Selic, IPCA, PIB nos próximos trimestres), dashboard visual
**Formato:** Web dashboard; CSV via plano pago; dados básicos gratuitos na interface
**Custo:** Gratuito (limitado) / Premium para API
**URL:** `https://tradingeconomics.com/brazil/indicators`

**Por que usar:** Complementa o BCB com a visão prospectiva do mercado — o que os analistas esperam, não só o que aconteceu. Útil para a seção de cenário macro da carta.

**Plano de implementação:**
- Para o MVP: acessar manualmente e copiar as projeções de consenso para um arquivo `macro_consenso.txt` que serve como input do LLM
- Para versão futura: assinar o plano de API e integrar via HTTP Request node no Rivet
- Frequência: mensal, antes de rodar o workflow

---

#### FRED (Federal Reserve Economic Data)

**O que fornece:** Mais de 1.200 séries econômicas do Brasil com histórico longo, incluindo PIB, inflação, taxa de câmbio, dados do BCB reexportados
**Formato:** CSV download, API JSON gratuita com chave
**Custo:** Gratuito (requer cadastro para chave de API)
**URL:** `https://fred.stlouisfed.org/tags/series?t=brazil`

**Por que usar:** Ideal para análises de tendência histórica (ex: "sua carteira teria performado assim nos últimos 5 anos"). A API é estável e bem documentada. Complementa o BCB com séries mais longas e formatação mais limpa.

**Plano de implementação:**
1. Criar conta e obter chave de API gratuita em `fred.stlouisfed.org`
2. HTTP Request node no Rivet: `https://api.stlouisfed.org/fred/series/observations?series_id=BRACPIALLMINMEI&api_key={KEY}&file_type=json`
3. Usar principalmente para contexto histórico na seção macro da carta
4. Frequência: mensal, em paralelo com o BCB

---

### Categoria 2 — Preços de Ativos (Ações e Índices)

---

#### brapi.dev

**O que fornece:** Cotações em tempo real e histórico de preços (OHLCV) para ações, FIIs, ETFs e índices da B3; dividendos; dados fundamentalistas básicos
**Formato:** REST API JSON
**Custo:** Gratuito (com limites de requisição); plano pago para volume maior
**URL:** `https://brapi.dev/api/quote/{ticker}`

**Por que usar:** É a solução mais direta para atualizar automaticamente o CSV de rentabilidade do Albert. Cobre todos os ativos da carteira (LREN3, MRFG3, ARZZ3, HAPV3) e os benchmarks (^BVSP para IBOVESPA). Não requer contrato comercial.

**Plano de implementação:**
1. Script Python `data_refresh.py`:
   ```python
   import requests, csv
   tickers = ["LREN3", "MRFG3", "ARZZ3", "HAPV3", "^BVSP"]
   for ticker in tickers:
       r = requests.get(f"https://brapi.dev/api/quote/{ticker}")
       # extrai regularPrice e previousClose
       # atualiza profitability_calc.csv
   ```
2. Rivet chama `data_refresh.py` via External Call node no início do workflow
3. O CSV atualizado é lido pelo Subgraph 2 (Profitability Engine)
4. Para IBOVESPA: usar ticker `^BVSP` — retorno do mês serve como benchmark de renda variável

**Séries de interesse:**

| Ticker | Uso |
|--------|-----|
| LREN3, MRFG3, ARZZ3, HAPV3 | Ações do portfólio do Albert |
| ^BVSP | Benchmark de renda variável (IBOVESPA) |
| ITUB4, BBAS3 (etc.) | Ações dos clientes sintéticos |

---

#### Alpha Vantage

**O que fornece:** Preços OHLCV ajustados por split/dividendo, 50+ indicadores técnicos, cobertura global incluindo B3
**Formato:** JSON, CSV via API
**Custo:** Gratuito (5 chamadas/minuto, 500/dia); plano pago para volume
**URL:** `https://www.alphavantage.co/`

**Por que usar:** Fallback para o brapi.dev. Se o brapi estiver instável ou o volume de clientes crescer além do plano gratuito, o Alpha Vantage cobre os mesmos ativos com dados ajustados.

**Plano de implementação:**
- Obter chave gratuita em `alphavantage.co`
- Implementar como segunda opção no `data_refresh.py` com lógica de fallback:
  ```python
  try:
      preco = buscar_brapi(ticker)
  except:
      preco = buscar_alpha_vantage(ticker)
  ```
- Não integrar no Rivet diretamente — manter no script Python externo

---

#### Twelve Data

**O que fornece:** Dados de ações de 50+ bolsas incluindo B3, 100+ indicadores técnicos, websockets para tempo real
**Formato:** JSON via API
**Custo:** Gratuito com limites; planos pagos a partir de $29/mês
**URL:** `https://twelvedata.com/`

**Por que usar:** Segunda alternativa ao brapi.dev, com melhor cobertura de ativos menos líquidos da B3. Útil se a carteira dos clientes sintéticos incluir small caps.

**Plano de implementação:**
- Reservar como terceiro fallback no `data_refresh.py`
- Prioridade: brapi.dev → Alpha Vantage → Twelve Data

---

### Categoria 3 — Fundos de Investimento

---

#### CVM — Informes Diários de Fundos (via brasa)

**O que fornece:** Cotas diárias de todos os fundos registrados na CVM, incluindo os fundos do Albert (Riza, Brave, Trend, Truxt, STK, Constellation, Ibiuna)
**Formato:** Arquivos CSV públicos no portal CVM; pacote Python `brasa` automatiza o download
**Custo:** Gratuito
**URL CVM:** `https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/`
**Pacote:** `https://github.com/wilsonfreitas/brasa`

**Por que usar:** É a única fonte gratuita com cotas históricas dos fundos da carteira do Albert. Sem isso, a rentabilidade dos fundos (67,71% da carteira) fica sem cálculo real — o maior gap do MVP atual.

**Plano de implementação:**
1. Instalar: `pip install brasa`
2. Script `fund_returns.py`:
   ```python
   from brasa.engine import read_dataset
   # Baixa informe diário do mês anterior
   df = read_dataset("inf_diario_fi", dt_refer="2025-03-01")
   # Filtra pelos CNPJs dos fundos da carteira
   fundos = {
       "Riza Lotus Plus": "XX.XXX.XXX/0001-XX",  # buscar CNPJ no site CVM
       "Brave I FIC FIM": "YY.YYY.YYY/0001-YY",
       # ...
   }
   # Calcula retorno do mês: (cota_final / cota_inicial) - 1
   ```
3. Output: dicionário `{nome_fundo: retorno_mensal}`
4. Integrar ao `profitability_calc.csv` antes de rodar o Rivet
5. Rivet chama o script via External Call node no início do workflow

**Passo adicional necessário:** Levantar os CNPJs dos 7 fundos do Albert no portal CVM (`cvmweb.cvm.gov.br`) — operação manual única.

---

#### ANBIMA Data Portal + Boletim Mensal de Fundos

**O que fornece:** Performance agregada da indústria de fundos por categoria (multimercado, renda fixa, ações), fluxos líquidos, AUM total, rankings de gestoras
**Formato:** PDF mensal (Boletim) + dashboard web interativo + downloads CSV
**Custo:** Gratuito
**URL:** `https://data.anbima.com.br/`
**Boletim:** `https://www.anbima.com.br/pt_br/informar/relatorios/fundos-de-investimento/`

**Por que usar:** Contextualiza a performance dos fundos do cliente dentro da indústria. Ex: "O Brave I FIC FIM rendeu 19% enquanto a categoria multimercado macro rendeu em média 12% no período." Esse tipo de comparação eleva muito a qualidade da carta.

**Plano de implementação:**
1. Download manual do Boletim PDF no início de cada mês
2. Salvar em `Input/macro/anbima_boletim_MMAAAA.pdf` (e versão `.txt`)
3. No Rivet: adicionar ao contexto do Subgraph 3 (Risk & Fit Analyzer) como documento de referência
4. O LLM usa o boletim para inserir benchmarks de categoria na análise de fundos
5. Versão futura: automatizar download via script Python + extração de tabelas com `pdfplumber`

---

### Categoria 4 — Relatórios Macro de Bancos

---

#### Itaú BBA — Análises Econômicas

**O que fornece:** Relatório macro mensal do Brasil com projeções de Selic, IPCA, PIB, câmbio e análise setorial. Um dos mais respeitados do mercado
**Formato:** PDF gratuito no site
**Custo:** Gratuito
**URL:** `https://www.itau.com.br/itaubba-pt/analises-economicas/brazil`

**Por que usar:** Oferece uma segunda visão macro independente da XP Research — importante para triangular cenários. Se XP e Itaú BBA concordam sobre Selic, a análise fica mais sólida. Se divergem, o assessor pode mencionar o debate.

**Plano de implementação:**
1. Download manual do PDF no início de cada mês
2. Converter para `.txt` (via `pdftotext` ou Rivet PDF node)
3. Salvar em `Input/macro/itaubba_macro_MMAAAA.txt`
4. No Rivet: adicionar como segundo documento de contexto no Subgraph 4 (Recommendation Engine)
5. Prompt do LLM passa ambos os relatórios: `XP Research diz X. Itaú BBA diz Y. Sintetize.`

---

#### BBVA Research — Brazil Economic Outlook

**O que fornece:** Relatório trimestral com projeções de PIB, inflação, taxa de câmbio e política fiscal do Brasil. Perspectiva de banco global
**Formato:** PDF gratuito
**Custo:** Gratuito
**URL:** `https://www.bbvaresearch.com/`

**Por que usar:** Complementa as fontes brasileiras com visão externa. Útil especialmente para clientes com exposição a ativos dolarizados ou fundos com hedge cambial.

**Plano de implementação:**
1. Download trimestral (não mensal) do PDF
2. Salvar em `Input/macro/bbva_outlook_TRIMESTRE.txt`
3. Usar como contexto secundário no Subgraph 4 quando a carta mencionar câmbio ou cenário externo
4. Frequência menor que os outros relatórios — atualizar a cada 3 meses

---

### Categoria 5 — Renda Fixa e Benchmarks

---

#### S&P/B3 Índices de Renda Fixa

**O que fornece:** Índices oficiais para debentures, títulos públicos, NTN-B (Tesouro IPCA+), crédito corporativo
**Formato:** Web dashboard; dados históricos via download
**Custo:** Gratuito (dados básicos)
**URL:** `https://www.b3.com.br/pt_br/market-data-e-indices/indices/`

**Por que usar:** Permite comparar o CDB do Albert (IPC-A +5,45%) com o índice de referência da categoria. Sem esse benchmark, a análise de renda fixa fica vaga.

**Plano de implementação:**
1. Para o MVP: acessar o site mensalmente e anotar o retorno do índice IMA-B (Tesouro IPCA+) e IRF-M (Tesouro prefixado)
2. Salvar em `Input/benchmarks/renda_fixa_benchmarks.csv`
3. O Subgraph 2 (Profitability Engine) usa esses valores para comparação
4. Versão futura: API B3 para automação

---

### Categoria 6 — Risco e Compliance

---

#### CVM — Portal Oficial

**O que fornece:** Regulação vigente, fichas cadastrais de fundos, histórico de enforcement, enquadramento de produtos por perfil de investidor
**Formato:** Portal web, PDFs, CSVs
**Custo:** Gratuito
**URL:** `https://www.gov.br/cvm/`

**Por que usar:** Garantir que as recomendações geradas pelo LLM estão dentro do escopo regulatório do perfil do cliente. Ex: um perfil conservador não pode receber recomendação de fundo de ações alavancado. O Subgraph 3 (Risk & Fit Analyzer) precisa ter esse contexto.

**Plano de implementação:**
1. Baixar o documento de suitability da CVM (Resolução 30) como referência estática
2. Salvar em `Input/compliance/cvm_suitability.txt`
3. Incluir no prompt do Subgraph 3 como restrição hard: "Never recommend products outside the client's regulatory profile as defined in [DOC]"
4. Atualizar apenas quando houver mudança regulatória

---

## Pipeline Consolidado

### Fluxo de dados mensal

```
[1º dia útil do mês]
        │
        ├─ AUTOMÁTICO ─────────────────────────────────────────────────┐
        │   data_refresh.py                                             │
        │     → brapi.dev: preços das ações                            │
        │     → BCB API: CDI, IPCA, Selic, câmbio                      │
        │     → CVM via brasa: cotas dos fundos                        │
        │   Resultado: profitability_calc.csv atualizado                │
        │                                                               │
        ├─ MANUAL (30 min) ────────────────────────────────────────────┤
        │   Download e conversão de PDFs:                               │
        │     → ANBIMA Boletim Mensal                                   │
        │     → Itaú BBA Macro                                          │
        │     → XP Macro Research (já existe no processo atual)         │
        │   Salvar em Input/macro/ como .txt                            │
        │                                                               │
        └─ RIVET EXECUTA ──────────────────────────────────────────────┘
            Para cada cliente:
              Subgraph 1: carrega dados + benchmarks
              Subgraph 2: calcula rentabilidade real
              Subgraph 3: analisa risco vs. perfil
              Subgraph 4: gera recomendações
              Subgraph 5: formata carta
            Output: carta_[cliente]_[mes].pdf
```

### Resumo por fonte: o que entra onde no Rivet

| Fonte | Subgraph que consome | Como entra |
|-------|---------------------|------------|
| BCB API (CDI, Selic) | Subgraph 2 e 4 | HTTP Request node automático |
| brapi.dev (ações) | Subgraph 2 | Via CSV atualizado pelo script |
| CVM/brasa (fundos) | Subgraph 2 | Via CSV atualizado pelo script |
| ANBIMA Boletim (PDF→txt) | Subgraph 3 | Documento de contexto do LLM |
| XP Macro Research (PDF→txt) | Subgraph 4 | Documento de contexto do LLM |
| Itaú BBA Macro (PDF→txt) | Subgraph 4 | Documento de contexto do LLM |
| S&P/B3 Benchmarks RF | Subgraph 2 | Via CSV manual mensal |
| CVM Suitability | Subgraph 3 | Documento de restrição estático |
