# Ranking de Classes de Ativos

Lógica de pontuação macro que ordena as 4 classes de ativos por atratividade dado um cenário econômico.
Cada indicador recebe um score de -2 a +2. O score de cada classe é o produto escalar entre esses scores e os pesos abaixo.
A saída é uma lista ordenada das classes — da mais favorecida à mais prejudicada pelo cenário atual.

```json
{
  "scoring_macro": {
    "convencao": {
      "escala": [-2, -1, 0, 1, 2],
      "interpretacao": {
        "-2": "cenário extremamente desfavorável para a classe",
        "-1": "cenário levemente desfavorável",
         "0": "neutro — indicador não afeta a classe de forma material",
        "+1": "cenário levemente favorável",
        "+2": "cenário extremamente favorável para a classe"
      },
      "calculo": "score_classe = Σ(score_indicador × peso_classe)"
    },
    "pesos": {
      "caixa": {
        "selic":    2,
        "ipca":     0,
        "cambio":   0,
        "pib":      0,
        "credito":  0,
        "fiscal":  -1,
        "externo":  0
      },
      "renda_fixa": {
        "selic":   -1,
        "ipca":     1,
        "cambio":   0,
        "pib":      0,
        "credito": -1,
        "fiscal":  -2,
        "externo": -1
      },
      "multimercado": {
        "selic":   -1,
        "ipca":     0,
        "cambio":   1,
        "pib":      1,
        "credito":  0,
        "fiscal":  -1,
        "externo":  0
      },
      "renda_variavel": {
        "selic":   -2,
        "ipca":     0,
        "cambio":   0,
        "pib":      2,
        "credito":  0,
        "fiscal":  -1,
        "externo": -2
      }
    }
  }
}
```

---

## Escala de Pontuação por Indicador

O score de cada indicador é extraído por um LLM que lê um parágrafo de análise macro e retorna um inteiro de -2 a +2. As escalas abaixo definem o que cada valor significa para cada indicador.

```json
{
  "escalas_indicadores": {
    "selic": {
      "+2": "Copom em ciclo de aperto agressivo. Selic subindo com força, sem sinal de pausa.",
      "+1": "Selic subindo em ritmo moderado, ou pausa próxima mas ainda não sinalizada.",
       "0": "Selic estável. Direção incerta ou sinais mistos.",
      "-1": "Selic caindo gradualmente, ou início de ciclo de corte.",
      "-2": "Copom em ciclo de afrouxamento agressivo. Selic caindo com força."
    },
    "ipca": {
      "+2": "Inflação muito alta, disseminada e acelerando. Bem acima da meta sem alívio próximo.",
      "+1": "Inflação elevada e persistente, mas com primeiros sinais de estabilização.",
       "0": "Inflação próxima da meta ou direção incerta.",
      "-1": "Inflação desacelerando e convergindo para a meta.",
      "-2": "Inflação bem controlada, na meta ou abaixo, e em queda."
    },
    "cambio": {
      "+2": "BRL severamente depreciado. USD/BRL muito alto e subindo, com forte pressão de desvalorização.",
      "+1": "BRL moderadamente fraco. USD/BRL elevado mas relativamente estável.",
       "0": "Câmbio próximo do equilíbrio ou direção incerta.",
      "-1": "BRL apreciando moderadamente. USD/BRL caindo gradualmente.",
      "-2": "BRL fortemente apreciado. USD/BRL caindo com força."
    },
    "pib": {
      "+2": "Economia crescendo com força. PIB bem acima do potencial, demanda robusta.",
      "+1": "Economia crescendo em ritmo moderado, acima da tendência.",
       "0": "Crescimento próximo do potencial ou sinais mistos.",
      "-1": "Economia desacelerando. Crescimento abaixo da tendência, consumo esfriando.",
      "-2": "Economia em recessão ou contração severa. Demanda em colapso."
    },
    "credito": {
      "+2": "Spreads de crédito muito abertos. Risco de default corporativo alto. Fundos de crédito privado sob estresse significativo.",
      "+1": "Spreads elevados e se abrindo. Primeiros sinais de estresse de crédito no setor corporativo.",
       "0": "Condições de crédito neutras. Spreads próximos das médias históricas.",
      "-1": "Spreads fechando. Condições de crédito melhorando para tomadores corporativos.",
      "-2": "Spreads muito comprimidos. Crédito abundante e barato para empresas."
    },
    "fiscal": {
      "+2": "Risco fiscal muito alto. Dívida pública em trajetória insustentável. Mercado precificando prêmio de risco soberano significativo.",
      "+1": "Risco fiscal elevado. Pressões fiscais persistem, dívida crescendo acima do PIB.",
       "0": "Situação fiscal neutra ou mista. Dívida estável em relação ao PIB.",
      "-1": "Condições fiscais melhorando. Superávit primário no caminho, trajetória da dívida estabilizando.",
      "-2": "Risco fiscal muito baixo. Orçamento equilibrado, dívida claramente sustentável."
    },
    "externo": {
      "+2": "Cenário externo muito adverso. Fed agressivamente hawkish, forte risk-off, capitais fugindo de emergentes.",
      "+1": "Cenário externo moderadamente adverso. Fed parado em juros altos, incerteza global elevada.",
       "0": "Cenário externo neutro. Sinais mistos, sem pressão direcional clara sobre o Brasil.",
      "-1": "Cenário externo moderadamente favorável. Fed sinalizando cortes, apetite por risco melhorando.",
      "-2": "Cenário externo muito favorável. Fed em ciclo de afrouxamento, forte risk-on, capital fluindo para emergentes."
    }
  }
}
```

---

## Regras de Negócio

### Caixa e Liquidez

A única variável que importa é a Selic. Quando o Banco Central eleva os juros, a remuneração diária do CDI/Selic sobe junto — Caixa ganha mais sem nenhum risco adicional. Inflação, câmbio, PIB, crédito e cenário externo não alteram a rentabilidade do caixa de forma material. O único risco indireto é o fiscal: deterioração severa das contas públicas pode antecipar cortes de juros e encurtar o período de juros altos.

| Indicador | Peso | Motivo |
|-----------|------|--------|
| selic     | +2   | remuneração do CDI/Selic sobe diretamente com a taxa |
| fiscal    | -1   | risco de reversão antecipada do ciclo de alta |
| demais    |  0   | sem impacto material |

---

### Renda Fixa Estruturada

Carrega duration e indexador definido na emissão, portanto sofre marcação a mercado. Alta de Selic deprecia o preço dos títulos e fundos de crédito. IPCA alto beneficia os papéis IPCA+ diretamente. Risco fiscal é o principal inimigo: abre o prêmio de risco nos títulos longos e derruba os preços. Risco de crédito privado afeta os fundos Multimercado RF que compõem essa classe. Cenário externo adverso contamina os spreads domésticos de crédito.

| Indicador | Peso | Motivo |
|-----------|------|--------|
| selic     | -1   | alta de juros deprecia o preço dos títulos com duration |
| ipca      | +1   | beneficia diretamente os papéis IPCA+ |
| credito   | -1   | amplia spreads e deprecia fundos de crédito privado |
| fiscal    | -2   | principal driver de abertura de prêmio nos títulos longos |
| externo   | -1   | contamina spreads domésticos de crédito |
| demais    |  0   | sem impacto material |

---

### Multimercado

Gestão ativa com mandato flexível: o gestor pode montar posições em qualquer mercado. PIB acelerado expande o universo de oportunidades direcionais. Câmbio desvalorizado abre posições em exportadoras e em ativos dolarizados dentro do fundo. Alta de Selic é levemente negativa porque eleva o custo de carregamento de posições alavancadas. Risco fiscal moderadamente negativo porque limita as posições em juros longos. IPCA, crédito e externo são neutros: o gestor pode ganhar ou perder com eles dependendo do posicionamento — o efeito líquido é zero.

| Indicador | Peso | Motivo |
|-----------|------|--------|
| pib       | +1   | expande universo de oportunidades direcionais |
| cambio    | +1   | abre posições em exportadoras e ativos dolarizados |
| selic     | -1   | eleva custo de carregamento de posições alavancadas |
| fiscal    | -1   | limita posições em juros longos |
| demais    |  0   | efeito depende do posicionamento — neutro em nível de classe |

---

### Renda Variável

O retorno é determinado principalmente pelo crescimento econômico (PIB) e pelo custo de capital (Selic). PIB forte expande lucros e valuation das empresas. Alta de Selic eleva a taxa de desconto dos fluxos futuros e derruba o preço dos ativos. Risco fiscal deteriora o ambiente macro, comprime múltiplos e afasta capital estrangeiro. Cenário externo adverso reduz exportações, aperta crédito global e provoca fuga de capitais. Câmbio e crédito têm efeitos opostos entre setores (exportadoras vs. consumo interno) que se cancelam em nível de classe.

| Indicador | Peso | Motivo |
|-----------|------|--------|
| pib       | +2   | expande lucros e valuation — principal driver de retorno |
| selic     | -2   | eleva taxa de desconto e derruba preço dos ativos |
| externo   | -2   | fuga de capitais, contração de crédito global, queda de exportações |
| fiscal    | -1   | comprime múltiplos e afasta capital estrangeiro |
| demais    |  0   | efeitos opostos entre setores se cancelam |
