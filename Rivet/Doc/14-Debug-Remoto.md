# Live Debugging e Remote Debugging

> Fonte: https://rivet.ironcladapp.com/docs/user-guide/remote-debugging
> Fonte: https://rivet.ironcladapp.com/docs/api-reference/remote-debugging

## Live Debugging (Local)

O Rivet oferece depuração ao vivo enquanto os grafos executam:

- Ver o estado de cada node em tempo real
- Visualizar inputs e outputs de cada node
- Streaming de respostas do LLM em tempo real
- Pausar e retomar execução a qualquer momento
- Abortar execução se necessário

---

## Remote Debugging

Permite integrar o Rivet Core/Node numa aplicação externa, executar grafos nessa aplicação, mas ver a execução ao vivo no Rivet IDE.

### Casos de Uso

- Debug de grafos em produção
- Debug de grafos com **External Call Nodes** (que só funcionam com host application)
- Debug em ambientes diferentes do Rivet IDE
- Testes com dados reais da sua aplicação

### Como Funciona

```
[Rivet IDE] <-- WebSocket --> [Sua Aplicação com Rivet Node]
                                 |
                                 v
                         [Execução do Grafo]
```

---

## Setup no Servidor (Sua Aplicação)

### 1. Instalar rivet-node

```bash
yarn add @ironclad/rivet-node
```

### 2. Iniciar o Debugger Server

```typescript
import { startDebuggerServer, runGraphInFile } from '@ironclad/rivet-node';

// Chamar uma vez na inicialização
const debuggerServer = startDebuggerServer({
  port: 21888, // Padrão. Pode customizar.
});

// Passar o debugger em cada execução de grafo
await runGraphInFile('./myProject.rivet', {
  graph: 'My Graph Name',
  remoteDebugger: debuggerServer,
  openAiKey: process.env.OPENAI_API_KEY,
  externalFunctions: {
    // suas funções externas...
  },
});
```

**Importante:** Chamar `startDebuggerServer` apenas **uma vez**. A mesma instância deve ser reutilizada em todas as chamadas de `runGraph` / `runGraphInFile`.

### 3. Opções Avançadas

O `startDebuggerServer` suporta opções avançadas:

```typescript
const debuggerServer = startDebuggerServer({
  port: 21888,

  // Permite que o Rivet IDE execute grafos no servidor
  dynamicGraphRun: async ({ inputs, graphId }) => {
    await runRivetGraph(graphId, inputs);
  },

  // Permite que o Rivet IDE faça upload do grafo ao servidor
  allowGraphUpload: true,
});
```

---

## Conectar pelo Rivet IDE

### Método 1: Menu

1. Clicar no menu `...` no Action Bar
2. Selecionar **Remote Debugger**
3. Inserir URI WebSocket: `ws://localhost:21888`

### Método 2: Atalho

- Pressionar **F5** para abrir o diálogo do Remote Debugger

### URI Padrão

```
ws://localhost:21888
```

Para servidor remoto:
```
ws://meu-servidor.com:21888
```

---

## Usando o Remote Debugger

### Visualização em Tempo Real

Quando o debugger está conectado:
- Toda execução de grafo no servidor é **imediatamente visível** no Rivet
- Nodes mostram seus inputs/outputs à medida que executam
- Respostas do LLM são streamadas em tempo real

### Controles

| Ação | Disponível | Descrição |
|------|------------|-----------|
| **Pausar** | Sim | Pausa execução no servidor |
| **Retomar** | Sim | Retoma a partir do ponto de pausa |
| **Abortar** | Sim | Aborta execução no servidor |
| **Run** | Se `dynamicGraphRun` configurado | Executa o grafo aberto no servidor |

### Executar Grafos Editados

Se `allowGraphUpload` estiver ativo no servidor:
- Clicar **Run** no Rivet envia o grafo atual ao servidor
- O grafo é executado sem precisar salvar ou deploy do projeto
- Útil para iteração rápida durante desenvolvimento

---

## Exemplo Completo: Express + Rivet + Remote Debugger

Extraído de https://github.com/Ironclad/rivet-example:

```typescript
// Router.ts
import { Router } from 'express';
import { WebSocketServer } from 'ws';
import {
  rivetDebuggerSocketRoutes,
  startRivetDebuggerServer
} from './RivetDebuggerRoutes.js';
import { runMessageGraph, runRivetGraph } from './services/RivetRunner.js';

const apiRouter = Router();

// Endpoint para executar grafo
apiRouter.post('/rivet-example', async (req, res) => {
  const input = req.body.input as { type: 'user' | 'assistant'; message: string }[];
  const response = await runMessageGraph(input);
  res.json({ output: response });
});

// WebSocket para Rivet debugger
const debuggerServer = new WebSocketServer({ noServer: true });
startRivetDebuggerServer(debuggerServer, {
  dynamicGraphRun: async ({ inputs, graphId }) => {
    await runRivetGraph(graphId, inputs);
  },
});
rivetDebuggerSocketRoutes(apiRouter, {
  path: '/rivet/debugger',
  wss: debuggerServer,
});

export default apiRouter;
```

```typescript
// RivetRunner.ts
import {
  GraphId, GraphInputs, GraphOutputs, coerceType,
  currentDebuggerState, loadProjectFromFile, runGraph
} from '@ironclad/rivet-node';
import { rivetDebuggerServerState } from '../RivetDebuggerRoutes.js';

export async function runRivetGraph(
  graphId: GraphId,
  inputs?: GraphInputs
): Promise<GraphOutputs> {
  const project = currentDebuggerState.uploadedProject
    ?? await loadProjectFromFile('../chat.rivet-project');

  return await runGraph(project, {
    graph: graphId,
    openAiKey: process.env.OPENAI_API_KEY!,
    inputs,
    remoteDebugger: rivetDebuggerServerState.server ?? undefined,
    externalFunctions: {
      calculate: async (_context, calculationStr) => {
        // Função externa de exemplo
        return { type: 'number', value: eval(calculationStr as string) };
      },
    },
  });
}
```
