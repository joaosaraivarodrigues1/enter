# Controle de Fluxo e Loops

> Fonte: https://rivet.ironcladapp.com/docs/user-guide/control-flow
> Fonte: https://rivet.ironcladapp.com/docs/user-guide/loops

## Controle de Fluxo

O fluxo de dados no Rivet é processado em duas passagens:

### Primeira Passagem: Topological Sort

1. Encontra todos os nodes sem dependentes (ninguém depende deles) → "output nodes"
2. Encontra todos os nodes que esses dependem, recursivamente → lista "precisa ser processado"
3. Nodes sem dependências (nenhum dado fluindo para eles) → marcados como "input nodes"
4. Ciclos são tratados normalmente nesta fase

### Segunda Passagem: Execução

1. Começa pelos "input nodes" da primeira passagem
2. Executa todos os nodes prontos **em paralelo**
3. Quando um node termina, verifica se algum dependente está pronto (todas as dependências satisfeitas)
4. Nodes prontos são executados em paralelo com outros em execução

## Control Flow Excluded

Valor especial `control-flow-excluded` que controla quais ramos do grafo executam ou não.

### Como Funciona

1. Um node (ex: If) retorna `control-flow-excluded` para um ramo
2. O node seguinte **não executa**
3. Esse node também retorna `control-flow-excluded` para seus dependentes
4. A exclusão se **propaga** por toda a cadeia de dependentes

### Nodes que Geram `control-flow-excluded`

- **If Node** — porta False/True quando condição não atende
- **Match Node** — ramos que não fazem match
- **Extract Object Path** — quando o path é inválido
- **Code Node** — retornando `{ type: 'control-flow-excluded', value: undefined }`

### Nodes que Consomem `control-flow-excluded`

Estes nodes "quebram" a propagação do `control-flow-excluded`:

| Node | Comportamento |
|------|---------------|
| **If/Else** | Se `If` recebe excluded, usa o valor de `Else` |
| **Coalesce** | Excluded é tratado como falsy, pula para próximo valor |
| **Race Inputs** | Excluded em um ramo = ramo ignorado, outros continuam |
| **Graph Output** | Excluded pode sair do grafo como output do Subgraph |
| **Loop Controller** | Consome excluded para rodar múltiplas vezes. Excluded em `Continue` = iteração "bem-sucedida" |

---

## Loops

O Loop Controller é o conceito mais difícil e poderoso do Rivet.

### Loop Controller Node

Único node que pode conter ciclos (incluindo a si mesmo). Valores que mudam no loop **devem** fluir pelo Loop Controller.

### Inputs

| Input | Descrição |
|-------|-----------|
| `Continue` | Boolean — se truthy, loop continua; se falsy, loop para |
| `Input X` | Valor que muda a cada iteração (vem de dentro do loop) |
| `Input X Default` | Valor inicial do loop (vem de fora do loop) |

### Outputs

| Output | Descrição |
|--------|-----------|
| `Output X` | Na 1ª iteração: valor do Default. Em seguidas: valor do Input correspondente |
| `Break` | Valor de saída quando o loop para |

### Regra Importante

- O `Break` output **não** passa `control-flow-excluded` até o loop terminar
- Isso permite que o loop rode múltiplas vezes antes de passar valor ao próximo node
- Sempre conecte algo ao `Break` (ex: Graph Output) — necessário para o grafo funcionar

### Max Iterations

- Configurável no editor (padrão: 100)
- Proteção contra loops infinitos acidentais
- Para loops "infinitos" intencionais, aumentar o valor

## Receita: Appending a uma Lista

Usar Array Node (com Flatten padrão) para concatenar o array "atual" com novos valores a cada iteração.

## Receita: Chatbot

Fluxo de um chatbot estilo ChatGPT:

```
Loop mantém 2 estados:
  1. Histórico completo de mensagens (menos a última do bot)
  2. Última mensagem do bot

A cada iteração:
  1. Constrói histórico completo = histórico anterior + última msg bot + resposta do usuário
  2. Envia ao Chat Node → recebe nova mensagem do bot
  3. Novo histórico → volta ao Loop Controller (estado 1)
  4. Nova mensagem do bot → volta ao Loop Controller (estado 2)
```

## Receita: Iterar sobre Array

```
Loop mantém:
  1. Array de entrada (diminui a cada iteração via Pop)
  2. Array de saída (cresce a cada iteração via Array Node)

A cada iteração:
  1. Pop remove primeiro elemento do array de entrada
  2. Processa o elemento (ex: append " Mapped")
  3. Array Node combina array de saída + novo elemento
  4. Compare verifica se array de entrada está vazio
  5. Se vazio → Continue = false → loop para
  6. Break output contém o array processado
```
