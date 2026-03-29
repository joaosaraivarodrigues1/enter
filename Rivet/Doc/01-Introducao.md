# Introdução ao Rivet

> Fonte: https://rivet.ironcladapp.com/docs

Rivet é um ambiente de desenvolvimento integrado (IDE) e biblioteca TypeScript para criação de agentes de IA usando uma interface visual baseada em grafos. Permite construir cadeias de prompts e agentes de IA complexos de forma visual.

## Componentes Principais

### Rivet Application (IDE)

O editor/IDE visual para criar cadeias de prompts e agentes de IA. Permite:

- Construir arquivos de projeto Rivet (`.rivet-project`) que podem ser executados dentro da sua aplicação
- Designer de prompts para ajuste fino
- Variações de nodes para testes A/B
- Testes integrados (Trivet) para garantir que os grafos funcionam como esperado

### Rivet Core / Rivet Node

Bibliotecas TypeScript que permitem executar projetos gerados pelo Rivet Application:

- **`@ironclad/rivet-core`** — Pacote ESM puro, sem dependências de browser ou Node.js. Pode ser usado em qualquer ambiente JavaScript moderno (incluindo PythonMonkey).
- **`@ironclad/rivet-node`** — Binding Node.js para Rivet Core. Inclui helpers para carregar grafos do filesystem e executá-los. Reexporta todos os tipos do rivet-core.

```bash
yarn add @ironclad/rivet-node
```

```typescript
import * as Rivet from '@ironclad/rivet-node';

const result = await Rivet.runGraphInFile('./myProject.rivet', {
  graph: 'My Graph Name',
  inputs: { myInput: 'hello world' },
  openAiKey: 'my-openai-key',
});
```

### Rivet CLI

Interface de linha de comando para executar grafos Rivet diretamente do terminal ou servir via HTTP.

```bash
npx @ironclad/rivet-cli run my-project.rivet-project --input name=Alice
npx @ironclad/rivet-cli serve --port 3000
```

## Editor Baseado em Nodes

O editor visual permite:

- Criar, configurar e depurar cadeias de prompts de IA
- Visualizar o fluxo de dados e o estado do agente em qualquer ponto
- Ver input/output de cada node e respostas da IA em tempo real
- Identificar e corrigir problemas rapidamente

## Biblioteca de Nodes

Tipos essenciais de nodes incluem:

| Categoria | Exemplos de Nodes |
|-----------|-------------------|
| **Texto** | Text, Prompt, Chunk, Join, Split Text, Extract Regex, To JSON, To YAML |
| **IA** | Chat, Assemble Prompt, GPT Function, Get Embedding, Trim Chat Messages |
| **MCP** | MCP Discovery, MCP Tool Call, MCP Get Prompt |
| **Listas** | Array, Filter, Pop, Shuffle, Slice |
| **Números** | Evaluate, Number, RNG |
| **Objetos** | Extract JSON, Extract Object Path, Extract YAML, Object |
| **Dados** | Audio, Bool, Hash, Image |
| **Lógica** | Abort Graph, Coalesce, Compare, Delay, If, If/Else, Match, Passthrough, Race Inputs |
| **I/O** | Graph Input, Graph Output, Read File, Read Directory, User Input, HTTP Call, Vector Store, Vector KNN |
| **Avançado** | Code, Comment, Context, External Call, Loop Controller, Subgraph, Set/Get Global, Raise/Wait Event |

## Live Debugging

O Rivet oferece depuração ao vivo das cadeias de IA enquanto executam, permitindo monitorar o estado do agente em tempo real.

### Remote Debugging

Suporta depuração remota — conectar-se a um servidor Rivet remoto para depurar agentes rodando em produção ou em outro ambiente.

## Links Úteis

- Documentação: https://rivet.ironcladapp.com/docs
- GitHub: https://github.com/Ironclad/rivet
- Exemplo: https://github.com/Ironclad/rivet-example
- Discord: https://discord.gg/qT8B2gv9Mg
- NPM Core: https://www.npmjs.com/package/@ironclad/rivet-core
- NPM Node: https://www.npmjs.com/package/@ironclad/rivet-node
