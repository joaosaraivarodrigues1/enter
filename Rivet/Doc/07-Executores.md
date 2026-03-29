# Executores

> Fonte: https://rivet.ironcladapp.com/docs/user-guide/executors

Executores são responsáveis por rodar os grafos no Rivet. O executor é escolhido via dropdown no menu da aplicação.

Há 3 executores disponíveis:

## Browser (Padrão)

O executor padrão. Roda no mesmo processo da aplicação Rivet (que é uma app web rodando em web view).

| Aspecto | Detalhe |
|---------|---------|
| **Simplicidade** | O mais simples de usar |
| **Limitações** | Restrito às capacidades do browser + algumas APIs de filesystem |
| **CORS** | Chamadas HTTP externas podem falhar por CORS |
| **Plugins** | Alguns plugins (ex: Anthropic) não funcionam neste executor |

## Node

Executor que roda um processo Node.js separado para executar grafos. Comunica-se via protocolo de remote debugger.

| Aspecto | Detalhe |
|---------|---------|
| **Poder** | Mais poderoso que o Browser — acesso a APIs do Node.js |
| **CORS** | Sem problemas de CORS |
| **Plugins** | Necessário para plugins que usam Node.js (ex: Anthropic, MCP) |
| **Estabilidade** | Pode ser mais instável que o Browser |
| **Requisito** | Node.js instalado no sistema |

**Quando usar:** Sempre que precisar fazer HTTP Calls para APIs externas (evitar CORS), usar plugins como Anthropic, ou usar MCP Nodes.

## Remote

Conecta-se a um servidor Rivet remoto para executar grafos. Requer:

1. Remote debugger configurado na aplicação remota
2. `dynamicGraphRun` implementado no servidor remoto
3. (Opcional) `allowGraphUpload` para enviar o grafo ao servidor

### Conectar

- Via dropdown no Action Bar > "Remote Debugger"
- Ou pressionar F5
- URL no formato: `ws://<host>:<port>` (padrão: `ws://localhost:21888`)

### Funcionamento

Quando conectado ao remote debugger:
- Clicar "Run" executa o grafo no servidor remoto
- A execução é visível em tempo real no Rivet
- Pode pausar e abortar a execução remotamente
- Se `allowGraphUpload` estiver ativo, o grafo é enviado ao servidor sem precisar salvar o arquivo

**Quando usar:** Para rodar grafos que usam `External Call` (que só funciona com host application), debug em produção, ou execução em ambientes diferentes.

## Comparativo

| Feature | Browser | Node | Remote |
|---------|---------|------|--------|
| Setup necessário | Nenhum | Node.js instalado | Servidor configurado |
| CORS | Problema | Sem problema | Depende do servidor |
| External Call | Não funciona | Não funciona | Funciona |
| MCP Nodes | Não funciona | Funciona | Depende do servidor |
| Plugins Node.js | Não funciona | Funciona | Depende do servidor |
| Performance | Boa | Boa | Depende da rede |
| Debug em produção | Não | Não | Sim |
