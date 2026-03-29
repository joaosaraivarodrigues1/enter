# Recordings (Gravação e Replay)

> Fonte: https://rivet.ironcladapp.com/docs/user-guide/recordings
> Fonte: https://rivet.ironcladapp.com/docs/api-reference/recording

## Visão Geral

Recordings permitem gravar execuções de grafos Rivet e reproduzi-las posteriormente no Rivet IDE. Útil para:

- Debug pós-execução
- Análise de comportamento do agente
- Compartilhar execuções com a equipe
- Documentação de comportamento

---

## Gerar Recordings (via código)

### 1. Instanciar o ExecutionRecorder

```typescript
import { ExecutionRecorder } from '@ironclad/rivet-node';

const recorder = new ExecutionRecorder({
  includePartialOutputs: true,  // streaming (padrão: true)
  includeTrace: true,           // eventos de debug trace (padrão: true)
});
```

Ambas as opções aumentam o tamanho do arquivo de gravação.

### 2. Gravar a Execução

Usar `createProcessor` (não `runGraph`) para obter a instância do `GraphProcessor`:

```typescript
import { createProcessor } from '@ironclad/rivet-node';

const processor = createProcessor({
  // opções...
});

recorder.record(processor);

// Executar o grafo
const outputs = await processor.processGraph();
```

### 3. Salvar a Gravação

```typescript
import { writeFile } from 'fs/promises';

const serializedRecording = recorder.serialize();
await writeFile(
  'my-recording.rivet-recording',
  serializedRecording,
  { encoding: 'utf8' }
);
```

### Formato do Arquivo

O formato `.rivet-recording` é um arquivo JSONL (JSON Lines), onde cada linha é um evento JSON da execução. Ao reproduzir, o `GraphProcessor` re-emite cada evento como se estivesse executando.

---

## Reproduzir Recordings no Rivet IDE

### Carregar Recording

- **Opção 1:** Menu `...` > **Load Recording**
- **Opção 2:** Atalho `Cmd/Ctrl + Shift + O` e selecionar o arquivo

Quando carregado, a borda do Rivet fica **amarela** e a opção "Unload Recording" aparece.

### Reproduzir

1. O botão **Play** vira **"Play Recording"**
2. Clicar para reproduzir
3. Chat Nodes são reproduzidos em taxa fixa (configurável em **Settings > General**)
4. Nodes intermediários entre Chats são reproduzidos instantaneamente

### Controles durante Reprodução

| Ação | Descrição |
|------|-----------|
| **Pause** | Pausa a reprodução no ponto atual |
| **Resume** | Retoma a reprodução |
| **Abort** | Para a reprodução (clicar Play Recording reinicia do início) |

### Descarregar Recording

Clicar **"Unload Recording"** no Action Bar para voltar à execução normal.
