# MCP Nodes (Model Context Protocol)

> Fonte: https://rivet.ironcladapp.com/docs/node-reference/mcp-discovery
> Fonte: https://rivet.ironcladapp.com/docs/node-reference/mcp-tool-call
> Fonte: https://rivet.ironcladapp.com/docs/node-reference/mcp-get-prompt

## Visão Geral

O [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) permite comunicação com servidores MCP-compatíveis. O Rivet suporta MCP nativamente com 3 nodes:

| Node | Função |
|------|--------|
| **MCP Discovery** | Descobrir capabilities (tools e prompts) de um servidor MCP |
| **MCP Tool Call** | Chamar uma ferramenta (tool) num servidor MCP |
| **MCP Get Prompt** | Obter um prompt de um servidor MCP |

**Requisito:** Todos os MCP nodes usam o SDK MCP oficial TypeScript e requerem o **executor Node** para funcionar no Rivet IDE.

## Modos de Comunicação

### STDIO Mode

Lança e comunica com servidores MCP locais via STDIO Transport.

**Configuração:** Adicionar o servidor em `Project > Edit MCP Configuration`

### HTTP Mode

Usa Streamable HTTP Transport (padrão) com fallback para SSE Transport.

---

## Configuração de Servidores MCP (STDIO)

Em `Project > MCP Configuration`, adicionar JSON:

```json
{
  "mcpServers": {
    "mongodb": {
      "command": "/path/to/node",
      "args": ["-y", "/path/to/mcp-mongo-server/build/index.js", "mongodb://localhost:27017/your-database"]
    },
    "weather": {
      "command": "node",
      "args": ["/absolute-path/weather/build/index.js"]
    }
  }
}
```

A configuração é salva no arquivo do projeto Rivet. Todos os servidores ficam disponíveis nos MCP Nodes.

---

## MCP Discovery Node

Descobre tools e prompts de um servidor MCP.

### Inputs

| Input | Tipo | Descrição | Padrão |
|-------|------|-----------|--------|
| Name | `string` | Nome da instância MCP Client | mcp-client |
| Version | `string` | Versão da instância | 1.0.0 |
| Server URL (HTTP) | `string` | URL do servidor (modo HTTP) | - |

### Outputs

- Lista de **Tools** disponíveis no servidor (nome, descrição, schema)
- Lista de **Prompts** disponíveis (nome, descrição, argumentos)

### Exemplo: HTTP Mode

1. Adicionar MCP Discovery Node
2. Definir Transport Type = "HTTP"
3. Definir Server URL = `http://localhost:8080/mcp`
4. Ativar **Node Executor** (menu superior direito)
5. Executar o grafo

### Exemplo: STDIO Mode

1. Configurar servidor em `Project > MCP Configuration`
2. Ativar **Node Executor**
3. Adicionar MCP Discovery Node
4. Definir Transport Type = "STDIO"
5. Definir Server ID = nome do servidor (ex: "weather")
6. Executar o grafo

---

## MCP Tool Call Node

Chama uma ferramenta (tool) em um servidor MCP.

### Inputs

| Input | Tipo | Descrição | Padrão |
|-------|------|-----------|--------|
| Name | `string` | Nome da instância MCP Client | mcp-tool-call-client |
| Version | `string` | Versão | 1.0.0 |
| Server URL (HTTP) | `string` | URL do servidor (modo HTTP) | - |
| Tool Name | `string` | Nome da ferramenta a chamar | - |
| Tool Arguments | `object` | Argumentos JSON para a ferramenta | - |
| Tool ID | `string` | ID associado à chamada (passthrough) | - |

### Outputs

- Resultado da chamada da ferramenta (conteúdo retornado pelo servidor)

### Exemplo: Chamar Tool de Weather

```
[MCP Discovery Node] → (descobrir tools) → Ver nome da tool
[Text Node: "get-forecast"] → Tool Name input
[Object Node: {"city": "São Paulo"}] → Tool Arguments input
[MCP Tool Call Node] → (resultado da previsão)
```

---

## MCP Get Prompt Node

Obtém um prompt de um servidor MCP.

### Inputs

Similar ao MCP Discovery, com campos adicionais para:
- Prompt Name
- Prompt Arguments

### Outputs

- Conteúdo do prompt retornado pelo servidor

---

## Tratamento de Erros

| Código de Erro | Descrição |
|----------------|-----------|
| `CONFIG_NOT_FOUND` | Configuração MCP não encontrada |
| `SERVER_NOT_FOUND` | Server ID não encontrado na configuração |
| `SERVER_COMMUNICATION_FAILED` | Falha na comunicação com o servidor |
| `INVALID_SCHEMA` | Schema inválido para argumentos de input |

## Troubleshooting

### STDIO Server Not Found
- Verificar configuração MCP no Project tab
- Usar caminhos absolutos na configuração

### HTTP Connection Failed
- Verificar URL do servidor
- Verificar configurações de CORS
- Confirmar conectividade de rede

### Node Executor Issues
- Ativar Node executor nas configurações do Rivet
- Verificar instalação do Node.js
- Verificar permissões do executável do servidor

## FAQ

**Pode usar no executor Browser?**
Não. Todos os MCP nodes requerem o executor Node.

**Suporta autenticação?**
STDIO: inclua detalhes na configuração do servidor. HTTP: autenticação é feature futura.

**Múltiplos servidores MCP no mesmo grafo?**
Sim. Cada MCP Node pode ser configurado para um servidor diferente.
