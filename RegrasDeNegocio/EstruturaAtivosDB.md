# Estrutura das Tabelas de Ativos — Supabase

```json
{
  "ativos_acoes": {
    "primary_key": "ticker",
    "rls": false,
    "columns": {
      "ticker":  { "type": "text",    "nullable": false },
      "nome":    { "type": "text",    "nullable": false },
      "tipo":    { "type": "text",    "nullable": true,  "enum": ["Ação", "FII"] },
      "setor":   { "type": "text",    "nullable": true  }
    },
    "referenced_by": ["posicoes_acoes.ticker", "precos_acoes.ticker"]
  },

  "ativos_fundos": {
    "primary_key": "cnpj",
    "rls": false,
    "columns": {
      "cnpj":               { "type": "text",    "nullable": false },
      "nome":               { "type": "text",    "nullable": false },
      "categoria":          { "type": "text",    "nullable": true,  "enum": ["RF DI", "RF Simples", "Multimercado RF", "Multimercado", "Long Biased", "FIA"] },
      "prazo_resgate_dias": { "type": "integer", "nullable": true  }
    },
    "referenced_by": ["posicoes_fundos.cnpj", "cotas_fundos.cnpj"]
  },

  "ativos_renda_fixa": {
    "primary_key": "id",
    "rls": false,
    "columns": {
      "id":          { "type": "uuid",    "nullable": false, "default": "gen_random_uuid()" },
      "nome":        { "type": "text",    "nullable": false, "unique": true },
      "instrumento": { "type": "text",    "nullable": false },
      "indexacao":   { "type": "text",    "nullable": false, "enum": ["pos_fixado_cdi", "pos_fixado_selic", "prefixado", "ipca_mais"] },
      "isento_ir":   { "type": "boolean", "nullable": false, "default": false },
      "emissor":     { "type": "text",    "nullable": true  }
    },
    "referenced_by": ["posicoes_renda_fixa.ativo_id"]
  }
}
```
