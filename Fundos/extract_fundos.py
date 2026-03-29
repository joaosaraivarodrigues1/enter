"""
extract_fundos.py — Importa o histórico de cotas de um fundo para o Supabase.

Uso:
    python extract_fundos.py "12.345.678/0001-90"

O CNPJ informado deve ser exatamente igual ao cadastrado em ativos_fundos.
O script normaliza o CNPJ só para comparar com os dados da CVM — o valor
armazenado no Supabase é sempre o original recebido como argumento.

Pré-requisito:
    Rodar download_cvm.py antes para ter os ZIPs em cvm/zips/.
"""

import os
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
ZIPS_DIR     = Path(__file__).parent / "cvm" / "zips"

# Aliases de colunas entre versões do CSV da CVM
COL_CNPJ  = ["CNPJ_FUNDO", "CNPJ_FUNDO_CLASSE"]
COL_DATA  = ["DT_COMPTC"]
COL_COTA  = ["VL_QUOTA"]


def normalizar_cnpj(cnpj: str) -> str:
    return re.sub(r"[.\-/\s]", "", cnpj).strip()


def encontrar_coluna(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    for c in candidatos:
        if c in df.columns:
            return c
    return None


def processar_zip(
    zip_path: Path,
    cnpj_original: str,
    cnpj_norm: str,
) -> list[dict]:
    try:
        with zipfile.ZipFile(zip_path) as z:
            csv_name = z.namelist()[0]
            with z.open(csv_name) as f:
                try:
                    df = pd.read_csv(f, sep=";", dtype=str, encoding="latin-1")
                except Exception:
                    # tenta UTF-8 para arquivos mais recentes
                    with z.open(csv_name) as f2:
                        df = pd.read_csv(f2, sep=";", dtype=str, encoding="utf-8")
    except Exception as e:
        print(f"  ⚠  erro ao abrir {zip_path.name}: {e}")
        return []

    col_cnpj = encontrar_coluna(df, COL_CNPJ)
    col_data = encontrar_coluna(df, COL_DATA)
    col_cota = encontrar_coluna(df, COL_COTA)

    if not all([col_cnpj, col_data, col_cota]):
        print(f"  ⚠  colunas não encontradas em {zip_path.name}")
        return []

    # Normaliza CNPJ do CSV só para comparação
    df["_cnpj_norm"] = df[col_cnpj].apply(
        lambda x: normalizar_cnpj(str(x)) if pd.notna(x) else ""
    )
    df_fundo = df[df["_cnpj_norm"] == cnpj_norm].copy()

    if df_fundo.empty:
        return []

    df_fundo[col_data] = pd.to_datetime(df_fundo[col_data], errors="coerce")
    df_fundo = df_fundo.dropna(subset=[col_data])
    df_fundo["_mes"] = df_fundo[col_data].dt.strftime("%Y-%m")

    # Último dia útil de cada mês
    idx = df_fundo.groupby("_mes")[col_data].idxmax()
    df_ultimo = df_fundo.loc[idx]

    registros = []
    for _, row in df_ultimo.iterrows():
        cota_str = str(row[col_cota]).replace(",", ".")
        try:
            cota = float(cota_str)
        except ValueError:
            continue
        registros.append({
            "cnpj":            cnpj_original,
            "mes":             row["_mes"],
            "cota_fechamento": cota,
        })

    return registros


def main():
    if len(sys.argv) < 2:
        print("Uso: python extract_fundos.py \"<CNPJ>\"")
        sys.exit(1)

    cnpj_original = sys.argv[1]
    cnpj_norm     = normalizar_cnpj(cnpj_original)

    zips = sorted(ZIPS_DIR.glob("inf_diario_fi_*.zip"))
    if not zips:
        print("Nenhum ZIP encontrado em cvm/zips/.")
        print("Execute primeiro: python download_cvm.py")
        sys.exit(1)

    print(f"CNPJ: {cnpj_original}  (normalizado: {cnpj_norm})")
    print(f"ZIPs encontrados: {len(zips)}\n")

    todos_registros: list[dict] = []
    for zip_path in zips:
        registros = processar_zip(zip_path, cnpj_original, cnpj_norm)
        if registros:
            print(f"  ok {zip_path.name}  ->  {len(registros)} mes(es)")
            todos_registros.extend(registros)

    if not todos_registros:
        print(f"\nNenhum dado encontrado para CNPJ {cnpj_original}.")
        print("Verifique se o CNPJ está correto e se os ZIPs cobrem o período.")
        sys.exit(1)

    print(f"\nTotal: {len(todos_registros)} meses. Enviando para o Supabase...")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase.table("cotas_fundos").upsert(
        todos_registros,
        on_conflict="cnpj,mes",
    ).execute()

    print(f"ok {len(todos_registros)} registros inseridos em cotas_fundos.")


if __name__ == "__main__":
    main()
