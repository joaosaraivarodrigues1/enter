# Referência Completa de Nodes

> Fonte: https://rivet.ironcladapp.com/docs/node-reference/all-nodes

Referência de todos os nodes built-in do Rivet, organizados por categoria.

---

## Texto

| Node | Descrição |
|------|-----------|
| **[Chunk](https://rivet.ironcladapp.com/docs/node-reference/chunk)** | Divide uma string em array de strings baseado em contagem de tokens. Útil para evitar limites de tokens em LLMs e garantir que contexto não é perdido entre chunks especificando overlap. |
| **[Extract Markdown Code Blocks](https://rivet.ironcladapp.com/docs/node-reference/extract-markdown-code-blocks)** | Extrai blocos de código de texto Markdown, incluindo todos os blocos e suas linguagens. |
| **[Extract with Regex](https://rivet.ironcladapp.com/docs/node-reference/extract-with-regex)** | Extrai uma ou mais strings usando expressão regular. |
| **[Join](https://rivet.ironcladapp.com/docs/node-reference/join)** | Concatena um array de strings em uma única string usando delimitador especificado. |
| **[Prompt](https://rivet.ironcladapp.com/docs/node-reference/prompt)** | Cria uma mensagem de chat com tipo (User, Assistant, System) e nome opcional. Suporta interpolação com `{{tags}}` e calcula contagem de tokens. |
| **[Split Text](https://rivet.ironcladapp.com/docs/node-reference/split-text)** | Divide uma string em array de substrings baseado em delimitador. |
| **[Text](https://rivet.ironcladapp.com/docs/node-reference/text)** | Gera uma string de texto com suporte a interpolação via `{{tags}}`. Suporta markdown. |
| **[To JSON](https://rivet.ironcladapp.com/docs/node-reference/to-json)** | Converte qualquer input em seu equivalente JSON (stringify). |
| **[To YAML](https://rivet.ironcladapp.com/docs/node-reference/to-yaml)** | Converte um objeto em string YAML. |

---

## IA

| Node | Descrição |
|------|-----------|
| **[Assemble Prompt](https://rivet.ironcladapp.com/docs/node-reference/assemble-prompt)** | Monta múltiplas mensagens de chat em um único prompt. Converte inputs não-chat em formato de chat message. |
| **[Chat](https://rivet.ironcladapp.com/docs/node-reference/chat)** | Envia mensagens para um LLM (GPT da OpenAI ou qualquer API compatível com OpenAI). Suporta LLMs locais (ex: LM Studio). Retorna a resposta do modelo. |
| **[GPT Function](https://rivet.ironcladapp.com/docs/node-reference/gpt-function)** | Define uma função que pode ser chamada pelo GPT ("function calling"). Definida via JSON Schema. |
| **[Get Embedding](https://rivet.ironcladapp.com/docs/node-reference/get-embedding)** | Gera embedding vetorial para um texto de entrada. Usado para busca de similaridade (KNN). |
| **[Trim Chat Messages](https://rivet.ironcladapp.com/docs/node-reference/trim-chat-messages)** | Gerencia o tamanho de cadeias de mensagens em termos de tokens. Remove mensagens do início ou fim até ficar dentro do limite configurado. |

---

## MCP (Model Context Protocol)

| Node | Descrição |
|------|-----------|
| **[MCP Discovery](https://rivet.ironcladapp.com/docs/node-reference/mcp-discovery)** | Conecta a um servidor MCP para descobrir capabilities (tools e prompts). Suporta HTTP e STDIO. |
| **[MCP Tool Call](https://rivet.ironcladapp.com/docs/node-reference/mcp-tool-call)** | Chama uma ferramenta (tool) num servidor MCP. |
| **[MCP Get Prompt](https://rivet.ironcladapp.com/docs/node-reference/mcp-get-prompt)** | Obtém um prompt de um servidor MCP. |

---

## Listas

| Node | Descrição |
|------|-----------|
| **[Array](https://rivet.ironcladapp.com/docs/node-reference/array)** | Constrói arrays a partir de múltiplos inputs ou merge de arrays. Opções: Flatten e Deep flatten. |
| **[Filter](https://rivet.ironcladapp.com/docs/node-reference/filter)** | Filtra elementos de um array baseado em array de booleanos correspondente. |
| **[Pop](https://rivet.ironcladapp.com/docs/node-reference/pop)** | Remove o primeiro ou último elemento de um array. Retorna o elemento removido e o array restante. |
| **[Shuffle](https://rivet.ironcladapp.com/docs/node-reference/shuffle)** | Randomiza a ordem dos elementos (Fisher-Yates shuffle). Não modifica o array original. |
| **[Slice](https://rivet.ironcladapp.com/docs/node-reference/slice)** | Extrai uma porção específica de um array (índice + quantidade). |

---

## Números

| Node | Descrição |
|------|-----------|
| **[Evaluate](https://rivet.ironcladapp.com/docs/node-reference/evaluate)** | Operações matemáticas: adição, subtração, multiplicação, divisão, exponenciação, módulo, absoluto, negação. |
| **[Number](https://rivet.ironcladapp.com/docs/node-reference/number)** | Gera um número constante ou converte input em número. Pode arredondar para casas decimais. |
| **[RNG](https://rivet.ironcladapp.com/docs/node-reference/RNG)** | Gera número aleatório dentro de um range (inteiro ou float). |

---

## Objetos

| Node | Descrição |
|------|-----------|
| **[Extract JSON](https://rivet.ironcladapp.com/docs/node-reference/extract-json)** | Extrai objeto/array JSON de uma string, ignorando dados fora da estrutura JSON. |
| **[Extract Object Path](https://rivet.ironcladapp.com/docs/node-reference/extract-object-path)** | Executa queries jsonpath em um objeto. Suporta queries complexas. |
| **[Extract YAML](https://rivet.ironcladapp.com/docs/node-reference/extract-yaml)** | Faz parse de objeto YAML a partir de uma string. |
| **[Object](https://rivet.ironcladapp.com/docs/node-reference/object)** | Cria um objeto a partir de valores de input e template JSON. |

---

## Dados

| Node | Descrição |
|------|-----------|
| **[Audio](https://rivet.ironcladapp.com/docs/node-reference/audio)** | Define uma amostra de áudio. Pode converter binary em audio. |
| **[Bool](https://rivet.ironcladapp.com/docs/node-reference/bool)** | Gera booleano constante ou converte input em booleano (regras truthy/falsy do JavaScript). |
| **[Hash](https://rivet.ironcladapp.com/docs/node-reference/hash)** | Computa hash do input (MD5, SHA-1, SHA-256, SHA-512). |
| **[Image](https://rivet.ironcladapp.com/docs/node-reference/image)** | Define uma imagem estática (PNG, JPEG, GIF). Pode converter binary em image. |

---

## Lógica

| Node | Descrição |
|------|-----------|
| **[Abort Graph](https://rivet.ironcladapp.com/docs/node-reference/abort-graph)** | Para a execução do grafo imediatamente (com sucesso ou com erro). |
| **[Coalesce](https://rivet.ironcladapp.com/docs/node-reference/coalesce)** | Retorna o primeiro valor não-nulo de uma lista (como SQL COALESCE). |
| **[Compare](https://rivet.ironcladapp.com/docs/node-reference/compare)** | Comparações: igualdade, desigualdade, lógicas, etc. Tenta coerção de tipos. |
| **[Delay](https://rivet.ironcladapp.com/docs/node-reference/delay)** | Pausa na execução do grafo. Passa valores para outputs após delay especificado. |
| **[If](https://rivet.ironcladapp.com/docs/node-reference/if)** | Condição + valor. Se truthy, passa pela porta True; senão, pela porta False. |
| **[If/Else](https://rivet.ironcladapp.com/docs/node-reference/if-else)** | Escolhe entre dois valores baseado em condição. Garante que sempre retorna um valor. |
| **[Match](https://rivet.ironcladapp.com/docs/node-reference/match)** | Faz match de string contra regex. Roteia fluxo baseado no conteúdo. Porta `Unmatched` se nenhum match. |
| **[Passthrough](https://rivet.ironcladapp.com/docs/node-reference/passthrough)** | Transfere input diretamente para output sem modificação. |
| **[Race Inputs](https://rivet.ironcladapp.com/docs/node-reference/race-inputs)** | Recebe múltiplos inputs. Output = primeiro input a completar. Cancela os restantes. |

---

## Input/Output

| Node | Descrição |
|------|-----------|
| **[Append to Dataset](https://rivet.ironcladapp.com/docs/node-reference/append-to-dataset)** | Adiciona uma linha de dados a um dataset. Requer dataset provider. |
| **[Create Dataset](https://rivet.ironcladapp.com/docs/node-reference/create-dataset)** | Gera novo dataset com ID e nome únicos. |
| **[Get All Datasets](https://rivet.ironcladapp.com/docs/node-reference/get-all-datasets)** | Retorna todos os datasets do projeto. |
| **[Get Dataset Row](https://rivet.ironcladapp.com/docs/node-reference/get-dataset-row)** | Retorna uma linha específica de um dataset por ID. |
| **[Graph Input](https://rivet.ironcladapp.com/docs/node-reference/graph-input)** | Define um input do grafo (parâmetro quando chamado via SDK ou porta quando usado como subgrafo). |
| **[Graph Output](https://rivet.ironcladapp.com/docs/node-reference/graph-output)** | Define um output do grafo. Torna-se porta de saída quando usado como subgrafo. |
| **[KNN Dataset](https://rivet.ironcladapp.com/docs/node-reference/knn-dataset)** | Busca k vizinhos mais próximos num dataset dado um embedding. |
| **[Load Dataset](https://rivet.ironcladapp.com/docs/node-reference/load-dataset)** | Carrega todo o conteúdo de um dataset. |
| **[Read Directory](https://rivet.ironcladapp.com/docs/node-reference/read-directory)** | Lê o conteúdo de um diretório. Suporta recursão, filtros, e caminhos relativos. |
| **[Read File](https://rivet.ironcladapp.com/docs/node-reference/read-file)** | Lê o conteúdo de um arquivo como string. Requer native API no contexto. |
| **[User Input](https://rivet.ironcladapp.com/docs/node-reference/user-input)** | Solicita input do usuário durante execução do grafo. |
| **[Vector Store](https://rivet.ironcladapp.com/docs/node-reference/vector-store)** | Armazena embedding vetorial numa base de dados vetorial. Aceita vetor + dados + ID. |
| **[Vector KNN](https://rivet.ironcladapp.com/docs/node-reference/vector-knn)** | Busca k vizinhos mais próximos numa base vetorial (ex: Pinecone). |

---

## Avançado

| Node | Descrição |
|------|-----------|
| **[Code](https://rivet.ironcladapp.com/docs/node-reference/code)** | Executa JavaScript arbitrário durante execução do grafo. Inputs via `inputs.nome.value`, outputs retornando objetos `{type, value}`. Sem `require/import`, sem `async/await`, sem `console.log`. |
| **[Comment](https://rivet.ironcladapp.com/docs/node-reference/comment)** | Adiciona notas/comentários ao grafo. Renderizado atrás dos outros nodes. |
| **[Context](https://rivet.ironcladapp.com/docs/node-reference/context)** | Acessa valores compartilhados (globais) definidos via `contextValues` no SDK. Disponível em qualquer grafo/subgrafo. Também acessível via `{{@context.nome}}` em Text/Prompt/Object nodes. |
| **[External Call](https://rivet.ironcladapp.com/docs/node-reference/external-call)** | Executa funções externas definidas no host application (`externalFunctions`). Usado para DB, APIs, etc. **Não funciona** no Rivet IDE (requer Remote Debugging). |
| **[Get Global](https://rivet.ironcladapp.com/docs/node-reference/get-global)** | Recupera valor global compartilhado entre grafos/subgrafos. |
| **[HTTP Call](https://rivet.ironcladapp.com/docs/node-reference/http-call)** | Faz chamada HTTP (GET, POST, PUT, DELETE) com headers e body customizados. **Atenção CORS** no executor Browser — usar executor Node para evitar. |
| **[Loop Controller](https://rivet.ironcladapp.com/docs/node-reference/loop-controller)** | Cria loops no grafo. Único node que permite ciclos. Controla fluxo e mantém estado do loop. |
| **[Raise Event](https://rivet.ironcladapp.com/docs/node-reference/raise-event)** | Dispara evento no grafo (capturado pelo host ou Wait For Event). |
| **[Set Global](https://rivet.ironcladapp.com/docs/node-reference/set-global)** | Define valor global compartilhado entre grafos/subgrafos. |
| **[Subgraph](https://rivet.ironcladapp.com/docs/node-reference/subgraph)** | Executa outro grafo dentro do grafo atual. Portas atualizadas automaticamente. Output de erro opcional. |
| **[Wait For Event](https://rivet.ironcladapp.com/docs/node-reference/wait-for-event)** | Pausa execução até um evento específico ser sinalizado (Raise Event ou host). |

---

## Nodes Detalhados Importantes

### Chat Node

```
Inputs:
  - System Prompt (string | chat-message) — opcional, prepended ao prompt
  - Prompt (string | string[] | chat-message | chat-message[]) — obrigatório
  - Functions (gpt-function[]) — se "Enable Function Use" ativo

Settings:
  - Model (GPT-4, GPT-3.5, etc.)
  - Temperature (0-2)
  - Top P
  - Max Tokens
  - Stop sequences
  - Endpoint (custom URL para LLMs locais como LM Studio)
  - Enable Function Use
  - Use Cache

Outputs:
  - Response (string)
  - All Messages (chat-message[])
  - Cost, Duration, Token counts
```

Para LM Studio, usar Endpoint: `http://localhost:1234/v1/chat/completions` e ativar CORS no LM Studio.

### External Call Node

```
Inputs:
  - Arguments (any | any[])

Settings:
  - Function Name — deve corresponder ao nome em externalFunctions

Outputs:
  - Result (any)
  - Error (string) — se "Use Error Output" ativado
```

Exemplo de external function no host:

```typescript
externalFunctions: {
  getUser: async (userId: string) => {
    const user = await db.getUser(userId);
    return { type: 'object', value: user };
  },
}
```

### HTTP Call Node

```
Settings:
  - Method (GET, POST, PUT, DELETE)
  - URL
  - Headers (JSON)
  - Body (string)
  - Error on non-200

Outputs:
  - Body (string)
  - Headers (object)
  - Status Code (number)
  - JSON (object) — body parseado como JSON
```

**CORS:** No executor Browser, APIs externas sem suporte CORS para `http://tauri.local` darão erro `fetch failed`. Usar executor **Node** para evitar.

### Context Node

```
Settings:
  - ID — identificador do valor de contexto
  - Data Type
  - Default Value

Acesso em Text Node: {{@context.nomeDoContexto}}
Acesso em Code Node: context.nomeDoContexto.value
```

Definido no host:

```typescript
const processor = Rivet.createProcessor({
  contextValues: {
    currentDate: new Date(),
    apiKey: process.env.MY_API_KEY,
  },
});
```
