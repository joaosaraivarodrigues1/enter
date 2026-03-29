"""
download_cvm.py — Baixa os ZIPs do Informe Diário de Fundos da CVM.

Uso:
    python download_cvm.py            # últimos 5 anos
    python download_cvm.py --anos 3   # últimos 3 anos

Os arquivos são salvos em cvm/zips/ e nunca sobrescritos se já existirem.
A CVM publica o arquivo de um mês com 1-2 meses de atraso — meses futuros
retornam 404 e são ignorados silenciosamente.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import requests

BASE_URL = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS"
ZIPS_DIR = Path(__file__).parent / "cvm" / "zips"


def meses_no_intervalo(anos: int) -> list[tuple[int, int]]:
    hoje = date.today()
    resultado = []
    ano, mes = hoje.year, hoje.month
    for _ in range(anos * 12):
        resultado.append((ano, mes))
        mes -= 1
        if mes == 0:
            mes = 12
            ano -= 1
    return resultado


def baixar(ano: int, mes: int) -> str:
    nome = f"inf_diario_fi_{ano}{mes:02d}.zip"
    destino = ZIPS_DIR / nome

    if destino.exists():
        return f"  já existe   {nome}"

    url = f"{BASE_URL}/{nome}"
    resp = requests.get(url, timeout=60, stream=True)

    if resp.status_code == 404:
        return f"  não publicado {nome}"
    resp.raise_for_status()

    with open(destino, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    kb = destino.stat().st_size // 1024
    return f"  baixado      {nome}  ({kb} KB)"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--anos", type=int, default=5)
    args = parser.parse_args()

    ZIPS_DIR.mkdir(parents=True, exist_ok=True)
    meses = meses_no_intervalo(args.anos)

    print(f"Verificando {len(meses)} meses ({args.anos} anos)...\n")

    for ano, mes in reversed(meses):
        try:
            print(baixar(ano, mes))
        except Exception as e:
            print(f"  erro         {ano}{mes:02d}  — {e}", file=sys.stderr)

    print("\nConcluído.")


if __name__ == "__main__":
    main()
