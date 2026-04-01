# Arquitetura do Sistema

Documentação completa de todos os servidores, conexões e protocolos do projeto Enter.
Inclui ambiente de produção e ambiente local de desenvolvimento.

---

## Servidores

| Servidor | Tecnologia | Onde roda |
|----------|-----------|-----------|
| **Streamlit** | Python | Streamlit Cloud |
| **Supabase DB** | PostgreSQL | Supabase Cloud (`kiwptwgbfywlgzkznmvz`) |
| **Edge Function: gerar-recomendacao** | Deno/TypeScript | Supabase Cloud |
| **Edge Function: ingest** | Deno/TypeScript | Supabase Cloud |
| **Edge Function: extract-pdf** | Deno/TypeScript | Supabase Cloud |
| **Railway** | Node.js (`server.mjs`) | Railway Cloud |
| **OpenAI** | API externa | OpenAI Cloud |
| **Anthropic** | API externa | Anthropic Cloud |
| **server.mjs local** | Node.js | PC local — porta 3000 |
| **Rivet IDE** | Electron app | PC local |

---

## Diagrama de produção

```
┌──────────────────────────────────────────────────────────────────┐
│                       STREAMLIT CLOUD                            │
│                                                                  │
│  1. load_table()              ── HTTPS REST GET ──────────────► │
│  2. gerar_recomendacao()      ── HTTPS POST ───────────────────► │
│  3. polling recomendacoes     ── HTTPS GET (a cada 3s) ────────► │
│  4. upload PDF                ── HTTPS POST multipart ─────────► │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                        SUPABASE CLOUD                            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  PostgreSQL DB                                         │     │
│  │                                                        │     │
│  │  clientes, ativos_*, posicoes_*, recomendacoes         │     │
│  │  dados_mercado, relatorios, precos_*, cotas_*          │     │
│  │  documents, document_analysis, document_client_links   │     │
│  │                                                        │     │
│  │  DATABASE WEBHOOK ────────────────────────────────────►│──┐  │
│  │  (INSERT em documents → dispara extract-pdf)           │  │  │
│  └────────────────────────────────────────────────────────┘  │  │
│                                                               │  │
│  ┌──────────────────┐  ┌─────────────────┐  ┌─────────────┐ │  │
│  │ gerar-recomendac │  │ ingest          │  │ extract-pdf │◄┘  │
│  │                  │  │                 │  │             │     │
│  │ recebe:          │  │ recebe:         │  │ recebe:     │     │
│  │ {cliente_id,mes} │  │ PDF (form-data) │  │ - webhook   │     │
│  │                  │  │                 │  │ - chamada   │     │
│  │ 1. INSERT job    │  │ 1. upload para  │  │   direta    │     │
│  │ 2. POST Railway  │  │    Storage      │  │             │     │
│  │ 3. retorna job_id│  │ 2. INSERT em    │  │ 1. download │     │
│  └──────────────────┘  │    documents    │  │    PDF do   │     │
│          │              └─────────────────┘  │    Storage  │     │
│          │                      │             │ 2. POST    ─────►│──► ANTHROPIC
│          │              ┌───────▼───────────┐ │    API      │     │
│          │              │ Storage           │◄│ 3. INSERT  │     │
│          │              │ documents-incoming│ │    analysis│     │
│          │              └───────────────────┘ └─────────────┘     │
└──────────┼───────────────────────────────────────────────────────┘
           │ HTTPS POST (RIVET_SERVER_URL)
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                        RAILWAY CLOUD                             │
│                        server.mjs                                │
│                                                                  │
│  recebe: { job_id, cliente_id, mes_referencia }                  │
│  responde 202 imediatamente                                      │
│  em background:                                                  │
│    1. runGraph("gerar_recomendacao")                             │
│       → 11 HTTP Calls para Supabase REST API                     │
│       → Chat nodes para OpenAI API                               │
│    2. PATCH recomendacoes SET status="done", resultado=...       │
│                                                                  │
└──────────┬────────────────────────────────────┬─────────────────┘
           │ HTTPS GET /rest/v1/*               │ HTTPS POST
           ▼                                    ▼
    SUPABASE (PostgREST)                   OPENAI API
    (busca dados do portfólio)             (gpt-4o-mini)
```

---

## Diagrama de desenvolvimento local

```
┌─────────────────────────────────────────────────────────────────┐
│  PC LOCAL                                                       │
│                                                                 │
│  ┌─────────────┐   HTTP POST :3000    ┌─────────────────────┐  │
│  │  dev.ps1    │────────────────────► │  server.mjs         │  │
│  │ (PowerShell)│                      │  porta 3000         │  │
│  └─────────────┘                      │                     │  │
│                                       │  porta 21888        │  │
│  ┌─────────────┐   WebSocket          │  (Remote Debugger)  │  │
│  │  Rivet IDE  │◄───────────────────► │                     │  │
│  │  (Electron) │  ws://localhost:21888 └─────────────────────┘  │
│  └─────────────┘                             │         │        │
│                                              │         │        │
└──────────────────────────────────────────────┼─────────┼────────┘
                                               │         │
                          HTTPS GET/PATCH      │         │ HTTPS POST
                          (mesmo que Railway)  │         │ chat completions
                                               ▼         ▼
                                        SUPABASE      OPENAI API
                                        (PostgREST)
```

Em desenvolvimento, o `dev.ps1` envia o job diretamente para `http://localhost:3000`, pulando Streamlit e Edge Function. O Rivet IDE conecta via WebSocket e exibe cada node sendo executado em tempo real.

---

## Todas as conexões

| # | De | Para | Protocolo | Trigger |
|---|----|----|-----------|---------|
| 1 | Streamlit | Supabase PostgREST | HTTPS REST GET | leitura de tabelas |
| 2 | Streamlit | Edge Function `gerar-recomendacao` | HTTPS POST | botão "Gerar recomendação" |
| 3 | Streamlit | Supabase `recomendacoes` | HTTPS GET | polling a cada 3s, até 5 min |
| 4 | Streamlit | Edge Function `ingest` | HTTPS POST multipart | upload de PDF |
| 5 | Edge Function `gerar-recomendacao` | Supabase DB | interno Supabase | INSERT job em `recomendacoes` |
| 6 | Edge Function `gerar-recomendacao` | Railway | HTTPS POST | após INSERT do job |
| 7 | Edge Function `ingest` | Supabase Storage | interno Supabase | upload do PDF para bucket |
| 8 | Edge Function `ingest` | Supabase DB | interno Supabase | INSERT em `documents` |
| 9 | **Database Webhook** | Edge Function `extract-pdf` | HTTPS POST | INSERT em `documents` (automático) |
| 10 | Edge Function `extract-pdf` | Supabase Storage | interno Supabase | download do PDF |
| 11 | Edge Function `extract-pdf` | Anthropic API | HTTPS POST | envia PDF em base64 para Claude |
| 12 | Edge Function `extract-pdf` | Supabase DB | interno Supabase | INSERT em `document_analysis` |
| 13 | Railway | Supabase PostgREST | HTTPS GET | Rivet busca dados (11 HTTP Calls) |
| 14 | Railway | OpenAI API | HTTPS POST | Rivet chat nodes (`gpt-4o-mini`) |
| 15 | Railway | Supabase `recomendacoes` | HTTPS PATCH | salva resultado ao finalizar |
| 16 | dev.ps1 | server.mjs local `:3000` | HTTP POST | teste manual de job |
| 17 | Rivet IDE | server.mjs local `:21888` | **WebSocket** | debug em tempo real (só local) |
| 18 | server.mjs local | Supabase PostgREST | HTTPS GET | idem Railway (conexão #13) |
| 19 | server.mjs local | OpenAI API | HTTPS POST | idem Railway (conexão #14) |

---

## Fluxo completo de uma recomendação (produção)

```
Streamlit          gerar-recomendacao     Railway           Supabase DB
    │                      │                  │                  │
    │── POST {cliente,mes} ►│                  │                  │
    │                      │── INSERT job ───────────────────────►│
    │                      │◄──────────────── job_id ────────────│
    │                      │── POST {job_id} ►│                  │
    │◄── { job_id } ───────│                  │                  │
    │                      │                  │── GET ativos ────►│
    │                      │                  │── GET posicoes ──►│
    │                      │                  │── GET macro ─────►│
    │                      │                  │── GET relatorio ─►│
    │                      │                  │   (11 calls)      │
    │                      │                  │── POST OpenAI     │
    │                      │                  │◄── resposta LLM   │
    │                      │                  │── PATCH done ────►│
    │                      │                  │                  │
    │── GET recomendacoes (polling 3s) ──────────────────────────►│
    │◄── status: processing ─────────────────────────────────────│
    │── GET recomendacoes ───────────────────────────────────────►│
    │◄── status: done, resultado ─────────────────────────────────│
```

---

## Fluxo de extração de PDF (produção)

```
Streamlit        ingest          Supabase DB+Storage    extract-pdf      Anthropic
    │               │                    │                    │               │
    │─ POST PDF ───►│                    │                    │               │
    │               │── upload Storage ─►│                    │               │
    │               │── INSERT document ►│                    │               │
    │◄── { id } ───│                    │                    │               │
    │               │                    │── Webhook POST ───►│               │
    │               │                    │                    │─ download PDF ►│ (Storage)
    │               │                    │                    │─ POST PDF ────────────────►│
    │               │                    │                    │◄── análise JSON ───────────│
    │               │                    │◄── INSERT analysis ┤               │
    │               │                    │◄── UPDATE status   │               │
```

---

## O único WebSocket

`ws://localhost:21888` — Remote Debugger do Rivet IDE.

Existe **apenas em desenvolvimento local** (`NODE_ENV !== "production"`). O Rivet IDE conecta nesse socket e recebe em tempo real o estado de cada node do grafo: inputs, outputs e erros. Em produção no Railway esse socket não é aberto.

---

## Autenticação por servidor

| Conexão | Credencial usada |
|---------|-----------------|
| Streamlit → Supabase | `SUPABASE_KEY` (anon key) nos secrets do Streamlit |
| Streamlit → Edge Functions | mesma anon key no header `Authorization` e `apikey` |
| Edge Functions → Supabase | `SUPABASE_SERVICE_ROLE_KEY` (acesso total, sem RLS) |
| Edge Function → Railway | `RIVET_SERVER_URL` (URL com token embutido, variável de ambiente) |
| Railway → Supabase | `SUPABASE_SERVICE_ROLE_KEY` (variável de ambiente no Railway) |
| Railway → OpenAI | `OPENAI_API_KEY` (variável de ambiente no Railway) |
| extract-pdf → Anthropic | `ANTHROPIC_API_KEY` (variável de ambiente no Supabase) |
| server.mjs local → Supabase | `SUPABASE_SERVICE_ROLE_KEY` (arquivo `.env` local) |
| server.mjs local → OpenAI | `OPENAI_API_KEY` (arquivo `.env` local) |

---

## Diagrama de Sequência Completo

### Produção — todos os fluxos

```mermaid
sequenceDiagram
    actor User as Usuário

    participant ST  as Streamlit Cloud
    participant REC as Edge Fn: gerar-recomendacao
    participant ING as Edge Fn: ingest
    participant PDF as Edge Fn: extract-pdf
    participant DB  as Supabase DB
    participant STG as Supabase Storage
    participant RW  as Railway (server.mjs)
    participant OAI as OpenAI API
    participant ANT as Anthropic API

    %% ────────────────────────────────────────────
    Note over User,ANT: INICIALIZAÇÃO — carga das tabelas
    %% ────────────────────────────────────────────

    User->>ST: abre a aplicação
    par carga paralela
        ST->>DB: GET /rest/v1/clientes
    and
        ST->>DB: GET /rest/v1/ativos_acoes
    and
        ST->>DB: GET /rest/v1/ativos_fundos
    and
        ST->>DB: GET /rest/v1/ativos_renda_fixa
    and
        ST->>DB: GET /rest/v1/recomendacoes
    end
    DB-->>ST: dados das tabelas (TTL 60s)
    ST-->>User: interface carregada

    %% ────────────────────────────────────────────
    Note over User,ANT: GERAÇÃO DE RECOMENDAÇÃO
    %% ────────────────────────────────────────────

    User->>ST: clica "Gerar Recomendação" (cliente_id + mes)
    ST->>REC: POST /functions/v1/gerar-recomendacao<br/>{cliente_id, mes}
    REC->>DB: INSERT recomendacoes {status: "processing"}
    DB-->>REC: {job_id}
    REC->>RW: POST {job_id, cliente_id, mes_referencia}
    RW-->>REC: 202 Accepted
    REC-->>ST: 202 {job_id}

    loop polling a cada 3 segundos (máx 100x / ~5 min)
        ST->>DB: GET recomendacoes WHERE job_id=...
        DB-->>ST: {status: "processing"}
    end

    Note over RW,DB: Railway executa o grafo Rivet em background

    par 11 HTTP Calls em paralelo
        RW->>DB: GET /rest/v1/clientes
    and
        RW->>DB: GET /rest/v1/posicoes_acoes
    and
        RW->>DB: GET /rest/v1/ativos_acoes
    and
        RW->>DB: GET /rest/v1/precos_acoes (12 meses)
    and
        RW->>DB: GET /rest/v1/posicoes_fundos
    and
        RW->>DB: GET /rest/v1/ativos_fundos
    and
        RW->>DB: GET /rest/v1/cotas_fundos (12 meses)
    and
        RW->>DB: GET /rest/v1/posicoes_renda_fixa
    and
        RW->>DB: GET /rest/v1/ativos_renda_fixa
    and
        RW->>DB: GET /rest/v1/dados_mercado (macro atual + 12 meses)
    and
        RW->>DB: GET /rest/v1/relatorios
    end
    DB-->>RW: todos os dados do portfólio

    Note over RW,OAI: Scoring macro — 7 prompts para os indicadores
    RW->>OAI: POST /v1/chat/completions (score Selic)
    RW->>OAI: POST /v1/chat/completions (score IPCA)
    RW->>OAI: POST /v1/chat/completions (score Câmbio)
    RW->>OAI: POST /v1/chat/completions (score PIB)
    RW->>OAI: POST /v1/chat/completions (score Crédito)
    RW->>OAI: POST /v1/chat/completions (score Fiscal)
    RW->>OAI: POST /v1/chat/completions (score Externo)
    OAI-->>RW: scores {-2 a +2} por indicador

    Note over RW,OAI: Narrativa — suitability + ranking + recomendação
    RW->>OAI: POST /v1/chat/completions (narrativa final)
    OAI-->>RW: texto da carta de recomendação

    RW->>DB: PATCH recomendacoes SET status="done", resultado=...
    DB-->>RW: ok

    ST->>DB: GET recomendacoes WHERE job_id=...
    DB-->>ST: {status: "done", resultado: "..."}
    ST-->>User: exibe recomendação

    %% ────────────────────────────────────────────
    Note over User,ANT: UPLOAD E EXTRAÇÃO DE PDF
    %% ────────────────────────────────────────────

    User->>ST: faz upload de PDF
    ST->>ING: POST /functions/v1/ingest (multipart/form-data)
    ING->>STG: upload PDF → bucket documents-incoming/inbox/
    STG-->>ING: storage_path
    ING->>DB: INSERT documents {status: "uploaded", storage_path}
    DB-->>ING: {document_id}
    ING-->>ST: {id, storage_path, filename}
    ST-->>User: upload confirmado

    Note over DB,ANT: Database Webhook dispara automaticamente (INSERT em documents)
    DB->>PDF: POST webhook {type:"INSERT", record: {id, status:"uploaded", ...}}
    PDF->>DB: UPDATE documents SET status="processing"
    PDF->>STG: download PDF (storage_path)
    STG-->>PDF: bytes do arquivo
    PDF->>ANT: POST /v1/messages<br/>{model: claude-sonnet-4, PDF em base64, tool: salvar_contrato}
    ANT-->>PDF: tool_use {dados estruturados do contrato}
    PDF->>DB: INSERT document_analysis {instrument_type, parties, valores, datas...}
    loop para cada parte do contrato
        PDF->>DB: UPSERT clients (por CPF/CNPJ ou nome normalizado)
        PDF->>DB: UPSERT document_client_links {document_id, client_id, role}
    end
    PDF->>DB: UPDATE documents SET status="analyzed"
    DB-->>PDF: ok
```

---

### Desenvolvimento local — debug com Rivet IDE

```mermaid
sequenceDiagram
    actor Dev as Desenvolvedor

    participant PS  as dev.ps1 (PowerShell)
    participant SRV as server.mjs :3000
    participant WS  as WebSocket :21888
    participant IDE as Rivet IDE
    participant DB  as Supabase DB
    participant OAI as OpenAI API

    %% ────────────────────────────────────────────
    Note over Dev,OAI: INICIALIZAÇÃO DO SERVIDOR LOCAL
    %% ────────────────────────────────────────────

    Dev->>PS: .\dev.ps1 albert-2026-03
    PS->>SRV: node server.mjs (start process)
    SRV->>SRV: carrega Rivet.rivet-project
    SRV->>WS: abre ws://localhost:21888 (Remote Debugger)
    SRV->>SRV: escuta HTTP em :3000

    loop até responder (15 tentativas, 1s cada)
        PS->>SRV: GET /health
        SRV-->>PS: {status: "ok"}
    end

    %% ────────────────────────────────────────────
    Note over Dev,OAI: CONEXÃO DO RIVET IDE
    %% ────────────────────────────────────────────

    Dev->>IDE: abre Rivet IDE → Remote Debugger → connect
    IDE->>WS: WebSocket connect ws://localhost:21888
    WS-->>IDE: connected — streaming de eventos ativo

    %% ────────────────────────────────────────────
    Note over Dev,OAI: ENVIO DO JOB DE TESTE
    %% ────────────────────────────────────────────

    PS->>SRV: POST / (body = tests/albert-2026-03.json)<br/>{job_id, cliente_id, mes_referencia}
    SRV-->>PS: 202 {status: "processing", job_id}

    Note over SRV,IDE: Grafo executa em background — IDE recebe eventos em tempo real

    par 11 HTTP Calls em paralelo
        SRV->>DB: GET /rest/v1/clientes
    and
        SRV->>DB: GET /rest/v1/posicoes_acoes
    and
        SRV->>DB: GET /rest/v1/ativos_acoes
    and
        SRV->>DB: GET /rest/v1/precos_acoes
    and
        SRV->>DB: GET /rest/v1/posicoes_fundos
    and
        SRV->>DB: GET /rest/v1/ativos_fundos
    and
        SRV->>DB: GET /rest/v1/cotas_fundos
    and
        SRV->>DB: GET /rest/v1/posicoes_renda_fixa
    and
        SRV->>DB: GET /rest/v1/ativos_renda_fixa
    and
        SRV->>DB: GET /rest/v1/dados_mercado
    and
        SRV->>DB: GET /rest/v1/relatorios
    end
    DB-->>SRV: dados
    SRV->>WS: node outputs (dados carregados)
    WS-->>IDE: atualiza nodes no grafo visual

    SRV->>OAI: POST /v1/chat/completions (scoring + narrativa)
    OAI-->>SRV: resposta do LLM
    SRV->>WS: node outputs (resposta do LLM)
    WS-->>IDE: atualiza Chat node no grafo visual

    SRV->>DB: PATCH recomendacoes SET status="done"
    SRV->>WS: graph completed
    WS-->>IDE: grafo finalizado — resultado visível no IDE
    IDE-->>Dev: inspeciona outputs de cada node
```
