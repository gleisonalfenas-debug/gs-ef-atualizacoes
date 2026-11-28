"""Verifica quais fontes oficiais de dados abertos respondem a partir do GitHub (registro em sonda.txt)."""
import urllib.request, sys
B = "https://consumo.tributos.gov.br/servico/calcular-tributos-consumo/api/calculadora/dados-abertos/"
U = [B + "versao", B + "classificacoes-tributarias/cbs-ibs?data=2026-11-28", B + "fundamentacoes-legais?data=2026-11-28"]
out = []
for u in U:
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "NFEPro-tabelas", "Accept": "application/json"}), timeout=60) as r:
            b = r.read(); out.append(f"{r.status} {len(b)} {u}\n   {b[:700]!r}")
    except Exception as e: out.append(f"ERRO {e} {u}")
open(sys.argv[1] + "/sonda.txt", "w").write("\n".join(out) + "\n")
