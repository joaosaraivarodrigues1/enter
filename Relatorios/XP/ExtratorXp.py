"""
Extração de PDFs para TXT usando PyMuPDF com ordenação por blocos.
- Lê PDFs de: Relatorios/XP/PDF/
- Salva TXTs em: Relatorios/XP/TXT/
- Extrai apenas PDFs que ainda não têm TXT correspondente
"""

import fitz  # pymupdf
from pathlib import Path

BASE_DIR   = Path(__file__).parent
PDF_DIR    = BASE_DIR / "PDF"
TXT_DIR    = BASE_DIR / "TXT"


def extract_pdf(pdf_path: Path) -> str:
    """Extrai texto de um PDF ordenando blocos por posição (Y, X).
    Resolve o problema de colunas misturadas em relatórios de 2 colunas."""
    doc = fitz.open(pdf_path)
    pages_text = []

    for page in doc:
        blocks = page.get_text("blocks")
        # Filtra blocos de texto (type == 0) e ordena por linha depois por coluna
        text_blocks = [b for b in blocks if b[6] == 0]
        text_blocks.sort(key=lambda b: (round(b[1] / 10), b[0]))

        page_text = "\n".join(b[4].strip() for b in text_blocks if b[4].strip())
        pages_text.append(page_text)

    doc.close()
    return "\n\n---\n\n".join(pages_text)


def main():
    TXT_DIR.mkdir(exist_ok=True)

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"Nenhum PDF encontrado em: {PDF_DIR}")
        return

    pending = [p for p in pdfs if not (TXT_DIR / p.with_suffix(".txt").name).exists()]

    print(f"PDFs encontrados : {len(pdfs)}")
    print(f"Já extraídos     : {len(pdfs) - len(pending)}")
    print(f"Pendentes        : {len(pending)}\n")

    if not pending:
        print("Nada a fazer — todos os PDFs já têm TXT correspondente.")
        return

    for i, pdf_path in enumerate(pending, 1):
        txt_path = TXT_DIR / pdf_path.with_suffix(".txt").name
        print(f"[{i}/{len(pending)}] {pdf_path.name} ...", end=" ", flush=True)
        try:
            text = extract_pdf(pdf_path)
            txt_path.write_text(text, encoding="utf-8")
            print("OK")
        except Exception as e:
            print(f"ERRO: {e}")

    print("\nConcluído.")


if __name__ == "__main__":
    main()
