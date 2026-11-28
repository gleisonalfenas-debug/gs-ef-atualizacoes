"""Gera as tabelas de sugestão do NFE Pro Web a partir das fontes oficiais.
- Anexos da LC 214/2025 (NCM) e cClassTrib: API pública do SVRS (Conformidade Fácil).
- CEST x NCM (Convênio ICMS 142/2018): base aberta lumina76-fiscal-data.
Se uma fonte falhar ou vier incompleta, o arquivo anterior é mantido (nada quebra no sistema)."""
import json, sys, os, re, csv, io, ssl, urllib.request, datetime, collections, traceback
saida = sys.argv[1]; os.makedirs(saida, exist_ok=True)
diag = []
def log(*a): diag.append(" ".join(str(x) for x in a)); print(*a)
def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NFEPro-tabelas", "Accept": "application/json,text/csv,*/*"})
    with urllib.request.urlopen(req, timeout=120) as r: return r.read()
def k(d, *nomes):
    low = {x.lower(): x for x in d}
    for n in nomes:
        if n.lower() in low: return d[low[n.lower()]]
    return None
hoje = datetime.date.today().isoformat()

# ---------------- cClassTrib + anexos
try:
    ct = json.loads(baixar("https://cff.svrs.rs.gov.br/api/v1/consultas/classTrib"))
    an = json.loads(baixar("https://cff.svrs.rs.gov.br/api/v1/consultas/anexos"))
    log("classTrib:", type(ct).__name__, len(ct), "chaves CST:", list(ct[0].keys()) if ct else "-")
    if ct and ct[0].get("classificacoesTributarias"): log("chaves cClassTrib:", list(ct[0]["classificacoesTributarias"][0].keys()))
    log("exemplo cClassTrib:", json.dumps((ct[1] if len(ct) > 1 else ct[0]).get("classificacoesTributarias", [{}])[0], ensure_ascii=False)[:1500])
    log("anexos:", len(an), "chaves:", list(an[0].keys()) if an else "-"); log("exemplo anexo:", json.dumps(an[0], ensure_ascii=False)[:800])
    cc, porAnexo = {}, collections.defaultdict(list)
    for g in ct:
        cst = str(k(g, "CST", "codCST", "cst") or "").zfill(3)
        for c in g.get("classificacoesTributarias") or []:
            cod = str(k(c, "cClassTrib", "codClassTrib") or "")
            if not re.fullmatch(r"\d{6}", cod): continue
            fim = k(c, "FimVigencia", "dFimVig")
            if fim and str(fim)[:10] < hoje: continue
            nfe = k(c, "indNFe", "IndNFe", "ind_NFe")
            if nfe is not None and str(nfe).lower() in ("0", "false", "n", "nao", "não"): continue
            nome = str(k(c, "NomecClassTrib", "nomeClassTrib", "DescricaoClassTrib", "descrClassTrib", "Descricao") or "").strip()
            red = k(c, "pRedIBS", "PercRedIBS", "percentualReducaoIBS") or 0
            anexo = k(c, "Anexo", "nroAnexo", "numAnexo")
            cc[cod] = [cst, nome[:160], float(red or 0), str(anexo) if anexo not in (None, "") else None]
            if anexo not in (None, ""):
                for a in re.findall(r"\d+", str(anexo)): porAnexo[a].append(cod)
    log("cClassTrib válidos NF-e:", len(cc), "anexos ligados:", {a: v for a, v in list(porAnexo.items())[:20]})
    ncm = collections.defaultdict(list); pref = collections.defaultdict(list)
    for r in an:
        if str(k(r, "TipoNomenclatura") or "").upper() != "NCM": continue
        fim = k(r, "dthFimVig")
        if fim and str(fim)[:10] < hoje: continue
        cod = re.sub(r"\D", "", str(k(r, "codNcmNbs") or "")); a = str(k(r, "nroAnexo") or "")
        if not cod: continue
        for c in porAnexo.get(a, []):
            (ncm if len(cod) == 8 else pref)[cod].append(c) if c not in (ncm if len(cod) == 8 else pref)[cod] else None
    log("NCM 8 dígitos:", len(ncm), "prefixos:", len(pref))
    if len(cc) >= 80 and "000001" in cc and len(ncm) + len(pref) >= 800:
        json.dump({"fonte": "SVRS Conformidade Fácil (tabela oficial cClassTrib e anexos da LC 214/2025)", "atualizado_em": hoje, "c": cc, "n": ncm, "p": pref},
                  open(f"{saida}/rtc_ncm.json", "w"), ensure_ascii=False, separators=(",", ":"))
        log("rtc_ncm.json GRAVADO")
    else: log("rtc_ncm.json NÃO gravado (dados incompletos) — mantido o anterior")
except Exception: log("ERRO cClassTrib:", traceback.format_exc()[-1500:])

# ---------------- CEST
try:
    base = "https://raw.githubusercontent.com/servostecnologia-dev/lumina76-fiscal-data/main/cest/"
    desc = {r["cest_normalizado"]: [r["descricao"][:140], r["segmento"]] for r in csv.DictReader(io.StringIO(baixar(base + "cest_atual.csv").decode("utf-8")), delimiter=";")}
    cest = collections.defaultdict(list)
    for r in csv.DictReader(io.StringIO(baixar(base + "cest_ncm_atual.csv").decode("utf-8")), delimiter=";"):
        p = re.sub(r"\D", "", r["ncm_sh"])
        if p and r["cest_normalizado"] not in cest[p]: cest[p].append(r["cest_normalizado"])
    log("CEST:", len(desc), "prefixos NCM:", len(cest))
    if len(desc) >= 800 and len(cest) >= 600:
        json.dump({"fonte": "Convênio ICMS 142/2018 (CONFAZ)", "atualizado_em": hoje, "d": desc, "n": cest}, open(f"{saida}/cest_ncm.json", "w"), ensure_ascii=False, separators=(",", ":"))
        log("cest_ncm.json GRAVADO")
    else: log("cest_ncm.json NÃO gravado — mantido o anterior")
except Exception: log("ERRO CEST:", traceback.format_exc()[-1500:])
open(f"{saida}/diagnostico.txt", "w").write(hoje + "\n" + "\n".join(diag) + "\n")
