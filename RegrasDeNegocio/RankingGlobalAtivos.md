# Ranking Global de Ativos

## Resumo

Combina três regras independentes — ranking interno de ativos por classe, ranking macro de classes e suitability por perfil — para produzir uma lista final ordenada de ativos, filtrada pelo que o cliente pode possuir e ordenada pelo que o cenário favorece.

---

## Os três inputs

| Input | Origem | Formato |
|-------|--------|---------|
| `ranking_ativos` | RankingAtivos — sharpe_proxy vs benchmark | `{ classe: [ativo, ...] }` |
| `ranking_classes` | RankingClassesAtivos — score macro | `["classe", ...]` do mais ao menos atraente |
| `classes_permitidas` | PerfisDeRisco — suitability do cliente | `["classe", ...]` sem ordem definida |

---

## Regra de combinação

**Passo 1 — Filtro de suitability (hard gate regulatório)**

Remove do `ranking_classes` qualquer classe que não esteja em `classes_permitidas`. Esse filtro é binário e não negociável — uma classe fora do perfil não aparece no output independente do cenário macro.

```
classes_ativas = ranking_classes.filter(c => classes_permitidas.includes(c))
```

Resultado: lista de classes permitidas, já na ordem de atratividade macro.

---

**Passo 2 — Montagem do output**

Para cada classe em `classes_ativas` (na ordem do passo 1), pega os ativos de `ranking_ativos` naquela classe. A ordem interna dos ativos é preservada — vem do RankingAtivos e não é reordenada aqui.

```
output = {}
for classe in classes_ativas:
  output[classe] = ranking_ativos[classe]
```

---

**Passo 3 — Resultado**

JSON com:
- Apenas classes permitidas pelo perfil
- Classes na ordem de atratividade macro (mais favorecida → menos favorecida)
- Ativos dentro de cada classe na ordem de sharpe_proxy (melhor → pior)

---

## Exemplo

**Inputs:**

```json
// ranking_ativos
{
  "caixa":          ["Tesouro Selic 2029", "Trend DI", "Trend Investback"],
  "renda_fixa":     ["Debênture CPFL", "Tesouro Prefixado 2027", "CDB C6 IPCA+"],
  "multimercado":   ["Truxt Long Bias", "Ibiuna Hedge ST"],
  "renda_variavel": ["WEGE3", "SUZB3", "VALE3"]
}

// ranking_classes — macro favorece caixa e renda_fixa, penaliza renda_variável
["caixa", "renda_fixa", "multimercado", "renda_variavel"]

// classes_permitidas — perfil moderado
["caixa", "renda_fixa", "multimercado"]
```

**Passo 1 — filtro:**
```
["caixa", "renda_fixa", "multimercado", "renda_variavel"]
  → remove "renda_variavel" (não permitida)
  → ["caixa", "renda_fixa", "multimercado"]
```

**Output:**
```json
{
  "caixa":        ["Tesouro Selic 2029", "Trend DI", "Trend Investback"],
  "renda_fixa":   ["Debênture CPFL", "Tesouro Prefixado 2027", "CDB C6 IPCA+"],
  "multimercado": ["Truxt Long Bias", "Ibiuna Hedge ST"]
}
```

---

## Formatos JSON

**Input 1 — ranking_ativos**
```json
{
  "caixa":          ["string"],
  "renda_fixa":     ["string"],
  "multimercado":   ["string"],
  "renda_variavel": ["string"]
}
```

**Input 2 — ranking_classes**
```json
["caixa", "renda_fixa", "multimercado", "renda_variavel"]
```

**Input 3 — classes_permitidas**
```json
["caixa", "renda_fixa", "multimercado"]
```

**Output**
```json
{
  "caixa":          ["string"],
  "renda_fixa":     ["string"],
  "multimercado":   ["string"]
}
```
Apenas as classes permitidas, na ordem macro. Renda variável omitida se não constar em `classes_permitidas`.

---

## Propriedades da regra

- **Sem recálculo de score** — os rankings de input já estão calculados. Esta função apenas filtra e ordena.
- **Idempotente** — aplicar duas vezes produz o mesmo resultado.
- **Sem empate** — a ordem de classes vem inteira do ranking macro. A ordem de ativos vem inteira do ranking interno. Não há critério de desempate a definir aqui.
- **Classes vazias são omitidas** — se `ranking_ativos` não tiver ativos para uma classe permitida, ela não aparece no output.
