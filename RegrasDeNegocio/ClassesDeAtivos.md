# Classes de Ativos

Regra de negócio central que classifica todos os ativos da plataforma em 4 grupos comportamentais.
Cada classe agrupa ativos que respondem de forma homogênea aos mesmos indicadores macroeconômicos.
Esta regra é a fonte única de verdade para suitability, scoring macro e ranking de ativos.

```json
{
    "classes_ativos": [
      {
        "id": "caixa",
        "nome": "Caixa e Liquidez",
        "itens": {
          "indexacao": ["pos_fixado_cdi", "pos_fixado_selic"],
          "categoria": ["RF DI", "RF Simples"]
        }
      },
      {
        "id": "renda_fixa",
        "nome": "Renda Fixa Estruturada",
        "itens": {
          "indexacao": ["ipca_mais", "prefixado"],
          "categoria": ["Multimercado RF"]
        }
      },
      {
        "id": "multimercado",
        "nome": "Multimercado",
        "itens": {
          "categoria": ["Multimercado", "Long Biased"]
        }
      },
      {
        "id": "renda_variavel",
        "nome": "Renda Variável",
        "itens": {
          "categoria": ["FIA"],
          "tipo": ["Ação", "FII"]
        }
      }
    ]
  }
```

---

## Como foi montada

O ponto de partida são as três tabelas do banco: `ativos_renda_fixa`, `ativos_fundos` e `ativos_acoes`. Cada uma tem uma coluna que diferencia os ativos no mesmo nível — `indexacao`, `categoria` e `tipo`, respectivamente. A classificação mapeia os valores dessas colunas para um dos 4 grupos.

O critério de agrupamento não é o instrumento jurídico (CDB, fundo, ação) nem o emissor. É o **comportamento frente ao cenário macroeconômico**: quais indicadores afetam o ativo, em qual direção e com qual intensidade.

## O princípio por trás

Cada classe tem uma assinatura de risco distinta e não sobreponível:

- **caixa** — segue a Selic diretamente, volatilidade quase zero, imune aos demais indicadores. Serve como reserva e referência de custo de oportunidade.
- **renda_fixa** — tem duration e indexador definido na contratação. Sofre marcação a mercado quando Selic ou risco fiscal mudam. `Multimercado RF` está aqui porque carrega crédito privado com duration — comporta-se como RF longa, não como fundo livre.
- **multimercado** — gestão ativa com mandato flexível. `Long Biased` está aqui porque não é direcional puro — ele hedgeia, diferente de FIA ou Ação.
- **renda_variavel** — retorno primariamente determinado pelo crescimento econômico (PIB) e pelo custo de capital (Selic). FII está aqui porque negocia em bolsa e tem o mesmo perfil de risco de suitability que Ação.

A consequência prática: qualquer código que precise classificar um ativo faz uma única consulta a este arquivo. Suitability, scoring macro e ranking intra-classe partem do mesmo `id` de classe — eliminando regras paralelas e inconsistentes espalhadas pelo projeto.
