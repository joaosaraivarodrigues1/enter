# Estrutura dos Ativos no Rivet

## Saídas de cada entrada

```js
// ativos_renda_fixa
{ id, nome, instrumento, indexacao }

// ativos_acoes
{ ticker, nome, tipo, setor }

// ativos_fundos
{ cnpj, nome, categoria }

// precos_acoes
{ mes, ticker, preco_fechamento }

// cotas_fundos
{ mes, cnpj, cota_fechamento }

// dados_mercado
{ mes, cdi_mensal, selic_mensal, ipca_mensal, ibovespa_retorno_mensal, usd_brl_fechamento, pib_crescimento_anual }
```

---


# Estruturas com a propriedade mes tem 12 messes registrados #