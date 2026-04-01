# Ranking de Ativos por Classe

## Resumo

Dado um conjunto de ativos e 12 meses de dados históricos e macro, ordena os ativos dentro de cada classe por prioridade de se possuir. Ativos com histórico de preços são ordenados por sharpe_proxy vs benchmark. Ativos de renda fixa pura (sem histórico) são ordenados por alinhamento com o cenário macro. A saída é um JSON com as 4 classes em ordem alfabética, cada uma com seus ativos ordenados por score decrescente.

---

## Dados disponíveis

```js
// ativos_renda_fixa  — sem histórico de preços
{ id, nome, instrumento, indexacao }

// ativos_acoes       — com histórico em precos_acoes
{ ticker, nome, tipo, setor }

// ativos_fundos      — com histórico em cotas_fundos
{ cnpj, nome, categoria }

// precos_acoes       — 12 meses
{ mes, ticker, preco_fechamento }

// cotas_fundos       — 12 meses
{ mes, cnpj, cota_fechamento }

// dados_mercado      — 12 meses
{ mes, cdi_mensal, selic_mensal, ipca_mensal, ibovespa_retorno_mensal, usd_brl_fechamento, pib_crescimento_anual }
```

---

## Derivações do macro

```
cdi_12m         = ∏(1 + cdi_mensal[i]/100) - 1
ibov_12m        = ∏(1 + ibov_mensal[i]/100) - 1
ipca_12m        = Σ(ipca_mensal[i])

selic_atual     = selic_mensal[11]
selic_media_3m  = média(selic_mensal[8..10])
selic_tendencia = selic_atual > selic_media_3m * 1.005 → "alta"
                | selic_atual < selic_media_3m * 0.995 → "baixa"
                | else                                 → "estavel"
```

---

## Score para ativos com histórico de preços

Aplicável a: `ativos_acoes`, `ativos_fundos`

```
retornos_mensais[i] = (preco[i] / preco[i-1]) - 1        // 11 valores

retorno_12m  = (preco_ultimo / preco_primeiro) - 1
volatilidade = desvio_padrao_amostral(retornos_mensais)   // divisor n-1

alpha_cdi    = retorno_12m - cdi_12m    // para caixa, renda_fixa, multimercado
alpha_ibov   = retorno_12m - ibov_12m   // para renda_variavel

score = alpha / volatilidade            // sharpe_proxy
```

---

## Score para renda fixa pura (sem histórico)

Aplicável a: `ativos_renda_fixa`

```
// classe caixa
pos_fixado_selic → score = selic_tendencia == "alta" ? 1 : 0
pos_fixado_cdi   → score = 0   // referência da classe

// classe renda_fixa
ipca_mais  → score = ipca_12m > 5 ? 1 : 0
prefixado  → score = selic_tendencia == "baixa" ? 1 : 0
```

---

## Critério por classe

**`caixa`** — RF(pos_fixado_cdi, pos_fixado_selic) + Fundos(RF DI, RF Simples)
- Fundos: score = alpha_cdi / volatilidade
- RF: score ordinal por selic_tendencia
- Benchmark: cdi_12m

**`multimercado`** — Fundos(Multimercado, Long Biased)
- Score = alpha_cdi / volatilidade
- Benchmark: cdi_12m

**`renda_fixa`** — RF(ipca_mais, prefixado) + Fundos(Multimercado RF)
- Fundos: score = alpha_cdi / volatilidade
- RF: score ordinal por ipca_12m e selic_tendencia
- Benchmark: cdi_12m

**`renda_variavel`** — Ações(Ação, FII) + Fundos(FIA)
- Score = alpha_ibov / volatilidade
- Benchmark: ibov_12m

---

## Formato de saída

```json
{
  "caixa": [
    { "id": "...", "nome": "...", "score": 0.42, "tipo_ativo": "fundo" },
    { "id": "...", "nome": "...", "score": 0.10, "tipo_ativo": "rf"    }
  ],
  "multimercado":   [ ... ],
  "renda_fixa":     [ ... ],
  "renda_variavel": [ ... ]
}
```

Dentro de cada classe: ordem decrescente por `score`. Classes: ordem alfabética.

---

## Limitações

**1. RF sem histórico de preços**
Score é 0 ou 1 — não contínuo. Empates frequentes dentro da mesma indexação. Fundos sempre terão scores mais discriminados que ativos RF puros na mesma classe.

**2. `setor` é null em todas as ações**
Impossível aplicar o sinal de câmbio (USD/BRL) por tipo de empresa. O macro de câmbio não é usado no ranking de ações individuais.

**3. `categoria` null em alguns fundos**
Fundos sem categoria não são classificáveis em nenhuma classe e ficam fora do ranking.

**4. Sharpe com 11 pontos**
Desvio padrão sobre 11 retornos mensais é estatisticamente instável. Um único mês atípico distorce o score significativamente.

**5. Benchmark único para renda_variavel**
Ações, FIIs e FIAs competem contra o mesmo Ibovespa. O benchmark ideal para FIIs seria o IFIX — não disponível nos dados.

**6. Sem ajuste por liquidez**
`prazo_resgate_dias` não está nos dados disponíveis no Rivet. Um fundo D+30 e um D+0 recebem o mesmo score.

**7. Janela fixa de 12 meses**
Não captura reversão recente. Um ativo que caiu 11 meses e recuperou no último recebe score baixo apesar da melhora.
