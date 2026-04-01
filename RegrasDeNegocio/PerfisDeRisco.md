# Perfis de Risco

Regras de negócio dos 4 perfis de investidor. Consumido por qualquer aplicação que precise de suitability ou alocação alvo por classe de ativo.

Os `id` de classes referenciam diretamente `ClassesDeAtivos.md`.

```json
{
  "perfis": [
    {
      "id": "conservador",
      "nome": "Conservador",
      "suitability": ["caixa", "renda_fixa"],
      "alocacao": {
        "caixa":          { "min": 30, "alvo": 60, "max": 80 },
        "renda_fixa":     { "min": 20, "alvo": 40, "max": 70 },
        "multimercado":   { "min": 0,  "alvo": 0,  "max": 0  },
        "renda_variavel": { "min": 0,  "alvo": 0,  "max": 0  }
      }
    },
    {
      "id": "moderado",
      "nome": "Moderado",
      "suitability": ["caixa", "renda_fixa", "multimercado"],
      "alocacao": {
        "caixa":          { "min": 10, "alvo": 30, "max": 50 },
        "renda_fixa":     { "min": 30, "alvo": 50, "max": 70 },
        "multimercado":   { "min": 0,  "alvo": 20, "max": 30 },
        "renda_variavel": { "min": 0,  "alvo": 0,  "max": 0  }
      }
    },
    {
      "id": "arrojado",
      "nome": "Arrojado",
      "suitability": ["caixa", "renda_fixa", "multimercado", "renda_variavel"],
      "alocacao": {
        "caixa":          { "min": 5,  "alvo": 15, "max": 30 },
        "renda_fixa":     { "min": 15, "alvo": 35, "max": 55 },
        "multimercado":   { "min": 10, "alvo": 25, "max": 40 },
        "renda_variavel": { "min": 5,  "alvo": 25, "max": 40 }
      }
    },
    {
      "id": "agressivo",
      "nome": "Agressivo",
      "suitability": ["caixa", "renda_fixa", "multimercado", "renda_variavel"],
      "alocacao": {
        "caixa":          { "min": 0,  "alvo": 5,  "max": 15 },
        "renda_fixa":     { "min": 0,  "alvo": 15, "max": 30 },
        "multimercado":   { "min": 10, "alvo": 30, "max": 50 },
        "renda_variavel": { "min": 25, "alvo": 50, "max": 70 }
      }
    }
  ]
}
```

---

## Como usar

**Suitability filter** — verificar se uma classe é permitida para o perfil:
```js
perfil.suitability.includes(classeId)
```

**Alocação alvo** — percentual-base para construção de carteira:
```js
perfil.alocacao[classeId].alvo
```

**Rebalanceamento** — o corredor `min/max` define os limites tolerados antes de recomendar ajuste.

> Os alvos de cada perfil somam 100%.
