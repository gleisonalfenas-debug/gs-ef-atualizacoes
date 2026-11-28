"""Gera as tabelas de sugestão do NFE Pro Web (roda toda semana no GitHub Actions).
- cClassTrib (descrição, CST, redução, vigência, uso na NF-e): Calculadora de Tributos oficial (RFB/CGIBS, dados abertos).
- NCM x anexos da LC 214/2025: tabelas/base_ncm_anexos.json (os anexos só mudam por lei); códigos que saírem da
  tabela oficial são retirados automaticamente das sugestões.
- CEST x NCM (Convênio ICMS 142/2018): base aberta lumina76-fiscal-data.
Se uma fonte falhar ou vier incompleta, o arquivo anterior é mantido (nada quebra no sistema)."""
import json, sys, os, re, csv, io, urllib.request, datetime, collections, traceback
saida = sys.argv[1]; os.makedirs(saida, exist_ok=True)
diag = []
def log(*a): diag.append(" ".join(str(x) for x in a)); print(*a)
def baixar(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "NFEPro-tabelas", "Accept": "application/json,text/csv"}), timeout=120) as r: return r.read()
hoje = datetime.date.today().isoformat()
CALC = "https://consumo.tributos.gov.br/servico/calcular-tributos-consumo/api/calculadora/dados-abertos/"

try:
    versao = json.loads(baixar(CALC + "versao"))
    cls = json.loads(baixar(CALC + f"classificacoes-tributarias/cbs-ibs?data={hoje}"))
    fun = json.loads(baixar(CALC + f"fundamentacoes-legais?data={hoje}"))
    log("calculadora:", versao.get("versaoDb"), versao.get("dataVersaoDb"), "| classificações:", len(cls), "| fundamentações:", len(fun))
    log("chaves:", sorted(cls[0].keys()))
    cst = {f.get("codigoClassificacaoTributaria"): f.get("codigoSituacaoTributaria") for f in fun}
    cc = {}
    for c in cls:
        cod = str(c.get("codigo") or "")
        dfe = [str(t.get("sigla") or t.get("descricao") or "") for t in (c.get("tiposDfeClassificacao") or [])]
        if not re.fullmatch(r"\d{6}", cod) or not any(re.fullmatch(r"NF-?e", d, re.I) or d == "Nota Fiscal Eletrônica" for d in dfe): continue
        red = max(float(c.get("percentualReducaoCbs") or 0), float(c.get("percentualReducaoIbsUf") or 0))
        cc[cod] = [str(cst.get(cod) or cod[:3]), str(c.get("descricao") or "").strip()[:160], red, None]
    base = json.load(open("tabelas/base_ncm_anexos.json", encoding="utf-8"))
    for cod, v in base["c"].items():
        if cod in cc: cc[cod][3] = v[3]
    # Códigos que só valem conforme QUEM compra (órgão público, produtor rural): nunca são a sugestão principal.
    ESPEC = {"200038": "venda de insumo agropecuário/aquícola (Anexo IX) para produção", "200005": "venda a órgão público ou entidade de saúde imune",
             "200043": "venda à administração pública (soberania e segurança)", "200011": "venda a órgão público ou entidade de saúde imune",
             "200008": "venda a órgão público ou entidade imune"}
    for cod, v in cc.items():
        d = v[1].lower()
        if cod not in ESPEC and ("administração pública" in d or "órgãos da" in d or "adquirid" in d and "imune" in d): ESPEC[cod] = "venda a órgão público ou entidade imune"
    ordem = lambda x: (x in ESPEC, -cc[x][2])          # gerais primeiro; maior redução antes
    ncm = {n: sorted([x for x in l if x in cc], key=ordem) for n, l in base["n"].items()}; ncm = {n: l for n, l in ncm.items() if l}
    fora = sorted({x for l in base["n"].values() for x in l} - set(cc))
    log("cClassTrib válidos na NF-e hoje:", len(cc), "| NCMs com sugestão:", len(ncm), "| códigos da base que saíram da tabela oficial:", fora)
    if len(cc) >= 60 and "000001" in cc and len(ncm) >= 1000:
        json.dump({"fonte": f"Calculadora de Tributos oficial (base {versao.get('versaoDb')} de {versao.get('dataVersaoDb')}) e anexos da LC 214/2025",
                   "atualizado_em": hoje, "c": cc, "n": ncm, "e": {k: v for k, v in ESPEC.items() if k in cc}}, open(f"{saida}/rtc_ncm.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        log("rtc_ncm.json GRAVADO")
    else: log("rtc_ncm.json NÃO gravado (dados incompletos) — mantido o anterior")
except Exception: log("ERRO cClassTrib:", traceback.format_exc()[-1200:])

try:
    b = "https://raw.githubusercontent.com/servostecnologia-dev/lumina76-fiscal-data/main/cest/"
    desc = {r["cest_normalizado"]: [r["descricao"][:140], r["segmento"]] for r in csv.DictReader(io.StringIO(baixar(b + "cest_atual.csv").decode("utf-8")), delimiter=";")}
    cest = collections.defaultdict(list)
    for r in csv.DictReader(io.StringIO(baixar(b + "cest_ncm_atual.csv").decode("utf-8")), delimiter=";"):
        p = re.sub(r"\D", "", r["ncm_sh"])
        if p and r["cest_normalizado"] not in cest[p]: cest[p].append(r["cest_normalizado"])
    log("CEST:", len(desc), "| prefixos NCM:", len(cest))
    if len(desc) >= 800 and len(cest) >= 600:
        json.dump({"fonte": "Convênio ICMS 142/2018 (CONFAZ)", "atualizado_em": hoje, "d": desc, "n": cest}, open(f"{saida}/cest_ncm.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        log("cest_ncm.json GRAVADO")
    else: log("cest_ncm.json NÃO gravado — mantido o anterior")
except Exception: log("ERRO CEST:", traceback.format_exc()[-1200:])
open(f"{saida}/diagnostico.txt", "w", encoding="utf-8").write(hoje + "\n" + "\n".join(diag) + "\n")
