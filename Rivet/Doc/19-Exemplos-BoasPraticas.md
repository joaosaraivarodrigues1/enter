# Exemplos e Boas Práticas

> Fonte: https://github.com/Ironclad/rivet-example
> Fonte: https://github.com/abrenneke/rivet-plugin-example
> Fonte: Documentação oficial do Rivet

---

## Exemplo Oficial: Chat Application

Repositório: https://github.com/Ironclad/rivet-example

Aplicação de chat completa usando Rivet com Express.js e Remote Debugger.

### Estrutura do Projeto

```
rivet-example/
├── chat.rivet-project          # Projeto Rivet com grafos
├── server/
│   ├── src/
│   │   ├── index.ts            # Setup Express
│   │   ├── Router.ts           # Rotas API + WebSocket debugger
│   │   ├── RivetDebuggerRoutes.ts
│   │   └── services/
│   │       ├── RivetRunner.ts  # Executor de grafos Rivet
│   │       └── CalculationService.ts
│   └── package.json
├── app/                        # Frontend
└── package.json
```

### Setup

```bash
git clone https://github.com/Ironclad/rivet-example
cd rivet-example
npm install
export OPENAI_API_KEY=sk-...
npm start
```

### Código do Runner (Padrão Recomendado)

```typescript
// server/src/services/RivetRunner.ts
import {
  GraphId, GraphInputs, GraphOutputs, coerceType,
  currentDebuggerState, loadProjectFromFile, runGraph
} from '@ironclad/rivet-node';
import { rivetDebuggerServerState } from '../RivetDebuggerRoutes.js';

export async function runMessageGraph(
  input: { type: 'assistant' | 'user'; message: string }[]
): Promise<string> {
  const outputs = await runRivetGraph(
    '5BI0Pfuu2naOUKqGUO-yZ' as GraphId,
    {
      messages: { type: 'object[]', value: input },
    }
  );
  return coerceType(outputs.output, 'string');
}

export async function runRivetGraph(
  graphId: GraphId,
  inputs?: GraphInputs
): Promise<GraphOutputs> {
  // Usa projeto uploaded pelo debugger ou carrega do disco
  const project = currentDebuggerState.uploadedProject
    ?? await loadProjectFromFile('../chat.rivet-project');

  return await runGraph(project, {
    graph: graphId,
    openAiKey: process.env.OPENAI_API_KEY!,
    inputs,
    remoteDebugger: rivetDebuggerServerState.server ?? undefined,
    externalFunctions: {
      calculate: async (_context, calculationStr) => {
        if (typeof calculationStr !== 'string') {
          throw Error('expected a string input');
        }
        const value = calculateExpression(calculationStr);
        return value
          ? { type: 'number', value }
          : { type: 'string', value: 'Error calculating' };
      },
    },
  });
}
```

### Código do Router (API + Remote Debugger)

```typescript
// server/src/Router.ts
import { Router } from 'express';
import { WebSocketServer } from 'ws';
import { startRivetDebuggerServer } from './RivetDebuggerRoutes.js';
import { runMessageGraph, runRivetGraph } from './services/RivetRunner.js';

const apiRouter = Router();

// Endpoint da API
apiRouter.post('/rivet-example', async (req, res) => {
  const input = req.body.input;
  const response = await runMessageGraph(input);
  res.json({ output: response });
});

// WebSocket para Remote Debugger
const debuggerServer = new WebSocketServer({ noServer: true });
startRivetDebuggerServer(debuggerServer, {
  dynamicGraphRun: async ({ inputs, graphId }) => {
    await runRivetGraph(graphId, inputs);
  },
});

export default apiRouter;
```

---

## Boas Práticas

### 1. Organização de Projetos

- **Um arquivo `.rivet-project` por domínio** — não misturar grafos de domínios diferentes
- **Nomes descritivos** para grafos e nodes — facilita navegação e debug
- **Descrições** em grafos e nodes — documenta intenção
- **Armazenar em Git** — projetos Rivet são JSON, funcionam bem com controle de versão
- **Um "Main Graph"** como entry point — grafos auxiliares como subgrafos

### 2. Segurança de API Keys

**Nunca hardcodar API keys nos grafos.** Usar:

```typescript
// Contexto para valores globais seguros
const processor = Rivet.createProcessor({
  contextValues: {
    supabaseKey: process.env.SUPABASE_KEY,
    openAiKey: process.env.OPENAI_API_KEY,
  },
});
```

No grafo, acessar via **Context Node** ou `{{@context.supabaseKey}}`.

### 3. External Functions para Lógica de Negócio

Regra de ouro: **grafos para orquestração de IA, External Functions para lógica de negócio.**

```
BOM:
  Grafo: prompt → LLM → parse → External Call (salvar no DB) → resposta

RUIM:
  Grafo: prompt → LLM → parse → HTTP Call (SQL raw) → parse manual → resposta
```

External Functions benefícios:
- Tipagem forte com TypeScript
- Acesso a ORMs e SDKs (Supabase, Prisma, etc.)
- Error handling robusto
- Testáveis unitariamente
- Reutilizáveis entre grafos

### 4. Subgrafos para Modularidade

Dividir grafos complexos em subgrafos reutilizáveis:

```
Subgrafos comuns:
  - "Classify Intent" — classifica intenção do usuário
  - "Retrieve Context" — busca contexto relevante (RAG)
  - "Generate Response" — gera resposta com contexto
  - "Validate Output" — valida output do LLM
  - "Error Handler" — tratamento de erros padronizado
```

### 5. Splitting para Processamento Paralelo

Usar splitting quando:
- Processar múltiplos documentos
- Fazer múltiplas chamadas de API
- Gerar embeddings para vários textos
- Executar variações de prompts em paralelo

**Cuidado:** Limitar `max split amount` para evitar rate limiting em APIs.

### 6. Error Handling

Padrões recomendados:

```
Padrão 1: Use Error Output (External Call)
  [External Call] → Result → [continuar normalmente]
                  → Error  → [If/Else] → [fallback ou mensagem de erro]

Padrão 2: Coalesce
  [Operação principal] → [Coalesce] → resultado
  [Fallback]           ↗

Padrão 3: Abort Graph
  [Validação] → [If: inválido?] → True → [Abort Graph: "Input inválido"]
                                → False → [continuar]
```

### 7. Context Values para Configuração Global

```typescript
contextValues: {
  // Ambiente
  environment: 'production',

  // Data atual (para prompts temporais)
  currentDate: new Date().toISOString(),

  // Configurações
  maxTokens: 4096,
  model: 'gpt-4',

  // IDs de sessão
  userId: req.user.id,
  sessionId: req.sessionId,
}
```

### 8. Trivet para Testes Automatizados

- Criar test suites para cada grafo importante
- Testar edge cases (inputs vazios, inputs inválidos)
- Usar validation graphs para validações complexas
- Integrar com CI/CD via biblioteca Trivet

### 9. Recordings para Debug

- Gravar execuções em produção para debug pós-mortem
- Útil quando o problema é intermitente
- Compartilhar recordings com a equipe

### 10. Remote Debugger em Desenvolvimento

Setup recomendado para desenvolvimento:

```typescript
// Só ativar debugger em desenvolvimento
const debuggerServer = process.env.NODE_ENV === 'development'
  ? startDebuggerServer({ port: 21888 })
  : undefined;

await runGraph(project, {
  remoteDebugger: debuggerServer,
  // ...
});
```

---

## Padrões de Arquitetura

### Padrão 1: API Server + Rivet Backend

```
[Cliente] → [Express API] → [Rivet Runner] → [Grafo Rivet]
                                  ↕
                            [External Functions]
                                  ↕
                          [Supabase / APIs / DB]
```

### Padrão 2: CLI Pipeline

```
[Input JSON] → [rivet-cli run] → [Output JSON] → [Próximo step do pipeline]
```

### Padrão 3: HTTP Service (rivet serve)

```
[Qualquer cliente HTTP] → [rivet serve :3000] → [Grafo Rivet] → [JSON Response]
```

### Padrão 4: Agent Loop com Supabase

```
[User Message]
      ↓
[Loop Controller]
  ↓ (Loop Body)
  [Chat Node (com tools/functions)]
      ↓
  [Match: tool_call?]
    → "search_docs" → [External Call: supabaseSearchVectors] → volta ao loop
    → "save_data"   → [External Call: supabaseInsert]        → volta ao loop
    → "none"        → Continue = false
  ↓ (Break)
[Graph Output: resposta final]
```

---

## Links de Referência

| Recurso | URL |
|---------|-----|
| Documentação oficial | https://rivet.ironcladapp.com/docs |
| GitHub Rivet | https://github.com/Ironclad/rivet |
| Exemplo de chat | https://github.com/Ironclad/rivet-example |
| Plugin example (TypeScript) | https://github.com/abrenneke/rivet-plugin-example |
| Plugin example (Python exec) | https://github.com/abrenneke/rivet-plugin-example-python-exec |
| NPM rivet-node | https://www.npmjs.com/package/@ironclad/rivet-node |
| NPM rivet-core | https://www.npmjs.com/package/@ironclad/rivet-core |
| NPM rivet-cli | https://www.npmjs.com/package/@ironclad/rivet-cli |
| Discord | https://discord.gg/qT8B2gv9Mg |
| Node Reference | https://rivet.ironcladapp.com/docs/node-reference/all-nodes |
| API Reference | https://rivet.ironcladapp.com/docs/api-reference |
| Supabase pgvector docs | https://supabase.com/docs/guides/database/extensions/pgvector |
| MCP Protocol | https://modelcontextprotocol.io/introduction |
