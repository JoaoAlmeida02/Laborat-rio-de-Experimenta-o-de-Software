"""Testa quais APIs da RQ3 trazem a data da correção do PHP2Shell (LAB05S01, João).

Para cada fonte com API (OSV, Debian, Ubuntu, Red Hat, Fedora, NVD, php.net) faz UMA
consulta, no máximo 1 requisição por segundo, e indica:
  - se a API respondeu (HTTP e JSON válido);
  - se a resposta cita o CVE / o PHP;
  - se há alguma DATA de correção que dê para usar na S02 (campo e valor).

Nenhum exploit é executado: só leitura de bases públicas de segurança.

Saída: dados/rq3_teste_apis.csv  (uma fonte por linha) e um resumo no terminal.

Uso (a partir da pasta LAB05):
    python scripts/testar_fontes_rq3.py
"""
import csv
import json
import time
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "dados" / "rq3_teste_apis.csv"

USER_AGENT = "lab05-experimento-academico"
PAUSA_S = 1.0
TIMEOUT_S = 30
CVE = "CVE-2026-109618"
CVE_2 = "CVE-2026-109619"

# nome -> (url, o que procurar). A URL do Debian é o JSON gigante com todas as CVEs.
FONTES = {
    "OSV": f"https://api.osv.dev/v1/vulns/{CVE}",
    "Debian": "https://security-tracker.debian.org/tracker/data/json",
    "Ubuntu": f"https://ubuntu.com/security/cves/{CVE}.json",
    "Red Hat": f"https://access.redhat.com/hydra/rest/securitydata/cve/{CVE}.json",
    "NVD": f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={CVE}",
    "Fedora (Bodhi)": f"https://bodhi.fedoraproject.org/updates/?cves={CVE}",
    "php.net": "https://www.php.net/releases/index.php?json&version=8.4&max=3",
}

CAMPOS = ["fonte", "url", "http", "json_valido", "cita_cve", "tem_data", "campo_data", "exemplo_data", "tamanho_kb", "veredito", "observacao"]


def _menor(datas):
    datas = sorted(d for d in datas if d)
    return datas[0] if datas else ("", "")


def extrair_correcao(nome, dados):
    """Devolve (campo, data) da DATA DE CORREÇÃO se a fonte a traz; ("", "") se não traz.

    Conferido na S01 olhando as respostas reais de cada API (ver docs/proposta.md).
    """
    if nome == "Red Hat":  # um aviso (RHSA) por produto; a 1ª correção é a menor data
        datas = [(a.get("release_date", ""), a.get("advisory", "")) for a in dados.get("affected_release", [])]
        d, adv = _menor(datas)
        return ("affected_release[].release_date", d) if d else ("", "")
    if nome == "Ubuntu":  # um aviso (USN) por pacote/versão; vale a menor data de publicação
        d, usn = _menor([(n.get("published", ""), n.get("id", "")) for n in dados.get("notices", [])])
        return ("notices[].published", d) if d else ("", "")
    if nome == "Fedora (Bodhi)":
        d, _ = _menor([(u.get("date_stable") or u.get("date_submitted") or "", u.get("alias", "")) for u in dados.get("updates", [])])
        return ("updates[].date_stable", d) if d else ("", "")
    return "", ""


def avisos_no_osv(dados):
    """O OSV não traz a data da correção, mas lista os avisos de cada distribuidor (campo related)."""
    familias = {"ALSA": "AlmaLinux", "RLSA": "Rocky", "SUSE-SU": "SUSE", "openSUSE-SU": "openSUSE", "DSA": "Debian", "DLA": "Debian", "USN": "Ubuntu", "ALPINE": "Alpine"}
    achadas = {}
    for rel in dados.get("related", []) + dados.get("aliases", []):
        for prefixo, nome in familias.items():
            if rel.startswith(prefixo):
                achadas[nome] = achadas.get(nome, 0) + 1
    return achadas


def classificar(http, json_valido, cita_cve, tem_data):
    if http is None or http >= 400:
        return "nao_serve"
    if not json_valido:
        return "nao_serve"
    if cita_cve and tem_data:
        return "serve"
    if cita_cve:
        return "parcial"  # cita o CVE mas sem data de correção
    return "sem_o_cve"  # respondeu mas não conhece o CVE (ainda não catalogado ou fora do escopo)


def testar(nome, url, sessao):
    linha = {c: "" for c in CAMPOS}
    linha.update(fonte=nome, url=url, tamanho_kb="")
    try:
        r = sessao.get(url, timeout=TIMEOUT_S)
    except requests.RequestException as e:
        linha.update(http="erro", veredito="nao_serve", observacao=f"{type(e).__name__}: {e}"[:200])
        return linha
    linha["http"] = r.status_code
    linha["tamanho_kb"] = round(len(r.content) / 1024, 1)
    try:
        dados = r.json()
        linha["json_valido"] = "sim"
    except ValueError:
        linha["json_valido"] = "nao"
        linha["veredito"] = classificar(r.status_code, False, False, False)
        linha["observacao"] = "resposta não é JSON (talvez bloqueio a clientes automatizados)"
        return linha

    texto = json.dumps(dados)
    cita = CVE in texto or CVE_2 in texto
    achados = []
    campo = exemplo = ""
    if nome == "Debian":  # JSON enorme: só interessa o trecho do PHP; traz versão corrigida, não data
        bloco = {pacote: dados.get(pacote, {}) for pacote in ("php8.4", "php8.2", "php7.4", "php")}
        cita = CVE in json.dumps(bloco)
        linha["observacao"] = "traz a versão corrigida por release, não a data: cruzar com o changelog do pacote (ou usar o OSV/DSA)"
    elif nome == "NVD":  # data de publicação do CVE = referência, não correção por distribuidor
        pub = dados.get("vulnerabilities", [{}])[0].get("cve", {}).get("published", "") if cita else ""
        linha["observacao"] = "só a data de publicação do CVE (referência), não a correção por distribuidor"
        campo, exemplo = ("vulnerabilities[0].cve.published", pub) if pub else ("", "")
        achados = [pub] if pub else []
        linha["veredito"] = "referencia" if pub else "sem_o_cve"
    elif nome == "OSV":
        pub = dados.get("published", "")
        avisos = avisos_no_osv(dados)
        linha["observacao"] = (
            f"'published' ({pub[:10]}) é a data do CVE, não da correção; mas lista avisos de: "
            + ", ".join(f"{k} ({v})" for k, v in sorted(avisos.items()))
            + ". Dá para buscar a data de cada aviso pelo ID em api.osv.dev/v1/vulns/<ID>"
        ) if avisos else f"'published' ({pub[:10]}) é a data do CVE, não da correção"
        campo, exemplo = "related[] (IDs dos avisos)", ", ".join(sorted(avisos))
        achados = [pub] if avisos else []
    elif nome == "php.net":
        cita = True
        linha["observacao"] = "referência (T0): o release 8.4.27 tem a data de 21/10/2026; checar a data no campo date do release"
    else:
        campo, exemplo = extrair_correcao(nome, dados) if cita else ("", "")
        achados = [exemplo] if exemplo else []
    linha.update(cita_cve="sim" if cita else "nao", tem_data="sim" if achados else "nao", campo_data=campo, exemplo_data=exemplo)
    if linha.get("veredito") != "referencia":
        linha["veredito"] = classificar(r.status_code, True, cita, bool(achados))
    if nome == "OSV" and linha["veredito"] == "serve":
        linha["veredito"] = "parcial"  # indica quem corrigiu, mas a data exige uma 2ª consulta por aviso
    return linha


def main():
    sessao = requests.Session()
    sessao.headers["User-Agent"] = USER_AGENT
    linhas = []
    for i, (nome, url) in enumerate(FONTES.items()):
        if i:
            time.sleep(PAUSA_S)
        print(f"[{i + 1}/{len(FONTES)}] {nome} ...", flush=True)
        linhas.append(testar(nome, url, sessao))

    SAIDA.parent.mkdir(exist_ok=True)
    with SAIDA.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(linhas)

    print(f"\n{'fonte':<16}{'http':<6}{'json':<6}{'cve':<5}{'data':<6}veredito")
    for l in linhas:
        print(f"{l['fonte']:<16}{str(l['http']):<6}{l['json_valido']:<6}{l['cita_cve']:<5}{l['tem_data']:<6}{l['veredito']}")
    print(f"\nSalvo em {SAIDA}")


if __name__ == "__main__":
    main()
