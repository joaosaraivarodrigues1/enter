# Instalação e Setup

> Fonte: https://rivet.ironcladapp.com/docs/getting-started/installation
> Fonte: https://rivet.ironcladapp.com/docs/getting-started/setup

## Requisitos do Sistema

| Plataforma | Requisito |
|------------|-----------|
| **macOS** | macOS Monterey ou superior |
| **Windows** | Windows 10 ou superior |
| **Linux** | Versão moderna de `webkitgtk` instalada |

## Instalação via Release

Baixar o último release do GitHub: https://github.com/Ironclad/rivet/releases

Disponível para macOS, Linux e Windows.

## Compilar do Código-Fonte

### Pré-requisitos

- **Rust** — instalar via [rustup](https://rustup.rs/)
- **Node 20+** — ou instalar via [Volta](https://volta.sh/)
- **Yarn**

### Clonar e Instalar

```bash
git clone --filter=blob:none git@github.com:Ironclad/rivet.git
cd rivet
yarn
```

### Build e Executar

```bash
yarn dev
```

## Configuração Inicial

Abrir o painel de Settings no menu do Rivet (macOS) ou na opção `...` no menu.

### Configurar OpenAI

Se usar GPT da OpenAI para geração de texto, é necessário adicionar a API key nas configurações do Rivet.

**Opção 1 — via Settings UI:**
- Navegar até `Settings > OpenAI`
- Inserir API Key e Organization ID (opcional)

**Opção 2 — via variáveis de ambiente:**
```bash
export OPENAI_API_KEY=sk-...
export OPENAI_ORG_ID=org-...
```

Se alterar as variáveis de ambiente, reiniciar o Rivet.

Os nodes que usam OpenAI:
- **Chat Node** — geração de texto via GPT
- **Get Embedding Node** — geração de embeddings vetoriais

### Configurar Plugins

Quando um plugin é habilitado num projeto (ver [11-Plugins.md](./11-Plugins.md)), a página de Plugins em Settings pode conter configurações adicionais (ex: API keys para Anthropic, Pinecone, etc.).

## Instalação das Bibliotecas (para integração)

### @ironclad/rivet-node (recomendado)

```bash
# Yarn
yarn add @ironclad/rivet-node

# NPM
npm install @ironclad/rivet-node

# pnpm
pnpm add @ironclad/rivet-node
```

Requisito: Node.js 16 ou superior.

### @ironclad/rivet-cli

```bash
# Uso direto com npx (sem instalar)
npx @ironclad/rivet-cli --help

# Instalação global
npm install -g @ironclad/rivet-cli
rivet --help
```

### Verificação

```typescript
import * as Rivet from '@ironclad/rivet-node';

const result = await Rivet.runGraphInFile('./myProject.rivet', {
  graph: 'My Graph Name',
  openAiKey: process.env.OPENAI_API_KEY,
});

console.log(result);
```
