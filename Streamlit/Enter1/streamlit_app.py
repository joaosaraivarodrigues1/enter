# -*- coding: utf-8 -*-
import json
import time

import streamlit as st
import pandas as pd
import requests as http
import plotly.graph_objects as go

from supabase import create_client
from postgrest.exceptions import APIError

from create_pdf import gerar_pdf, salvar_pdf_supabase
from calculos import (
    calcular_retorno_acoes,
    calcular_retorno_fundos,
    calcular_retorno_rf,
    calcular_retorno_portfolio,
    calcular_alfas,
)
from theme import (
    colors, typography, spacing, charts, layouts, components,
    GLOBAL_CSS, PROFILE_BADGES, PROFILE_BADGE_FALLBACK,
)

st.set_page_config(
    page_title="Enter",
    layout="wide",
)

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── Conexões ─────────────────────────────────────────────────────────────────

@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

@st.cache_data(ttl=60)
def load_table(table: str):
    client = get_supabase()
    try:
        res = client.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar '{table}': {e}")
        return pd.DataFrame()

def functions_url():
    return st.secrets["SUPABASE_URL"].strip() + "/functions/v1"

def auth_header():
    return {"Authorization": f"Bearer {st.secrets['SUPABASE_KEY'].strip()}"}

def montar_relatorio(partes: list) -> str:
    (mes, nome_cliente, perfil_risco, titulo,
     titulo_selic, paragrafo_selic,
     titulo_ipca, paragrafo_ipca,
     titulo_cambio, paragrafo_cambio,
     titulo_pib, paragrafo_pib,
     titulo_credito, paragrafo_credito,
     titulo_fiscal, paragrafo_fiscal,
     titulo_externo, paragrafo_externo,
     parag) = partes

    return f"""CARTA DE ANÁLISE DE PORTFÓLIO
{mes}
Cliente: {nome_cliente}
Perfil de Risco: {perfil_risco}

---

{titulo}

---

{titulo_selic}

{paragrafo_selic}

---

{titulo_ipca}

{paragrafo_ipca}

---

{titulo_cambio}

{paragrafo_cambio}

---

{titulo_pib}

{paragrafo_pib}

---

{titulo_credito}

{paragrafo_credito}

---

{titulo_fiscal}

{paragrafo_fiscal}

---

{titulo_externo}

{paragrafo_externo}

---

Recomendação de ações

{parag}

Este relatório foi gerado automaticamente com base no relatório macro \
de referência do mês de {mes} e nas posições registradas na carteira \
do cliente."""


def gerar_recomendacao(cliente_id: str, mes: str) -> tuple:
    """Dispara a Edge Function, faz polling e retorna (texto, partes, job_id)."""
    # 1. Disparar
    resp = http.post(
        functions_url() + "/gerar-recomendacao",
        headers={
            **auth_header(),
            "apikey": st.secrets["SUPABASE_KEY"].strip(),
            "Content-Type": "application/json",
        },
        json={"cliente_id": cliente_id, "mes": mes},
        timeout=30,
    )
    resp.raise_for_status()
    job_id = resp.json()["job_id"]

    # 2. Polling na tabela recomendacoes (até 7 minutos)
    sb = get_supabase()
    for _ in range(140):
        time.sleep(3)
        row = (
            sb.table("recomendacoes")
            .select("status, resultado, erro")
            .eq("job_id", job_id)
            .single()
            .execute()
            .data
        )
        if row["status"] == "done":
            resultado = row["resultado"]
            try:
                parsed = json.loads(resultado)
                if isinstance(parsed, list):
                    return montar_relatorio(parsed), parsed, job_id
            except (json.JSONDecodeError, TypeError):
                pass
            return resultado, None, job_id
        if row["status"] == "error":
            raise RuntimeError(row.get("erro") or "Erro no processamento Rivet")

    raise TimeoutError("Timeout: recomendação não foi gerada em 7 minutos")

# ── Navegação ─────────────────────────────────────────────────────────────────

if "page" not in st.session_state:
    st.session_state.page = "home"
if "mes_selecionado" not in st.session_state:
    st.session_state.mes_selecionado = "2025-02"

@st.dialog("Período de referência")
def modal_selecionar_data():
    df_rel = load_table("relatorios")
    df_m = load_table("dados_mercado")

    # Meses com relatório disponível
    meses_rel = set()
    if not df_rel.empty:
        meses_rel = set(df_rel["mes"].dropna().unique())

    # Indicadores obrigatórios (ignora IMA-B)
    _INDICADORES = ["cdi_mensal", "selic_mensal", "ipca_mensal",
                     "ibovespa_retorno_mensal", "pib_crescimento_anual",
                     "usd_brl_fechamento"]

    # Meses com dados completos (todos indicadores não-null)
    meses_completos = set()
    if not df_m.empty:
        for _, row in df_m.iterrows():
            if all(pd.notna(row.get(ind)) for ind in _INDICADORES):
                meses_completos.add(row["mes"])

    meses_completos_sorted = sorted(meses_completos)

    # Filtrar: mês deve ter relatório E 12 meses anteriores completos
    meses_validos = []
    for mes in sorted(meses_rel):
        # Verificar se existem 12 meses anteriores com dados completos
        idx_in_sorted = None
        if mes in meses_completos_sorted:
            idx_in_sorted = meses_completos_sorted.index(mes)
        if idx_in_sorted is not None and idx_in_sorted >= 12:
            # Checar se os 12 anteriores são consecutivos e completos
            anteriores = meses_completos_sorted[idx_in_sorted - 12:idx_in_sorted]
            if len(anteriores) == 12:
                meses_validos.append(mes)

    if not meses_validos:
        st.info("Nenhum mês com relatório e 12 meses de dados históricos completos.")
        return

    atual = st.session_state.mes_selecionado
    idx = meses_validos.index(atual) if atual in meses_validos else len(meses_validos) - 1

    mes_escolhido = st.selectbox(
        "Mês de referência",
        options=meses_validos,
        index=idx,
        format_func=lambda m: pd.to_datetime(m + "-01").strftime("%b/%Y"),
    )
    st.caption(f"{len(meses_validos)} meses disponíveis · {meses_validos[0]} → {meses_validos[-1]}")

    if st.button("Confirmar", type="primary", use_container_width=True):
        st.session_state.mes_selecionado = mes_escolhido
        st.rerun()

from pathlib import Path
_LOGO_PATH = Path(__file__).parent / "XP_Investimentos_logo-removebg-preview.png"

col_logo, col_titulo = st.columns(layouts.header)
with col_logo:
    st.image(str(_LOGO_PATH), width=layouts.logo_width)
with col_titulo:
    st.title("Xp - Análise de portfólio e rendimentos")

col_home, col_clientes, col_ativos, col_indices, col_data, *_ = st.columns(layouts.nav_bar)

if col_home.button("Home", use_container_width=True):
    st.session_state.page = "home"
if col_clientes.button("Clientes", use_container_width=True):
    st.session_state.page = "clientes"
if col_ativos.button("Ativos Disponíveis", use_container_width=True):
    st.session_state.page = "ativos"
if col_indices.button("Índice Mercado", use_container_width=True):
    st.session_state.page = "indice_mercado"

_mes_sel = st.session_state.mes_selecionado
_data_label = pd.to_datetime(_mes_sel + "-01").strftime("%b/%Y") if _mes_sel else "Data"
if col_data.button(_data_label, use_container_width=True):
    modal_selecionar_data()

st.divider()

# ── Páginas ───────────────────────────────────────────────────────────────────

if st.session_state.page == "home":
    st.markdown("## Plataforma de Gestão de Portfólios")
    st.markdown(
        "A XP possui uma rede de mais de 20.000 assessores financeiros, cada um responsável por 50 a 300 clientes. "
        "O segmento *middle market* — clientes com menos de R$ 1M sob gestão — é sistematicamente mal atendido, "
        "dado que o volume de clientes inviabiliza a personalização manual de relatórios e recomendações. "
        "Esta plataforma é um MVP que integra **cálculo de rendimentos**, comparação de performance com benchmarks de mercado "
        "e **geração de recomendações personalizadas** por cliente, com base no perfil de risco e na composição atual da carteira, "
        "utilizando modelos de linguagem orquestrados para produzir relatórios mensais individualizados de forma automática."
    )

    tab_solucao, tab_regras, tab_modelo, tab_infra, tab_proximos = st.tabs(
        ["Solução", "Regras de Negócio", "Modelo", "Infraestrutura", "Próximos Passos"]
    )

    # ── Solução ──────────────────────────────────────────────────────────────
    with tab_solucao:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("#### Cálculo de Rendimentos")
            st.markdown("""
Consolida automaticamente todas as posições do cliente — **ações, FIIs, fundos e renda fixa** —
e calcula o retorno mensal e acumulado de cada ativo.

Os resultados são comparados com os principais benchmarks:

| Benchmark | Descrição |
|-----------|-----------|
| CDI | Referência de renda fixa |
| IPCA | Inflação oficial |
| Selic | Taxa básica de juros |
| IBOVESPA | Referência de renda variável |

Assim é possível identificar quais ativos superam o mercado e quais estão abaixo do esperado para o perfil do cliente.
""")

        with col2:
            st.markdown("#### Recomendações por Cliente")
            st.markdown("""
Com base no **perfil de risco** (conservador, moderado ou agressivo) e na distribuição atual da carteira,
o sistema identifica oportunidades de rebalanceamento.

O fluxo de análise segue três etapas:

1. **Diagnóstico** — leitura da carteira atual e cálculo de exposição por classe de ativo
2. **Comparação** — performance vs. benchmarks no mês selecionado
3. **Recomendação** — sugestão de ativos disponíveis no catálogo alinhados ao perfil

As recomendações são geradas por uma Edge Function que combina os dados de mercado com as posições do cliente.
""")

        with col3:
            st.markdown("#### Estrutura de Dados")
            st.markdown("""
Os dados são coletados de fontes públicas e armazenados no **Supabase** com atualização mensal.

**Catálogo de ativos**
- `ativos_acoes` / `ativos_fundos` / `ativos_renda_fixa`

**Posições por cliente**
- `posicoes_acoes` / `posicoes_fundos` / `posicoes_renda_fixa`

**Série histórica**
- `precos_acoes` — preços mensais via brapi.dev
- `cotas_fundos` — cotas mensais via CVM (Informe Diário)
- `dados_mercado` — CDI, IPCA, Selic, IBOVESPA via BCB API e brapi.dev

**Clientes**
- `clientes` — perfil de risco e dados cadastrais
""")

        st.divider()

        st.markdown("#### Como usar")
        c1, c2, c3, c4 = st.columns(4)
        _card_style = "background-color:#404040;border-radius:8px;padding:1rem 1.2rem;color:#f0f0f0;"
        _cards = [
            ("<b>1. Selecione o período</b>", "Use o botão de data no menu para escolher o mês de referência da análise."),
            ("<b>2. Acesse Clientes</b>", "Escolha um cliente para ver a carteira consolidada, os rendimentos mensais e as recomendações geradas."),
            ("<b>3. Explore Ativos</b>", "Consulte o catálogo completo de ações, FIIs e fundos disponíveis para alocação."),
            ("<b>4. Acompanhe o Mercado</b>", "Veja a evolução dos benchmarks no tempo e entenda o contexto macro de cada período."),
        ]
        for col, (title, desc) in zip([c1, c2, c3, c4], _cards):
            with col:
                st.markdown(
                    f'<div style="{_card_style}">'
                    f'<p style="margin:0 0 0.5rem 0;">{title}</p>'
                    f'<p style="margin:0;font-size:0.9rem;">{desc}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Regras de Negócio ────────────────────────────────────────────────────
    with tab_regras:
        st.markdown("""
O primeiro passo na construção do MVP foi classificar todos os instrumentos financeiros em 4 classes baseadas em
comportamento macroeconômico (caixa, renda fixa, multimercado e renda variável) independente do tipo legal do
ativo. Essa classificação alimenta os perfis de risco que para cada um dos 4 perfis (conservador, moderado, arrojado,
agressivo) define as classes que o cliente pode acessar e a alocação-alvo para rebalanceamento.
""")

        with st.expander("Classes de Ativos"):
            st.markdown("""
Regra de negócio central que classifica todos os ativos da plataforma em 4 grupos comportamentais.
Cada classe agrupa ativos que respondem de forma homogênea aos mesmos indicadores macroeconômicos.

```json
{
    "classes_ativos": [
      { "id": "caixa",          "nome": "Caixa e Liquidez",        "itens": { "indexacao": ["pos_fixado_cdi", "pos_fixado_selic"], "categoria": ["RF DI", "RF Simples"] } },
      { "id": "renda_fixa",     "nome": "Renda Fixa Estruturada",  "itens": { "indexacao": ["ipca_mais", "prefixado"], "categoria": ["Multimercado RF"] } },
      { "id": "multimercado",   "nome": "Multimercado",            "itens": { "categoria": ["Multimercado", "Long Biased"] } },
      { "id": "renda_variavel", "nome": "Renda Variável",          "itens": { "categoria": ["FIA"], "tipo": ["Ação", "FII"] } }
    ]
}
```

O critério de agrupamento não é o instrumento jurídico (CDB, fundo, ação) nem o emissor. É o **comportamento frente ao cenário macroeconômico**.

- **caixa** — segue a Selic diretamente, volatilidade quase zero
- **renda_fixa** — tem duration e indexador definido na contratação, sofre marcação a mercado
- **multimercado** — gestão ativa com mandato flexível
- **renda_variavel** — retorno determinado pelo crescimento econômico (PIB) e custo de capital (Selic)
""")

        with st.expander("Perfis de Risco"):
            st.markdown("""
Regras de negócio dos 4 perfis de investidor. Define suitability e alocação alvo por classe.

```json
{
  "perfis": [
    { "id": "conservador", "suitability": ["caixa", "renda_fixa"],
      "alocacao": { "caixa": {"min":30,"alvo":60,"max":80}, "renda_fixa": {"min":20,"alvo":40,"max":70}, "multimercado": {"min":0,"alvo":0,"max":0}, "renda_variavel": {"min":0,"alvo":0,"max":0} } },
    { "id": "moderado", "suitability": ["caixa", "renda_fixa", "multimercado"],
      "alocacao": { "caixa": {"min":10,"alvo":30,"max":50}, "renda_fixa": {"min":30,"alvo":50,"max":70}, "multimercado": {"min":0,"alvo":20,"max":30}, "renda_variavel": {"min":0,"alvo":0,"max":0} } },
    { "id": "arrojado", "suitability": ["caixa", "renda_fixa", "multimercado", "renda_variavel"],
      "alocacao": { "caixa": {"min":5,"alvo":15,"max":30}, "renda_fixa": {"min":15,"alvo":35,"max":55}, "multimercado": {"min":10,"alvo":25,"max":40}, "renda_variavel": {"min":5,"alvo":25,"max":40} } },
    { "id": "agressivo", "suitability": ["caixa", "renda_fixa", "multimercado", "renda_variavel"],
      "alocacao": { "caixa": {"min":0,"alvo":5,"max":15}, "renda_fixa": {"min":0,"alvo":15,"max":30}, "multimercado": {"min":10,"alvo":30,"max":50}, "renda_variavel": {"min":25,"alvo":50,"max":70} } }
  ]
}
```

O corredor `min/max` define os limites tolerados antes de recomendar ajuste. Os alvos de cada perfil somam 100%.
""")

        with st.expander("Indicadores Macroeconômicos"):
            st.markdown("""
7 indicadores macroeconômicos usados para scoring de cenário:

| # | ID | Nome |
|---|-----|------|
| 1 | selic | Selic |
| 2 | ipca | IPCA |
| 3 | cambio | Câmbio |
| 4 | pib | PIB |
| 5 | credito | Mercado de Crédito |
| 6 | fiscal | Risco Fiscal |
| 7 | externo | Cenário Externo |

Cada indicador recebe um score de **-2 a +2** extraído por um LLM a partir da análise macro.
""")

        with st.expander("Ranking de Classes de Ativos"):
            st.markdown("""
Lógica de pontuação macro que ordena as 4 classes por atratividade dado um cenário econômico.
O score de cada classe é o produto escalar entre os scores dos indicadores e os pesos abaixo.

| Indicador | Caixa | Renda Fixa | Multimercado | Renda Variável |
|-----------|-------|------------|--------------|----------------|
| selic | +2 | -1 | -1 | -2 |
| ipca | 0 | +1 | 0 | 0 |
| cambio | 0 | 0 | +1 | 0 |
| pib | 0 | 0 | +1 | +2 |
| credito | 0 | -1 | 0 | 0 |
| fiscal | -1 | -2 | -1 | -1 |
| externo | 0 | -1 | 0 | -2 |
""")

        with st.expander("Ranking de Ativos por Classe"):
            st.markdown("""
Ordena ativos dentro de cada classe por prioridade. Ativos com histórico de preços são ordenados por **sharpe_proxy** vs benchmark.
Ativos de renda fixa pura (sem histórico) são ordenados por alinhamento com o cenário macro.

**Ativos com histórico (ações, fundos):**
```
retorno_12m  = (preco_ultimo / preco_primeiro) - 1
volatilidade = desvio_padrao_amostral(retornos_mensais)
alpha        = retorno_12m - benchmark_12m
score        = alpha / volatilidade   (sharpe_proxy)
```

**Renda fixa pura (sem histórico):**
```
pos_fixado_selic → score = selic_tendencia == "alta" ? 1 : 0
pos_fixado_cdi   → score = 0
ipca_mais        → score = ipca_12m > 5 ? 1 : 0
prefixado        → score = selic_tendencia == "baixa" ? 1 : 0
```
""")

        with st.expander("Ranking Global de Ativos"):
            st.markdown("""
Combina três regras independentes para produzir a lista final ordenada de ativos:

1. **Filtro de suitability** — remove classes não permitidas pelo perfil (hard gate regulatório)
2. **Ordem de classes** — mantém a ordem de atratividade macro
3. **Ordem interna** — preserva a ordem do sharpe_proxy dentro de cada classe

Resultado: apenas classes permitidas pelo perfil, na ordem macro, com ativos na ordem interna.
""")

        with st.expander("Recomendação de Rebalanceamento"):
            st.markdown("""
Pipeline determinístico que produz recomendações de compra e venda:

**Valorizar Posições** → calcula valor atual de cada posição e atribui classe

**Percentuais por Classe** → agrega valor por classe e calcula percentual sobre o total

**Desvios vs Alvo** → compara alocação atual com alvos do perfil
- `status = "excesso"` se acima do max → candidato a venda
- `status = "deficit"` se abaixo do min → candidato a compra
- `status = "ok"` se dentro do corredor

**Venda** — para cada classe em excesso, vende ativos com menor prioridade no ranking

**Compra** — para cada classe em deficit, compra o ativo com maior prioridade no ranking
""")

        with st.expander("Estrutura das Tabelas de Ativos (Supabase)"):
            st.markdown("""
```json
{
  "ativos_acoes": {
    "primary_key": "ticker",
    "columns": { "ticker": "text", "nome": "text", "tipo": "text (Ação/FII)", "setor": "text" }
  },
  "ativos_fundos": {
    "primary_key": "cnpj",
    "columns": { "cnpj": "text", "nome": "text", "categoria": "text (RF DI/RF Simples/Multimercado RF/Multimercado/Long Biased/FIA)", "prazo_resgate_dias": "integer" }
  },
  "ativos_renda_fixa": {
    "primary_key": "id (uuid)",
    "columns": { "nome": "text (unique)", "instrumento": "text", "indexacao": "text (pos_fixado_cdi/pos_fixado_selic/prefixado/ipca_mais)", "isento_ir": "boolean", "emissor": "text" }
  }
}
```
""")

        with st.expander("Estrutura dos Ativos no Rivet"):
            st.markdown("""
Saídas de cada entrada no grafo Rivet:

```js
ativos_renda_fixa  →  { id, nome, instrumento, indexacao }
ativos_acoes       →  { ticker, nome, tipo, setor }
ativos_fundos      →  { cnpj, nome, categoria }
precos_acoes       →  { mes, ticker, preco_fechamento }
cotas_fundos       →  { mes, cnpj, cota_fechamento }
dados_mercado      →  { mes, cdi_mensal, selic_mensal, ipca_mensal, ibovespa_retorno_mensal, usd_brl_fechamento, pib_crescimento_anual }
```

Estruturas com a propriedade `mes` têm 12 meses registrados.
""")

        with st.expander("Geração de PDF"):
            st.markdown("""
Gera um PDF profissional a partir do array de **19 partes** produzido pelo Rivet.

```
gerar_pdf(partes) → pdf_bytes
  1. Cabeçalho: nome da empresa, mês, cliente, perfil de risco
  2. Título geral do cenário
  3. Para cada indicador (7x): título + parágrafo + separador
  4. Seção de recomendação de ações
  5. Rodapé: disclaimer

salvar_pdf_supabase(sb, cliente_id, mes, job_id, pdf_bytes) → url
  1. Upload para Storage bucket relatorios-pdf
  2. Gera URL assinada (365 dias)
  3. Atualiza recomendacoes.pdf_url
```

O PDF é gerado em memória com FPDF2 (pure Python), sem arquivos temporários.
""")

        with st.expander("Estrutura do Cliente"):
            st.markdown("""
Tabela `clientes` no Supabase:
- `id` — identificador único
- `nome` — nome do cliente
- `perfil_de_risco` — conservador, moderado, arrojado ou agressivo

O perfil de risco determina quais classes de ativos o cliente pode acessar (suitability) e as faixas de alocação alvo.
""")

        with st.expander("Benchmarking"):
            st.markdown("""
Benchmarks utilizados para comparação de performance:

| Classe | Benchmark |
|--------|-----------|
| Caixa | CDI acumulado 12m |
| Renda Fixa | CDI acumulado 12m |
| Multimercado | CDI acumulado 12m |
| Renda Variável | IBOVESPA retorno 12m |

Os alfas são calculados como a diferença entre o retorno do ativo e o benchmark da classe.
""")

    # ── Modelo ───────────────────────────────────────────────────────────────
    with tab_modelo:
        st.markdown("""
#### Pipeline do Modelo

O pipeline do modelo trabalha em três grandes frentes: **extração**, **geração de cenários** e **recomendação**.

---

##### Extração

Na **extração**, o relatório macroeconômico bruto passa por um pré-processamento separando o documento por
páginas, removendo tabelas quebradas e capas, reagrupa o corpo do texto limpo e divide por seções preservando a
estrutura original. Cada seção é então subdividida em parágrafos, e cada parágrafo é classificado (tagueado) com
mais de um dos 7 indicadores macro (Selic, IPCA, câmbio, PIB, crédito fiscal e externo). Os parágrafos de mesma
tag são reagrupados, de modo que o modelo recebe todo o conteúdo disponível sobre cada indicador de forma
consolidada, em vez de fragmentos espalhados pelo documento.

Essa abordagem, chamada de **Decomposição Semântica Orientada a Domínio**, reduz alucinação porque o LLM analisa trechos reais e focados, não o
documento inteiro de forma genérica.

---

##### Geração de Cenários

Na **geração de cenários**, cada indicador alimenta dois prompts: um para cenário positivo e outro para negativo. Dentro de cada prompt, o modelo recebe as classes de ativos disponíveis e descreve como aquele cenário
impacta cada uma das classes ignorando as que não são sensíveis àquele indicador. Resultando em 7 parágrafos contextualizados, cada um explicando o cenário do indicador e seu efeito direto sobre os ativos.

Indicadores independentes são processados em paralelo (fan-out), e os resultados convergem ao final (fan-in). A arquitetura
**Scenario-Conditioned Generation com Cross-Entity Reasoning** garante que cada afirmação está ancorada
em evidência macroeconômica.

---

##### Recomendação

Na etapa de **recomendação**, o mesmo padrão é aplicado: o modelo recebe o cenário consolidado, os desvios de
alocação calculados pelas regras de negócio e os ativos ranqueados, e gera um parágrafo final que não apenas
indica o que comprar e vender, mas contextualiza cada sugestão com o cenário que a justifica.

O output completo — 19 campos estruturados (mês, nome, perfil, título, 7 indicadores com título e parágrafo cada, e parágrafo de
recomendação) — alimenta a geração programática do PDF.
""")

    # ── Infraestrutura ───────────────────────────────────────────────────────
    with tab_infra:
        st.markdown("#### Servidores")
        st.markdown("""
| Servidor | Tecnologia | Onde roda |
|----------|-----------|-----------|
| **Streamlit** | Python | Streamlit Cloud |
| **Supabase DB** | PostgreSQL | Supabase Cloud |
| **Edge Function: gerar-recomendacao** | Deno/TypeScript | Supabase Cloud |
| **Edge Function: ingest** | Deno/TypeScript | Supabase Cloud |
| **Edge Function: extract-pdf** | Deno/TypeScript | Supabase Cloud |
| **Railway** | Node.js (`server.mjs`) | Railway Cloud |
| **OpenAI** | API externa | OpenAI Cloud |
| **Anthropic** | API externa | Anthropic Cloud |
""")

        st.markdown("#### Diagrama de Produção")
        st.code("""
┌──────────────────────────────────────────────────────────────────┐
│                       STREAMLIT CLOUD                            │
│                                                                  │
│  1. load_table()              ── HTTPS REST GET ──────────────►  │
│  2. gerar_recomendacao()      ── HTTPS POST ───────────────────► │
│  3. polling recomendacoes     ── HTTPS GET (a cada 3s) ────────► │
│  4. upload PDF                ── HTTPS POST multipart ─────────► │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                        SUPABASE CLOUD                            │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  PostgreSQL DB                                         │     │
│  │  clientes, ativos_*, posicoes_*, recomendacoes         │     │
│  │  dados_mercado, relatorios, precos_*, cotas_*          │     │
│  │  DATABASE WEBHOOK → dispara extract-pdf                │     │
│  └────────────────────────────────────────────────────────┘     │
│  ┌──────────────────┐  ┌─────────────────┐  ┌─────────────┐   │
│  │ gerar-recomendac │  │ ingest          │  │ extract-pdf │   │
│  │ {cliente_id,mes} │  │ PDF (form-data) │  │ webhook/dir │   │
│  └──────────────────┘  └─────────────────┘  └─────────────┘   │
└──────────┬─────────────────────────────────────────────────────┘
           │ HTTPS POST
           ▼
┌──────────────────────────────────────────────────────────────────┐
│                        RAILWAY CLOUD — server.mjs                │
│  runGraph("gerar_recomendacao")                                  │
│    → 11 HTTP Calls para Supabase REST API                        │
│    → Chat nodes para OpenAI API                                  │
│    → PATCH recomendacoes SET status="done"                       │
└──────────┬────────────────────────────────────┬─────────────────┘
           ▼                                    ▼
    SUPABASE (PostgREST)                   OPENAI API
""", language=None)

        st.markdown("#### Todas as Conexões")
        st.markdown("""
| # | De | Para | Protocolo | Trigger |
|---|----|----|-----------|---------|
| 1 | Streamlit | Supabase PostgREST | HTTPS GET | leitura de tabelas |
| 2 | Streamlit | Edge Fn `gerar-recomendacao` | HTTPS POST | botão "Gerar recomendação" |
| 3 | Streamlit | Supabase `recomendacoes` | HTTPS GET | polling a cada 3s |
| 4 | Streamlit | Edge Fn `ingest` | HTTPS POST | upload de PDF |
| 5 | Edge Fn `gerar-recomendacao` | Supabase DB | interno | INSERT job |
| 6 | Edge Fn `gerar-recomendacao` | Railway | HTTPS POST | após INSERT |
| 7 | Edge Fn `ingest` | Storage | interno | upload PDF |
| 8 | Edge Fn `ingest` | Supabase DB | interno | INSERT documents |
| 9 | Database Webhook | Edge Fn `extract-pdf` | HTTPS POST | INSERT documents |
| 10 | Edge Fn `extract-pdf` | Anthropic API | HTTPS POST | PDF → Claude |
| 11 | Railway | Supabase PostgREST | HTTPS GET | 11 HTTP Calls |
| 12 | Railway | OpenAI API | HTTPS POST | scoring + narrativa |
| 13 | Railway | Supabase `recomendacoes` | HTTPS PATCH | salva resultado |
""")

        st.markdown("#### Fluxo de Recomendação")
        st.code("""
Streamlit          gerar-recomendacao     Railway           Supabase DB
    │                      │                  │                  │
    │── POST {cliente,mes} ►│                  │                  │
    │                      │── INSERT job ───────────────────────►│
    │                      │◄──────────────── job_id ────────────│
    │                      │── POST {job_id} ►│                  │
    │◄── { job_id } ───────│                  │                  │
    │                      │                  │── GET dados ─────►│
    │                      │                  │   (11 calls)      │
    │                      │                  │── POST OpenAI     │
    │                      │                  │── PATCH done ────►│
    │── GET recomendacoes (polling 3s) ──────────────────────────►│
    │◄── status: done, resultado ─────────────────────────────────│
""", language=None)

    # ── Próximos Passos ──────────────────────────────────────────────────────
    with tab_proximos:
        st.markdown("""
#### Próximos Passos

A prioridade imediata é ampliar a cobertura de dados integrando fontes adicionais como relatórios da **BTG
Pactual Research** e dados da **B3**, permitindo triangular cenários macroeconômicos com múltiplas fontes e reduzir
a dependência de uma única API.

Com mais dados disponíveis, o próximo passo é incorporar modelos mais
sofisticados como **time series forecasting** para projeções de curto prazo na carta, **clustering** para segmentar clientes
por comportamento real de investimento (além do perfil declarado) e **classificação automatizada de sinais de compra
e venda**.

A matriz de pesos e os corredores de rebalanceamento devem ser validados com técnicos especializados para
garantir aderência regulatória e suitability.

Na camada de escala, a geração precisa evoluir para uma **fila assíncrona**,
permitindo processar múltiplos clientes simultaneamente.

Por fim, a introdução de um **feedback loop** onde
o assessor revisa e edita a carta antes de enviar alimentaria o sistema com correções reais, viabilizando melhoria
contínua da qualidade do output.
""")

elif st.session_state.page == "clientes":
    st.subheader("Clientes")

    # ── Carregar todos os dados uma vez ───────────────────────────────────────
    df_clientes      = load_table("clientes")
    df_pos_acoes     = load_table("posicoes_acoes")
    df_pos_fundos    = load_table("posicoes_fundos")
    df_pos_rf        = load_table("posicoes_renda_fixa")
    df_ativos_acoes  = load_table("ativos_acoes")
    df_ativos_fundos = load_table("ativos_fundos")
    df_ativos_rf     = load_table("ativos_renda_fixa")
    df_precos        = load_table("precos_acoes")
    df_cotas         = load_table("cotas_fundos")
    df_mercado       = load_table("dados_mercado")

    nomes = df_clientes["nome"].tolist() if not df_clientes.empty else []
    ids   = df_clientes["id"].tolist()   if not df_clientes.empty else []

    # Mês de referência — usa seleção do usuário ou último disponível
    meses_ord = sorted(df_mercado["mes"].unique()) if not df_mercado.empty else []
    mes_sel   = st.session_state.mes_selecionado
    if mes_sel and mes_sel in meses_ord:
        mes_atual = mes_sel
        idx_sel   = meses_ord.index(mes_sel)
        mes_ant   = meses_ord[idx_sel - 1] if idx_sel > 0 else None
    else:
        mes_atual = meses_ord[-1] if len(meses_ord) >= 1 else None
        mes_ant   = meses_ord[-2] if len(meses_ord) >= 2 else None
    row_merc  = df_mercado[df_mercado["mes"] == mes_atual].iloc[0] if mes_atual else None

    tabs_clientes = st.tabs(nomes + ["＋"])
    *tabs_pessoas, tab_add = tabs_clientes

    for tab, nome_cliente, cliente_id in zip(tabs_pessoas, nomes, ids):
        with tab:
            key = f"subpage_{cliente_id}"
            if key not in st.session_state:
                st.session_state[key] = "carteira"

            col_b0, col_b1, col_b2, _ = st.columns(layouts.sub_nav)
            if col_b0.button("Dados Pessoais", key=f"btn_dados_{cliente_id}", use_container_width=True,
                             type="primary" if st.session_state[key] == "dados" else "secondary"):
                st.session_state[key] = "dados"
            if col_b1.button("Carteira", key=f"btn_carteira_{cliente_id}", use_container_width=True,
                             type="primary" if st.session_state[key] == "carteira" else "secondary"):
                st.session_state[key] = "carteira"
            if col_b2.button("Resultados", key=f"btn_resultados_{cliente_id}", use_container_width=True,
                             type="primary" if st.session_state[key] == "resultados" else "secondary"):
                st.session_state[key] = "resultados"

            st.divider()

            # Posições filtradas por cliente
            acoes_c  = df_pos_acoes[df_pos_acoes["cliente_id"]   == cliente_id] if not df_pos_acoes.empty  else pd.DataFrame()
            fundos_c = df_pos_fundos[df_pos_fundos["cliente_id"] == cliente_id] if not df_pos_fundos.empty else pd.DataFrame()
            rf_c     = df_pos_rf[df_pos_rf["cliente_id"]         == cliente_id] if not df_pos_rf.empty     else pd.DataFrame()

            # ── Dados Pessoais ────────────────────────────────────────────────
            if st.session_state[key] == "dados":
                row_cli = df_clientes[df_clientes["id"] == cliente_id].iloc[0]
                perfil_texto = row_cli.get("perfil_de_risco", "") or ""
                nome_cli = row_cli.get("nome", "—")

                if perfil_texto:
                    linhas = perfil_texto.splitlines()
                    classificacao = next(
                        (l.replace("Classificação do Perfil de Investimento:", "").strip()
                         for l in linhas if "Classificação" in l), "—"
                    )
                    _badge = PROFILE_BADGES.get(classificacao, PROFILE_BADGE_FALLBACK)
                    cor_badge, cor_bg = _badge.fg, _badge.bg

                    # ── Cabeçalho ──────────────────────────────────────────────
                    _, card_col, _ = st.columns(layouts.card_center)
                    with card_col:
                        st.markdown(
                            components.client_card(nome_cli, classificacao, cor_badge),
                            unsafe_allow_html=True,
                        )

                    st.write("")

                    # ── Corpo do perfil ────────────────────────────────────────
                    # Parseia seções numeradas e sub-itens
                    secoes = []   # lista de (titulo, [(sub_titulo, texto)])
                    sec_titulo = None; sub_titulo = None; buf = []

                    for linha in linhas[2:]:
                        l = linha.strip()
                        if not l:
                            if buf and sub_titulo is not None:
                                if secoes: secoes[-1][1].append((sub_titulo, " ".join(buf)))
                                sub_titulo = None; buf = []
                            elif buf and sec_titulo:
                                if secoes: secoes[-1][1].append((None, " ".join(buf)))
                                buf = []
                            continue
                        if l[0].isdigit() and l[1] == ".":
                            if buf and secoes:
                                secoes[-1][1].append((sub_titulo, " ".join(buf)))
                                buf = []; sub_titulo = None
                            sec_titulo = l[2:].strip() if len(l) > 2 else l
                            secoes.append((sec_titulo, []))
                        elif len(l) >= 2 and l[0].isalpha() and l[1] == "." and l[0].islower():
                            if buf and secoes:
                                secoes[-1][1].append((sub_titulo, " ".join(buf)))
                                buf = []
                            sub_titulo = l[2:].strip() if len(l) > 2 else l
                        else:
                            buf.append(l)
                    if buf and secoes:
                        secoes[-1][1].append((sub_titulo, " ".join(buf)))

                    _, body_col, _ = st.columns(layouts.card_center)
                    with body_col:
                        for sec_t, items in secoes:
                            items_html = ""
                            for sub_t, texto in items:
                                if sub_t:
                                    items_html += components.profile_item(sub_t, texto)
                                else:
                                    items_html += f"""
  <p style="font-size:{typography.size_sm};color:{colors.text_muted};
  line-height:{typography.lh_loose};margin:0;">{texto}</p>"""
                            st.markdown(
                                components.profile_section(sec_t, cor_badge, items_html),
                                unsafe_allow_html=True,
                            )
                else:
                    st.info("Perfil de risco não cadastrado para este cliente.")

            # ── Carteira ──────────────────────────────────────────────────────
            elif st.session_state[key] == "carteira":
                # Totais por categoria
                total_acoes_c = 0.0
                for _, p in acoes_c.iterrows():
                    pa_r = df_precos[(df_precos["ticker"] == p["ticker"]) & (df_precos["mes"] == mes_atual)] if mes_atual else pd.DataFrame()
                    total_acoes_c += float(pa_r.iloc[0]["preco_fechamento"]) * float(p["quantidade"]) if not pa_r.empty else float(p["quantidade"]) * float(p["preco_medio_compra"])

                total_fundos_c = 0.0
                for _, p in fundos_c.iterrows():
                    ca_r = df_cotas[(df_cotas["cnpj"] == p["cnpj"]) & (df_cotas["mes"] == mes_atual)] if mes_atual else pd.DataFrame()
                    total_fundos_c += float(ca_r.iloc[0]["cota_fechamento"]) * float(p["numero_cotas"]) if not ca_r.empty else float(p["valor_aplicado"])

                total_rf_c = rf_c["valor_aplicado"].astype(float).sum() if not rf_c.empty else 0.0
                total_g = total_acoes_c + total_fundos_c + total_rf_c or 1.0

                def _pct(v): return v / total_g * 100

                COLS_A = [0.9, 1.8, 0.8, 1.1, 1.1, 1.1, 1.1, 0.8, 1.1, 0.5]
                HDRS_A = ["Ticker", "Nome", "Qtd", "P. Médio", "V. Invest.", "P. Atual", "V. Atual", "Var %", "Data compra", ""]
                COLS_F = [2.2, 1.8, 0.9, 1.1, 1.1, 1.1, 0.8, 1.1, 0.5]
                HDRS_F = ["Fundo", "CNPJ", "Cotas", "V. Aplicado", "Cota Atual", "V. Atual", "Var %", "Data invest.", ""]
                COLS_R = [2.2, 1.3, 0.8, 0.9, 1.1, 1.1, 1.1, 0.5]
                HDRS_R = ["Instrumento", "Indexação", "Taxa", "Unidade", "V. Aplicado", "Início", "Vencimento", ""]

                def _sec_header(label, n_pos, total, pct, tkey):
                    if tkey not in st.session_state:
                        st.session_state[tkey] = False
                    _ha, _hb, _hc = st.columns(layouts.section_header)
                    with _ha:
                        if st.button("▼" if st.session_state[tkey] else "▶", key=f"tog_{tkey}"):
                            st.session_state[tkey] = not st.session_state[tkey]; st.rerun()
                    _hb.markdown(
                        components.section_label(label, n_pos, total, pct),
                        unsafe_allow_html=True,
                    )
                    _hc.markdown(
                        components.section_total(total, pct),
                        unsafe_allow_html=True,
                    )
                    st.divider()
                    return st.session_state[tkey]

                # ── Ações ──────────────────────────────────────────────────────
                n_a = len(acoes_c)
                if _sec_header("Ações", n_a, total_acoes_c, _pct(total_acoes_c), f"exp_a_{cliente_id}"):
                    hc = st.columns(COLS_A)
                    for c, h in zip(hc, HDRS_A):
                        c.markdown(f"**{h}**")
                    st.divider()

                    for _, p in acoes_c.iterrows():
                        qtd = float(p["quantidade"]); pm = float(p["preco_medio_compra"]); vi = qtd * pm
                        nome_at = "—"
                        if not df_ativos_acoes.empty:
                            m = df_ativos_acoes[df_ativos_acoes["ticker"] == p["ticker"]]
                            if not m.empty: nome_at = m.iloc[0]["nome"]
                        pa_r = df_precos[(df_precos["ticker"] == p["ticker"]) & (df_precos["mes"] == mes_atual)] if mes_atual else pd.DataFrame()
                        pa  = float(pa_r.iloc[0]["preco_fechamento"]) if not pa_r.empty else None
                        va  = pa * qtd if pa else None
                        var = (pa - pm) / pm * 100 if pa else None

                        rc = st.columns(COLS_A)
                        rc[0].write(p["ticker"])
                        rc[1].write(nome_at)
                        rc[2].write(f"{qtd:,.0f}")
                        rc[3].write(f"R$ {pm:,.2f}")
                        rc[4].markdown(f"**R$ {vi:,.0f}**")
                        rc[5].write(f"R$ {pa:,.2f}" if pa else "—")
                        rc[6].write(f"R$ {va:,.0f}" if va else "—")
                        if var is not None:
                            sg = "+" if var >= 0 else ""; cor = "green" if var >= 0 else "red"
                            rc[7].markdown(f":{cor}[**{sg}{var:.1f}%**]")
                        else:
                            rc[7].write("—")
                        rc[8].write(str(p.get("data_compra", "—")))
                        with rc[9]:
                            with st.popover("🗑"):
                                st.caption(f"Remover **{p['ticker']}**?")
                                if st.button("Confirmar", key=f"del_a_{p['id']}", type="primary"):
                                    get_supabase().table("posicoes_acoes").delete().eq("id", str(p["id"])).execute()
                                    st.cache_data.clear(); st.rerun()

                    st.divider()
                    add_a = f"add_acao_{cliente_id}"
                    if not st.session_state.get(add_a):
                        if st.button("＋ Adicionar ação", key=f"btn_add_a_{cliente_id}"):
                            st.session_state[add_a] = True; st.rerun()
                    else:
                        if df_ativos_acoes.empty:
                            st.warning("Nenhuma ação cadastrada em Ativos Disponíveis.")
                        else:
                            opcoes_a = {row["ticker"]: row.get("nome", row["ticker"])
                                        for _, row in df_ativos_acoes.iterrows()}
                            ac = st.columns(COLS_A)
                            with ac[0]:
                                tk_sel = st.selectbox("Ticker", options=list(opcoes_a.keys()),
                                    key=f"na_tk_{cliente_id}", label_visibility="collapsed")
                            ac[1].markdown(opcoes_a.get(tk_sel, "—"))
                            with ac[2]:
                                qtd_str = st.text_input("Qtd", key=f"na_qtd_{cliente_id}",
                                    label_visibility="collapsed", placeholder="Qtd")
                            try:
                                qtd_v = float(qtd_str.replace(",", ".")) if qtd_str.strip() else 0.0
                            except ValueError:
                                qtd_v = 0.0
                            pa_r = df_precos[(df_precos["ticker"] == tk_sel) & (df_precos["mes"] == mes_atual)] if mes_atual and tk_sel else pd.DataFrame()
                            preco_at = float(pa_r.iloc[0]["preco_fechamento"]) if not pa_r.empty else None
                            total_ac = preco_at * qtd_v if (preco_at and qtd_v > 0) else None
                            ac[3].markdown(f"R$ {preco_at:,.2f}" if preco_at else "—")
                            ac[4].markdown(f"**R$ {total_ac:,.0f}**" if total_ac else "—")
                            all_a = bool(tk_sel) and qtd_v > 0 and preco_at is not None
                            with ac[9]:
                                if st.button("Salvar", key=f"save_a_{cliente_id}", type="primary", disabled=not all_a, use_container_width=True):
                                    data_compra = (mes_atual + "-01") if mes_atual else pd.Timestamp.today().strftime("%Y-%m-%d")
                                    get_supabase().table("posicoes_acoes").insert({
                                        "cliente_id": cliente_id, "ticker": tk_sel,
                                        "quantidade": qtd_v, "preco_medio_compra": preco_at,
                                        "data_compra": data_compra,
                                    }).execute()
                                    st.session_state[add_a] = False; st.cache_data.clear(); st.rerun()
                        if st.button("✕ Cancelar", key=f"cancel_a_{cliente_id}"):
                            st.session_state[add_a] = False; st.rerun()

                # ── Fundos ─────────────────────────────────────────────────────
                n_f = len(fundos_c)
                if _sec_header("Fundos", n_f, total_fundos_c, _pct(total_fundos_c), f"exp_f_{cliente_id}"):
                    hc = st.columns(COLS_F)
                    for c, h in zip(hc, HDRS_F):
                        c.markdown(f"**{h}**")
                    st.divider()

                    for _, p in fundos_c.iterrows():
                        nome_f = "—"
                        if not df_ativos_fundos.empty:
                            m = df_ativos_fundos[df_ativos_fundos["cnpj"] == p["cnpj"]]
                            if not m.empty: nome_f = m.iloc[0]["nome"]
                        ca_r  = df_cotas[(df_cotas["cnpj"] == p["cnpj"]) & (df_cotas["mes"] == mes_atual)] if mes_atual else pd.DataFrame()
                        ca    = float(ca_r.iloc[0]["cota_fechamento"]) if not ca_r.empty else None
                        cotas = float(p["numero_cotas"]); vaplic = float(p["valor_aplicado"])
                        va    = ca * cotas if ca else None
                        var   = (va - vaplic) / vaplic * 100 if va else None

                        rc = st.columns(COLS_F)
                        rc[0].write(nome_f)
                        rc[1].write(p["cnpj"])
                        rc[2].write(f"{cotas:,.0f}")
                        rc[3].markdown(f"**R$ {vaplic:,.0f}**")
                        rc[4].write(f"R$ {ca:,.4f}" if ca else "—")
                        rc[5].write(f"R$ {va:,.0f}" if va else "—")
                        if var is not None:
                            sg = "+" if var >= 0 else ""; cor = "green" if var >= 0 else "red"
                            rc[6].markdown(f":{cor}[**{sg}{var:.1f}%**]")
                        else:
                            rc[6].write("—")
                        rc[7].write(str(p.get("data_investimento", "—")))
                        with rc[8]:
                            with st.popover("🗑"):
                                st.caption(f"Remover **{nome_f}**?")
                                if st.button("Confirmar", key=f"del_f_{p['id']}", type="primary"):
                                    get_supabase().table("posicoes_fundos").delete().eq("id", str(p["id"])).execute()
                                    st.cache_data.clear(); st.rerun()

                    st.divider()
                    add_f = f"add_fundo_{cliente_id}"
                    if not st.session_state.get(add_f):
                        if st.button("＋ Adicionar fundo", key=f"btn_add_f_{cliente_id}"):
                            st.session_state[add_f] = True; st.rerun()
                    else:
                        if df_ativos_fundos.empty:
                            st.warning("Nenhum fundo cadastrado em Ativos Disponíveis.")
                        else:
                            opcoes_f = {row["cnpj"]: row["nome"] for _, row in df_ativos_fundos.iterrows()}
                            fc = st.columns(COLS_F)
                            with fc[0]:
                                cnpj_sel = st.selectbox("Fundo", options=list(opcoes_f.keys()),
                                    format_func=lambda x: opcoes_f[x],
                                    key=f"nf_cnpj_{cliente_id}", label_visibility="collapsed")
                            fc[1].markdown(cnpj_sel or "—")
                            with fc[2]:
                                cotas_str = st.text_input("Cotas", key=f"nf_cotas_{cliente_id}",
                                    label_visibility="collapsed", placeholder="Nº cotas")
                            try:
                                cotas_v = float(cotas_str.replace(",", ".")) if cotas_str.strip() else 0.0
                            except ValueError:
                                cotas_v = 0.0
                            ca_r = df_cotas[(df_cotas["cnpj"] == cnpj_sel) & (df_cotas["mes"] == mes_atual)] if mes_atual and cnpj_sel else pd.DataFrame()
                            cota_at = float(ca_r.iloc[0]["cota_fechamento"]) if not ca_r.empty else None
                            vaplic_calc = cotas_v * cota_at if (cota_at and cotas_v > 0) else None
                            fc[3].markdown(f"**R$ {vaplic_calc:,.0f}**" if vaplic_calc else "—")
                            fc[4].markdown(f"R$ {cota_at:,.4f}" if cota_at else "—")
                            all_f = cotas_v > 0 and cota_at is not None
                            with fc[8]:
                                if st.button("Salvar", key=f"save_f_{cliente_id}", type="primary", disabled=not all_f, use_container_width=True):
                                    data_inv = (mes_atual + "-01") if mes_atual else pd.Timestamp.today().strftime("%Y-%m-%d")
                                    get_supabase().table("posicoes_fundos").insert({
                                        "cliente_id": cliente_id, "cnpj": cnpj_sel,
                                        "numero_cotas": cotas_v, "valor_aplicado": vaplic_calc,
                                        "data_investimento": data_inv,
                                    }).execute()
                                    st.session_state[add_f] = False; st.cache_data.clear(); st.rerun()
                        if st.button("✕ Cancelar", key=f"cancel_f_{cliente_id}"):
                            st.session_state[add_f] = False; st.rerun()

                # ── Renda Fixa ─────────────────────────────────────────────────
                n_r = len(rf_c)
                if _sec_header("Renda Fixa", n_r, total_rf_c, _pct(total_rf_c), f"exp_r_{cliente_id}"):
                    hc = st.columns(COLS_R)
                    for c, h in zip(hc, HDRS_R):
                        c.markdown(f"**{h}**")
                    st.divider()

                    for _, p in rf_c.iterrows():
                        nome_rf = "—"; idx_rf = "—"
                        if not df_ativos_rf.empty:
                            m = df_ativos_rf[df_ativos_rf["id"] == p["ativo_id"]]
                            if not m.empty:
                                nome_rf = m.iloc[0]["nome"]
                                idx_rf  = m.iloc[0].get("indexacao", "—")

                        rc = st.columns(COLS_R)
                        rc[0].write(nome_rf)
                        rc[1].write(idx_rf)
                        rc[2].write(str(p.get("taxa_contratada", "—")))
                        rc[3].write(str(p.get("unidade_taxa", "—")))
                        rc[4].markdown(f"**R$ {float(p['valor_aplicado']):,.0f}**")
                        rc[5].write(str(p.get("data_inicio", "—")))
                        rc[6].write(str(p.get("data_vencimento", "—")))
                        with rc[7]:
                            with st.popover("🗑"):
                                st.caption(f"Remover **{nome_rf}**?")
                                if st.button("Confirmar", key=f"del_r_{p['id']}", type="primary"):
                                    get_supabase().table("posicoes_renda_fixa").delete().eq("id", str(p["id"])).execute()
                                    st.cache_data.clear(); st.rerun()

                    st.divider()
                    add_r = f"add_rf_{cliente_id}"
                    if not st.session_state.get(add_r):
                        if st.button("＋ Adicionar renda fixa", key=f"btn_add_r_{cliente_id}"):
                            st.session_state[add_r] = True; st.rerun()
                    else:
                        if df_ativos_rf.empty:
                            st.warning("Nenhum instrumento cadastrado em Ativos Disponíveis.")
                        else:
                            opcoes_r = {row["id"]: row["nome"] for _, row in df_ativos_rf.iterrows()}
                            rc2 = st.columns(COLS_R)
                            with rc2[0]:
                                ativo_sel = st.selectbox("Instrumento", options=list(opcoes_r.keys()),
                                    format_func=lambda x: opcoes_r[x],
                                    key=f"nr_ativo_{cliente_id}", label_visibility="collapsed")
                            with rc2[2]:
                                taxa_str = st.text_input("Taxa", key=f"nr_taxa_{cliente_id}",
                                    label_visibility="collapsed", placeholder="ex: 110")
                            try:
                                taxa_v = float(taxa_str.replace(",", ".")) if taxa_str.strip() else 0.0
                            except ValueError:
                                taxa_v = 0.0
                            with rc2[3]: unid_v = st.selectbox("Unidade", ["% CDI", "% Selic", "% a.a."], key=f"nr_unid_{cliente_id}", label_visibility="collapsed")
                            with rc2[4]:
                                vaplic_str = st.text_input("V.Aplic", key=f"nr_vaplic_{cliente_id}",
                                    label_visibility="collapsed", placeholder="ex: 10000")
                            try:
                                vaplic_r = float(vaplic_str.replace(",", ".")) if vaplic_str.strip() else 0.0
                            except ValueError:
                                vaplic_r = 0.0
                            with rc2[5]: dt_ini_v  = st.date_input("Início", key=f"nr_ini_{cliente_id}",  label_visibility="collapsed")
                            with rc2[6]: dt_venc_v = st.date_input("Venc.",  key=f"nr_venc_{cliente_id}", label_visibility="collapsed")
                            all_r = taxa_v > 0 and vaplic_r > 0
                            with rc2[7]:
                                if st.button("Salvar", key=f"save_r_{cliente_id}", type="primary", disabled=not all_r):
                                    get_supabase().table("posicoes_renda_fixa").insert({
                                        "cliente_id": cliente_id, "ativo_id": ativo_sel,
                                        "taxa_contratada": taxa_v, "unidade_taxa": unid_v,
                                        "valor_aplicado": vaplic_r,
                                        "data_inicio": str(dt_ini_v),
                                        "data_vencimento": str(dt_venc_v),
                                    }).execute()
                                    st.session_state[add_r] = False; st.cache_data.clear(); st.rerun()
                        if st.button("✕ Cancelar", key=f"cancel_r_{cliente_id}"):
                            st.session_state[add_r] = False; st.rerun()

            # ── Resultados ────────────────────────────────────────────────────
            elif st.session_state[key] == "resultados":
                if not mes_atual or not mes_ant:
                    st.info("Selecione um mês com pelo menos dois períodos disponíveis.")
                else:
                    mes_label = pd.to_datetime(mes_atual + "-01").strftime("%b/%Y")
                    st.caption(f"Mês de referência: **{mes_label}**")

                    mercado = row_merc.to_dict() if row_merc is not None else {}

                    # ── Módulos 1, 2, 3 — Retorno individual por ativo ────────
                    linhas_acoes  = calcular_retorno_acoes(acoes_c, df_precos, df_ativos_acoes, mes_atual, mes_ant)
                    linhas_fundos = calcular_retorno_fundos(fundos_c, df_cotas, df_ativos_fundos, mes_atual, mes_ant)
                    linhas_rf     = calcular_retorno_rf(rf_c, df_ativos_rf, mercado)

                    todas_linhas = linhas_acoes + linhas_fundos + linhas_rf

                    # ── Módulo 4 — Retorno total ponderado ────────────────────
                    portfolio = calcular_retorno_portfolio(todas_linhas)

                    # ── Módulo 5 — Alfas vs. benchmarks ──────────────────────
                    alfas = calcular_alfas(portfolio["retorno_portfolio"], linhas_acoes, mercado)

                    # ── Métricas de topo ──────────────────────────────────────
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric(
                        "Retorno do portfólio",
                        f"{portfolio['retorno_portfolio']:.2f}%",
                        help="Rentabilidade total ponderada de todos os ativos do cliente no mês",
                    )
                    m2.metric(
                        "Variação no mês",
                        f"R$ {portfolio['variacao_total_rs']:+,.2f}",
                        help="Ganho ou perda em reais no mês, considerando todos os ativos",
                    )
                    m3.metric(
                        "Valor total",
                        f"R$ {portfolio['valor_total']:,.2f}",
                        help="Soma do valor atual de todas as posições do cliente",
                    )
                    m4.metric(
                        "Alfa vs CDI",
                        f"{alfas['alfa_cdi']:+.2f} p.p.",
                        help="Diferença em pontos percentuais entre o retorno do portfólio e o CDI do mês. Positivo = superou o CDI",
                    )

                    st.divider()

                    # ── Tabela de ativos ──────────────────────────────────────
                    st.subheader("Ativos")
                    if todas_linhas:
                        df_ret = pd.DataFrame([{
                            "Ativo":            l["ativo"],
                            "Tipo":             l["tipo"],
                            "Retorno mês (%)":  l["retorno_mes"],
                            "Peso (%)":         l["peso"] * 100 if l.get("peso") is not None else None,
                            "Contribuição (%)": l["contribuicao"],
                            "Variação R$":      l["variacao_rs"],
                            "Valor atual":      l["valor_posicao"],
                        } for l in todas_linhas])

                        st.dataframe(
                            df_ret,
                            use_container_width=True,
                            hide_index=True,
                            height=(len(df_ret) + 1) * 35 + 3,
                            column_config={
                                "Retorno mês (%)":  st.column_config.NumberColumn(format="%.2f%%", help="Variação percentual do ativo no mês"),
                                "Peso (%)":         st.column_config.NumberColumn(format="%.2f%%", help="Participação do ativo no valor total do portfólio"),
                                "Contribuição (%)": st.column_config.NumberColumn(format="%.3f%%", help="Impacto do ativo no retorno total do portfólio (retorno × peso)"),
                                "Variação R$":      st.column_config.NumberColumn(format="R$ %,.2f", help="Ganho ou perda em reais do ativo no mês"),
                                "Valor atual":      st.column_config.NumberColumn(format="R$ %,.2f", help="Valor de mercado atual da posição"),
                            },
                        )
                    else:
                        st.info("Nenhuma posição cadastrada para este cliente.")

                    # ── Destaques do mês ──────────────────────────────────────
                    contributors = portfolio["top_contributors"]
                    detractors   = portfolio["top_detractors"]

                    if contributors or detractors:
                        st.divider()
                        st.subheader("Destaques do mês", help="Ativos que mais contribuíram (positiva ou negativamente) para o retorno do portfólio. O valor exibido é a contribuição: retorno do ativo × peso no portfólio")
                        _all_highlights = []
                        for item in contributors:
                            _all_highlights.append(("pos", item))
                        for item in detractors:
                            _all_highlights.append(("neg", item))

                        _h_cols = st.columns(len(_all_highlights)) if _all_highlights else []
                        for col, (tipo, item) in zip(_h_cols, _all_highlights):
                            with col:
                                st.metric(
                                    item["ativo"],
                                    f"{item['contribuicao']:+.3f}%",
                                    f"Retorno: {item['retorno_mes']:+.2f}%",
                                    delta_color="normal" if tipo == "pos" else "inverse",
                                )

                    # ── Performance vs. benchmarks ────────────────────────────
                    st.divider()
                    st.markdown(
                        '<h3 style="text-align:center;">Performance vs. benchmarks</h3>',
                        unsafe_allow_html=True,
                    )

                    _, col_bench, _, col_alfa, _ = st.columns(5)

                    with col_bench:
                        st.markdown(
                            '<p style="text-align:center;font-weight:600;">Benchmarks do mês</p>',
                            unsafe_allow_html=True,
                        )
                        if mercado:
                            st.dataframe(
                                pd.DataFrame({
                                    "Indicador": ["CDI", "IPCA", "Selic", "IBOVESPA"],
                                    "Retorno (%)": [
                                        alfas["cdi"],
                                        alfas["ipca"],
                                        alfas["selic"],
                                        alfas["ibov"],
                                    ],
                                }),
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "Indicador": st.column_config.TextColumn(
                                        help="CDI = referência para renda fixa · IPCA = inflação oficial · Selic = taxa básica de juros · IBOVESPA = principal índice de ações do Brasil",
                                    ),
                                    "Retorno (%)": st.column_config.NumberColumn(format="%.2f%%", help="Retorno do indicador no mês de referência"),
                                },
                            )
                        else:
                            st.info("Sem dados de benchmarks.")

                    with col_alfa:
                        st.markdown(
                            '<p style="text-align:center;font-weight:600;">Alfas do portfólio</p>',
                            unsafe_allow_html=True,
                        )
                        linhas_alfa = [
                            {"Indicador": "Alfa vs CDI",        "Valor (p.p.)": alfas["alfa_cdi"]},
                            {"Indicador": "Retorno real (IPCA)", "Valor (p.p.)": alfas["retorno_real_vs_ipca"]},
                        ]
                        if alfas["alfa_acoes_vs_ibovespa"] is not None:
                            linhas_alfa.append({
                                "Indicador": "Ações vs IBOVESPA",
                                "Valor (p.p.)": alfas["alfa_acoes_vs_ibovespa"],
                            })
                        st.dataframe(
                            pd.DataFrame(linhas_alfa),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Indicador": st.column_config.TextColumn(
                                    help="Alfa vs CDI = retorno acima/abaixo do CDI · Retorno real (IPCA) = ganho descontada a inflação · Ações vs IBOVESPA = retorno da classe de ações comparado ao índice",
                                ),
                                "Valor (p.p.)": st.column_config.NumberColumn(
                                    format="%+.2f p.p.",
                                    help="Pontos percentuais: diferença absoluta entre duas porcentagens. Ex.: 12% − 10% = 2 p.p.",
                                ),
                            },
                        )

                    # ── Recomendação — Rivet ─────────────────────────────────
                    st.divider()
                    st.subheader("Recomendação")

                    rec_key = f"recomendacao_{cliente_id}_{mes_atual}"

                    pdf_key = f"pdf_{cliente_id}_{mes_atual}"
                    url_key = f"pdf_url_{cliente_id}_{mes_atual}"
                    recomendacao = st.session_state.get(rec_key)
                    pdf_bytes = st.session_state.get(pdf_key)
                    pdf_url = st.session_state.get(url_key)

                    col_gerar, col_visualizar, col_baixar = st.columns(3)

                    with col_gerar:
                        if st.button(
                            "Gerar recomendação",
                            key=f"btn_rec_{cliente_id}",
                            type="primary",
                            use_container_width=True,
                            disabled=not mes_atual,
                        ):
                            st.session_state[rec_key] = None
                            st.session_state[pdf_key] = None
                            st.session_state[url_key] = None
                            with st.spinner("Analisando carteira e gerando recomendação..."):
                                try:
                                    texto, partes, job_id = gerar_recomendacao(cliente_id, mes_atual)
                                    st.session_state[rec_key] = texto
                                    if partes:
                                        pdf_bytes = gerar_pdf(partes)
                                        st.session_state[pdf_key] = pdf_bytes
                                        try:
                                            pdf_url = salvar_pdf_supabase(
                                                get_supabase(), cliente_id, mes_atual, job_id, pdf_bytes
                                            )
                                            st.session_state[url_key] = pdf_url
                                        except Exception:
                                            pass
                                except Exception as e:
                                    st.session_state[rec_key] = f"__erro__: {e}"
                            st.rerun()

                    with col_visualizar:
                        if pdf_url:
                            st.link_button("Visualizar PDF", pdf_url, use_container_width=True)

                    with col_baixar:
                        if pdf_bytes:
                            st.download_button(
                                label="Baixar PDF",
                                data=pdf_bytes,
                                file_name=f"relatorio_{mes_atual}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )

                    if recomendacao and recomendacao.startswith("__erro__"):
                        st.error(recomendacao.replace("__erro__: ", ""))

    with tab_add:
        st.subheader("Novo cliente")
        with st.form("form_add_cliente"):
            novo_nome = st.text_input("Nome")
            submit = st.form_submit_button("Criar cliente", type="primary")
            if submit:
                if not novo_nome.strip():
                    st.error("Preencha o nome.")
                else:
                    try:
                        get_supabase().table("clientes").insert({"nome": novo_nome.strip()}).execute()
                        st.cache_data.clear()
                        st.success(f"Cliente **{novo_nome.strip()}** criado.")
                        st.rerun()
                    except APIError as e:
                        st.error(f"Erro: {e}")

elif st.session_state.page == "ativos":
    st.subheader("Ativos Disponíveis")

    df_acoes  = load_table("ativos_acoes")
    df_fundos = load_table("ativos_fundos")
    df_rf     = load_table("ativos_renda_fixa")
    df_precos = load_table("precos_acoes")
    df_cotas  = load_table("cotas_fundos")

    # ── Métricas ──────────────────────────────────────────────────────────────
    cm1, cm2, cm3, cm4 = st.columns(4)
    cm1.metric("Total de ativos", len(df_acoes) + len(df_fundos) + len(df_rf))
    cm2.metric("Ações / FII", len(df_acoes), f"{len(df_precos)} preços históricos")
    cm3.metric("Fundos", len(df_fundos), f"{len(df_cotas)} cotas históricas")
    cm4.metric("Renda Fixa", len(df_rf))

    st.divider()

    # ── Layout: tabelas + formulário ──────────────────────────────────────────
    col_form, col_tabs = st.columns(layouts.sidebar_main)

    with col_tabs:
        max_meses_a = df_precos["mes"].nunique() if not df_precos.empty else 1
        max_meses_f = df_cotas["mes"].nunique()  if not df_cotas.empty else 1

        tab_a, tab_f, tab_rf_view = st.tabs(["Ações / FII", "Fundos", "Renda Fixa"])

        with tab_a:
            rows_a = []
            for _, a in df_acoes.iterrows():
                hist = df_precos[df_precos["ticker"] == a["ticker"]] if not df_precos.empty else pd.DataFrame()
                ultimo = hist.sort_values("mes").iloc[-1] if not hist.empty else None
                rows_a.append({
                    "Ticker":       a["ticker"],
                    "Nome":         a.get("nome", "—"),
                    "Meses":        len(hist),
                    "Último mês":   ultimo["mes"] if ultimo is not None else "—",
                    "Último preço": float(ultimo["preco_fechamento"]) if ultimo is not None else None,
                })
            st.dataframe(
                pd.DataFrame(rows_a),
                use_container_width=True, hide_index=True,
                column_config={
                    "Meses": st.column_config.ProgressColumn(
                        "Cobertura", min_value=0, max_value=max_meses_a, format="%d meses",
                    ),
                    "Último preço": st.column_config.NumberColumn("Último preço", format="R$ %.2f"),
                },
            )

        with tab_f:
            rows_f = []
            for _, f in df_fundos.iterrows():
                hist = df_cotas[df_cotas["cnpj"] == f["cnpj"]] if not df_cotas.empty else pd.DataFrame()
                ultimo = hist.sort_values("mes").iloc[-1] if not hist.empty else None
                rows_f.append({
                    "Nome":         f.get("nome", "—"),
                    "CNPJ":         f["cnpj"],
                    "Meses":        len(hist),
                    "Último mês":   ultimo["mes"] if ultimo is not None else "—",
                    "Última cota":  float(ultimo["cota_fechamento"]) if ultimo is not None else None,
                })
            st.dataframe(
                pd.DataFrame(rows_f),
                use_container_width=True, hide_index=True,
                column_config={
                    "Meses": st.column_config.ProgressColumn(
                        "Cobertura", min_value=0, max_value=max_meses_f, format="%d meses",
                    ),
                    "Última cota": st.column_config.NumberColumn("Última cota", format="R$ %.4f"),
                },
            )

        with tab_rf_view:
            if df_rf.empty:
                st.info("Nenhum instrumento de renda fixa cadastrado.")
            else:
                st.dataframe(
                    df_rf[["nome", "instrumento", "indexacao", "isento_ir", "emissor"]],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "nome":        st.column_config.TextColumn("Nome"),
                        "instrumento": st.column_config.TextColumn("Instrumento"),
                        "indexacao":   st.column_config.TextColumn("Indexação"),
                        "isento_ir":   st.column_config.CheckboxColumn("IR Isento"),
                        "emissor":     st.column_config.TextColumn("Emissor"),
                    },
                )

    with col_form:
        st.caption("Adicionar ativo")
        tipo = st.radio("tipo", ["Ação / FII", "Fundo", "Renda Fixa"],
                        horizontal=True, label_visibility="collapsed")

        with st.form("form_add_ativo"):
            if tipo == "Ação / FII":
                tipo_ativo = st.selectbox("Tipo", ["Ação", "FII"])
                ticker = st.text_input("Ticker", placeholder="ex: PETR4").upper().strip()
                nome   = st.text_input("Nome", placeholder="ex: Petrobras")
                submit = st.form_submit_button("Adicionar", type="primary", use_container_width=True)

                if submit:
                    if not ticker or not nome:
                        st.error("Preencha ticker e nome.")
                    else:
                        try:
                            get_supabase().table("ativos_acoes").insert({"ticker": ticker, "nome": nome, "tipo": tipo_ativo}).execute()
                        except APIError as e:
                            if "23505" in str(e):
                                st.error(f"**{ticker}** já cadastrado.")
                            else:
                                st.error(f"Erro: {e}")
                            st.stop()
                        st.cache_data.clear()
                        with st.status("Adicionando ativo...", expanded=True) as s:
                            st.write("✅ Ativo registrado no banco de dados")
                            bar = st.progress(0, text="Importando preços históricos...")
                            try:
                                bar.progress(15, text="Conectando ao brapi.dev...")
                                resp = http.post(
                                    f"{functions_url()}/fetch-acoes",
                                    headers={**auth_header(), "Content-Type": "application/json"},
                                    json={"ticker": ticker},
                                    timeout=120,
                                )
                                bar.progress(85, text="Salvando no banco de dados...")
                                data = resp.json()
                                bar.progress(100, text="Concluído!")
                                if resp.status_code == 200:
                                    st.write(f"✅ {data.get('meses_inseridos', 0)} meses importados")
                                    s.update(label=f"{ticker} adicionado!", state="complete")
                                else:
                                    st.write(f"⚠️ Preços não importados: {data.get('error', resp.text)}")
                                    s.update(label=f"{ticker} cadastrado (preços pendentes)", state="error")
                            except Exception as e:
                                bar.progress(100, text="Falhou")
                                st.write(f"⚠️ Erro de conexão: {e}")
                                s.update(label=f"{ticker} cadastrado (preços pendentes)", state="error")

            elif tipo == "Fundo":
                cnpj      = st.text_input("CNPJ", placeholder="ex: 12.345.678/0001-90").strip()
                nome      = st.text_input("Nome", placeholder="ex: Riza Lotus Plus")
                categoria = st.selectbox("Categoria", ["RF DI", "RF Simples", "Multimercado RF", "Multimercado", "Long Biased", "FIA"])
                submit    = st.form_submit_button("Adicionar", type="primary", use_container_width=True)

                if submit:
                    if not cnpj or not nome:
                        st.error("Preencha CNPJ e nome.")
                    else:
                        res = get_supabase().table("ativos_fundos").insert({"cnpj": cnpj, "nome": nome, "categoria": categoria}).execute()
                        if res.data:
                            st.success(f"{nome} adicionado.")
                            st.cache_data.clear()
                            st.info("Para importar histórico de cotas:")
                            st.code(f'python extract_fundos.py "{cnpj}"', language="bash")
                        else:
                            st.error(f"Erro: {res}")

            elif tipo == "Renda Fixa":
                nome        = st.text_input("Nome", placeholder="ex: CDB BTG 110% CDI")
                instrumento = st.selectbox("Instrumento", ["CDB", "LCI", "LCA", "Tesouro Direto", "Debênture"])
                indexacao   = st.selectbox("Indexação", ["pos_fixado_cdi", "pos_fixado_selic", "prefixado", "ipca_mais"])
                isento_ir   = st.checkbox("Isento de IR")
                emissor     = st.text_input("Emissor", placeholder="ex: BTG Pactual (opcional)")
                submit      = st.form_submit_button("Adicionar", type="primary", use_container_width=True)

                if submit:
                    if not nome:
                        st.error("Preencha o nome.")
                    else:
                        try:
                            get_supabase().table("ativos_renda_fixa").insert({
                                "nome": nome, "instrumento": instrumento,
                                "indexacao": indexacao, "isento_ir": isento_ir,
                                "emissor": emissor or None,
                            }).execute()
                            st.success(f"**{nome}** adicionado.")
                            st.cache_data.clear()
                        except APIError as e:
                            if "23505" in str(e):
                                st.error(f"**{nome}** já cadastrado.")
                            else:
                                st.error(f"Erro: {e}")

elif st.session_state.page == "indice_mercado":
    col_title, col_btn = st.columns(layouts.title_btn)
    col_title.subheader("Índices de mercado")

    with col_btn:
        st.write("")
        if st.button("Atualizar", type="primary", use_container_width=True):
            with st.spinner("Buscando índices..."):
                try:
                    resp = http.post(
                        f"{functions_url()}/fetch-indices",
                        headers={**auth_header(), "Content-Type": "application/json"},
                        json={},
                        timeout=60,
                    )
                    data = resp.json()
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")
                    data = None

            if data and resp.status_code == 200:
                st.success(f"{data.get('meses_inseridos', 0)} meses atualizados.")
                st.cache_data.clear()
                st.rerun()
            elif data:
                st.error(f"Erro: {data.get('error', resp.text)}")

    df = load_table("dados_mercado")

    if df.empty:
        st.info("Nenhum dado encontrado. Clique em Atualizar para buscar os índices.")
    else:
        INDICES_PCT = {
            "cdi_mensal":              "CDI",
            "ipca_mensal":             "IPCA",
            "selic_mensal":            "Selic",
            "ibovespa_retorno_mensal": "IBOVESPA",
            "ima_b_retorno_mensal":    "IMA-B",
            "pib_crescimento_anual":   "PIB (YoY)",
        }
        INDICES_FX = {
            "usd_brl_fechamento": "USD/BRL",
        }

        df_sorted = df.sort_values("mes").reset_index(drop=True)

        col_esq, col_dir = st.columns(layouts.market_split)

        # ── Esquerda: valores do mês selecionado ────────────────────────────
        with col_esq:
            _mes_ref = st.session_state.mes_selecionado
            _df_ref = df_sorted[df_sorted["mes"] == _mes_ref] if _mes_ref else pd.DataFrame()
            ultimo = _df_ref.iloc[0] if not _df_ref.empty else df_sorted.iloc[-1]
            mes_label = pd.to_datetime(ultimo["mes"] + "-01").strftime("%b/%Y")
            st.caption(f"Mês de referência: **{mes_label}**")

            for campo, label in INDICES_PCT.items():
                val = ultimo.get(campo)
                texto = f"{val:.2f}%" if pd.notna(val) else "—"
                st.markdown(components.index_stat(label, texto), unsafe_allow_html=True)
            for campo, label in INDICES_FX.items():
                val = ultimo.get(campo)
                texto = f"R$ {val:.4f}" if pd.notna(val) else "—"
                st.markdown(components.index_stat(label, texto), unsafe_allow_html=True)

        # ── Direita: gráficos históricos ──────────────────────────────────────
        with col_dir:
            # Gráfico 1 — Índices em % (CDI, IPCA, Selic, IBOV, IMA-B, PIB)
            df_chart = df_sorted[["mes"] + list(INDICES_PCT.keys())].copy()
            df_chart["mes"] = pd.to_datetime(df_chart["mes"] + "-01")

            fig = go.Figure()
            for (campo, label), cor in zip(INDICES_PCT.items(), charts.line_colors):
                serie = df_chart[["mes", campo]].dropna()
                fig.add_trace(go.Scatter(
                    x=serie["mes"], y=serie[campo],
                    name=label, mode="lines",
                    line=dict(width=charts.line_width, color=cor),
                ))

            # Linha vertical do mês selecionado
            _vline_date = _mes_ref + "-01" if _mes_ref else None

            def _add_vline(figure, date_str):
                figure.add_shape(
                    type="line", x0=date_str, x1=date_str,
                    y0=0, y1=1, yref="paper",
                    line=dict(width=1.5, dash="dash", color=colors.accent),
                )
                figure.add_annotation(
                    x=date_str, y=1, yref="paper",
                    text=mes_label, showarrow=False,
                    font=dict(color=colors.accent, size=11),
                    yshift=10,
                )

            _layout1 = charts.base_layout(charts.height_main)
            _layout1["yaxis"]["ticksuffix"] = "%"
            fig.update_layout(**_layout1)
            if _vline_date:
                _add_vline(fig, _vline_date)
            st.plotly_chart(fig, use_container_width=True)

            # Gráfico 2 — USD/BRL
            df_fx = df_sorted[["mes", "usd_brl_fechamento"]].copy()
            df_fx["mes"] = pd.to_datetime(df_fx["mes"] + "-01")
            df_fx = df_fx.dropna()

            fig_fx = go.Figure()
            fig_fx.add_trace(go.Scatter(
                x=df_fx["mes"], y=df_fx["usd_brl_fechamento"],
                name="USD/BRL", mode="lines",
                line=dict(width=charts.line_width, color=charts.accent_line),
                fill="tozeroy", fillcolor=charts.accent_fill,
            ))
            _layout2 = charts.base_layout(charts.height_secondary)
            _layout2["margin"]["t"] = 10
            _layout2["legend"]["y"] = -0.18
            _layout2["yaxis"]["tickprefix"] = "R$ "
            fig_fx.update_layout(**_layout2)
            if _vline_date:
                _add_vline(fig_fx, _vline_date)
            st.plotly_chart(fig_fx, use_container_width=True)

            # ── Grid de relatórios disponíveis ──────────────────────────────
            st.markdown(f"**Relatórios Disponíveis**")

            @st.cache_data(ttl=3500)
            def _get_rel_signed_urls():
                _df = load_table("relatorios")
                _map = {}
                if _df.empty:
                    return _map
                _sb = get_supabase()
                _keys = []
                _paths = []
                for _, r in _df.iterrows():
                    if r.get("pdf_url") and "/object/relatorios-pdf/" in str(r["pdf_url"]):
                        parts = str(r["mes"]).split("-")
                        if len(parts) == 2:
                            spath = r["pdf_url"].split("/object/relatorios-pdf/")[-1]
                            _keys.append((parts[0], parts[1]))
                            _paths.append(spath)
                if not _paths:
                    return _map
                try:
                    signed_list = _sb.storage.from_("relatorios-pdf").create_signed_urls(_paths, 3600)
                    for key, item in zip(_keys, signed_list):
                        url = item.get("signedURL") or item.get("signedUrl")
                        if url:
                            _map[key] = url
                except Exception:
                    pass
                return _map

            rel_map = _get_rel_signed_urls()

            _MESES_LABEL = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
            _ANOS = ["2022","2023","2024","2025","2026"]

            _cell_has = (
                f"background:rgba(245,166,35,0.15);color:{colors.accent};"
                f"border-radius:{spacing.radius_sm};font-weight:{typography.weight_semibold};"
                f"cursor:pointer;text-decoration:none;display:block;text-align:center;"
                f"padding:{spacing.xs} 0;"
            )
            _cell_empty = (
                f"background:{colors.bg_tertiary};color:{colors.text_muted};"
                f"border-radius:{spacing.radius_sm};text-align:center;"
                f"padding:{spacing.xs} 0;"
            )
            _cell_header = (
                f"color:{colors.text_muted};font-size:{typography.size_sm};"
                f"text-align:center;padding:{spacing.xs} 0;font-weight:{typography.weight_medium};"
            )
            _cell_year = (
                f"color:{colors.text_secondary};font-weight:{typography.weight_bold};"
                f"padding:{spacing.xs} 0;text-align:right;padding-right:{spacing.sm};"
            )

            rows_html = ""
            rows_html += f'<tr><td style="{_cell_header}"></td>'
            for ml in _MESES_LABEL:
                rows_html += f'<td style="{_cell_header}">{ml}</td>'
            rows_html += "</tr>"
            for ano in _ANOS:
                rows_html += f'<tr><td style="{_cell_year}">{ano}</td>'
                for i in range(12):
                    mes_num = f"{i+1:02d}"
                    url = rel_map.get((ano, mes_num))
                    if url:
                        rows_html += (
                            f'<td><a href="{url}" target="_blank" '
                            f'style="{_cell_has}">&#9632;</a></td>'
                        )
                    else:
                        rows_html += f'<td style="{_cell_empty}">&middot;</td>'
                rows_html += "</tr>"

            grid_html = (
                f'<table style="width:100%;border-collapse:separate;border-spacing:4px;">'
                f'{rows_html}</table>'
            )
            st.markdown(grid_html, unsafe_allow_html=True)

# ── Rodapé ────────────────────────────────────────────────────────────────────

st.divider()
_logo_footer = Path(__file__).parent / "XP_Investimentos_logo-removebg-preview.png"
import base64 as _b64
_logo_b64 = _b64.b64encode(_logo_footer.read_bytes()).decode()
_footer_text = (
    'Este é um <strong>case acadêmico / prova de conceito</strong> sem qualquer vínculo com a XP Inc. '
    'Os relatórios macro utilizados são disponibilizados gratuitamente pela XP Research.<br>'
    'Não constitui oferta ou recomendação de investimento.<br>'
    '© 2026 João Saraiva — IA Deployment'
)
st.markdown(components.footer(_footer_text, _logo_b64), unsafe_allow_html=True)
