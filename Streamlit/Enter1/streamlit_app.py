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
    st.title("Análise de portfólio e rendimentos")

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
        "Esta plataforma é um MVP que integra **cálculo de rendimentos**, comparação de performance com benchmarks de mercado "
        "e **geração de recomendações personalizadas** por cliente, com base no perfil de risco e na composição atual da carteira, "
        "utilizando modelos de linguagem orquestrados para produzir relatórios mensais individualizados de forma automática. "
        "Além disso, é o ponto de partida de uma **lógica centralizada de gestão de rendimentos e recomendações**, "
        "permitindo que assessores acompanhem a evolução de cada cliente e tomem decisões de alocação de forma mais eficiente e escalável."
    )

    tab_solucao, tab_regras, tab_modelo, tab_infra, tab_proximos = st.tabs(
        ["Solução", "Regras de Negócio", "Modelo", "Infraestrutura", "Próximos Passos"]
    )

    # ── Solução ──────────────────────────────────────────────────────────────
    with tab_solucao:
        _sol_card = (
            "background-color:#404040;border-radius:10px;padding:1.5rem 1.5rem 1.2rem;"
            "color:#f0f0f0;height:100%;text-align:center;"
        )
        _icon_style = f"width:48px;height:48px;stroke:{colors.accent};margin:0 auto 0.6rem auto;display:block;"
        _icon_dir = Path(__file__).parent / "icons"

        import base64 as _b64_icons

        def _svg_icon(filename: str) -> str:
            svg = (_icon_dir / filename).read_text(encoding="utf-8")
            svg = svg.replace('stroke="currentColor"', f'stroke="{colors.accent}"')
            svg = svg.replace('width="24"', 'width="48"').replace('height="24"', 'height="48"')
            b64 = _b64_icons.b64encode(svg.encode()).decode()
            return f'<img src="data:image/svg+xml;base64,{b64}" style="{_icon_style}" />'

        _ic_clientes = _svg_icon("icon_clientes.svg")
        _ic_rendimentos = _svg_icon("icon_rendimentos.svg")
        _ic_recomendacoes = _svg_icon("icon_recomendacoes.svg")

        _, col1, col2, col3, _ = st.columns([1, 3, 3, 3, 1])

        with col1:
            st.markdown(
                f'<div style="{_sol_card}">'
                f'{_ic_clientes}'
                f'<p style="font-size:1.15rem;font-weight:700;color:{colors.accent};margin:0 0 0.6rem 0;">'
                'Gestão de Clientes e Ativos</p>'
                '<p style="font-size:0.92rem;line-height:1.55;margin:0;text-align:left;">'
                'Cadastro completo de clientes com <b>perfil de risco</b> (conservador, moderado, arrojado ou agressivo) '
                'e visualização consolidada de todas as posições — <b>ações, FIIs, fundos e renda fixa</b>.<br><br>'
                'Para cada cliente é possível:<br>'
                '• Consultar a <b>composição da carteira</b> com peso de cada ativo<br>'
                '• Acompanhar o <b>valor total</b> e a <b>variação mensal</b> em reais<br>'
                '• Visualizar o <b>histórico de rendimentos</b> mês a mês<br>'
                '• Comparar a performance individual com os benchmarks de mercado<br><br>'
                'O catálogo de ativos disponíveis para alocação inclui ações listadas na B3, fundos de investimento '
                'com cotas da CVM e instrumentos de renda fixa indexados a CDI, Selic, IPCA ou prefixados.'
                '</p></div>',
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f'<div style="{_sol_card}">'
                f'{_ic_rendimentos}'
                f'<p style="font-size:1.15rem;font-weight:700;color:{colors.accent};margin:0 0 0.6rem 0;">'
                'Cálculo de Rendimentos</p>'
                '<p style="font-size:0.92rem;line-height:1.55;margin:0;text-align:left;">'
                'A cada mês, o sistema consolida automaticamente todas as posições do cliente e calcula o '
                '<b>retorno individual de cada ativo</b> com base em preços de mercado (ações), cotas oficiais da CVM (fundos) '
                'e taxas de referência (renda fixa).<br><br>'
                'O <b>retorno ponderado do portfólio</b> é calculado considerando o peso de cada posição no patrimônio total. '
                'A partir disso, são gerados os <b>alfas</b> — a diferença entre o retorno do portfólio e os principais benchmarks:<br>'
                '• <b>Alfa vs CDI</b> — mede se o portfólio superou a renda fixa básica<br>'
                '• <b>Retorno real (IPCA)</b> — mostra o ganho acima da inflação<br>'
                '• <b>Ações vs IBOVESPA</b> — compara a classe de ações com o índice da bolsa<br><br>'
                'Além disso, são identificados os <b>maiores contribuidores e detratores</b> do mês, '
                'permitindo entender quais ativos impulsionaram ou prejudicaram o resultado.'
                '</p></div>',
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f'<div style="{_sol_card}">'
                f'{_ic_recomendacoes}'
                f'<p style="font-size:1.15rem;font-weight:700;color:{colors.accent};margin:0 0 0.6rem 0;">'
                'Recomendações</p>'
                '<p style="font-size:0.92rem;line-height:1.55;margin:0;text-align:left;">'
                'O módulo de recomendações combina a <b>leitura do cenário econômico</b> com o perfil de cada cliente '
                'para gerar sugestões de alocação personalizadas.<br><br>'
                'O cenário macro é construído a partir de:<br>'
                '• <b>Relatórios mensais</b> de research com análise de conjuntura<br>'
                '• <b>Indicadores econômicos</b> — CDI, IPCA, Selic, IBOVESPA, câmbio e PIB<br>'
                '• <b>Tendências</b> identificadas na variação dos indicadores ao longo dos meses<br><br>'
                'Com base nesse contexto, um modelo de linguagem orquestrado via <b>Rivet</b> cruza o diagnóstico da carteira, '
                'o perfil de risco e o cenário atual para produzir um <b>relatório mensal individualizado</b> '
                'com recomendações de rebalanceamento e oportunidades alinhadas ao momento de mercado.'
                '</p></div>',
                unsafe_allow_html=True,
            )

        st.divider()

        st.markdown("#### Como usar")
        c1, c2, c3, c4 = st.columns(4)
        _card_style = "background-color:#404040;border-radius:8px;padding:1rem 1.2rem;color:#f0f0f0;"
        _cards = [
            ("<b>1. Selecione o período</b>", "No menu superior, escolha o mês de referência. Todos os cálculos, gráficos e recomendações serão atualizados para refletir esse período."),
            ("<b>2. Acesse Clientes</b>", "Escolha um cliente para visualizar a carteira consolidada, os rendimentos de cada ativo, os alfas vs. benchmarks e os destaques do mês. Também é possível gerar a recomendação personalizada."),
            ("<b>3. Explore Ativos</b>", "Consulte o catálogo completo de ações, FIIs, fundos e renda fixa disponíveis para alocação, com detalhes de indexação, emissor e categoria."),
            ("<b>4. Acompanhe o Mercado</b>", "Acompanhe a evolução mensal dos indicadores econômicos — CDI, IPCA, Selic, IBOVESPA, câmbio e PIB — e acesse os relatórios de research disponíveis."),
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
            st.markdown(
                "Regra de negócio central que classifica todos os ativos da plataforma em **4 grupos comportamentais**. "
                "Cada classe agrupa ativos que respondem de forma homogênea aos mesmos indicadores macroeconômicos. "
                "O critério de agrupamento não é o instrumento jurídico (CDB, fundo, ação) nem o emissor — "
                "é o **comportamento frente ao cenário macroeconômico**."
            )

            _cls_card = "background-color:#404040;border-radius:10px;padding:1.2rem;color:#f0f0f0;margin-bottom:1rem;min-height:280px;"
            _cls1, _cls2, _cls3, _cls4 = st.columns(4)

            with _cls1:
                st.markdown(
                    f'<div style="{_cls_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Caixa e Liquidez</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">'
                    'Reúne ativos pós-fixados indexados ao <b>CDI</b> ou à <b>Selic</b> e fundos de renda fixa simples (RF DI, RF Simples). '
                    'Seguem a taxa básica de juros diretamente, com volatilidade próxima de zero e liquidez imediata.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Limitação da categorização: unir CDI e Selic numa só classe ignora diferenças de liquidez e tributação entre CDBs, LCIs e fundos DI — ativos com prazos e condições de resgate distintos são tratados como equivalentes.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _cls2:
                st.markdown(
                    f'<div style="{_cls_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Renda Fixa Estruturada</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">'
                    'Agrupa ativos com indexador definido na contratação — <b>IPCA+</b> e <b>prefixados</b> — além de fundos Multimercado RF. '
                    'Possuem duration e sofrem marcação a mercado, gerando oscilações conforme as expectativas de juros.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Limitação da categorização: agrupar IPCA+, prefixados e fundos Multimercado RF na mesma classe esconde diferenças de duration e risco de crédito — um CRA IPCA+ longo e um CDB prefixado curto têm sensibilidades a juros muito distintas.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _cls3:
                st.markdown(
                    f'<div style="{_cls_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Multimercado</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">'
                    'Inclui fundos com gestão ativa e mandato flexível — <b>Multimercado</b> e <b>Long Biased</b>. '
                    'Podem operar juros, câmbio, ações e derivativos simultaneamente, buscando retorno acima do CDI em diferentes cenários.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Limitação da categorização: Multimercado e Long Biased têm mandatos muito diferentes — um fundo macro pode estar vendido em bolsa enquanto um Long Biased está comprado. Tratá-los como uma classe homogênea mascara exposições opostas ao mesmo fator de risco.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _cls4:
                st.markdown(
                    f'<div style="{_cls_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Renda Variável</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">'
                    'Reúne <b>ações</b>, <b>FIIs</b> e <b>fundos de ações (FIA)</b>. '
                    'O retorno é determinado pelo crescimento econômico (PIB) e pelo custo de capital (Selic), '
                    'com exposição direta ao risco de mercado.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Limitação da categorização: ações, FIIs e FIAs são tratados como um bloco único, mas têm perfis de risco distintos — FIIs geram renda recorrente com menor volatilidade, enquanto ações de crescimento e FIAs alavancados podem ter drawdowns muito maiores.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

        with st.expander("Perfis de Risco"):
            st.markdown(
                "Cada cliente é classificado em um dos **4 perfis de investidor**, que determina quais classes de ativos ele pode acessar "
                "(suitability) e a **alocação-alvo** para rebalanceamento. "
                "Quando a distribuição da carteira se desvia do alvo, o sistema recomenda ajuste — os alvos de cada perfil somam 100%."
            )

            _prf_card = "background-color:#404040;border-radius:10px;padding:1.2rem;color:#f0f0f0;margin-bottom:1rem;min-height:280px;"
            _prf1, _prf2, _prf3, _prf4 = st.columns(4)

            with _prf1:
                st.markdown(
                    f'<div style="{_prf_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Conservador</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">'
                    'Acessa apenas <b>Caixa</b> e <b>Renda Fixa</b>. Prioriza preservação de capital e previsibilidade. '
                    'Alocação-alvo: 60% Caixa, 40% Renda Fixa. Sem exposição a multimercado ou renda variável.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Limitação: ao restringir a 2 classes, o perfil pode subestimar a tolerância real do investidor — '
                    'clientes conservadores com horizonte longo perdem oportunidade de ganho real acima da inflação.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _prf2:
                st.markdown(
                    f'<div style="{_prf_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Moderado</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">'
                    'Acessa <b>Caixa</b>, <b>Renda Fixa</b> e <b>Multimercado</b>. Busca retorno acima do CDI com volatilidade controlada. '
                    'Alocação-alvo: 30% Caixa, 50% Renda Fixa, 20% Multimercado.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Limitação: a vedação total a renda variável é uma simplificação — na prática, muitos moderados aceitam '
                    'pequena exposição a FIIs ou fundos de dividendos, que ficam inacessíveis neste perfil.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _prf3:
                st.markdown(
                    f'<div style="{_prf_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Arrojado</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">'
                    'Acessa <b>todas as 4 classes</b>. Aceita oscilações em troca de maior potencial de retorno. '
                    'Alocação-alvo: 15% Caixa, 35% Renda Fixa, 25% Multimercado, 25% Renda Variável.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Limitação: a amplitude da alocação em renda variável permite carteiras com perfis de risco muito diferentes '
                    'serem ambas classificadas como "arrojado", dificultando comparações entre clientes.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _prf4:
                st.markdown(
                    f'<div style="{_prf_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Agressivo</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">'
                    'Acessa <b>todas as 4 classes</b> com foco em maximizar retorno. '
                    'Alocação-alvo: 5% Caixa, 15% Renda Fixa, 30% Multimercado, 50% Renda Variável.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Limitação: o perfil concentra fortemente em renda variável sem distinguir entre estratégias '
                    '(value vs. growth, small vs. large cap), tratando toda exposição a RV como equivalente.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

        with st.expander("Indicadores Macroeconômicos"):
            st.markdown(
                "O sistema utiliza **7 indicadores macroeconômicos** para construir uma leitura do cenário econômico. "
                "A partir dos relatórios de research, cada indicador é avaliado "
                "quanto à sua **tendência atual** — se está em deterioração, estável ou melhora. "
                "Essa leitura alimenta o ranking de classes de ativos e orienta as recomendações de alocação."
            )

            _ind_card = "background-color:#404040;border-radius:10px;padding:1.2rem;color:#f0f0f0;margin-bottom:1rem;min-height:280px;"
            _ind_r1c1, _ind_r1c2, _ind_r1c3, _ind_r1c4 = st.columns(4)
            _ind_r2c1, _ind_r2c2, _ind_r2c3, _ind_r2c4 = st.columns(4)

            _indicadores = [
                ("Selic", "Taxa básica de juros definida pelo Copom/Banco Central. Quando sobe, encarece o crédito e torna a renda fixa mais atrativa; quando cai, estimula o consumo e favorece ativos de risco.",
                 "Limitação: captura apenas a meta Selic — não reflete o spread bancário real nem as condições efetivas de crédito ao consumidor."),
                ("IPCA", "Inflação oficial medida pelo IBGE. Mede a perda de poder de compra da moeda e é o principal termômetro para decisões de política monetária. Inflação alta corrói retornos reais; inflação controlada dá previsibilidade.",
                 "Limitação: é um índice agregado nacional — não captura diferenças regionais nem a inflação percebida em segmentos específicos do mercado."),
                ("Câmbio", "Taxa de câmbio BRL/USD. Um real desvalorizado beneficia exportadores e pressiona a inflação importada; um real forte favorece importações e reduz custos de empresas endividadas em dólar.",
                 "Limitação: considera apenas o dólar — ignora outras moedas relevantes e não distingue entre movimentos estruturais e volatilidade de curto prazo."),
                ("PIB", "Crescimento econômico do país medido pelo IBGE. PIB em expansão sinaliza aumento de lucros corporativos e arrecadação; retração indica menor atividade e maior aversão a risco.",
                 "Limitação: dado publicado com defasagem significativa — a tendência pode já ter mudado quando a análise é gerada."),
                ("Mercado de Crédito", "Condições de oferta e demanda por crédito no mercado privado. Spreads elevados indicam aversão a risco e encarecimento do financiamento; spreads comprimidos indicam apetite por risco e liquidez abundante.",
                 "Limitação: não há um indicador único e público para crédito privado — a avaliação depende de interpretação qualitativa dos relatórios de research."),
                ("Risco Fiscal", "Percepção sobre a trajetória das contas públicas — dívida, déficit e credibilidade da política fiscal. Deterioração fiscal pressiona juros futuros e o câmbio; disciplina fiscal transmite confiança ao mercado.",
                 "Limitação: altamente subjetivo — diferentes analistas podem ter leituras opostas sobre o mesmo dado fiscal, e a análise herda essa ambiguidade."),
                ("Cenário Externo", "Contexto global que influencia o Brasil: política monetária dos EUA (Fed), preços de commodities, tensões geopolíticas e fluxo de capital estrangeiro. Um ambiente global favorável atrai investimentos; crises externas provocam fuga de capital.",
                 "Limitação: condensa múltiplos fatores globais em uma única avaliação, perdendo nuances — uma alta de juros nos EUA e uma guerra comercial têm impactos distintos mas recebem o mesmo tratamento."),
            ]

            _ind_cols = [_ind_r1c1, _ind_r1c2, _ind_r1c3, _ind_r1c4, _ind_r2c1, _ind_r2c2, _ind_r2c3]
            for col, (nome, desc, lim) in zip(_ind_cols, _indicadores):
                with col:
                    st.markdown(
                        f'<div style="{_ind_card}">'
                        f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">{nome}</p>'
                        f'<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">{desc}</p>'
                        f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">{lim}</p>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                "Dois cenários relevantes **não são contemplados** pelos 7 indicadores atuais:\n\n"
                "1. **Expectativas futuras do mercado** — os indicadores atuais refletem o estado presente ou passado da economia, "
                "mas não capturam o que o mercado já está precificando para os próximos meses. "
                "A **Curva de Juros (DI Futuro)** resolveria isso: sua inclinação revela se o mercado espera alta ou corte de juros, "
                "permitindo antecipar movimentos antes de o Copom agir.\n\n"
                "2. **Sentimento do investidor estrangeiro** — o cenário externo atual é avaliado de forma qualitativa e genérica, "
                "sem medir o impacto real sobre o fluxo de capital para o Brasil. "
                "Dois indicadores cobririam essa lacuna: o **CDS Brasil (Risco Soberano)**, que mede em tempo real o custo de proteção "
                "contra calote da dívida brasileira (mais objetivo que a análise qualitativa de risco fiscal), "
                "e o **Fluxo Estrangeiro na B3**, que mostra diretamente se investidores internacionais estão entrando ou saindo — "
                "fluxo positivo sustentado tende a valorizar o real e impulsionar a bolsa, enquanto saídas pressionam câmbio e ações."
            )

        with st.expander("Ranking de Classes de Ativos"):
            st.markdown(
                "A cada mês, o sistema ordena as 4 classes de ativos por **atratividade relativa** "
                "dado o cenário econômico. Para cada classe, é calculado um score que combina a avaliação "
                "de cada indicador com o peso que ele exerce sobre aquela classe. "
                "A classe com maior score final é a mais favorecida pelo momento de mercado."
            )

            _rank_card = "background-color:#404040;border-radius:10px;padding:1.2rem;color:#f0f0f0;margin-bottom:1rem;min-height:320px;"
            _rk1, _rk2, _rk3, _rk4 = st.columns(4)

            with _rk1:
                st.markdown(
                    f'<div style="{_rank_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Caixa</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">'
                    '<b>Selic (+2)</b> — único driver: CDI/Selic sobe, caixa rende mais sem risco adicional<br>'
                    '<b>Fiscal (-1)</b> — deterioração fiscal pode antecipar cortes e encurtar o período de juros altos<br><br>'
                    'Todos os outros indicadores têm peso zero — não afetam a rentabilidade do caixa de forma material.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Classe mais defensiva: só depende da taxa básica de juros.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _rk2:
                st.markdown(
                    f'<div style="{_rank_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Renda Fixa</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">'
                    '<b>Fiscal (-2)</b> — principal inimigo: abre prêmio de risco nos títulos longos e derruba preços<br>'
                    '<b>Selic (-1)</b> — alta de juros deprecia títulos com duration (marcação a mercado)<br>'
                    '<b>IPCA (+1)</b> — beneficia diretamente papéis IPCA+<br>'
                    '<b>Crédito (-1)</b> — spreads abertos depreciam fundos de crédito privado<br>'
                    '<b>Externo (-1)</b> — cenário adverso contamina spreads domésticos'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Classe mais sensível ao risco fiscal — 5 dos 7 indicadores a afetam.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _rk3:
                st.markdown(
                    f'<div style="{_rank_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Multimercado</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">'
                    '<b>Câmbio (+1)</b> — BRL desvalorizado abre posições em exportadoras e ativos dolarizados<br>'
                    '<b>PIB (+1)</b> — crescimento expande o universo de oportunidades direcionais<br>'
                    '<b>Selic (-1)</b> — eleva custo de carregamento de posições alavancadas<br>'
                    '<b>Fiscal (-1)</b> — limita posições em juros longos'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Classe mais equilibrada: pesos moderados porque o gestor ativo pode se adaptar ao cenário.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _rk4:
                st.markdown(
                    f'<div style="{_rank_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Renda Variável</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;">'
                    '<b>PIB (+2)</b> — driver principal: crescimento expande lucros e valuations<br>'
                    '<b>Selic (-2)</b> — alta de juros eleva taxa de desconto e derruba preços dos ativos<br>'
                    '<b>Externo (-2)</b> — adversidade externa provoca fuga de capitais e aperta crédito global<br>'
                    '<b>Fiscal (-1)</b> — comprime múltiplos e afasta capital estrangeiro'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Classe com pesos mais extremos (+2/-2): maior potencial e maior sensibilidade ao cenário.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            st.markdown(
                "Os pesos mais fortes (**+2/-2**) aparecem onde o indicador é o driver primário da classe. "
                "Pesos moderados (**+1/-1**) indicam influência relevante mas não dominante. "
                "**Zero** significa que o efeito líquido é neutro no nível da classe — pode afetar ativos individuais, "
                "mas se cancela no agregado."
            )

        with st.expander("Ranking de Ativos por Classe"):
            st.markdown(
                "Após definir a ordem de atratividade das classes, o sistema ordena os **ativos dentro de cada classe** "
                "por prioridade. A abordagem varia conforme o tipo de ativo: ativos com série histórica de preços "
                "são avaliados por retorno ajustado ao risco, enquanto ativos de renda fixa pura são avaliados "
                "por alinhamento com a tendência macroeconômica."
            )

            _atv_card = "background-color:#404040;border-radius:10px;padding:1.2rem;color:#f0f0f0;margin-bottom:1rem;min-height:300px;"
            _atv1, _atv2 = st.columns(2)

            with _atv1:
                st.markdown(
                    f'<div style="{_atv_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">'
                    'Ativos com Histórico (Ações e Fundos)</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Para ações e fundos que possuem série de preços/cotas dos últimos 12 meses, o ranking usa '
                    'um <b>Sharpe proxy</b> — uma medida de retorno ajustado ao risco:<br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Retorno₁₂ₘ = (Preço_final / Preço_inicial) − 1</code><br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Volatilidade = σ(retornos mensais)</code><br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Alfa = Retorno₁₂ₘ − Benchmark₁₂ₘ</code><br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Score = Alfa / Volatilidade</code><br><br>'
                    'O benchmark é o <b>IBOVESPA</b> para renda variável e o <b>CDI</b> para as demais. '
                    'Quanto maior o score, melhor o retorno acima do mercado por unidade de risco.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Limitação: usa apenas 12 meses de dados — ativos recentes com poucos meses de histórico '
                    'podem ter scores distorcidos por janelas curtas e pouco representativas.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _atv2:
                st.markdown(
                    f'<div style="{_atv_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">'
                    'Renda Fixa Pura (Sem Histórico)</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Ativos de renda fixa direta (CDBs, LCIs, debêntures) não possuem série de preços negociados. '
                    'O score é definido pelo <b>alinhamento entre o indexador e a tendência da Selic</b>.<br><br>'
                    'Primeiro, calcula-se a tendência:<br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Tendência = Selic_atual vs Média(Selic últimos 3 meses)</code><br>'
                    '<span style="font-size:0.82rem;">Se atual &gt; média × 1,005 → alta · Se atual &lt; média × 0,995 → baixa · Senão → estável</span><br><br>'
                    'Depois, o score de cada indexador:<br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Pós-fixado Selic → 1 se tendência = alta, senão 0</code><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Pós-fixado CDI &nbsp; → sempre 0 (neutro)</code><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'IPCA+ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; → 1 se IPCA acum. 12m &gt; 5%, senão 0</code><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Prefixado &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; → 1 se tendência = baixa, senão 0</code>'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Limitação: score binário (0 ou 1) — não diferencia entre ativos do mesmo indexador com prazos, '
                    'emissores ou spreads diferentes.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            st.markdown(
                "Cada ativo é automaticamente mapeado para sua classe: "
                "**Caixa** (pós-fixado CDI/Selic, fundos RF DI e RF Simples), "
                "**Renda Fixa** (IPCA+, prefixado, fundos Multimercado RF), "
                "**Multimercado** (fundos Multimercado e Long Biased), "
                "**Renda Variável** (ações, FIIs, fundos FIA). "
                "Dentro de cada classe, os ativos são ordenados por score decrescente."
            )

        with st.expander("Regra de Suitability"):
            st.markdown(
                "Antes de montar o ranking final, o sistema aplica um **filtro de suitability** que determina "
                "quais classes de ativos cada cliente pode acessar, com base no seu perfil de risco. "
                "É uma barreira regulatória binária — se a classe não está na lista permitida, nenhum ativo dela "
                "aparece na recomendação, independentemente da atratividade macro."
            )

            _suit_card = "background-color:#404040;border-radius:10px;padding:1.2rem;color:#f0f0f0;margin-bottom:1rem;min-height:200px;"
            _su1, _su2, _su3, _su4 = st.columns(4)

            with _su1:
                st.markdown(
                    f'<div style="{_suit_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Conservador</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;text-align:center;">'
                    'Caixa<br>Renda Fixa'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Multimercado e Renda Variável são bloqueados — mesmo que sejam as classes mais atrativas no cenário.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _su2:
                st.markdown(
                    f'<div style="{_suit_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Moderado</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;text-align:center;">'
                    'Caixa<br>Renda Fixa<br>Multimercado'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Renda Variável é bloqueada — o cliente não recebe recomendações de ações, FIIs ou FIAs.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _su3:
                st.markdown(
                    f'<div style="{_suit_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Arrojado</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;text-align:center;">'
                    'Caixa<br>Renda Fixa<br>Multimercado<br>Renda Variável'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Acesso total — todas as classes estão disponíveis para recomendação.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _su4:
                st.markdown(
                    f'<div style="{_suit_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Agressivo</p>'
                    '<p style="font-size:0.88rem;line-height:1.5;margin:0 0 0.8rem 0;text-align:center;">'
                    'Caixa<br>Renda Fixa<br>Multimercado<br>Renda Variável'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Acesso total — a diferença para o arrojado está na alocação-alvo, não nas classes permitidas.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            st.markdown(
                "O filtro é aplicado **antes** da montagem do ranking global: as classes não permitidas "
                "são removidas do ranking de atratividade macro, e seus ativos não aparecem na lista final."
            )

        with st.expander("Ranking Global de Ativos"):
            st.markdown(
                "Etapa final que combina os resultados das etapas anteriores em uma **lista única e ordenada de ativos** "
                "para cada cliente. Não há recálculo — apenas filtragem e composição de rankings já prontos."
            )

            _gl_card = "background-color:#404040;border-radius:10px;padding:1.2rem;color:#f0f0f0;margin-bottom:1rem;min-height:250px;"
            _gl1, _gl2, _gl3 = st.columns(3)

            with _gl1:
                st.markdown(
                    f'<div style="{_gl_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">'
                    'Entrada</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'O nó recebe três inputs já calculados pelas etapas anteriores:<br><br>'
                    '• <b>ranking_classes</b> — lista ordenada das 4 classes por atratividade macro '
                    '(ex: [multimercado, renda_variavel, caixa, renda_fixa])<br>'
                    '• <b>ranking_ativos</b> — objeto com os ativos ordenados por score dentro de cada classe<br>'
                    '• <b>classes_permitidas</b> — lista de classes que o perfil do cliente pode acessar (regra de suitability)'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Nenhum dado bruto chega aqui — apenas rankings prontos.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _gl2:
                st.markdown(
                    f'<div style="{_gl_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">'
                    'Processamento</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Duas operações sequenciais:<br><br>'
                    '<b>1. Filtro</b> — percorre o ranking_classes e mantém apenas as classes presentes em classes_permitidas, '
                    'preservando a ordem de atratividade macro.<br><br>'
                    '<b>2. Montagem</b> — para cada classe que passou no filtro, busca seus ativos em ranking_ativos. '
                    'Se a classe existe e tem ativos, inclui na saída. Se não tem ativos, é omitida silenciosamente.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Não há recálculo de scores, reordenação ou desempate — a ordem vem integralmente dos inputs.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _gl3:
                st.markdown(
                    f'<div style="{_gl_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">'
                    'Saída</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Um objeto onde as chaves são as classes permitidas (na ordem macro) e os valores são as listas de ativos '
                    '(na ordem interna do score):<br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    '{ classe_mais_atrativa: [melhor, ...],<br>'
                    '&nbsp;&nbsp;segunda_classe: [melhor, ...] }</code><br><br>'
                    'Essa lista alimenta diretamente o módulo de <b>recomendação de rebalanceamento</b>, '
                    'que decide o que comprar e vender para alinhar a carteira ao cenário atual.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'A operação é idempotente — aplicar duas vezes produz o mesmo resultado.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

        with st.expander("Recomendação de Rebalanceamento"):
            st.markdown(
                "Pipeline determinístico de **5 etapas** que transforma as posições do cliente em recomendações "
                "concretas de compra e venda, alinhando a carteira ao perfil de risco e ao cenário macro."
            )

            _rec_card = "background-color:#404040;border-radius:10px;padding:1.2rem;color:#f0f0f0;margin-bottom:1rem;min-height:260px;"

            # Linha 1: etapas 1, 2, 3
            _rc1, _rc2, _rc3 = st.columns(3)

            with _rc1:
                st.markdown(
                    f'<div style="{_rec_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">'
                    'Etapa 1 — Valorizar Posições</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Calcula o <b>valor atual</b> de cada posição do cliente e atribui sua classe:<br><br>'
                    '• <b>Ações</b>: quantidade × último preço de fechamento<br>'
                    '• <b>Fundos</b>: nº de cotas × última cota de fechamento<br>'
                    '• <b>Renda Fixa</b>: valor aplicado (sem marcação a mercado)<br><br>'
                    'Cada posição recebe sua classe pelo mesmo mapeamento usado no ranking (indexação/categoria). '
                    'Posições sem classe válida são descartadas.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Saída: lista de posições com id, nome, classe, tipo e valor_atual.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _rc2:
                st.markdown(
                    f'<div style="{_rec_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">'
                    'Etapa 2 — Percentual por Classe</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Agrega as posições valorizadas por classe:<br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'total_carteira = Σ valor_atual</code><br><br>'
                    'Para cada classe:<br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'percentual = (valor_classe / total) × 100</code><br><br>'
                    'O resultado mostra quanto da carteira está alocado em cada classe (ex: caixa 45%, renda fixa 30%, etc.).'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Saída: total_carteira + valor e percentual por classe.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _rc3:
                st.markdown(
                    f'<div style="{_rec_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">'
                    'Etapa 3 — Calcular Desvios</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Compara a alocação atual com a <b>alocação-alvo do perfil</b>:<br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'desvio_pp = atual − alvo</code><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'desvio_brl = (desvio_pp / 100) × total</code><br><br>'
                    'Status de cada classe:<br>'
                    '• <b>excesso</b> — atual &gt; máximo → candidata a venda<br>'
                    '• <b>déficit</b> — atual &lt; mínimo → candidata a compra<br>'
                    '• <b>ok</b> — dentro da faixa mín/máx'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Se o perfil não é reconhecido, usa moderado como fallback.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            # Linha 2: etapas 4a, 4b, 5
            _rc4, _rc5, _rc6 = st.columns(3)

            with _rc4:
                st.markdown(
                    f'<div style="{_rec_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">'
                    'Etapa 4a — Vender (Excesso)</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Para cada classe com status <b>excesso</b>:<br><br>'
                    '1. Define saldo a vender = desvio_brl<br>'
                    '2. Pega as posições do cliente na classe<br>'
                    '3. Ordena pelos <b>piores no ranking primeiro</b> (último do ranking vende primeiro)<br>'
                    '4. Vai vendendo até zerar o saldo<br><br>'
                    'Se o ativo nem aparece no ranking → <i>"ativo não consta no ranking recomendado"</i><br>'
                    'Se aparece mas é dos últimos → <i>"classe em excesso — menor prioridade"</i>'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Pode gerar múltiplas recomendações de venda por classe.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _rc5:
                st.markdown(
                    f'<div style="{_rec_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">'
                    'Etapa 4b — Comprar (Déficit)</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Para cada classe com status <b>déficit</b>:<br><br>'
                    '1. Define valor a aportar = |desvio_brl|<br>'
                    '2. Percorre o ranking da classe (melhor → pior)<br>'
                    '3. Procura o <b>1º ativo que o cliente já tem</b> → recomenda aumentar posição<br>'
                    '4. Se nenhum ativo do ranking está na carteira → recomenda <b>abrir posição no 1º do ranking</b><br><br>'
                    'Gera apenas <b>1 recomendação de compra por classe</b> em déficit.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Prioriza reforçar posições existentes antes de abrir novas.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _rc6:
                st.markdown(
                    f'<div style="{_rec_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">'
                    'Etapa 5 — Consolidar</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Agrupa todas as recomendações de venda e compra por classe:<br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    '{ vendas: &nbsp;{ classe: [...] },<br>'
                    '&nbsp;&nbsp;compras: { classe: [...] } }</code><br><br>'
                    'Esse resultado é enviado ao LLM que redige o <b>relatório final em linguagem natural</b>, '
                    'contextualizando as recomendações com o cenário macro e o perfil do cliente.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'O relatório é o produto final entregue ao assessor.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

        with st.expander("Cálculo de Rendimento dos Ativos"):
            st.markdown(
                "O sistema calcula o **retorno individual de cada ativo** do cliente a cada mês, "
                "usando a fonte de dados e a fórmula adequada para cada tipo de instrumento."
            )

            _rend_card = "background-color:#404040;border-radius:10px;padding:1.2rem;color:#f0f0f0;margin-bottom:1rem;min-height:280px;"
            _ra1, _ra2, _ra3 = st.columns(3)

            with _ra1:
                st.markdown(
                    f'<div style="{_rend_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Ações e FIIs</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Retorno baseado na variação de preço + dividendos:<br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'retorno = (preço_atual − preço_ant + div) / preço_ant × 100</code><br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'valor_posição = quantidade × preço_atual</code><br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'variação_R$ = (preço_atual − preço_ant + div) × qtd</code>'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Fonte: preços mensais de fechamento + dividendos pagos no mês.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _ra2:
                st.markdown(
                    f'<div style="{_rend_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Fundos de Investimento</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Retorno pela variação da cota:<br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'retorno = (cota_atual / cota_ant − 1) × 100</code><br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'valor_posição = nº_cotas × cota_atual</code><br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'variação_R$ = nº_cotas × (cota_atual − cota_ant)</code>'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Fonte: cotas mensais da CVM (Informe Diário de Fundos).'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _ra3:
                st.markdown(
                    f'<div style="{_rend_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Renda Fixa</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Fórmula depende do indexador:<br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Pós CDI: &nbsp;CDI_mês × (taxa / 100)</code><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Pós Selic: Selic_mês × (taxa / 100)</code><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Prefixado: ((1+taxa/100)^(1/12) − 1) × 100</code><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'IPCA+: (1+IPCA/100) × (1+spread_mês) − 1</code><br><br>'
                    'valor_posição = valor_aplicado (sem marcação a mercado).'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Taxa significa: % do CDI/Selic (pós) ou % a.a. (pré/IPCA+).'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Limitações do modelo de cálculo:**")

            _lim_card = "background-color:#333;border-radius:10px;padding:1.2rem;color:#f0f0f0;border:1px dashed #666;margin-bottom:1rem;"
            _lm1, _lm2, _lm3 = st.columns(3)

            with _lm1:
                st.markdown(
                    f'<div style="{_lim_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Ações e FIIs</p>'
                    '<p style="font-size:0.85rem;line-height:1.5;margin:0;">'
                    '• Usa apenas preço de <b>fechamento mensal</b> — não captura volatilidade intra-mês nem '
                    'oportunidades de compra/venda durante o período<br><br>'
                    '• Dividendos dependem de o campo estar preenchido na base — se ausente, o retorno fica subestimado<br><br>'
                    '• Não considera <b>eventos corporativos</b> como desdobramentos, agrupamentos ou bonificações '
                    'que alteram a base de preço sem representar ganho/perda real'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _lm2:
                st.markdown(
                    f'<div style="{_lim_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Fundos</p>'
                    '<p style="font-size:0.85rem;line-height:1.5;margin:0;">'
                    '• Cotas da CVM podem ter <b>defasagem de publicação</b> — alguns fundos reportam com dias de atraso, '
                    'e o valor exibido pode não refletir a cota mais recente<br><br>'
                    '• Não considera <b>come-cotas</b> (antecipação semestral de IR em fundos abertos), '
                    'que reduz o número de cotas sem alterar o valor da cota<br><br>'
                    '• Fundos com período de carência ou resgate D+30/60 aparecem com o mesmo tratamento de fundos líquidos'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _lm3:
                st.markdown(
                    f'<div style="{_lim_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Renda Fixa</p>'
                    '<p style="font-size:0.85rem;line-height:1.5;margin:0;">'
                    '• <b>Sem marcação a mercado</b> — o valor da posição é sempre o valor aplicado, não refletindo '
                    'ganhos ou perdas de quem vendesse antes do vencimento<br><br>'
                    '• Prefixados e IPCA+ podem ter retorno mensal <b>descolado da realidade</b> porque a fórmula '
                    'usa a taxa contratada linearizada, não o preço de mercado do título<br><br>'
                    '• Não diferencia ativos com <b>risco de crédito</b> distintos — um CDB de banco grande '
                    'e uma debênture de empresa pequena recebem o mesmo tratamento'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

        with st.expander("Rendimento do Portfólio e Benchmarking"):
            st.markdown(
                "Após calcular os retornos individuais, o sistema consolida todas as posições em um "
                "**retorno ponderado do portfólio** e compara o resultado com os principais benchmarks de mercado."
            )

            _bench_card = "background-color:#404040;border-radius:10px;padding:1.2rem;color:#f0f0f0;margin-bottom:1rem;min-height:280px;"
            _bp1, _bp2, _bp3 = st.columns(3)

            with _bp1:
                st.markdown(
                    f'<div style="{_bench_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Retorno Ponderado</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Consolida todos os ativos em um retorno único:<br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'peso_i = valor_posição_i / Σ valor_posição</code><br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'contribuição_i = peso_i × retorno_mês_i</code><br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'retorno_portfólio = Σ contribuição_i</code><br><br>'
                    'Também identifica os <b>top 3 contribuidores</b> e <b>top 3 detratores</b> do mês.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'O peso de cada ativo é proporcional ao seu valor na carteira.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _bp2:
                st.markdown(
                    f'<div style="{_bench_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Alfas vs. Benchmarks</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Compara o retorno do portfólio com 3 benchmarks:<br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Alfa CDI = retorno_portfólio − CDI_mês</code><br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Retorno real = ((1+ret/100) / (1+IPCA/100) − 1) × 100</code><br><br>'
                    '<code style="background:#333;padding:2px 6px;border-radius:3px;font-size:0.82rem;">'
                    'Alfa ações = retorno_classe_ações − IBOV_mês</code><br><br>'
                    'O alfa de ações só aparece se o cliente tem ações na carteira.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'Positivo = superou o benchmark. Negativo = ficou abaixo.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

            with _bp3:
                st.markdown(
                    f'<div style="{_bench_card}">'
                    f'<p style="font-weight:700;color:{colors.accent};margin:0 0 0.5rem 0;text-align:center;">Benchmarks Utilizados</p>'
                    '<p style="font-size:0.88rem;line-height:1.6;margin:0 0 0.8rem 0;">'
                    'Cada comparação usa o benchmark mais relevante:<br><br>'
                    '• <b>CDI mensal</b> — referência para o portfólio total e para a renda fixa<br>'
                    '• <b>IPCA mensal</b> — referência de inflação para medir ganho real de poder de compra<br>'
                    '• <b>IBOVESPA mensal</b> — referência para a classe de ações/FIIs<br><br>'
                    'No ranking de ativos por classe (Rivet), o benchmark acumulado 12 meses é usado: '
                    '<b>CDI 12m</b> para caixa, renda fixa e multimercado; <b>IBOVESPA 12m</b> para renda variável.'
                    '</p>'
                    f'<p style="font-size:0.82rem;color:#aaa;margin:0;border-top:1px solid #555;padding-top:0.5rem;">'
                    'A Selic aparece nos indicadores mas não é usada como benchmark de comparação direta.'
                    '</p></div>',
                    unsafe_allow_html=True,
                )

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
        with st.expander("Estrutura das Tabelas (Supabase)"):
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
  },
  "clientes": {
    "primary_key": "id (uuid)",
    "columns": { "nome": "text", "perfil_de_risco": "text (conservador/moderado/arrojado/agressivo)" }
  }
}
```
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
