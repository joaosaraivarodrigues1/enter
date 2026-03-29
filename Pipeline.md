# Pipeline de Recomendações — Documentação Operacional

## Visão Geral

O pipeline gera recomendações de portfólio por cliente usando IA. O fluxo completo é:

```
Streamlit (frontend)
    → Edge Function (Supabase)
        → insere job na tabela recomendacoes
        → dispara Railway (HTTP POST)
            → server.mjs recebe job
            → executa grafo Rivet
                → 11 HTTP Calls ao Supabase REST API
                → Code node: cruza dados + monta prompt
                → Chat node: gera recomendacao (OpenAI)
            → PATCH recomendacoes com resultado
    → Streamlit faz polling do status
```

---

## Componentes

### 1. Edge Function — `Estudo/supabase/functions/gerar-recomendacao/index.ts`

**Responsabilidade:** receber a chamada do frontend, criar o job e acionar o Railway.

**Entrada (POST body):**
```json
{ "cliente_id": "uuid", "mes": "2026-03" }
```

**O que faz:**
1. Valida `cliente_id` e `mes`
2. Insere linha em `recomendacoes` com `status: "processing"`
3. Faz POST para `RIVET_SERVER_URL` com `{ job_id, cliente_id, mes_referencia }`
4. Retorna `{ job_id }` com status 202

**Variáveis de ambiente (Supabase):**
| Variável | Descrição |
|----------|-----------|
| `SUPABASE_URL` | URL do projeto Supabase (automática) |
| `SUPABASE_SERVICE_ROLE_KEY` | Chave service_role (automática) |
| `RIVET_SERVER_URL` | URL pública do Railway, ex: `https://enter-rivet-server-production.up.railway.app` |

**Deploy:**
```bash
# Via MCP (Supabase) ou CLI:
supabase functions deploy gerar-recomendacao --project-ref kiwptwgbfywlgzkznmvz
```

---

### 2. Railway Server — `Rivet/server.mjs`

**Responsabilidade:** receber o job, executar o grafo Rivet e salvar o resultado.

**Entrada (POST /):**
```json
{ "job_id": "uuid", "cliente_id": "uuid", "mes_referencia": "2026-03" }
```

**O que faz:**
1. Responde 202 imediatamente (non-blocking)
2. Em background: executa `runGraph` passando:
   - `inputs.job` = objeto com os 3 campos acima
   - `context.supabase_url` e `context.supabase_key` = credenciais para os HTTP Call nodes
3. Faz PATCH em `recomendacoes` com `status: "done"` + `resultado` (texto gerado)
4. Em caso de erro: PATCH com `status: "error"` + `erro`

**Variáveis de ambiente (Railway):**
| Variável | Descrição |
|----------|-----------|
| `OPENAI_API_KEY` | Chave OpenAI para o Chat node |
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Chave service_role |
| `PORT` | Porta do servidor (Railway injeta automaticamente) |
| `NODE_ENV` | `production` em produção (desativa Remote Debugger) |

**Debug local:**
```bash
cd Rivet
node server.mjs
# Em modo dev (NODE_ENV != production): Remote Debugger ativo em ws://localhost:21888
# Conectar no Rivet IDE: Remote Debugging → localhost:21888
```

**Testar localmente (PowerShell):**
```powershell
# Primeiro inserir um job real no Supabase e pegar o job_id
# Depois:
Invoke-RestMethod -Uri http://localhost:3000 -Method POST `
  -ContentType "application/json" `
  -Body (Get-Content Rivet\test-albert.json -Raw)
```

**Arquivo de teste:** `Rivet/test-albert.json`
```json
{
  "job_id": "uuid-do-job-inserido-no-supabase",
  "cliente_id": "bb648f53-0d15-47b3-bc39-565bbf41e8a2",
  "mes_referencia": "2026-03"
}
```

> **Atenção:** `job_id` deve ser um UUID real existente na tabela `recomendacoes`.
> Para gerar um novo job de teste, inserir via Supabase SQL:
> ```sql
> INSERT INTO recomendacoes (cliente_id, mes, status)
> VALUES ('bb648f53-0d15-47b3-bc39-565bbf41e8a2', '2026-03', 'processing')
> RETURNING job_id;
> ```

---

### 3. Grafo Rivet — `Rivet/Rivet.rivet-project` (grafo `gerar_recomendacao`)

**Estrutura do grafo:**

```
[graphInput "job"]
        ↓
[Extract Object Path: $.job_id]       → job_id (string)
[Extract Object Path: $.cliente_id]   → cliente_id (string)
[Extract Object Path: $.mes_referencia] → mes (string)

[Context: supabase_url]    [Context: supabase_key]
        ↓                          ↓
                [Text node: "Bearer {{supabase_key}}"]
                        ↓ auth_header
        [Object node: headers JSON com apikey + Authorization + Content-Type]
                        ↓ (porta Headers dos HTTP Call nodes)

[11 Text nodes: URLs das queries]
        ↓ (porta URL dos HTTP Call nodes)
[11 HTTP Call nodes GET] → porta JSON (array parseado)
        ↓
[Code node: code-node.js]
        ↓
[Chat node: gera recomendacao]
        ↓
[graphOutput "recomendacao"]
```

**Por que Object node + Text node separados para Authorization:**
O Object node do Rivet não suporta interpolação `{{}}` dentro de strings mistas como
`"Bearer {{supabase_key}}"`. A solução é um Text node com template `Bearer {{supabase_key}}`
que produz a string completa, e o Object node referencia via `{{auth_header}}`.

**Queries (11 HTTP Calls):**
| Input no Code node | URL |
|--------------------|-----|
| `r_cliente` | `/rest/v1/clientes?id=eq.{cliente_id}&select=id,nome,perfil_de_risco` |
| `r_posicoes_acoes` | `/rest/v1/posicoes_acoes?cliente_id=eq.{cliente_id}&select=ticker,quantidade,preco_medio_compra,data_compra` |
| `r_ativos_acoes` | `/rest/v1/ativos_acoes?select=ticker,nome,tipo,setor` |
| `r_precos_acoes` | `/rest/v1/precos_acoes?mes=eq.{mes}&select=ticker,preco_fechamento` |
| `r_posicoes_fundos` | `/rest/v1/posicoes_fundos?cliente_id=eq.{cliente_id}&select=cnpj,numero_cotas,valor_aplicado,data_investimento` |
| `r_ativos_fundos` | `/rest/v1/ativos_fundos?select=cnpj,nome,categoria,prazo_resgate_dias` |
| `r_cotas_fundos` | `/rest/v1/cotas_fundos?mes=eq.{mes}&select=cnpj,cota_fechamento` |
| `r_posicoes_rf` | `/rest/v1/posicoes_renda_fixa?cliente_id=eq.{cliente_id}&select=ativo_id,taxa_contratada,valor_aplicado,data_inicio,data_vencimento` |
| `r_ativos_rf` | `/rest/v1/ativos_renda_fixa?select=id,nome,instrumento,indexacao,isento_ir` |
| `r_macro` | `/rest/v1/dados_mercado?mes=eq.{mes}&select=cdi_mensal,selic_mensal,ipca_mensal,ibovespa_retorno_mensal,usd_brl_fechamento,pib_crescimento_anual` |
| `r_relatorio` | `/rest/v1/relatorios?mes=eq.{mes}&fonte=eq.XP&tipo=eq.macro_mensal&select=conteudo_txt&limit=1` |

**Code node — `Rivet/code-node.js`:**
Contém o JavaScript completo do Code node. Principais responsabilidades:
- Joins entre tabelas (posicoes + ativos + precos/cotas) usando maps por ticker/cnpj/id
- Cálculo de `valor_atual`, `drawdown`, `retorno_aplicado`, `peso`, `ir_aliquota_pct`
- Conversão de macro: valores em % no banco (ex: `1.05`) → decimal (ex: `0.0105`)
- Renomeia `usd_brl_fechamento` → `usd_brl`
- Monta `promptText` completo como string
- Retorna `{ prompt: { type: 'string', value: promptText } }`

> **IMPORTANTE:** Ao editar o Code node no Rivet IDE, copiar o conteúdo do arquivo
> `Rivet/code-node.js`. Nunca copiar diretamente do chat — o Claude Code pode introduzir
> aspas tipográficas (`"` `"`) que causam "Invalid or unexpected token" no Rivet.

---

## Schema do Banco (Supabase)

| Tabela | Colunas armazenadas |
|--------|---------------------|
| `clientes` | id, nome, perfil_de_risco |
| `posicoes_acoes` | cliente_id, ticker, quantidade, preco_medio_compra, data_compra |
| `ativos_acoes` | ticker, nome, tipo, setor |
| `precos_acoes` | ticker, mes, preco_fechamento |
| `posicoes_fundos` | cliente_id, cnpj, numero_cotas, valor_aplicado, data_investimento |
| `ativos_fundos` | cnpj, nome, categoria, prazo_resgate_dias |
| `cotas_fundos` | cnpj, mes, cota_fechamento |
| `posicoes_renda_fixa` | cliente_id, ativo_id, taxa_contratada, valor_aplicado, data_inicio, data_vencimento |
| `ativos_renda_fixa` | id, nome, instrumento, indexacao, isento_ir |
| `dados_mercado` | mes, cdi_mensal, selic_mensal, ipca_mensal, ibovespa_retorno_mensal, usd_brl_fechamento, pib_crescimento_anual |
| `relatorios` | mes, fonte, tipo, conteudo_txt |
| `recomendacoes` | job_id (PK), cliente_id, mes, status, resultado, erro, concluido_em |

**Campos calculados no Code node (não existem no banco):**
- `valor_atual` (ações e fundos)
- `drawdown` (ações)
- `retorno_aplicado` (fundos)
- `peso` (todas as classes)
- `ir_aliquota_pct` (renda fixa, regressivo por prazo)
- `usd_brl` (renomeado de `usd_brl_fechamento`)
- conversões de % para decimal em todos os campos de `dados_mercado`

---

## Como Reproduzir do Zero

1. **Supabase:** project ref `kiwptwgbfywlgzkznmvz`
   - Variáveis de ambiente: configurar `RIVET_SERVER_URL` nas secrets da Edge Function
   - Fazer deploy: `supabase functions deploy gerar-recomendacao`

2. **Railway:** conectar ao repositório `enter`, Root Directory = `Rivet`
   - Configurar variáveis: `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
   - Deploy automático no push para main

3. **Rivet IDE:** abrir `Rivet/Rivet.rivet-project`
   - Remote Debugger: conectar em `ws://localhost:21888` (server local em modo dev)
   - Editar Code node: copiar de `Rivet/code-node.js`

---

## Como Testar

### Teste local do servidor

```bash
# 1. Iniciar servidor (modo dev)
cd Rivet && node server.mjs

# 2. Inserir job de teste no Supabase (SQL editor)
# INSERT INTO recomendacoes (cliente_id, mes, status)
# VALUES ('bb648f53-0d15-47b3-bc39-565bbf41e8a2', '2026-03', 'processing')
# RETURNING job_id;

# 3. Atualizar Rivet/test-albert.json com o job_id retornado

# 4. Enviar requisição (PowerShell)
Invoke-RestMethod -Uri http://localhost:3000 -Method POST `
  -ContentType "application/json" `
  -Body (Get-Content Rivet\test-albert.json -Raw)

# 5. Verificar log do servidor — deve aparecer:
# [uuid] running Rivet graph — cliente: ..., mes: ...
# [uuid] resultado length: XXXX
# [uuid] done.

# 6. Verificar resultado no Supabase:
# SELECT status, length(resultado) FROM recomendacoes WHERE job_id = 'uuid';
```

### Teste do fluxo completo

1. Abrir o Streamlit
2. Selecionar cliente e mês
3. Clicar em "Gerar Recomendação"
4. Aguardar polling retornar `status: "done"`
5. Conferir o texto gerado na tela

### Verificar logs em produção (Railway)

Acessar o dashboard do Railway → serviço `enter-rivet-server` → aba Logs.

---

## Troubleshooting

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| `status: "error"`, erro = `insertJob: ...` | RLS bloqueando insert em `recomendacoes` | Usar service_role key na Edge Function |
| `status: "error"`, erro = `Graph ... cause: Invalid or unexpected token` | Aspas tipográficas no Code node | Copiar código de `Rivet/code-node.js`, não do chat |
| HTTP 401 nas queries do grafo | Context nodes com ID errado ou `contextValues` no server.mjs | Confirmar que server.mjs usa `context:` (não `contextValues:`); IDs dos Context nodes = `supabase_url` e `supabase_key` |
| HTTP 400 em query específica | Espaço extra na URL do Text node ou coluna inexistente | Revisar Text node da query com problema; checar nomes das colunas no banco |
| `resultado length: 0` | Chat node não conectado ao graphOutput | Verificar conexão Chat node → graphOutput `recomendacao` no grafo |
| Railway não atualiza após push | Root Directory não configurado | Railway → Settings → Source → Root Directory = `Rivet` |
| Context node retorna null | `context` key não bate com Context node ID | ID do Context node deve ser exatamente `supabase_url` ou `supabase_key` |
