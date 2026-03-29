# API Reference

> Fonte: https://rivet.ironcladapp.com/docs/api-reference
> Fonte: https://rivet.ironcladapp.com/docs/api-reference/getting-started-integration
> Fonte: https://rivet.ironcladapp.com/docs/api-reference/node/overview

## Pacotes

### @ironclad/rivet-core

Pacote ESM puro com as APIs core do Rivet. Sem dependências de browser ou Node.js. Funciona em qualquer ambiente JavaScript moderno.

### @ironclad/rivet-node

Binding Node.js para Rivet Core. Inclui helpers para carregar grafos do filesystem. **Reexporta todos os tipos do rivet-core.**

Requisito: Node.js 16+

### @ironclad/rivet-cli

CLI para executar grafos via terminal ou servir via HTTP. Ver [13-CLI.md](./13-CLI.md).

## Instalação

```bash
# Yarn
yarn add @ironclad/rivet-node

# NPM
npm install @ironclad/rivet-node

# pnpm
pnpm add @ironclad/rivet-node
```

## Uso Básico

```typescript
import * as Rivet from '@ironclad/rivet-node';
```

## Funções Principais

### runGraphInFile

Executa um grafo a partir de um arquivo `.rivet-project`.

```typescript
import { runGraphInFile, DataValue } from '@ironclad/rivet-node';

const outputs = await runGraphInFile('./myProject.rivet', {
  graph: 'My Graph Name',  // ID ou nome do grafo

  inputs: {
    myInput: 'hello world',                        // LooseDataValue (simplificado)
    myObject: { type: 'object', value: { k: 1 } }, // DataValue (explícito)
  },

  context: {
    myContext: 'global value',  // disponível em todos os grafos/subgrafos
  },

  externalFunctions: {
    helloWorld: async (...args: unknown[]): Promise<DataValue> => {
      return { type: 'string', value: 'hello world' };
    },
  },

  onUserEvent: {
    myEvent: (data: DataValue): Promise<void> => {
      console.log(data);
    },
  },

  openAiKey: 'my-openai-key',
  openAiOrganization: 'my-organization',
});
```

### loadProjectFromFile

Carrega um projeto de um arquivo.

```typescript
import { loadProjectFromFile } from '@ironclad/rivet-node';
const project = await loadProjectFromFile('./myProject.rivet');
```

### loadProjectFromString

Carrega um projeto de uma string (conteúdo do arquivo).

```typescript
import { loadProjectFromString } from '@ironclad/rivet-node';
const project = loadProjectFromString(fileContents);
```

### runGraph

Executa um grafo de um projeto já carregado.

```typescript
import { runGraph, loadProjectFromFile } from '@ironclad/rivet-node';

const project = await loadProjectFromFile('./myProject.rivet');
const outputs = await runGraph(project, {
  graph: 'My Graph',
  openAiKey: process.env.OPENAI_API_KEY,
  inputs: { name: 'Alice' },
});
```

### createProcessor

Cria um processador para controle mais granular da execução.

```typescript
import { createProcessor, loadProjectFromFile } from '@ironclad/rivet-node';

const project = await loadProjectFromFile('./myProject.rivet');
const processor = createProcessor(project, {
  graph: 'My Graph',
  openAiKey: process.env.OPENAI_API_KEY,
});

// Escutar eventos
processor.on('nodeStart', (data) => console.log('Node started:', data));
processor.on('partialOutput', (data) => console.log('Partial:', data));
processor.on('nodeFinish', (data) => console.log('Node finished:', data));

// Executar
const outputs = await processor.processGraph();
```

### startDebuggerServer

Inicia servidor de depuração para Remote Debugging.

```typescript
import { startDebuggerServer, runGraphInFile } from '@ironclad/rivet-node';

const debuggerServer = startDebuggerServer({
  port: 21888, // padrão
});

await runGraphInFile('./myProject.rivet', {
  graph: 'My Graph',
  remoteDebugger: debuggerServer,
});
```

## RunGraphOptions (Completo)

```typescript
export type RunGraphOptions = {
  graph: string;                                    // ID ou nome do grafo
  inputs?: Record<string, LooseDataValue>;          // Inputs do grafo
  context?: Record<string, LooseDataValue>;         // Valores de contexto (globais)
  remoteDebugger?: RivetDebuggerServer;             // Servidor de debug remoto
  nativeApi?: NativeApi;                            // API nativa (filesystem, etc.)
  externalFunctions?: {                             // Funções externas
    [key: string]: ExternalFunction;
  };
  onUserEvent?: {                                   // Handlers de eventos
    [key: string]: (data: DataValue | undefined) => void;
  };
  abortSignal?: AbortSignal;                        // Sinal de abortar execução

  // Settings
  openAiKey?: string;
  openAiOrganization?: string;
  openAiEndpoint?: string;

  // Event handlers
  onNodeStart?: (params) => void;
  onNodeFinish?: (params) => void;
  onPartialOutput?: (params) => void;
  // ... outros eventos
};
```

## LooseDataValue

Tipo que aceita tanto valores simples quanto DataValues explícitos:

```typescript
export type LooseDataValue = DataValue | string | number | boolean;

// Exemplos válidos:
const inputs = {
  texto: 'hello',                                    // string → type: 'string'
  numero: 42,                                        // number → type: 'number'
  flag: true,                                        // boolean → type: 'boolean'
  objeto: { type: 'object', value: { key: 'val' } }, // DataValue explícito
};
```

## Tipos Importantes

### DataValue

```typescript
interface DataValue {
  type: string;  // 'string' | 'number' | 'boolean' | 'object' | etc.
  value: any;
}
```

### RivetDebuggerServer

```typescript
interface RivetDebuggerServer {
  webSocketServer: WebSocketServer;
  on(event: string, handler: Function): void;
  off(event: string, handler: Function): void;
  // ...
}
```

### ExternalFunction

```typescript
type ExternalFunction = (
  context: InternalProcessContext,
  ...args: unknown[]
) => Promise<DataValue> | DataValue;
```
