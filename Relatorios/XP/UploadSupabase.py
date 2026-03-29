"""
Upload dos relatórios XP para o Supabase:
- PDFs → Storage bucket 'relatorios-pdf'
- Metadados + TXT → tabela 'relatorios'
Pula arquivos já existentes (idempotente).
"""

import re
from pathlib import Path
from supabase import create_client

SUPABASE_URL = "https://kiwptwgbfywlgzkznmvz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtpd3B0d2diZnl3bGd6a3pubXZ6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQxOTI1NDIsImV4cCI6MjA4OTc2ODU0Mn0.KRbTDUZLhRFZQe1JpPT6HZ0AdxYmDZqgaPQEB6I57jw"
BUCKET      = "relatorios-pdf"

BASE_DIR = Path(__file__).parent
PDF_DIR  = BASE_DIR / "PDF"
TXT_DIR  = BASE_DIR / "TXT"

# Padrão: XP-Macro-Monthly-YYYY-MM.pdf
PATTERN = re.compile(r"XP-Macro-Monthly-(\d{4}-\d{2})\.pdf", re.IGNORECASE)


def parse_metadata(filename: str) -> dict | None:
    m = PATTERN.match(filename)
    if not m:
        return None
    return {
        "fonte": "XP",
        "tipo":  "macro_mensal",
        "mes":   m.group(1),
    }


def main():
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Meses já existentes no banco para evitar duplicatas
    existing = {
        r["mes"]
        for r in client.table("relatorios")
                        .select("mes")
                        .eq("fonte", "XP")
                        .eq("tipo", "macro_mensal")
                        .execute()
                        .data
    }

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    pending = [p for p in pdfs if (meta := parse_metadata(p.name)) and meta["mes"] not in existing]

    print(f"PDFs encontrados : {len(pdfs)}")
    print(f"Já no Supabase   : {len(existing)}")
    print(f"Pendentes        : {len(pending)}\n")

    if not pending:
        print("Nada a fazer.")
        return

    for i, pdf_path in enumerate(pending, 1):
        meta = parse_metadata(pdf_path.name)
        txt_path = TXT_DIR / pdf_path.with_suffix(".txt").name
        print(f"[{i}/{len(pending)}] {pdf_path.name} ...", end=" ", flush=True)

        try:
            # 1. Upload PDF para Storage
            storage_path = f"XP/{pdf_path.name}"
            with open(pdf_path, "rb") as f:
                client.storage.from_(BUCKET).upload(
                    storage_path,
                    f,
                    {"content-type": "application/pdf", "upsert": "true"},
                )
            pdf_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{storage_path}"

            # 2. Lê TXT
            conteudo = txt_path.read_text(encoding="utf-8") if txt_path.exists() else None

            # 3. Insere linha na tabela
            client.table("relatorios").insert({
                **meta,
                "conteudo_txt": conteudo,
                "pdf_url":      pdf_url,
            }).execute()

            print("OK")

        except Exception as e:
            print(f"ERRO: {e}")

    print("\nConcluído.")


if __name__ == "__main__":
    main()
