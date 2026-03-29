# Integração Rivet + Supabase

> **FOCO PRINCIPAL** — Rotas de conexão entre Rivet e Supabase

O Rivet **não possui um plugin nativo para Supabase**. Porém, há 4 caminhos claros e bem documentados para integrar Rivet com Supabase, do mais simples ao mais avançado.

---

## Sumário dos 4 Caminhos

| # | Método | Complexidade | Onde roda | Melhor para |
|---|--------|-------------|-----------|-------------|
| 1 | HTTP Call Node | Baixa | Direto no grafo Rivet | CRUD simples, prototipação rápida |
| 2 | External Call Node | Média | Host Node.js | Lógica complexa, queries tipadas, autenticação |
| 3 | Vector Store + pgvector | Média-Alta | Host Node.js | RAG, busca semântica, embeddings |
| 4 | MCP Node + Supabase MCP | Média | Rivet + MCP Server | Acesso genérico via protocolo MCP |

---

## Caminho 1: HTTP Call Node (REST API direta)

O método mais simples. Usa o node **HTTP Call** para chamar a Supabase REST API (PostgREST) diretamente do grafo.

### Pré-requisitos

- URL do projeto Supabase: `https://<project-ref>.supabase.co`
- API Key (anon ou service_role)
- **Executor Node** ativado (evitar problemas de CORS)

### Configuração de Headers

Todos os requests à Supabase REST API precisam dos headers:

```json
{
  "apikey": "<SUPABASE_ANON_KEY>",
  "Authorization": "Bearer <SUPABASE_ANON_KEY>",
  "Content-Type": "application/json"
}
```

**Boa prática:** Usar **Context Node** para passar a API key de forma segura (não hardcodar no grafo):

```typescript
// No host application
const processor = Rivet.createProcessor({
  contextValues: {
    supabaseUrl: 'https://xyzproject.supabase.co',
    supabaseKey: process.env.SUPABASE_ANON_KEY,
  },
});
```

No grafo, usar `{{@context.supabaseKey}}` em Text Nodes para compor headers.

### Exemplo 1: SELECT (Leitura)

```
Grafo Rivet:

[Context Node: supabaseUrl] → [Text Node: "{{supabaseUrl}}/rest/v1/usuarios?select=*"]
                                        ↓
                               [HTTP Call Node]
                               Method: GET
                               Headers: {"apikey": "{{@context.supabaseKey}}", "Authorization": "Bearer {{@context.supabaseKey}}"}
                                        ↓
                               [Extract JSON Node] → dados dos usuários
```

**URL PostgREST padrão:**
```
GET  /rest/v1/<tabela>?select=*
GET  /rest/v1/<tabela>?select=nome,email&idade=gt.18
GET  /rest/v1/<tabela>?select=*&order=created_at.desc&limit=10
```

### Exemplo 2: INSERT (Criação)

```
[Object Node] → {"nome": "João", "email": "joao@email.com"}
      ↓
[To JSON Node]
      ↓
[HTTP Call Node]
  Method: POST
  URL: https://<project>.supabase.co/rest/v1/usuarios
  Headers: {
    "apikey": "<key>",
    "Authorization": "Bearer <key>",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
  }
  Body: (conectado do To JSON)
      ↓
[Extract JSON Node] → registro criado
```

### Exemplo 3: UPDATE

```
URL: https://<project>.supabase.co/rest/v1/usuarios?id=eq.123
Method: PATCH
Body: {"nome": "João Atualizado"}
Headers: mesmos + "Prefer": "return=representation"
```

### Exemplo 4: DELETE

```
URL: https://<project>.supabase.co/rest/v1/usuarios?id=eq.123
Method: DELETE
Headers: mesmos
```

### Exemplo 5: RPC (Funções PostgreSQL)

Para chamar funções SQL do Supabase:

```
URL: https://<project>.supabase.co/rest/v1/rpc/minha_funcao
Method: POST
Body: {"param1": "valor1", "param2": 42}
```

### Filtros PostgREST Comuns

| Filtro | Significado | Exemplo |
|--------|-------------|---------|
| `eq` | Igual | `?campo=eq.valor` |
| `neq` | Diferente | `?campo=neq.valor` |
| `gt` | Maior que | `?idade=gt.18` |
| `gte` | Maior ou igual | `?idade=gte.18` |
| `lt` | Menor que | `?idade=lt.65` |
| `lte` | Menor ou igual | `?idade=lte.65` |
| `like` | LIKE | `?nome=like.*João*` |
| `ilike` | ILIKE (case insensitive) | `?nome=ilike.*joão*` |
| `in` | IN | `?id=in.(1,2,3)` |
| `is` | IS (null/true/false) | `?deletado=is.null` |
| `order` | ORDER BY | `?order=nome.asc` |
| `limit` | LIMIT | `?limit=10` |
| `offset` | OFFSET | `?offset=20` |

---

## Caminho 2: External Call Node (via Host Node.js)

O método mais robusto e recomendado para produção. Define `externalFunctions` no host application usando `@supabase/supabase-js`.

### Setup do Host

```bash
yarn add @ironclad/rivet-node @supabase/supabase-js
```

### Código do Host Application

```typescript
import { runGraphInFile } from '@ironclad/rivet-node';
import { createClient } from '@supabase/supabase-js';

// Criar cliente Supabase
const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

// Executar grafo com funções externas para Supabase
const outputs = await runGraphInFile('./myProject.rivet', {
  graph: 'Main Graph',
  openAiKey: process.env.OPENAI_API_KEY!,

  externalFunctions: {
    // --- CRUD Operations ---

    supabaseSelect: async (_context, table: any, query: any) => {
      const { data, error } = await supabase
        .from(table as string)
        .select(query as string || '*');

      if (error) throw new Error(error.message);
      return { type: 'object', value: data };
    },

    supabaseInsert: async (_context, table: any, record: any) => {
      const { data, error } = await supabase
        .from(table as string)
        .insert(record)
        .select();

      if (error) throw new Error(error.message);
      return { type: 'object', value: data };
    },

    supabaseUpdate: async (_context, table: any, id: any, updates: any) => {
      const { data, error } = await supabase
        .from(table as string)
        .update(updates)
        .eq('id', id)
        .select();

      if (error) throw new Error(error.message);
      return { type: 'object', value: data };
    },

    supabaseDelete: async (_context, table: any, id: any) => {
      const { error } = await supabase
        .from(table as string)
        .delete()
        .eq('id', id);

      if (error) throw new Error(error.message);
      return { type: 'boolean', value: true };
    },

    // --- RPC (Chamar funções PostgreSQL) ---

    supabaseRpc: async (_context, funcName: any, params: any) => {
      const { data, error } = await supabase
        .rpc(funcName as string, params as Record<string, unknown>);

      if (error) throw new Error(error.message);
      return { type: 'object', value: data };
    },

    // --- Auth ---

    supabaseGetUser: async (_context, token: any) => {
      const { data, error } = await supabase.auth.getUser(token as string);
      if (error) throw new Error(error.message);
      return { type: 'object', value: data.user };
    },

    // --- Storage ---

    supabaseUpload: async (_context, bucket: any, path: any, content: any) => {
      const { data, error } = await supabase.storage
        .from(bucket as string)
        .upload(path as string, content);

      if (error) throw new Error(error.message);
      return { type: 'object', value: data };
    },

    supabaseGetPublicUrl: async (_context, bucket: any, path: any) => {
      const { data } = supabase.storage
        .from(bucket as string)
        .getPublicUrl(path as string);

      return { type: 'string', value: data.publicUrl };
    },
  },
});
```

### No Grafo Rivet

Para cada operação, usar **External Call Node**:

```
[Array Node: ["usuarios", "*"]] → [External Call Node: "supabaseSelect"]
                                          ↓
                                   [Extract Object Path: "$.0.nome"]
                                          ↓
                                   [Text Node: "Usuário: {{input}}"]
```

**Lembrete:** External Call Nodes só funcionam com host application. No Rivet IDE, usar **Remote Debugger** (ver [14-Debug-Remoto.md](./14-Debug-Remoto.md)).

### Error Handling

Ativar "Use Error Output" no External Call Node:

```
[External Call: "supabaseSelect"]
      ↓ Result          ↓ Error
  [continuar]     [If Node: error existe?]
                         ↓
                  [Text Node: "Erro: {{input}}"]
```

---

## Caminho 3: Vector Store + Supabase pgvector (RAG)

Padrão para Retrieval-Augmented Generation (RAG) com Supabase como banco vetorial.

### 1. Setup do Supabase (SQL)

Executar no SQL Editor do Supabase:

```sql
-- Habilitar extensão pgvector
create extension if not exists vector;

-- Tabela de documentos com embeddings
create table documents (
  id bigserial primary key,
  content text not null,
  metadata jsonb default '{}'::jsonb,
  embedding vector(1536)  -- 1536 para OpenAI text-embedding-ada-002/3-small
);

-- Índice para busca vetorial eficiente
create index on documents
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- Função de busca por similaridade
create or replace function match_documents(
  query_embedding vector(1536),
  match_threshold float default 0.78,
  match_count int default 10
)
returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    id,
    content,
    metadata,
    1 - (embedding <=> query_embedding) as similarity
  from documents
  where 1 - (embedding <=> query_embedding) > match_threshold
  order by (embedding <=> query_embedding) asc
  limit match_count;
$$;
```

### 2. External Functions para Vector Operations

```typescript
externalFunctions: {
  // Armazenar documento com embedding
  supabaseStoreVector: async (_context, content: any, embedding: any, metadata: any) => {
    const { data, error } = await supabase
      .from('documents')
      .insert({
        content: content as string,
        embedding: embedding as number[],
        metadata: metadata || {},
      })
      .select();

    if (error) throw new Error(error.message);
    return { type: 'object', value: data };
  },

  // Busca por similaridade (KNN)
  supabaseSearchVectors: async (_context, embedding: any, threshold: any, count: any) => {
    const { data, error } = await supabase
      .rpc('match_documents', {
        query_embedding: embedding as number[],
        match_threshold: (threshold as number) || 0.78,
        match_count: (count as number) || 10,
      });

    if (error) throw new Error(error.message);
    return { type: 'object', value: data };
  },
}
```

### 3. Fluxo RAG no Grafo Rivet

```
INDEXAÇÃO (armazenar documentos):

[Read File] → [Chunk Node (overlap 10%)] → [Get Embedding Node (split)]
                                                    ↓
                                      [External Call: "supabaseStoreVector" (split)]


BUSCA (query do usuário):

[User Input: "pergunta"] → [Get Embedding Node]
                                    ↓
                    [External Call: "supabaseSearchVectors"]
                                    ↓
                    [Extract Object Path: "$.*.content"]
                                    ↓
                    [Join Node (separator: "\n---\n")]
                                    ↓
[Assemble Prompt]
  System: "Responda baseado nos documentos: {{contexto}}"
  User: "{{pergunta}}"
          ↓
    [Chat Node] → resposta com contexto
```

### 4. Diagrama Completo do Fluxo RAG

```
┌─────────────────────────────────────────────────────────────┐
│                    INDEXAÇÃO                                  │
│                                                              │
│  [Documento] → [Chunk] → [Get Embedding] → [Store Vector]   │
│                              (OpenAI)        (Supabase)      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    BUSCA (RAG)                                │
│                                                              │
│  [Pergunta] → [Get Embedding] → [Search Vectors] → [Join]   │
│                   (OpenAI)        (Supabase)          │      │
│                                                       ↓      │
│             [Chat Node] ← [Assemble Prompt] ← [Contexto]    │
│                  ↓                                           │
│            [Resposta]                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Caminho 4: MCP Node + Supabase MCP Server

Usar o servidor MCP oficial do Supabase para interagir via protocolo MCP.

### 1. Configurar Supabase MCP Server

No Rivet, ir a `Project > Edit MCP Configuration`:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--supabase-url", "https://<project-ref>.supabase.co",
        "--supabase-key", "<SUPABASE_SERVICE_ROLE_KEY>"
      ]
    }
  }
}
```

Ou se instalado globalmente:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "supabase-mcp-server",
      "args": [],
      "env": {
        "SUPABASE_URL": "https://<project-ref>.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "<key>"
      }
    }
  }
}
```

### 2. Descobrir Tools Disponíveis

```
[MCP Discovery Node]
  Transport: STDIO
  Server ID: supabase
      ↓
  Lista de tools: query, insert, update, delete, rpc, etc.
```

### 3. Chamar Tools

```
[Text Node: "query"] → Tool Name
[Object Node: {"table": "usuarios", "select": "*", "limit": 10}] → Tool Arguments
      ↓
[MCP Tool Call Node]
  Transport: STDIO
  Server ID: supabase
      ↓
  [Extract JSON] → dados retornados
```

### Vantagens do MCP

- Protocolo padronizado — funciona com qualquer servidor MCP
- Não requer código TypeScript no host
- Supabase MCP Server implementa operações CRUD + mais
- Descoberta automática de capabilities

### Limitações do MCP

- Requer executor Node no Rivet
- Autenticação HTTP ainda em desenvolvimento
- Menos controle granular que External Call
- Performance pode ser menor (overhead do protocolo MCP)

---

## Comparativo dos 4 Caminhos

| Aspecto | HTTP Call | External Call | Vector+pgvector | MCP |
|---------|-----------|--------------|-----------------|-----|
| **Setup** | Mínimo | Código Node.js | SQL + Node.js | Config JSON |
| **CORS** | Problema (Browser) | N/A | N/A | N/A |
| **Tipagem** | Manual | Forte (supabase-js) | Forte | Via schema |
| **Auth** | Headers manuais | supabase-js nativo | supabase-js | Config do server |
| **Vectors** | Não prático | Sim (via RPC) | Otimizado | Depende do server |
| **Debugging** | Visível no grafo | Requer Remote Debug | Requer Remote Debug | Visível no grafo |
| **Produção** | Possível | Recomendado | Recomendado | Experimental |

---

## Recomendações

1. **Prototipação rápida / CRUD simples** → Caminho 1 (HTTP Call)
2. **Produção com lógica complexa** → Caminho 2 (External Call)
3. **RAG / Busca semântica** → Caminho 3 (Vector + pgvector)
4. **Exploração / ferramentas genéricas** → Caminho 4 (MCP)
5. **Combinação ideal:** External Call para operações + MCP para discovery
