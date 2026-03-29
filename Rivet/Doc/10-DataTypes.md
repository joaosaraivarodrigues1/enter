# Tipos de Dados

> Fonte: https://rivet.ironcladapp.com/docs/user-guide/data-types

## DataValue

Todos os dados que passam pelo Rivet são representados como `DataValue` — um objeto com propriedades `type` e `value`:

```typescript
{
  type: string;   // tipo do dado
  value: any;     // valor do dado
}
```

## Decoradores

Decoradores podem ser aplicados a um tipo, alterando-o:

| Decorador | Descrição | Exemplo |
|-----------|-----------|---------|
| `[]` | Array do tipo | `string[]` → array de strings |
| `fn<T>` | Função que retorna o tipo T | `fn<string>` → função que retorna string |

Decoradores podem ser combinados. Ex: `fn<string[]>` = função que retorna array de strings.

## Tipos Disponíveis

| Tipo | Descrição | TypeScript Type | Notas |
|------|-----------|-----------------|-------|
| `any` | Armazena qualquer coisa | `unknown` | Valor é inferido ou coerced. Evitar quando tipo é conhecido. |
| `boolean` | Verdadeiro/falso | `boolean` | Equivalente ao JS `boolean` |
| `string` | Texto | `string` | Equivalente ao JS `string` |
| `number` | Número | `number` | Equivalente ao JS `number` |
| `date` | Data | `string` | ISO-8601 date string |
| `time` | Hora | `string` | ISO-8601 time string |
| `datetime` | Data e hora | `string` | ISO-8601 datetime string |
| `chat-message` | Mensagem de chat para LLM | `{ type: string; message: string; name?: string; function_call?: string }` | Inclui quem enviou (user, assistant, system) |
| `object` | Objeto | `Record<string, unknown>` | Similar ao JS `object`. Pode ser array às vezes. |
| `control-flow-excluded` | Valor excluído do fluxo | `undefined` | Ver [09-ControlFlow-Loops.md](./09-ControlFlow-Loops.md) |
| `gpt-function` | Definição de função GPT | (Ver source) | Usado pelo Chat node com "Enable function use" |
| `vector` | Vetor de números | `number[]` | Para embeddings |
| `image` | Imagem | `{ mediaType: string; data: Uint8Array }` | PNG, JPEG, GIF |
| `audio` | Áudio | `{ mediaType: string; data: Uint8Array }` | |
| `binary` | Dados binários | `Uint8Array` | |

## Coerção de Tipos

O Rivet tenta automaticamente converter (coerce) valores entre tipos quando necessário:

- `number` → `string`: converte para representação textual
- `string` → `number`: faz parse numérico
- `any` → tipo específico: tenta inferir baseado no valor JavaScript
- `string[]` passado para Text Node: concatena com newlines

## Usando DataValues no Código

### No Code Node

```javascript
// Acessar input
const valor = inputs.meuInput.value;
const tipo = inputs.meuInput.type;

// Retornar output
return {
  resultado: {
    type: 'string',
    value: 'Hello World',
  },
  contagem: {
    type: 'number',
    value: 42,
  },
};
```

### No Host Application (External Functions)

```typescript
externalFunctions: {
  minhaFuncao: async (...args: unknown[]) => {
    return {
      type: 'object',
      value: { key: 'valor' },
    };
  },
}
```

### Passando Inputs via SDK

```typescript
await Rivet.runGraphInFile('./project.rivet', {
  graph: 'My Graph',
  inputs: {
    // Forma simplificada (LooseDataValue)
    meuTexto: 'hello',
    meuNumero: 42,
    meuBoolean: true,

    // Forma explícita (DataValue)
    meuObjeto: {
      type: 'object',
      value: { key: 'valor' },
    },
  },
});
```
