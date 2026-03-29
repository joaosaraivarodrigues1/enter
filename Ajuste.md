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
- Funciona sem CORS porque server.mjs e Railway rodam Node.js

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
  [HTTP Call node: GET + headers com {{@context.supabase_key}}]
        ↓
  [porta JSON do HTTP Call] → dados prontos (ja parseado)

[Code node: monta prompt + calcula valor_atual, retorno_aplicado, conversoes]
        ↓
[Chat node: gera recomendacao]
```

---

## Queries no grafo (apenas campos existentes no banco)

Cada query busca somente sua tabela direta, sem joins. O Code node cruza os dados.

| Query | URL |
|-------|-----|
| Cliente | `/rest/v1/clientes?id=eq.{cliente_id}&select=*` |
| Posicoes acoes | `/rest/v1/posicoes_acoes?cliente_id=eq.{cliente_id}&select=*` |
| Ativos acoes | `/rest/v1/ativos_acoes?select=*` |
| Precos acoes | `/rest/v1/precos_acoes?mes=eq.{mes}&select=*` |
| Posicoes fundos | `/rest/v1/posicoes_fundos?cliente_id=eq.{cliente_id}&select=*` |
| Ativos fundos | `/rest/v1/ativos_fundos?select=*` |
| Cotas fundos | `/rest/v1/cotas_fundos?mes=eq.{mes}&select=*` |
| Posicoes renda fixa | `/rest/v1/posicoes_renda_fixa?cliente_id=eq.{cliente_id}&select=*` |
| Ativos renda fixa | `/rest/v1/ativos_renda_fixa?select=*` |
| Macro | `/rest/v1/dados_mercado?mes=eq.{mes}&select=*` |
| Relatorio | `/rest/v1/relatorios?mes=eq.{mes}&fonte=eq.XP&tipo=eq.macro_mensal&select=conteudo_txt&limit=1` |

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
- Atualizar Code node: cruzar dados das tabelas, calcular valor_atual e retorno_aplicado, converter % para decimal, renomear usd_brl_fechamento → usd_brl
- Manter Chat node

---

## Schema do Supabase (tabelas relevantes)

| Tabela | Chave | Dados |
|--------|-------|-------|
| clientes | id (uuid) | nome, perfil_de_risco |
| posicoes_acoes | cliente_id, ticker | quantidade, preco_medio_compra, data_compra |
| ativos_acoes | ticker | nome, tipo, setor |
| precos_acoes | ticker, mes | preco_fechamento |
| posicoes_fundos | cliente_id, cnpj | numero_cotas, valor_aplicado, data_investimento |
| ativos_fundos | cnpj | nome, categoria, prazo_resgate_dias |
| cotas_fundos | cnpj, mes | cota_fechamento |
| posicoes_renda_fixa | cliente_id, ativo_id | taxa_contratada, valor_aplicado, datas |
| ativos_renda_fixa | id | nome, instrumento, indexacao, isento_ir |
| dados_mercado | mes | cdi_mensal (%), selic_mensal (%), ipca_mensal (%), ibovespa_retorno_mensal (%), usd_brl_fechamento, pib_crescimento_anual (%) |
| relatorios | mes, fonte, tipo | conteudo_txt |
| recomendacoes | job_id, cliente_id, mes | status, resultado (RLS ativo, usar service_role) |

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

## Nota: como passar credenciais para os headers do HTTP Call

O HTTP Call node nao suporta interpolacao dinamica no campo Headers das configuracoes.
A forma correta e conectar um Object node na porta de entrada Headers:

```
[Context: supabase_key]
        ↓
[Object node: { "apikey": "{{supabase_key}}", "Authorization": "Bearer {{supabase_key}}" }]
        ↓ porta Headers
[HTTP Call node]
```

O Object node suporta interpolacao via `{{nome_da_variavel}}`, permitindo compor
os headers dinamicamente a partir do valor vindo do Context node.
