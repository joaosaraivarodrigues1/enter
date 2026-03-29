# Trivet — Framework de Testes

> Fonte: https://rivet.ironcladapp.com/docs/trivet

## Visão Geral

Trivet é a biblioteca integrada do Rivet para executar testes em grafos. Está disponível:

1. **No Rivet IDE** — como overlay integrado para criar e executar testes
2. **Como biblioteca** — para execução programática (ex: CI/CD)

## Acessar no Rivet IDE

1. Clicar na aba **Trivet Tests** nos overlays no topo da tela
2. Criar suítes de teste e casos de teste
3. Executar testes e ver resultados

## Conceitos

### Test Suite (Suíte de Teste)

Um conjunto de casos de teste para um grafo específico. Cada suíte é associada a um grafo do projeto.

### Test Case (Caso de Teste)

Define um cenário de teste com:
- **Inputs** — valores de entrada para o grafo
- **Expected outputs** — valores esperados de saída
- **Validation** — como validar se o output está correto

### Validation Graphs (Grafos de Validação)

Grafos especiais que recebem o output do grafo testado e retornam se a validação passou ou não. Permitem validações complexas como:
- Verificar se a resposta contém determinadas informações
- Comparar com valores esperados
- Usar LLM para avaliar a qualidade da resposta

## Uso Programático (CI/CD)

A biblioteca Trivet pode ser usada para executar testes fora do Rivet IDE:

```bash
yarn add @ironclad/trivet
```

Útil para:
- Integração contínua (CI)
- Testes automatizados em pipeline
- Validação pré-deploy

## Links

- Getting Started: https://rivet.ironcladapp.com/docs/user-guide/trivet-getting-started
- Validation Graphs: https://rivet.ironcladapp.com/docs/user-guide/trivet-validation
- Tutorial: https://rivet.ironcladapp.com/docs/user-guide/trivet-tutorial
- Trivet Library: https://rivet.ironcladapp.com/docs/user-guide/trivet-library
