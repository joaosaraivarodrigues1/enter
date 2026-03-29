# Splitting (Execução Paralela)

> Fonte: https://rivet.ironcladapp.com/docs/user-guide/splitting

Splitting é uma ferramenta poderosa para paralelizar execução no Rivet.

## Como Ativar

1. Abrir o editor de um node (ícone de engrenagem)
2. Ativar o toggle **Split**
3. Definir o **maximum split amount** (proteção contra splitting excessivo)

## Como Funciona

Quando um node é split:

1. O node é executado **N vezes em paralelo**
2. As portas de entrada aceitam **arrays** do mesmo tipo que normalmente aceitariam
3. As portas de saída retornam **arrays** do tipo que normalmente retornariam
4. Cada execução recebe **um único valor** do array de entrada
5. Os outputs de cada execução são coletados em um array

### Regras de Múltiplos Inputs

- **Input não-array** → Tratado como N cópias do valor (broadcast)
- **Múltiplos arrays** → Valores são "zipados" juntos para cada execução

**Exemplo:** Se uma porta recebe `["a", "b"]` e outra recebe `[1, 2]`, o node executa duas vezes: uma com `("a", 1)` e outra com `("b", 2)`.

## Caso de Uso Básico

```
[Read Directory] → (array de paths) → [Read File (split)] → (array de conteúdos)
```

1. Read Directory retorna um array de nomes de arquivos
2. Read File com Split ativado lê cada arquivo em paralelo
3. Output é um array de strings com o conteúdo de cada arquivo

## Encadeamento (Chaining)

Splits podem ser encadeados:

```
[Read Directory] → [Read File (split)] → [Text Node (split)] → [Chat Node (split)]
```

Cada node split recebe o array do node anterior e processa cada item em paralelo. O resultado final é um array com as respostas da IA para cada arquivo.

## Junção (Joining)

Para reunir dados de nodes split de volta a nodes normais:

| Método | Como funciona |
|--------|---------------|
| **Text Node / Prompt Node** | Array de strings → concatena com newlines |
| **Chat Node** | Aceita array de strings ou chat messages no input Prompt |
| **Extract Object Path** | Extrai valor único de um array de objetos |
| **Pop Node** | Extrai valor único de um array |
| **Code Node** | JavaScript customizado (ex: `Array.prototype.reduce`) |

## Splitting Aninhado

Splitting aninhado direto (arrays de arrays) **não é suportado**.

**Workaround:** Usar **Subgraph Node com Split** ativado. O subgrafo é executado N vezes em paralelo. Dentro do subgrafo, mais nodes com split podem ser usados, criando efetivamente splitting aninhado em qualquer profundidade.

**Cuidado:** Evitar splitting excessivo ou recursivo que pode causar loops infinitos.
