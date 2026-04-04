# -*- coding: utf-8 -*-
from pathlib import Path
from fpdf import FPDF


_LOGO_PATH = Path(__file__).parent / "icone-XP-removebg-preview_preto.png"


def _limpar(texto: str) -> str:
    """Substitui caracteres fora do Latin-1 por equivalentes ASCII."""
    return (str(texto)
        .replace("\u2014", "-")   # em dash —
        .replace("\u2013", "-")   # en dash –
        .replace("\u2018", "'")   # '
        .replace("\u2019", "'")   # '
        .replace("\u201c", '"')   # "
        .replace("\u201d", '"')   # "
        .replace("\u2026", "...")  # …
        .replace("\u00b0", " graus")
    )


def gerar_pdf(partes: list) -> bytes:
    """Gera o PDF do relatório a partir do array de 19 partes. Máximo 2 páginas."""
    (mes, nome_cliente, perfil_risco, titulo,
     titulo_selic, paragrafo_selic,
     titulo_ipca, paragrafo_ipca,
     titulo_cambio, paragrafo_cambio,
     titulo_pib, paragrafo_pib,
     titulo_credito, paragrafo_credito,
     titulo_fiscal, paragrafo_fiscal,
     titulo_externo, paragrafo_externo,
     parag) = [_limpar(p) for p in partes]

    M = 12  # margem
    pdf = FPDF()
    pdf.set_margins(M, M, M)
    pdf.set_auto_page_break(auto=True, margin=M)
    pdf.add_page()

    line_right = 210 - M

    # ── Logo XP topo esquerdo ───────────────────────────────────────────────
    if _LOGO_PATH.exists():
        pdf.image(str(_LOGO_PATH), x=M, y=M, h=10)
    pdf.ln(12)

    # ── Cabeçalho ───────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "CARTA DE ANÁLISE DE PORTFÓLIO", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, mes, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, f"Cliente: {nome_cliente}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Perfil de Risco: {perfil_risco}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.line(M, pdf.get_y(), line_right, pdf.get_y())
    pdf.ln(3)

    # ── Título geral do cenário ─────────────────────────────────────────────
    pdf.set_font("Helvetica", "BI", 10)
    pdf.multi_cell(0, 5, titulo)
    pdf.ln(2)
    pdf.line(M, pdf.get_y(), line_right, pdf.get_y())
    pdf.ln(3)

    # ── Blocos por indicador ────────────────────────────────────────────────
    blocos = [
        (titulo_selic,   paragrafo_selic),
        (titulo_ipca,    paragrafo_ipca),
        (titulo_cambio,  paragrafo_cambio),
        (titulo_pib,     paragrafo_pib),
        (titulo_credito, paragrafo_credito),
        (titulo_fiscal,  paragrafo_fiscal),
        (titulo_externo, paragrafo_externo),
    ]

    for titulo_bloco, paragrafo_bloco in blocos:
        pdf.set_font("Helvetica", "B", 9)
        pdf.multi_cell(0, 5, titulo_bloco)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 8)
        pdf.multi_cell(0, 4.2, paragrafo_bloco)
        pdf.ln(2)
        pdf.line(M, pdf.get_y(), line_right, pdf.get_y())
        pdf.ln(3)

    # ── Recomendação de ações ───────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "Recomendação de ações", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4.2, parag)
    pdf.ln(3)
    pdf.line(M, pdf.get_y(), line_right, pdf.get_y())
    pdf.ln(3)

    # ── Disclaimer ──────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(130, 130, 130)
    pdf.multi_cell(
        0, 4,
        f"Este relatório foi gerado automaticamente com base no relatório macro "
        f"de referência do mês de {mes} e nas posições registradas na carteira do cliente."
    )

    return bytes(pdf.output())


def salvar_pdf_supabase(sb, cliente_id: str, mes: str, job_id: str, pdf_bytes: bytes) -> str:
    """Faz upload do PDF no Storage, salva a URL em recomendacoes e retorna a URL assinada."""
    path = f"{cliente_id}/{mes}/relatorio.pdf"

    sb.storage.from_("relatorios-pdf").upload(
        path,
        pdf_bytes,
        {"content-type": "application/pdf", "upsert": "true"},
    )

    signed = sb.storage.from_("relatorios-pdf").create_signed_url(path, 365 * 24 * 3600)
    url = signed["signedURL"]

    sb.table("recomendacoes").update({"pdf_url": url}).eq("job_id", job_id).execute()

    return url
