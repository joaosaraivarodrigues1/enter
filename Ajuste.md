# Plano de Ajuste — Arquitetura de Inputs

## Objetivo

Eliminar o acoplamento entre Edge Function, server.mjs e grafo Rivet.
Qualquer dado novo adicionado ao portfolio nao deve exigir mudancas em cascata.

---

## Arquitetura alvo

```
Edge Function  →  POST { job_id, cliente_id, mes_referencia }
server.mjs     →  input: job (objeto unico)
                   contextValues: { supabase_url, supabase_key }
                   (zero externalFunctions — grafo faz as queries diretamente)
Grafo Rivet    →  graphInput "job"
                   → Extract Object Path → job_id, cliente_id, mes_referencia
                   → Context nodes → supabase_url, supabase_key
                   → HTTP Call nodes → queries diretas ao Supabase REST API
                   → Code node: monta prompt + calculos derivados
                   → Chat node: gera recomendacao
```

---

## Por que HTTP Call em vez de External Call

External Call nodes exigem que cada funcao seja declarada em server.mjs com o mesmo nome.
Adicionar uma nova query no grafo = mudanca obrigatoria em server.mjs. Acoplamento persiste.

Com HTTP Call nodes, o grafo e completamente autonomo:
- server.mjs passa apenas credenciais via contextValues (fixo para sempre)
- Qualquer nova query e adicionada direto no grafo, sem tocar server.mjs
- Funciona sem CORS porque server.mjs e Railway rodam Node.js (executor Node, nao Browser)

---

## Fluxo dentro do grafo

```
[graphInput "job"]
        ↓
[Extract Object Path: $.cliente_id]     → "uuid..."
[Extract Object Path: $.mes_referencia] → "2026-03"
[Extract Object Path: $.job_id]         → "uuid..."

[Context: supabase_url]  [Context: supabase_key]

Para cada query:
  [Text node: url com {{cliente_id}} e {{mes_referencia}} interpolados]
        ↓
  [Object node: headers com {{@context.supabase_key}}]
        ↓ porta Headers
  [HTTP Call node: GET]
        ↓
  [porta JSON do HTTP Call] → array de objetos ja parseado

[Code node: cruza tabelas, calcula valor_atual / retorno_aplicado / pesos / conversoes]
        ↓
[Chat node: gera recomendacao]
```

---

## Queries no grafo — apenas colunas existentes no banco

Cada query busca somente sua tabela, sem joins. O Code node cruza os dados.
Os selects listam explicitamente apenas as colunas que existem na tabela.

| Query | URL completa |
|-------|-------------|
| Cliente | `/rest/v1/clientes?id=eq.{cliente_id}&select=id,nome,perfil_de_risco` |
| Posicoes acoes | `/rest/v1/posicoes_acoes?cliente_id=eq.{cliente_id}&select=ticker,quantidade,preco_medio_compra,data_compra` |
| Ativos acoes | `/rest/v1/ativos_acoes?select=ticker,nome,tipo,setor` |
| Precos acoes | `/rest/v1/precos_acoes?mes=eq.{mes}&select=ticker,preco_fechamento` |
| Posicoes fundos | `/rest/v1/posicoes_fundos?cliente_id=eq.{cliente_id}&select=cnpj,numero_cotas,valor_aplicado,data_investimento` |
| Ativos fundos | `/rest/v1/ativos_fundos?select=cnpj,nome,categoria,prazo_resgate_dias` |
| Cotas fundos | `/rest/v1/cotas_fundos?mes=eq.{mes}&select=cnpj,cota_fechamento` |
| Posicoes renda fixa | `/rest/v1/posicoes_renda_fixa?cliente_id=eq.{cliente_id}&select=ativo_id,taxa_contratada,valor_aplicado,data_inicio,data_vencimento` |
| Ativos renda fixa | `/rest/v1/ativos_renda_fixa?select=id,nome,instrumento,indexacao,isento_ir` |
| Macro | `/rest/v1/dados_mercado?mes=eq.{mes}&select=cdi_mensal,selic_mensal,ipca_mensal,ibovespa_retorno_mensal,usd_brl_fechamento,pib_crescimento_anual` |
| Relatorio | `/rest/v1/relatorios?mes=eq.{mes}&fonte=eq.XP&tipo=eq.macro_mensal&select=conteudo_txt&limit=1` |

---

## O que o Code node calcula (nao existe no banco)

Tudo abaixo e derivado — o banco nao armazena esses valores:

| Campo calculado | Formula |
|----------------|---------|
| `valor_atual` (acoes) | `quantidade × preco_fechamento` (join posicoes_acoes + precos_acoes por ticker) |
| `drawdown` (acoes) | `(preco_fechamento - preco_medio_compra) / preco_medio_compra` |
| `valor_atual` (fundos) | `numero_cotas × cota_fechamento` (join posicoes_fundos + cotas_fundos por cnpj) |
| `retorno_aplicado` (fundos) | `(valor_atual - valor_aplicado) / valor_aplicado` |
| `valor_total` portfolio | soma de todos os valor_atual |
| `peso` de cada posicao | `valor_atual / valor_total` |
| `alocacao_pct` por classe | soma dos pesos por categoria |
| `usd_brl` | renomear `usd_brl_fechamento` do banco |
| conversao % macro | `cdi_mensal` vem como `1.05` (%) → converter para `0.0105` (decimal) |
| `ir_aliquota_pct` (renda fixa) | regressivo por prazo desde `data_inicio` |

---

## Mudancas necessarias

### 1. Edge Function
- Simplificar payload: remover cliente, portfolio, macro, relatorio
- Enviar apenas: `{ job_id, cliente_id, mes_referencia }`

### 2. server.mjs
- Trocar 4 inputs separados por 1 objeto unico `job`
- Adicionar `contextValues: { supabase_url, supabase_key }` no runGraph
- Nenhuma externalFunction de dados necessaria

### 3. Grafo Rivet
- Remover 4 graphInput nodes
- Adicionar 1 graphInput "job" + 3 Extract Object Path
- Adicionar Context nodes para supabase_url e supabase_key
- Adicionar HTTP Call nodes (11 queries conforme tabela acima)
- Atualizar Code node: cruzar dados das tabelas, calcular campos derivados (tabela acima)
- Manter Chat node

---

## Schema do Supabase (apenas colunas existentes)

| Tabela | Colunas |
|--------|---------|
| clientes | id, nome, perfil_de_risco |
| posicoes_acoes | cliente_id, ticker, quantidade, preco_medio_compra, data_compra |
| ativos_acoes | ticker, nome, tipo, setor |
| precos_acoes | ticker, mes, preco_fechamento |
| posicoes_fundos | cliente_id, cnpj, numero_cotas, valor_aplicado, data_investimento |
| ativos_fundos | cnpj, nome, categoria, prazo_resgate_dias |
| cotas_fundos | cnpj, mes, cota_fechamento |
| posicoes_renda_fixa | cliente_id, ativo_id, taxa_contratada, valor_aplicado, data_inicio, data_vencimento |
| ativos_renda_fixa | id, nome, instrumento, indexacao, isento_ir |
| dados_mercado | mes, cdi_mensal, selic_mensal, ipca_mensal, ibovespa_retorno_mensal, usd_brl_fechamento, pib_crescimento_anual |
| relatorios | mes, fonte, tipo, conteudo_txt |
| recomendacoes | job_id, cliente_id, mes, status, resultado (RLS ativo, usar service_role) |

---

## Endpoints e credenciais

| Item | Valor |
|------|-------|
| Railway URL | `https://enter-rivet-server-production.up.railway.app` |
| Supabase URL | `https://kiwptwgbfywlgzkznmvz.supabase.co` |
| Edge Function | `gerar-recomendacao` (slug) |
| Supabase URL contextValue | `SUPABASE_URL` (ja em .env) |
| Supabase Key contextValue | `SUPABASE_SERVICE_ROLE_KEY` (ja em .env) |

---

## Ordem de implementacao

1. Atualizar server.mjs (1 input job + contextValues)
2. Reestruturar grafo Rivet (graphInput + Extracts + Context + HTTP Calls)
3. Testar queries individualmente antes de conectar ao grafo
4. Atualizar Code node com cruzamento de dados e calculos derivados
5. Simplificar Edge Function (trocar payload gordo por { job_id, cliente_id, mes_referencia })
6. Testar localmente com test-albert.json atualizado (cliente_id + mes_referencia reais)
7. Push para GitHub → Railway redeploy automatico

---

## Como passar credenciais para os headers do HTTP Call

O HTTP Call node nao suporta interpolacao dinamica no campo Headers das configuracoes.
A forma correta e conectar um Object node na porta de entrada Headers:

```
[Context: supabase_key]
        ↓
[Object node: { "apikey": "{{supabase_key}}", "Authorization": "Bearer {{supabase_key}}", "Content-Type": "application/json" }]
        ↓ porta Headers
[HTTP Call node]
```

O Object node suporta interpolacao via `{{nome_da_variavel}}`, permitindo compor
os headers dinamicamente a partir do valor vindo do Context node.

O HTTP Call node retorna 4 portas de saida: Body (string), Headers (object),
Status Code (number) e JSON (object). Usar sempre a porta **JSON** — o body ja
vem parseado como array de objetos, pronto para o Code node consumir.
