# Plano de Priorização de Ativos — Engine de Recomendação

**Versão:** 1.0
**Data:** 2026-03-31
**Grafo alvo:** `gerar_recomendacao` (graph_recomendacao_001)

---

## 1. Contexto e Estado Atual

### O que já existe no grafo

| Componente | Node | Saída |
|---|---|---|
| Suitability | Code `pJsCwAf6EH1XY4onJPYMm` | `{ perfil_cliente, acoes[], fundos[], rf[] }` — cada ativo com `adequado: bool` |
| Scoring Macro | Code `SpBIrk0LtDlP2tssP_5lh` | scores de -2 a +2 para 7 indicadores macro |
| Preços ações 12m | Http Call → Code `55TFLR6ZPkr88UFGauHV6` | array `{ mes, ticker, preco_fechamento }` |
| Cotas fundos 12m | Http Call → Code (URL Cotas) | array `{ mes, cnpj, cota_fechamento }` |
| Macro 12m | Http Call → Code `0iDY3cnMcZm-_MPQ8XxwP` | array `{ mes, cdi_mensal, selic_mensal, ... }` |
| Posições ações | Http Call POSICOES ACOES | array `{ ticker, quantidade, preco_medio_compra }` |
| Posições fundos | Http Call POSICOES FUNDOS | array `{ cnpj, numero_cotas, valor_aplicado }` |
| Posições RF | Http Call Posicoes RF | array `{ ativo_id, taxa_contratada, valor_aplicado, data_vencimento }` |

### O que falta

O grafo atual tem dados e suitability, mas não tem:
1. **Performance histórica** de cada ativo calculada (retorno 12m, drawdown)
2. **Ranking dentro da mesma classe** (qual ação preferir entre LREN3 e ARZZ3?)
3. **Diagnóstico de alocação** (o cliente está sobre/subexposto em qual classe?)
4. **Recomendação de rebalanceamento** (comprar X, vender Y para voltar ao alvo)

---

## 2. Arquitetura dos Módulos

```
[Suitability] ──────────────────────────────────────────────► [M2: Ranking]
[Preços 12m]  ──► [M1: Enriquecimento] ──────────────────────► [M2: Ranking]
[Cotas 12m]   ──► [M1: Enriquecimento]                                │
[Macro 12m]   ──► [M1: Enriquecimento]                                ▼
                                                             [M4: Recomendações]
[Posições]    ──────────────────────────────────────────────►          ▲
[Preços atuais] ► [M3: Alocação Atual vs Alvo] ──────────────────────┘
[Perfil cliente] ► [M3: Alocação]
```

**Princípio de design:** cada módulo é um Code node autossuficiente. Seu output é um
JSON estruturado que tem valor por si só — pode ser inspecionado no Remote Debugger,
logado, ou consumido por outros grafos no futuro sem depender dos módulos anteriores.

---

## 3. Módulo 1 — Enriquecimento de Ativos

### Por que este módulo existe

O Suitability retorna ativos com `adequado: true/false` mas sem nenhuma informação
de performance. Para ordenar ativos da mesma classe precisamos de métricas comparáveis.
O enriquecimento centraliza todos os cálculos de performance em um único lugar,
evitando repetição nos módulos seguintes.

### Inputs

| Input | Origem | Tipo |
|---|---|---|
| `suitability` | output do node Suitability | object |
| `precos_12m` | json do Http Call PRECOS ACOES | array |
| `cotas_12m` | json do Http Call COTAS FUNDOS | array |
| `macro_12m` | json do Http Call MACRO | array |
| `posicoes_acoes` | json do Http Call POSICOES ACOES | array |
| `posicoes_fundos` | json do Http Call POSICOES FUNDOS | array |
| `posicoes_rf` | json do Http Call Posicoes RF | array |

### Cálculos por classe

#### Ações

**`retorno_12m`**
```
retorno_12m = (preco_atual / preco_12_meses_atras) - 1
```
- `preco_atual` = registro mais recente em `precos_12m` para o ticker
- `preco_12_meses_atras` = registro mais antigo em `precos_12m` para o ticker
- Justificativa: retorno 12m é a métrica de momentum mais usada em gestão ativa.
  Captura ciclos completos sem ser sensível demais ao curto prazo.

**`drawdown_vs_pm`**
```
drawdown_vs_pm = (preco_atual / preco_medio_compra) - 1
```
- `preco_medio_compra` vem de `posicoes_acoes`
- Justificativa: drawdown vs PM é o que o cliente vê no extrato. Um ativo com
  retorno positivo no mercado mas negativo vs PM do cliente cria atrito na
  recomendação de venda — o cliente não percebe o ganho relativo.

#### Fundos

**`retorno_12m`**
```
cota_atual = cota mais recente em cotas_12m para o cnpj
cota_inicial = cota mais antiga em cotas_12m para o cnpj
retorno_12m = (cota_atual / cota_inicial) - 1
```

**`retorno_vs_cdi`**
```
cdi_acumulado_12m = produto de (1 + cdi_mensal/100) para cada mês em macro_12m
retorno_vs_cdi = retorno_12m - cdi_acumulado_12m
```
- Justificativa: CDI é o benchmark universal de custo de oportunidade no Brasil.
  Um fundo que entrega menos que o CDI está destruindo valor — o cliente poderia
  estar num CDB. Este é o critério mais direto para recomendar saída de um fundo.

#### Renda Fixa

**`spread_vs_cdi`**
```
cdi_atual = último valor de cdi_mensal em macro_12m * 12  (anualizado)
spread_vs_cdi = taxa_contratada - cdi_atual
```
- Positivo = título remunera acima do CDI anual → favorável
- Negativo = título remunera abaixo do CDI anual → candidato a troca
- Justificativa: para RF pós-fixada, o spread sobre CDI é o critério definitivo.
  Para prefixado e IPCA+, comparar diretamente não é correto (são indexadores
  diferentes), mas serve como referência de atratividade relativa.

### Output

```json
{
  "acoes": [
    {
      "ticker": "LREN3",
      "nome": "Lojas Renner",
      "tipo": "Ação",
      "setor": "Varejo",
      "perfil_minimo": "moderado",
      "adequado": true,
      "preco_atual": 12.50,
      "preco_medio_compra": 18.30,
      "retorno_12m": -0.12,
      "drawdown_vs_pm": -0.317
    }
  ],
  "fundos": [
    {
      "cnpj": "...",
      "nome": "Ibiuna Hedge ST",
      "categoria": "Multimercado",
      "adequado": true,
      "retorno_12m": 0.118,
      "cdi_acumulado_12m": 0.107,
      "retorno_vs_cdi": 0.011
    }
  ],
  "rf": [
    {
      "id": "...",
      "nome": "CDB BTG CDI",
      "indexacao": "pos_fixado_cdi",
      "taxa_contratada": 13.5,
      "cdi_atual_anual": 13.15,
      "spread_vs_cdi": 0.35,
      "data_vencimento": "2026-12-01",
      "valor_aplicado": 50000
    }
  ]
}
```

### Node no Rivet

| Propriedade | Valor |
|---|---|
| Tipo | Code node |
| Nome sugerido | `Enriquecimento` |
| inputNames | `suitability`, `precos_12m`, `cotas_12m`, `macro_12m`, `posicoes_acoes`, `posicoes_fundos`, `posicoes_rf` |
| outputNames | `output` |
| Conexões de entrada | Suitability/output, Http Calls diretos (json) |
| Conexões de saída | M2 Ranking / `enriquecido` |

---

## 4. Módulo 2 — Ranking Intra-classe

### Por que este módulo existe

Dentro de uma classe, o cliente pode ter múltiplos ativos adequados. Quando o
M3 identifica que Ações estão subrepresentadas, precisamos saber *qual* ação
recomendar comprar. O ranking resolve isso com critérios objetivos e auditáveis,
sem depender do LLM para escolher.

### Inputs

| Input | Origem | Tipo |
|---|---|---|
| `enriquecido` | output do M1 Enriquecimento | object |

### Critérios de score por classe

#### Ações — score de 0 a 100

```
base = 50

+ retorno_12m * 100           (ex: +15% → +15 pontos)
- abs(drawdown_vs_pm) * 50    (ex: -30% drawdown → -15 pontos)
- penalidade_concentracao      (peso > 20% do portfólio → -10)
- penalidade_drawdown_severo   (drawdown_vs_pm < -40% → -20)
```

Justificativa das penalidades:
- `drawdown_vs_pm` severo: ativo em queda acentuada vs PM cria risco de
  "realizar prejuízo". A recomendação de venda encontrará resistência do cliente.
  Penalizar no ranking faz o modelo hesitar antes de sugerir comprar mais.
- Concentração: portfólio com >20% num único ativo tem risco idiossincrático
  elevado. Mesmo que o ativo seja bom, aumentar concentração é má prática.

#### Fundos — score de 0 a 100

```
base = 50

+ retorno_vs_cdi * 300        (ex: +1% acima CDI → +3 pontos)
- penalidade_liquidez          (prazo_resgate_dias > 30 → -10)
- penalidade_underperformance  (retorno_vs_cdi < -0.02 → -25)
```

Justificativa:
- `retorno_vs_cdi` tem peso maior (300x) porque é o critério mais discriminante.
  Fundos que entregam consistentemente acima do CDI são raros e valiosos.
- Penalidade de liquidez: fundos com resgate longo travam capital. Num cenário
  de rebalanceamento urgente, isso é um passivo operacional.

#### RF — score de 0 a 100

```
base = 50

+ spread_vs_cdi * 100         (ex: +2pp → +2 pontos)
- penalidade_vencimento_curto  (meses_até_vencimento < 6 → -15)
- penalidade_vencimento_longo  (meses_até_vencimento > 60 → -5)
```

Justificativa:
- Vencimento curto: título que vence em menos de 6 meses já está "se resgatando
  sozinho". Não faz sentido recomendar comprar mais de algo que vai se liquidar.
- Vencimento muito longo: aumenta risco de mercado e imobiliza capital por
  tempo excessivo, especialmente em ambiente de juros incertos.

### Output

```json
{
  "acoes_ranked": [
    { "ticker": "WEGE3", "score": 72, "rank": 1, "motivo_principal": "retorno_12m +18%" },
    { "ticker": "ITUB4", "score": 65, "rank": 2, "motivo_principal": "retorno_12m +12%" },
    { "ticker": "LREN3", "score": 38, "rank": 3, "motivo_principal": "drawdown_vs_pm -31%" }
  ],
  "fundos_ranked": [
    { "cnpj": "...", "nome": "Ibiuna Hedge ST", "score": 68, "rank": 1 },
    { "cnpj": "...", "nome": "Brave I FIC",     "score": 55, "rank": 2 }
  ],
  "rf_ranked": [
    { "nome": "CDB BTG CDI", "score": 71, "rank": 1 },
    { "nome": "Tesouro Selic 2029", "score": 60, "rank": 2 }
  ]
}
```

### Node no Rivet

| Propriedade | Valor |
|---|---|
| Tipo | Code node |
| Nome sugerido | `Ranking` |
| inputNames | `enriquecido` |
| outputNames | `output` |
| Conexões de entrada | M1 Enriquecimento / `output` |
| Conexões de saída | M4 Recomendações / `ranking` |

---

## 5. Módulo 3 — Alocação Atual vs Alvo

### Por que este módulo existe

Saber que LREN3 tem bom score não é suficiente para recomendar compra. Se o cliente
já tem 30% em ações (alvo máximo para moderado) não faz sentido comprar mais ações
independente de qual seja. O diagnóstico de alocação transforma o problema de
"qual ativo é melhor" para "qual classe precisa de capital" — que é a pergunta
correta em gestão de portfólio.

### Inputs

| Input | Origem | Tipo |
|---|---|---|
| `enriquecido` | output do M1 | object |
| `posicoes_acoes` | json Http Call POSICOES ACOES | array |
| `posicoes_fundos` | json Http Call POSICOES FUNDOS | array |
| `posicoes_rf` | json Http Call Posicoes RF | array |
| `perfil_cliente` | extraído do Suitability output | string |

### Mapeamento ativo → bucket de alocação

```
Bucket rf_pos:
  ativos_acoes:  —
  ativos_fundos: categoria = 'RF DI' | 'RF Simples'
  ativos_rf:     indexacao = 'pos_fixado_cdi' | 'pos_fixado_selic'

Bucket rf_ipca:
  ativos_acoes:  —
  ativos_fundos: categoria = 'Multimercado RF'
  ativos_rf:     indexacao = 'ipca_mais' | 'prefixado'

Bucket mm_baixo:
  ativos_acoes:  —
  ativos_fundos: categoria = 'Multimercado'
  ativos_rf:     —

Bucket mm_alto:
  ativos_acoes:  —
  ativos_fundos: categoria = 'Long Biased'
  ativos_rf:     —

Bucket acoes:
  ativos_acoes:  tipo = 'Ação' | 'FII'
  ativos_fundos: categoria = 'FIA'
  ativos_rf:     —
```

Justificativa do mapeamento:
- `Multimercado RF` vai para `rf_ipca` (não `mm_baixo`) porque esses fundos têm
  mandato de crédito privado com duration — comportam-se mais como RF longa que
  como multimercado livre.
- `Long Biased` vai para `mm_alto` porque, apesar de ser fundo, tem exposição
  direcional em ações — seu risco efetivo é mais próximo de renda variável.
- FIA vai para `acoes` pelo mesmo motivo: são fundos com mandato 100% ações.

### Faixas alvo por perfil

```javascript
const FAIXAS = {
  conservador: {
    rf_pos:   { min: 0.50, max: 0.80 },
    rf_ipca:  { min: 0.10, max: 0.30 },
    mm_baixo: { min: 0.05, max: 0.15 },
    mm_alto:  { min: 0.00, max: 0.00 },
    acoes:    { min: 0.00, max: 0.05 },
  },
  moderado: {
    rf_pos:   { min: 0.20, max: 0.40 },
    rf_ipca:  { min: 0.10, max: 0.20 },
    mm_baixo: { min: 0.10, max: 0.20 },
    mm_alto:  { min: 0.05, max: 0.15 },
    acoes:    { min: 0.15, max: 0.30 },
  },
  arrojado: {
    rf_pos:   { min: 0.05, max: 0.15 },
    rf_ipca:  { min: 0.05, max: 0.10 },
    mm_baixo: { min: 0.10, max: 0.20 },
    mm_alto:  { min: 0.15, max: 0.25 },
    acoes:    { min: 0.40, max: 0.60 },
  },
  agressivo: {
    rf_pos:   { min: 0.00, max: 0.10 },
    rf_ipca:  { min: 0.00, max: 0.10 },
    mm_baixo: { min: 0.05, max: 0.15 },
    mm_alto:  { min: 0.20, max: 0.30 },
    acoes:    { min: 0.50, max: 0.70 },
  },
};
```

### Cálculo de valor atual por bucket

Para cada posição, o valor atual é:

```
Ações:   valor_atual = quantidade * preco_atual  (preco_atual do mês referência)
Fundos:  valor_atual = numero_cotas * cota_atual (cota_atual do mês referência)
RF:      valor_atual = valor_aplicado            (não tem marcação a mercado diária)
```

Justificativa de usar `valor_aplicado` para RF: renda fixa no modelo atual não tem
histórico de marcação a mercado. O valor aplicado é a melhor aproximação disponível
sem adicionar complexidade de cálculo de PU (preço unitário).

### Status por bucket

```
ABAIXO  → atual < min
OK      → min <= atual <= max
ACIMA   → atual > max
```

### Output

```json
{
  "valor_total": 386858.00,
  "perfil": "moderado",
  "buckets": {
    "rf_pos": {
      "valor": 212000,
      "pct_atual": 0.548,
      "min": 0.20,
      "max": 0.40,
      "status": "ACIMA",
      "desvio_pct": 0.148,
      "desvio_brl": 57280
    },
    "acoes": {
      "valor": 46000,
      "pct_atual": 0.119,
      "min": 0.15,
      "max": 0.30,
      "status": "ABAIXO",
      "desvio_pct": -0.031,
      "desvio_brl": -12000
    },
    "mm_alto": {
      "valor": 29000,
      "pct_atual": 0.075,
      "min": 0.05,
      "max": 0.15,
      "status": "OK",
      "desvio_pct": 0.0,
      "desvio_brl": 0
    }
  }
}
```

O campo `desvio_brl` é crítico: ele diz quantos reais precisam ser movidos para
corrigir o desvio. Isso alimenta diretamente a recomendação de valor no M4.

### Node no Rivet

| Propriedade | Valor |
|---|---|
| Tipo | Code node |
| Nome sugerido | `Alocacao` |
| inputNames | `enriquecido`, `posicoes_acoes`, `posicoes_fundos`, `posicoes_rf` |
| outputNames | `output` |
| Conexões de entrada | M1/output, Http Calls diretos (json) |
| Conexões de saída | M4 Recomendações / `alocacao` |

**Nota:** `perfil_cliente` não precisa ser input separado — já está dentro de
`enriquecido.perfil_cliente` herdado do Suitability.

---

## 6. Módulo 4 — Recomendações

### Por que este módulo existe

Este módulo é o árbitro final. Ele cruza três sinais:
1. **Ranking** (M2): qual ativo é mais qualificado dentro da classe?
2. **Alocação** (M3): qual classe precisa de capital ou está sobrando?
3. **Macro** (Scoring Macro existente): o ambiente favorece ou penaliza esta classe?

A combinação dos três evita recomendações contraditórias — ex: não recomendar
comprar ações quando ações já estão acima do alvo E o macro está desfavorável.

### Inputs

| Input | Origem | Tipo |
|---|---|---|
| `ranking` | output M2 | object |
| `alocacao` | output M3 | object |
| `macro_scores` | output Scoring Macro existente | object |

### Lógica de decisão

#### Passo 1 — Ativos inadequados (Suitability override)

Ativos com `adequado: false` recebem `acao: VENDER` e `urgencia: REGULATORIO`
independentemente de qualquer outro sinal. Esta regra não pode ser sobrescrita.

Justificativa: ICVM 539/2013 exige que ativos inadequados ao perfil do cliente
sejam recomendados para venda. É obrigação regulatória, não escolha de gestão.

#### Passo 2 — Buckets ACIMA do alvo

Para cada bucket com `status: ACIMA`:
- Pegar ativo de **menor score** no ranking desse bucket
- `acao: REDUZIR`
- `valor_sugerido_brl: desvio_brl` do bucket
- `urgencia: ALTA` se desvio > 10pp | `MEDIA` se 5-10pp | `BAIXA` se < 5pp

Justificativa de usar o de menor score: se precisamos reduzir exposição em RF pós,
faz mais sentido reduzir o título menos atrativo (menor spread, vencimento próximo)
do que o melhor. Preservamos os ativos de maior qualidade.

#### Passo 3 — Buckets ABAIXO do alvo

Para cada bucket com `status: ABAIXO`:
- Verificar se macro_score da classe é >= 0 (neutro ou positivo)
- Pegar ativo de **maior score** no ranking desse bucket com `adequado: true`
- `acao: COMPRAR`
- `valor_sugerido_brl: abs(desvio_brl)` do bucket
- `urgencia: ALTA` se macro favorável E desvio > 5pp | caso contrário `MEDIA`

Se macro_score < 0 (cenário desfavorável para a classe):
- `acao: MANTER_ABAIXO` — não recomendar compra mesmo com alocação abaixo do alvo
- Justificativa: comprar ações num cenário macro desfavorável só para atingir alvo
  de alocação é tecnicamente correto mas destruidor de valor. Aguardar o cenário
  melhorar é a decisão de gestão mais saudável.

#### Passo 4 — Buckets OK

- `acao: MANTER` para todos os ativos do bucket
- Sem valor sugerido

### Output

```json
{
  "recomendacoes": [
    {
      "ativo": "Trend DI",
      "classe": "rf_pos",
      "bucket": "rf_pos",
      "acao": "REDUZIR",
      "urgencia": "ALTA",
      "valor_sugerido_brl": 57280,
      "motivo": "RF pós 14.8pp acima do alvo. Score mais baixo da classe.",
      "score_ativo": 45,
      "rank_na_classe": 3
    },
    {
      "ativo": "WEGE3",
      "classe": "acoes",
      "bucket": "acoes",
      "acao": "COMPRAR",
      "urgencia": "ALTA",
      "valor_sugerido_brl": 12000,
      "motivo": "Ações 3.1pp abaixo do alvo. Melhor score da classe. Macro favorável.",
      "score_ativo": 72,
      "rank_na_classe": 1
    },
    {
      "ativo": "Truxt Long Bias",
      "classe": "mm_alto",
      "bucket": "mm_alto",
      "acao": "VENDER",
      "urgencia": "REGULATORIO",
      "valor_sugerido_brl": null,
      "motivo": "Suitability: Long Biased requer perfil arrojado. Cliente é moderado.",
      "score_ativo": null,
      "rank_na_classe": null
    }
  ],
  "resumo": {
    "total_vender_brl": 57280,
    "total_comprar_brl": 12000,
    "ativos_regulatorio": 2,
    "buckets_acima": 1,
    "buckets_abaixo": 1,
    "buckets_ok": 3
  }
}
```

### Node no Rivet

| Propriedade | Valor |
|---|---|
| Tipo | Code node |
| Nome sugerido | `Recomendacoes` |
| inputNames | `ranking`, `alocacao`, `macro_scores` |
| outputNames | `output` |
| Conexões de entrada | M2/output, M3/output, Scoring Macro/output |
| Conexões de saída | `Montar Prompt` (substitui ou complementa lógica atual) |

---

## 7. Ordem de Implementação Incremental

A ordem prioriza entregar valor observável em cada passo, antes de construir o
passo seguinte.

### Passo 1 — M3: Alocação (implementar primeiro)

**Por quê primeiro:** depende apenas de dados já no grafo (posições + preços atuais).
Não depende de M1 nem M2. Permite validar imediatamente se os buckets e percentuais
calculados fazem sentido para o Albert antes de construir qualquer ranking.

**Critério de aceite:** rodar com `albert-2025-02`, conferir os percentuais por
bucket contra o extrato real do cliente. Os números devem bater.

### Passo 2 — M1: Enriquecimento

**Por quê segundo:** já temos preços e cotas 12m no grafo (mudança anterior).
Implementar agora aproveita esses dados e valida se os cálculos de retorno 12m
estão corretos antes de usá-los no ranking.

**Critério de aceite:** inspecionar o output no Remote Debugger. `retorno_12m`
de WEGE3 e Ibiuna devem ser razoáveis vs dados públicos.

### Passo 3 — M2: Ranking

**Por quê terceiro:** depende do M1. Uma vez que o enriquecimento estiver correto,
o ranking é só ordenação — rápido de implementar e fácil de validar (checar
se a ordem faz sentido intuitivamente).

**Critério de aceite:** WEGE3 e ITUB4 devem estar entre os primeiros em ações.
Ibiuna deve estar acima de fundos que underperformam CDI.

### Passo 4 — M4: Recomendações

**Por quê por último:** depende de M2 + M3 corretos. Só faz sentido construir
quando os dois anteriores estiverem validados.

**Critério de aceite:** recomendações para Albert devem incluir VENDA de Truxt e
STK (suitability), REDUÇÃO de RF pós se acima do alvo, e não recomendar compra
de algo que já está ACIMA do alvo.

---

## 8. Interfaces entre Módulos — Contrato de Dados

Cada interface é um contrato. Se os campos abaixo estiverem presentes e corretos,
o módulo seguinte funciona independentemente de como o anterior foi implementado.

### Interface M1 → M2

Campo obrigatório em cada ativo do output de M1:
- `adequado: boolean`
- `retorno_12m: number | null`
- `drawdown_vs_pm: number | null` (apenas ações)
- `retorno_vs_cdi: number | null` (apenas fundos)
- `spread_vs_cdi: number | null` (apenas RF)

### Interface M2 → M4

Campo obrigatório em cada array ranked do output de M2:
- `score: number` (0-100)
- `rank: number` (1 = melhor)
- `adequado: boolean`
- `bucket: string` (qual bucket de alocação este ativo pertence)

### Interface M3 → M4

Campo obrigatório em cada bucket do output de M3:
- `status: 'ACIMA' | 'OK' | 'ABAIXO'`
- `desvio_brl: number`
- `desvio_pct: number`
- `pct_atual: number`

### Interface M4 → Montar Prompt

Campo obrigatório em cada recomendação:
- `ativo: string`
- `acao: 'COMPRAR' | 'AUMENTAR' | 'MANTER' | 'MANTER_ABAIXO' | 'REDUZIR' | 'VENDER'`
- `urgencia: 'REGULATORIO' | 'ALTA' | 'MEDIA' | 'BAIXA'`
- `motivo: string`
- `valor_sugerido_brl: number | null`

---

## 9. O que não muda

- `server.mjs` — nenhuma alteração
- Edge Function — nenhuma alteração
- Streamlit — nenhuma alteração
- `graphInput "job"` — permanece igual
- HTTP Calls existentes — nenhuma alteração
- Scoring Macro — permanece igual, apenas seu output é consumido pelo M4
