# Rivet CLI

> Fonte: https://rivet.ironcladapp.com/docs/cli
> Fonte: https://rivet.ironcladapp.com/docs/cli/run
> Fonte: https://rivet.ironcladapp.com/docs/cli/serve

## Instalação

```bash
# Uso direto com npx (sem instalar)
npx @ironclad/rivet-cli --help

# Instalação global
npm install -g @ironclad/rivet-cli
rivet --help
```

---

## Comando: `rivet run`

Executa um grafo Rivet com inputs fornecidos.

### Uso Básico

```bash
# Executar grafo principal
npx @ironclad/rivet-cli run my-project.rivet-project

# Executar grafo específico
npx @ironclad/rivet-cli run my-project.rivet-project "My Graph"

# Com inputs
npx @ironclad/rivet-cli run my-project.rivet-project --input name=Alice --input age=30

# Com inputs JSON via stdin
echo '{"name": "Alice", "age": 30}' | npx @ironclad/rivet-cli run my-project.rivet-project --inputs-stdin

# Com context values
npx @ironclad/rivet-cli run my-project.rivet-project --context apiKey=sk-123

# Incluir custo no output
npx @ironclad/rivet-cli run my-project.rivet-project --include-cost
```

### Output

JSON com cada Graph Output Node como chave:

```json
{
  "output1": {
    "type": "string",
    "value": "Hello, World!"
  },
  "output2": {
    "type": "number",
    "value": 42
  }
}
```

### Opções

| Opção | Descrição |
|-------|-----------|
| `--input key=value` | Define um input (pode repetir) |
| `--inputs-stdin` | Lê inputs como JSON do stdin |
| `--context key=value` | Define um context value (pode repetir) |
| `--include-cost` | Inclui custo da execução no JSON de output |

---

## Comando: `rivet serve`

Serve um projeto Rivet via servidor HTTP local.

### Uso Básico

```bash
# Servidor com settings padrão (porta 3000)
npx @ironclad/rivet-cli serve

# Porta customizada
npx @ironclad/rivet-cli serve --port 8080

# Projeto específico
npx @ironclad/rivet-cli serve my-project.rivet-project --port 8080

# Modo desenvolvimento (relê arquivo a cada request)
npx @ironclad/rivet-cli serve --dev
```

### Endpoints

| Endpoint | Descrição |
|----------|-----------|
| `POST /` | Executa o grafo principal |
| `POST /:graphId` | Executa grafo específico (requer `--allow-specifying-graph-id`) |

### Request Body

JSON com inputs do grafo:

```json
{
  "name": "Alice",
  "age": 30,
  "complexInput": {
    "type": "object",
    "value": { "key1": "value1" }
  }
}
```

### Response

```json
{
  "greeting": {
    "type": "string",
    "value": "Hello, Alice!"
  },
  "canVote": {
    "type": "boolean",
    "value": true
  }
}
```

### Exemplo com curl

```bash
curl -X POST http://localhost:3000 \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "age": 30}'
```

### Opções do Servidor

| Opção | Descrição | Padrão |
|-------|-----------|--------|
| `--port <n>` | Porta do servidor | 3000 |
| `--dev` | Modo dev (relê projeto a cada request) | false |
| `--graph <name>` | Grafo padrão a executar | Main Graph |
| `--allow-specifying-graph-id` | Permite `POST /:graphId` | false |
| `--openai-api-key` | API key OpenAI (ou env `OPENAI_API_KEY`) | - |
| `--openai-endpoint` | Endpoint OpenAI customizado | api.openai.com |
| `--openai-organization` | Organization ID | - |
| `--expose-cost` | Incluir custo na resposta | false |

### Streaming Mode

#### Rivet Events (padrão com `--stream`)

```bash
npx @ironclad/rivet-cli serve --stream
```

Streama eventos SSE (Server-Sent Events):
- `nodeStart` — node começou a executar
- `partialOutput` — output parcial (streaming do LLM)
- `nodeFinish` — node terminou com outputs completos

Exemplo de resposta SSE:

```
event: nodeStart
data: {"nodeId": "xyz", "nodeTitle": "Chat", "type": "nodeStart"}

event: partialOutput
data: {"delta": "Hello", "nodeId": "xyz", "type": "partialOutput"}

event: partialOutput
data: {"delta": " World!", "nodeId": "xyz", "type": "partialOutput"}

event: nodeFinish
data: {"nodeId": "xyz", "outputs": {...}, "type": "nodeFinish"}
```

#### Filtrar por Node

```bash
npx @ironclad/rivet-cli serve --stream=MyChatNode
```

Streama apenas eventos do node especificado (por ID ou título).

#### Text Streaming

```bash
npx @ironclad/rivet-cli serve --stream --stream-node=MyChatNode
```

Streama apenas texto (deltas) do node especificado:

```
data: "Hello"
data: " World!"
data: " How are you?"
```

Recomendado apenas para Chat nodes.

---

## Docker

```bash
docker run -p 3000:3000 -v $(pwd):/app abrenenkeironclad/rivet-server
```

---

## Segurança

- O servidor é destinado a **desenvolvimento e testes**
- **Sem autenticação** built-in
- Para exposição à internet: usar reverse proxy com SSL, rate limiting, e autenticação
- Usar **variáveis de ambiente** para API keys
