# Pendências

Itens identificados que precisam ser resolvidos, mas mantidos em suspenso por ora.

---

## Dados históricos incompletos

### 1. MRFG3 — sem histórico de preços

- **Problema:** MRFG3 está cadastrado em `ativos_acoes` mas não tem nenhum registro em `precos_acoes`.
- **Impacto:** Albert tem MRFG3 na carteira. Na página Resultados, o retorno mensal dessa posição não será calculado — aparecerá vazio.
- **Decisão atual:** Manter assim por enquanto.
- **Resolução futura:** Importar o histórico via edge function `fetch-acoes` ou inserir manualmente.

---

### 2. Brave I FIC FIM CP — cotas paradas em nov/2024

- **Problema:** A tabela `cotas_fundos` tem dados do Brave I FIC FIM CP somente até novembro/2024. Os últimos ~16 meses (dez/2024 → mar/2026) estão sem cota.
- **Impacto:** Carlos e Gustavo têm esse fundo nas suas carteiras planejadas. O retorno mensal desse fundo não será calculado para os meses sem cota.
- **Decisão atual:** Manter assim por enquanto.
- **Resolução futura:** Rodar `extract_fundos.py` com o CNPJ `35.726.300/0001-37` para importar as cotas faltantes via CVM.

---

## Carteiras planejadas (contexto)

Clientes afetados por essas pendências:

| Cliente | Fundo/Ação com problema | Pendência |
|---------|------------------------|-----------|
| Albert  | MRFG3                  | Sem histórico de preços |
| Carlos  | Brave I FIC FIM CP     | Cotas paradas em nov/2024 |
| Gustavo | Brave I FIC FIM CP     | Cotas paradas em nov/2024 |
