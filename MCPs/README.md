# MCPs — Configurações de MCP do Projeto Enter

Esta pasta centraliza toda a documentação de MCPs usados neste projeto.

---

## Arquivo de configuração real

Claude Code armazena toda a configuração em:

```
C:\Users\joaos\.claude.json
```

**Não edite esse arquivo manualmente.** Use os comandos abaixo.

O arquivo `~/.claude/settings.json` **NÃO serve para MCPs** — só guarda configurações gerais.

---

## Supabase MCP

**Status:** Ativo (HTTP, projeto-level para `C:/Users/joaos/Enter`)
**Conta:** João Saraiva — joao.saraiva@arcca.io

### Como foi registrado

```bash
claude mcp add --transport http supabase https://mcp.supabase.com/mcp \
  --header "Authorization: Bearer <ACCESS_TOKEN>"
```

### Como verificar se está funcionando

```bash
claude mcp list
# Deve mostrar: supabase: https://mcp.supabase.com/mcp (HTTP) - ✓ Connected
```

### Como remover (se precisar recomeçar do zero)

```bash
claude mcp remove supabase
```

### Token atual

Armazenado em `.claude.json`. Para gerar novo: supabase.com → Account → Access Tokens

---

## GitHub MCP

**Status:** Ativo (stdio, project-level para `C:/Users/joaos/Enter/Streamlit/Enter1`)
**Conta:** joaosaraivarodrigues1 — github.com/joaosaraivarodrigues1

### Como foi registrado

```bash
claude mcp add github \
  -e GITHUB_PERSONAL_ACCESS_TOKEN=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 \
  -- npx -y @modelcontextprotocol/server-github
```

### Como reativar (quando desconectado)

1. Abra o Claude Code na pasta do projeto (`Enter/Streamlit/Enter1`)
2. Execute:

```bash
claude mcp add github -e GITHUB_PERSONAL_ACCESS_TOKEN=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 -- npx -y @modelcontextprotocol/server-github
```

Ou no chat, use `!` antes do comando:

```
! claude mcp add github -e GITHUB_PERSONAL_ACCESS_TOKEN=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 -- npx -y @modelcontextprotocol/server-github
```

### Como verificar se está funcionando

```bash
claude mcp list
# Deve mostrar: github (stdio) - npx -y @modelcontextprotocol/server-github
```

### Como remover (se precisar recomeçar)

```bash
claude mcp remove github
```

### Token atual

```
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
```

Gerado em: 2026-03-27
Escopos necessários: `repo`, `read:org`, `read:user`
Para gerar novo: github.com → Settings → Developer Settings → Personal access tokens → Tokens (classic)

### Repositório conectado

- `https://github.com/joaosaraivarodrigues1/Enter1`

---

## Arquivos relacionados ao Supabase fora da pasta Enter

| Arquivo/Pasta | Localização | Uso |
|---|---|---|
| Config geral | `C:\Users\joaos\.claude.json` | Configuração real dos MCPs (gerenciado via CLI) |
| Plugin template | `C:\Users\joaos\.claude\plugins\...\supabase\.mcp.json` | Template do marketplace, sem credenciais, não usado ativamente |
