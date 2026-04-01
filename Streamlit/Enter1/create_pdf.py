# -*- coding: utf-8 -*-
from fpdf import FPDF


def gerar_pdf(partes: list) -> bytes:
    """Gera o PDF do relatório a partir do array de 19 partes."""
    (mes, nome_cliente, perfil_risco, titulo,
     titulo_selic, paragrafo_selic,
     titulo_ipca, paragrafo_ipca,
     titulo_cambio, paragrafo_cambio,
     titulo_pib, paragrafo_pib,
     titulo_credito, paragrafo_credito,
     titulo_fiscal, paragrafo_fiscal,
     titulo_externo, paragrafo_externo,
     parag) = partes

    pdf = FPDF()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ── Cabeçalho ────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "CARTA DE ANÁLISE DE PORTFÓLIO", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, mes, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, f"Cliente: {nome_cliente}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Perfil de Risco: {perfil_risco}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

    # ── Título geral do cenário ───────────────────────────────────────────────
    pdf.set_font("Helvetica", "BI", 12)
    pdf.multi_cell(0, 7, titulo)
    pdf.ln(3)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

    # ── Blocos por indicador ──────────────────────────────────────────────────
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
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 7, titulo_bloco)
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, paragrafo_bloco)
        pdf.ln(4)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)

    # ── Recomendação de ações ─────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Recomendação de ações", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, parag)
    pdf.ln(6)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

    # ── Disclaimer ───────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(130, 130, 130)
    pdf.multi_cell(
        0, 5,
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
