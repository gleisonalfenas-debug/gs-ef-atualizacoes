"""Verifica endpoints de dados abertos da Calculadora oficial (registro em sonda.txt)."""
import urllib.request, sys
B = "https://consumo.tributos.gov.br/servico/calcular-tributos-consumo/api/calculadora/dados-abertos/"
U = [B + "ncm?ncm=15079011&data=2026-11-28", B + "ncm/15079011?data=2026-11-28", B + "nomenclaturas?data=2026-11-28", B + "anexos?data=2026-11-28",
     B + "classificacoes-tributarias/ncm/15079011?data=2026-11-28", "https://consumo.tributos.gov.br/servico/calcular-tributos-consumo/api/v3/api-docs",
     "https://consumo.tributos.gov.br/servico/calcular-tributos-consumo/api/calculadora/v3/api-docs", "https://consumo.tributos.gov.br/servico/calcular-tributos-consumo/api/v2/api-docs"]
out = []
for u in U:
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "NFEPro-tabelas", "Accept": "application/json"}), timeout=60) as r:
            b = r.read(); out.append(f"{r.status} {len(b)} {u}\n   {b[:1500]!r}")
    except Exception as e: out.append(f"ERRO {e} {u}")
open(sys.argv[1] + "/sonda.txt", "w").write("\n".join(out) + "\n")
