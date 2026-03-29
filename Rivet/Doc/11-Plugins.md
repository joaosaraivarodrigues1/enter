# Plugins

> Fonte: https://rivet.ironcladapp.com/docs/user-guide/plugins
> Fonte: https://rivet.ironcladapp.com/docs/user-guide/plugins/built-in/all
> Fonte: https://rivet.ironcladapp.com/docs/user-guide/plugins/creating-plugins

## Visão Geral

Plugins estendem a funcionalidade do Rivet, adicionando novos nodes que podem ser usados nos grafos.

## Plugins Built-In

| Plugin | Descrição |
|--------|-----------|
| **[Anthropic](https://rivet.ironcladapp.com/docs/user-guide/plugins/built-in/anthropic)** | Acesso a Claude (Opus, Sonnet, Instant). Requer executor Node. Suporta visão com Claude 3. |
| **[AssemblyAI](https://rivet.ironcladapp.com/docs/user-guide/plugins/built-in/assemblyai)** | Transcrição de áudio. |
| **[Autoevals](https://rivet.ironcladapp.com/docs/user-guide/plugins/built-in/autoevals)** | Avaliação automática de outputs de IA. |
| **[Gentrace](https://rivet.ironcladapp.com/docs/user-guide/plugins/built-in/gentrace)** | Tracing e observabilidade para LLMs. |
| **[Google](https://rivet.ironcladapp.com/docs/user-guide/plugins/built-in/google)** | Modelos Google (Gemini). |
| **[HuggingFace](https://rivet.ironcladapp.com/docs/user-guide/plugins/built-in/huggingface)** | Modelos HuggingFace. |
| **[Pinecone](https://rivet.ironcladapp.com/docs/user-guide/plugins/built-in/pinecone)** | Base de dados vetorial Pinecone para Vector Store e Vector KNN. |

## Gerenciar Plugins

### Habilitar Plugin

1. Ir à aba **Plugins** no topo da tela
2. Ver lista de plugins disponíveis
3. Clicar **Add** ao lado do plugin desejado
4. Configurar settings adicionais em **Settings > Plugins** se necessário

### Remover Plugin

1. Ir à aba **Project** na sidebar esquerda
2. Encontrar o plugin na lista
3. Clicar `...` > **Remove**

### Instalar Plugin do NPM

1. Na lista de plugins, usar opção **NPM Plugin** no final
2. Inserir nome do pacote NPM (e opcionalmente versão)
3. O plugin deve estar publicado no NPM

### Instalar Plugin do Código-Fonte

1. Navegar ao diretório de plugins do Rivet (mostrado no final da lista de Plugins)
2. Criar diretório `<nome-do-pacote>-latest`
3. Clonar o repositório dentro como `package/`: `git clone <url> package`
4. No Rivet, "Add NPM Plugin" com o nome exato do pacote
5. Se necessário: `yarn && yarn build` dentro de `package/`

## Plugin Anthropic (Detalhes)

Requer **executor Node** para funcionar no Rivet IDE.

### Configuração

- Habilitar o plugin no projeto
- Inserir API key em **Settings > Plugins > Anthropic**

### Chat (Anthropic) Node

| Setting | Descrição | Default |
|---------|-----------|---------|
| Model | Claude 3 Opus, Sonnet, Haiku, Claude 2.1, Instant | Claude 2 |
| Temperature | 0-2 | 0.5 |
| Top P | Amostragem top-X% | 1 |
| Max Tokens | Limite de tokens | 1024 |
| Stop | Tokens de parada | (nenhum) |

**Visão (Claude 3):** Usar Assemble Message Node para criar prompts com imagens.

**System Prompt (Claude 3):** Input separado para system prompt. Claude 2.x não suporta system prompt nativo.

---

## Criar Plugin Customizado

### Requisitos

1. Código deve ser JavaScript/TypeScript **puro e isomórfico** (sem imports de Node.js ou browser-only)
2. Não pode importar `@ironclad/rivet-core` diretamente — a biblioteca é passada como argumento
3. Deve ser bundlado em um único arquivo (recomenda-se ESBuild)

### Projetos de Exemplo

- **Isomórfico:** https://github.com/abrenneke/rivet-plugin-example
- **Com Node.js:** https://github.com/abrenneke/rivet-plugin-example-python-exec

### Estrutura Mínima do Plugin

```typescript
import type { RivetPluginInitializer } from '@ironclad/rivet-core';

const plugin: RivetPluginInitializer = (rivet) => ({
  id: 'meu-plugin',
  name: 'Meu Plugin',
});

export default plugin;
```

### Plugin com Nodes

```typescript
import type { RivetPlugin, RivetPluginInitializer } from '@ironclad/rivet-core';
import myNode from './nodes/myNode';

const plugin: RivetPluginInitializer = (rivet) => {
  const myPlugin: RivetPlugin = {
    id: 'meu-plugin',
    name: 'Meu Plugin',
    register: (register) => {
      register(myNode(rivet));
    },
  };
  return myPlugin;
};

export default plugin;
```

### Definição de Node

Cada node deve exportar uma **função** que recebe a biblioteca Rivet e retorna um `PluginNodeDefinition`:

```typescript
import type {
  ChartNode, EditorDefinition, Inputs,
  InternalProcessContext, NodeBodySpec, NodeConnection,
  NodeId, NodeInputDefinition, NodeOutputDefinition,
  NodeUIData, Outputs, PluginNodeImpl, PortId,
  Project, Rivet,
} from '@ironclad/rivet-core';

export type MeuNode = ChartNode<'meuNode', MeuNodeData>;

export type MeuNodeData = {
  algumDado: string;
  useAlgumDadoInput?: boolean;
};

export function meuNode(rivet: typeof Rivet) {
  const impl: PluginNodeImpl<MeuNode> = {
    create(): MeuNode {
      return {
        id: rivet.newId<NodeId>(),
        data: { algumDado: 'Hello World' },
        title: 'Meu Node',
        type: 'meuNode',
        visualData: { x: 0, y: 0, width: 200 },
      };
    },

    getInputDefinitions(data) {
      const inputs: NodeInputDefinition[] = [];
      if (data.useAlgumDadoInput) {
        inputs.push({
          id: 'algumDado' as PortId,
          dataType: 'string',
          title: 'Algum Dado',
        });
      }
      return inputs;
    },

    getOutputDefinitions() {
      return [{
        id: 'algumDado' as PortId,
        dataType: 'string',
        title: 'Algum Dado',
      }];
    },

    getUIData(): NodeUIData {
      return {
        contextMenuTitle: 'Meu Node',
        group: 'Meu Plugin',
        infoBoxBody: 'Descrição do meu node.',
        infoBoxTitle: 'Meu Node',
      };
    },

    getEditors(): EditorDefinition<MeuNode>[] {
      return [{
        type: 'string',
        dataKey: 'algumDado',
        useInputToggleDataKey: 'useAlgumDadoInput',
        label: 'Algum Dado',
      }];
    },

    getBody(data) {
      return rivet.dedent`
        Meu Node
        Data: ${data.useAlgumDadoInput ? '(Using Input)' : data.algumDado}
      `;
    },

    async process(data, inputData) {
      const algumDado = rivet.getInputOrData(data, inputData, 'algumDado', 'string');
      return {
        ['algumDado' as PortId]: {
          type: 'string',
          value: algumDado,
        },
      };
    },
  };

  return rivet.pluginNodeDefinition(impl, 'Meu Node');
}
```

### Configuração do Plugin

```typescript
const plugin: RivetPluginInitializer = (rivet) => ({
  id: 'meu-plugin',
  name: 'Meu Plugin',
  configSpec: {
    apiKey: {
      type: 'secret',
      label: 'API Key',
      description: 'API key para este plugin',
      pullEnvironmentVariable: 'MEU_PLUGIN_API_KEY',
    },
    algumaSetting: {
      type: 'string',
      label: 'Alguma Setting',
      description: 'Uma configuração de exemplo',
    },
  },
});
```

### Ler Configuração no Node

```typescript
async process(_data, _inputData, context) {
  const apiKey = context.getPluginConfig('apiKey');
  // usar apiKey...
}
```

### Desenvolvimento de Plugins

1. Criar diretório `<nome>-latest` dentro do diretório de plugins do Rivet
2. Clonar repositório dentro de `package/`
3. Usar `yarn dev` em `package/` para hot reload
4. Reiniciar Rivet a cada mudança para ver atualizações
