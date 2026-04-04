# -*- coding: utf-8 -*-
"""
Design System — inspirado no XP Trader (trader.xpi.com.br)

Arquivo central de tokens visuais. Toda estilização do app referencia este arquivo.
Para trocar o tema, basta alterar os valores aqui.
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple


# ─── Cores ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Colors:
    # Fundos
    bg_primary: str = "#121214"
    bg_secondary: str = "#1c1c1e"
    bg_tertiary: str = "#2c2c2e"

    # Accent
    accent: str = "#f5a623"
    accent_hover: str = "#d4911e"

    # Texto
    text_primary: str = "#ffffff"
    text_secondary: str = "#a1a1aa"
    text_muted: str = "#71717a"
    text_accent: str = "#f5a623"

    # Semânticas
    positive: str = "#22c55e"
    negative: str = "#ef4444"

    # Bordas
    border_default: str = "#2c2c2e"
    border_subtle: str = "#1c1c1e"

    # Cards
    card_bg: str = "#1c1c1e"
    card_border: str = "#2c2c2e"


# ─── Perfis de Risco ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProfileBadge:
    fg: str
    bg: str


PROFILE_BADGES: Dict[str, ProfileBadge] = {
    "Conservador": ProfileBadge("#22c55e", "#052e16"),
    "Moderado":    ProfileBadge("#3b82f6", "#0c1a3a"),
    "Arrojado":    ProfileBadge("#f5a623", "#3a2a00"),
    "Agressivo":   ProfileBadge("#ef4444", "#3a0c0c"),
}

PROFILE_BADGE_FALLBACK = ProfileBadge("#71717a", "#1c1c1e")


# ─── Tipografia ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Typography:
    font_family: str = "'Roboto', sans-serif"
    font_family_heading: str = "'Roboto Slab', serif"

    size_xs: str = "0.75rem"
    size_sm: str = "0.875rem"
    size_base: str = "1rem"
    size_md: str = "1.125rem"
    size_lg: str = "1.25rem"
    size_xl: str = "1.5rem"
    size_2xl: str = "2rem"
    size_hero: str = "3rem"
    size_stat_label: str = "1.375rem"
    size_stat_value: str = "3.5rem"

    weight_normal: int = 400
    weight_medium: int = 500
    weight_semibold: int = 600
    weight_bold: int = 700

    ls_tight: str = "-1px"
    ls_normal: str = "0.1px"
    ls_wide: str = "0.5px"
    ls_wider: str = "0.8px"

    lh_none: float = 1.0
    lh_tight: float = 1.1
    lh_normal: float = 1.5
    lh_relaxed: float = 1.6
    lh_loose: float = 1.7


# ─── Espaçamento ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Spacing:
    xs: str = "4px"
    sm: str = "8px"
    md: str = "16px"
    lg: str = "24px"
    xl: str = "32px"
    xxl: str = "48px"

    radius_sm: str = "8px"
    radius_md: str = "12px"
    radius_lg: str = "16px"


# ─── Charts (Plotly) ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Charts:
    height_main: int = 420
    height_secondary: int = 280
    line_width: float = 2.0

    line_colors: Tuple[str, ...] = (
        "#f5a623", "#3b82f6", "#22c55e",
        "#ef4444", "#a78bfa", "#7dd3fc",
    )
    accent_line: str = "#22c55e"
    accent_fill: str = "rgba(34,197,94,0.08)"

    hover_bg: str = "#1c1c1e"
    hover_text: str = "#ffffff"
    grid_color: str = "#2c2c2e"
    axis_line: str = "#2c2c2e"
    tick_color: str = "#71717a"
    tick_size: int = 12
    legend_size: int = 13
    font_size: int = 14

    def base_layout(self, height: int = None) -> dict:
        """Layout Plotly reutilizável. Retorna dict novo a cada chamada."""
        return dict(
            height=height or self.height_main,
            margin=dict(t=20, b=20, l=0, r=10),
            plot_bgcolor=colors.bg_primary,
            paper_bgcolor=colors.bg_primary,
            font=dict(color=colors.text_primary, size=self.font_size),
            legend=dict(
                orientation="h", y=-0.12,
                font=dict(size=self.legend_size, color=colors.text_primary),
            ),
            xaxis=dict(
                showgrid=False,
                tickfont=dict(size=self.tick_size, color=self.tick_color),
                linecolor=self.axis_line,
            ),
            yaxis=dict(
                autorange=True, showgrid=True,
                gridcolor=self.grid_color,
                tickfont=dict(size=self.tick_size, color=self.tick_color),
                linecolor=self.axis_line,
            ),
            hovermode="x unified",
            hoverlabel=dict(bgcolor=self.hover_bg, font_color=self.hover_text),
        )


# ─── Layouts (column ratios) ──────────────────────────────────────────────────

@dataclass(frozen=True)
class Layouts:
    header: list = field(default_factory=lambda: [1, 11])
    nav_bar: list = field(default_factory=lambda: [1, 1, 1, 1, 1, 3])
    sub_nav: list = field(default_factory=lambda: [3, 3, 3, 1])
    card_center: list = field(default_factory=lambda: [3, 4, 3])
    section_header: list = field(default_factory=lambda: [0.35, 7, 3])
    sidebar_main: list = field(default_factory=lambda: [4, 16])
    btn_wide: list = field(default_factory=lambda: [2, 8])
    title_btn: list = field(default_factory=lambda: [5, 1])
    market_split: list = field(default_factory=lambda: [1, 2])

    logo_width: int = 90
    footer_logo_width: int = 48


# ─── Instâncias singleton ─────────────────────────────────────────────────────

colors = Colors()
typography = Typography()
spacing = Spacing()
charts = Charts()
layouts = Layouts()


# ─── CSS Global ───────────────────────────────────────────────────────────────

GLOBAL_CSS = f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;600;700&family=Roboto+Slab:wght@600;700&display=swap"
      rel="stylesheet" media="print" onload="this.media='all'">
<style>
    html, body, [class*="css"] {{
        font-family: {typography.font_family};
    }}

    h1, h2, h3, h4, h5, h6 {{
        font-family: {typography.font_family_heading};
    }}

    button[data-baseweb="tab"] > div[data-testid="stMarkdownContainer"] > p {{
        font-size: {typography.size_lg} !important;
    }}

    ::-webkit-scrollbar {{ width: 6px; }}
    ::-webkit-scrollbar-track {{ background: {colors.bg_primary}; }}
    ::-webkit-scrollbar-thumb {{ background: {colors.bg_tertiary}; border-radius: 3px; }}

    .block-container {{
        padding-top: 2rem !important;
    }}

    [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMarkdownContainer"] b {{
        color: {colors.accent} !important;
    }}
</style>
"""


# ─── Componentes HTML reutilizáveis ───────────────────────────────────────────

class Components:

    @staticmethod
    def client_card(name: str, badge_text: str, badge_color: str) -> str:
        return f"""
<div style="background:{colors.card_bg};border:1px solid {colors.card_border};
border-radius:{spacing.radius_lg};padding:44px {spacing.xxl} 36px {spacing.xxl};
text-align:center;margin-bottom:{spacing.sm};">
  <h1 style="font-family:{typography.font_family_heading};font-size:{typography.size_hero};
  font-weight:{typography.weight_bold};margin:0 0 18px 0;
  letter-spacing:{typography.ls_tight};line-height:{typography.lh_tight};">{name}</h1>
  <span style="background:{badge_color};color:#fff;padding:6px {spacing.lg};
  border-radius:{spacing.radius_lg};font-size:{typography.size_base};
  font-weight:{typography.weight_bold};letter-spacing:{typography.ls_wide};
  text-transform:uppercase;">{badge_text}</span>
  <p style="font-size:{typography.size_xl};color:{colors.text_secondary};
  margin:22px 0 0 0;font-weight:{typography.weight_normal};
  letter-spacing:{typography.ls_normal};">Perfil de Investimento · XP Assessoria</p>
</div>"""

    @staticmethod
    def profile_section(title: str, color: str, content_html: str) -> str:
        return f"""
<div style="margin-bottom:28px;">
  <p style="font-size:{typography.size_md};font-weight:{typography.weight_bold};color:{color};
  text-transform:uppercase;letter-spacing:{typography.ls_wider};margin:0 0 {spacing.md} 0;
  border-left:3px solid {color};padding-left:10px;">{title}</p>
  {content_html}
</div>"""

    @staticmethod
    def profile_item(subtitle: str, text: str) -> str:
        return f"""
  <p style="font-size:{typography.size_base};font-weight:{typography.weight_semibold};
  color:{colors.text_secondary};margin:{spacing.md} 0 {spacing.xs} 0;">{subtitle}</p>
  <p style="font-size:{typography.size_sm};color:{colors.text_muted};
  line-height:{typography.lh_loose};margin:0;">{text}</p>"""

    @staticmethod
    def index_stat(label: str, value: str) -> str:
        return f"""
<div style="padding:{spacing.lg} 0 {spacing.md} 0;border-bottom:1px solid {colors.border_default};">
  <div style="font-size:{typography.size_stat_label};color:{colors.text_secondary};
  font-weight:{typography.weight_medium};margin-bottom:{spacing.xs};">{label}</div>
  <div style="font-size:{typography.size_stat_value};font-weight:{typography.weight_bold};
  line-height:{typography.lh_none};">{value}</div>
</div>"""

    @staticmethod
    def section_label(label: str, count: str, total: str, pct: str) -> str:
        return f"""
<p style="font-size:{typography.size_xl};font-weight:{typography.weight_normal};
margin:0;padding:{spacing.xs} 0">{label}<span style="font-size:{typography.size_base};
color:{colors.text_secondary};margin-left:2.5rem">{count} posições</span></p>"""

    @staticmethod
    def section_total(total: float, pct: float) -> str:
        return f"""
<p style="text-align:right;font-size:{typography.size_md};font-weight:{typography.weight_normal};
margin:0;padding:{spacing.xs} 0">R$ {total:,.2f}&ensp;&ensp;{pct:.1f}%</p>"""

    @staticmethod
    def footer(text: str, logo_b64: str) -> str:
        return f"""
<div style="text-align:center;color:{colors.text_primary};font-size:{typography.size_xs};
padding:{spacing.xs} 0 {spacing.sm} 0;line-height:{typography.lh_relaxed};">
  {text}
</div>
<div style="text-align:center;padding:0 0 20px 0;">
  <img src="data:image/png;base64,{logo_b64}" width="{layouts.footer_logo_width}" style="opacity:1;" />
</div>"""


components = Components()
