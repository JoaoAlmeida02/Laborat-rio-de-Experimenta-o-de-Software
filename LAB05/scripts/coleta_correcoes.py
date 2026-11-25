"""Coleta as datas em que cada distribuidor publicou a correção do PHP2Shell (LAB05S02, Lucas — RQ3).

Evento estudado: publicação da 1ª correção da CVE-2026-109618 por cada distribuidor.
A CVE-2026-109619 é registrada numa coluna extra. T0 = 21/10/2026 (correção no php.net).

Fontes automáticas (no máximo 1 requisição por segundo, User-Agent genérico):
- Ubuntu ............ ubuntu.com/security/cves/<CVE>.json          (notices[].published)
- Red Hat ........... access.redhat.com/hydra/rest/securitydata    (affected_release[].release_date)
- AlmaLinux, SUSE,
  openSUSE .......... api.osv.dev: IDs em related[] da CVE e depois a data (published) de cada aviso
- Rocky Linux ....... apollo.build.resf.org: o RLSA tem o mesmo número do RHSA do Red Hat
- Fedora ............ bodhi.fedoraproject.org: busca pelo título da versão corrigida (date_stable)

Fontes sem API: dados/rq3_correcoes_manual.csv (preenchido à mão, com link e data de acesso).

Entradas:  dados/rq3_fontes.csv, dados/rq3_correcoes_manual.csv
Saídas:    dados/rq3_bruto/*.json   respostas brutas das APIs (permite refazer tudo com --offline)
           dados/rq3_avisos.csv     um aviso de segurança por linha (fontes automáticas)
           dados/rq3_correcoes.csv  um distribuidor por linha, pronto para a análise de sobrevivência
                                    (tempo_dias + evento: 1 = corrigiu, 0 = censurado)

Uso (a partir da pasta LAB05):
    python scripts/coleta_correcoes.py                         # coleta e consolida
    python scripts/coleta_correcoes.py --offline               # só reprocessa dados/rq3_bruto/
    python scripts/coleta_correcoes.py --data-corte 2026-11-24 # fixa a data de corte da censura
"""
import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "dados"
BRUTO = DADOS / "rq3_bruto"
ARQ_FONTES = DADOS / "rq3_fontes.csv"
ARQ_MANUAL = DADOS / "rq3_correcoes_manual.csv"
ARQ_AVISOS = DADOS / "rq3_avisos.csv"
ARQ_SAIDA = DADOS / "rq3_correcoes.csv"

USER_AGENT = "lab05-experimento-academico"
PAUSA_S = 1.0
TIMEOUT_S = 60

T0 = date(2026, 10, 21)
CVE = "CVE-2026-109618"
CVE_2 = "CVE-2026-109619"
CVES = (CVE, CVE_2)
VERSOES_CORRIGIDAS = ["8.5.12", "8.4.27", "8.3.36", "8.2.35"]

# ids de dados/rq3_fontes.csv
ID_UBUNTU, ID_REDHAT, ID_SUSE, ID_FEDORA, ID_ROCKY, ID_ALMA = 2, 3, 4, 8, 9, 10
PREFIXOS_OSV = {"ALSA-": ID_ALMA, "SUSE-SU-": ID_SUSE, "openSUSE-SU-": ID_SUSE}

STATUS_PENDENTE_UBUNTU = {"needed", "pending", "deferred"}
ESTADO_PENDENTE_REDHAT = {"Affected", "Fix deferred", "Under investigation", "Will not fix"}

SITUACOES_NA_ANALISE = {"corrigido", "sem_correcao_publicada"}

URL_UBUNTU = "https://ubuntu.com/security/cves/{cve}.json"
URL_REDHAT = "https://access.redhat.com/hydra/rest/securitydata/cve/{cve}.json"
URL_OSV = "https://api.osv.dev/v1/vulns/{id}"
URL_ROCKY = "https://apollo.build.resf.org/api/v3/advisories/{id}"
URL_BODHI = "https://bodhi.fedoraproject.org/updates/?search=php-{versao}&rows_per_page=20"

CAMPOS_AVISOS = ["distribuidor_id", "distribuidor", "aviso", "data", "dias_desde_t0", "produto", "cves", "url"]
CAMPOS_SAIDA = [
    "id", "distribuidor", "grupo", "forma_coleta", "situacao",
    "data_primeira_correcao", "data_ultima_correcao", "precisao_data",
    "dias_ate_primeira_correcao", "dias_ate_ultima_correcao",
    "n_avisos", "avisos", "pendentes", "data_primeira_correcao_109619",
    "tempo_dias", "evento", "incluir_analise", "data_corte", "fonte_url", "observacao",
]


@dataclass(frozen=True)
class Aviso:
    distribuidor_id: int
    aviso: str
    data: date
    produto: str
    cves: frozenset
    url: str


# ----------------------------------------------------------------------------------------------
# Funções puras de extração (testadas em tests/test_coleta_correcoes.py)
# ----------------------------------------------------------------------------------------------

def para_data(texto):
    """'2026-10-21T13:56:19.5', '2026-10-21 16:40:54', '2026-10-22T00:08:23+00:00' -> date (dia em UTC)."""
    return date.fromisoformat(str(texto)[:10])


def cves_no_texto(objeto):
    texto = json.dumps(objeto)
    return frozenset(c for c in CVES if c in texto)


def avisos_ubuntu(dados, cve, url):
    return [
        Aviso(ID_UBUNTU, n["id"], para_data(n["published"]), n.get("title", ""), frozenset({cve}), url)
        for n in dados.get("notices", []) if n.get("id") and n.get("published")
    ]


def pendentes_ubuntu(dados):
    """Releases ainda sem correção (ignora a linha 'upstream', que não é uma release do Ubuntu)."""
    return sum(
        1 for pacote in dados.get("packages", []) for s in pacote.get("statuses", [])
        if s.get("status") in STATUS_PENDENTE_UBUNTU and s.get("release_codename") != "upstream"
    )


def avisos_redhat(dados, cve, url):
    return [
        Aviso(ID_REDHAT, a["advisory"], para_data(a["release_date"]), a.get("product_name", ""), frozenset({cve}), url)
        for a in dados.get("affected_release", []) if a.get("advisory") and a.get("release_date")
    ]


def pendentes_redhat(dados):
    return sum(1 for p in dados.get("package_state", []) if p.get("fix_state") in ESTADO_PENDENTE_REDHAT)


def ids_relacionados_osv(dados):
    """IDs de avisos de distribuidores (ALSA, SUSE-SU, openSUSE-SU) citados por uma CVE no OSV."""
    return [i for i in dados.get("related", []) if any(i.startswith(p) for p in PREFIXOS_OSV)]


def distribuidor_do_aviso_osv(aviso_id):
    # openSUSE-SU começa diferente de SUSE-SU, então a ordem do dicionário não importa
    for prefixo, dist in PREFIXOS_OSV.items():
        if aviso_id.startswith(prefixo):
            return dist
    return None


def aviso_osv(dados, url):
    """Um aviso do OSV (ex.: ALSA-2026:87070) -> Aviso, ou None se ele não corrige as CVEs estudadas."""
    dist = distribuidor_do_aviso_osv(dados.get("id", ""))
    cves = cves_no_texto(dados.get("upstream", []) + dados.get("aliases", []) + dados.get("related", []))
    if dist is None or not cves or not dados.get("published"):
        return None
    ecossistemas = sorted({a.get("package", {}).get("ecosystem", "") for a in dados.get("affected", [])} - {""})
    return Aviso(dist, dados["id"], para_data(dados["published"]), "; ".join(ecossistemas), cves, url)


def id_rocky(rhsa):
    """'RHSA-2026:87070' -> 'RLSA-2026:87070'"""
    return "RLSA" + rhsa[4:] if rhsa.startswith("RHSA") else None


def aviso_rocky(dados, url):
    adv = dados.get("advisory", dados)
    cves = cves_no_texto(adv.get("cves", []))
    if not cves or not adv.get("published_at"):
        return None
    produtos = sorted({
        re.sub(r"\s+(x86_64|aarch64|ppc64le|s390x|riscv64)$", "", p.get("name", "") if isinstance(p, dict) else str(p))
        for p in adv.get("affected_products", [])
    } - {""})
    return Aviso(ID_ROCKY, adv["name"], para_data(adv["published_at"]), "; ".join(produtos), cves, url)


def avisos_bodhi(dados, url):
    """Atualizações estáveis do pacote php no Fedora que citam as CVEs."""
    avisos = []
    for u in dados.get("updates", []):
        titulo = u.get("title", "")
        cves = cves_no_texto(u)
        if titulo.startswith("php-") and cves and u.get("date_stable"):
            release = u.get("release", {}).get("name", "")
            avisos.append(Aviso(ID_FEDORA, u["alias"], para_data(u["date_stable"]), f"{release} {titulo}", cves, url))
    return avisos


def unificar(avisos):
    """Junta avisos repetidos (ex.: a mesma USN aparece na consulta das duas CVEs)."""
    por_chave = {}
    for a in avisos:
        chave = (a.distribuidor_id, a.aviso, a.produto)
        if chave in por_chave:
            antigo = por_chave[chave]
            por_chave[chave] = Aviso(a.distribuidor_id, a.aviso, min(a.data, antigo.data), a.produto,
                                     antigo.cves | a.cves, antigo.url)
        else:
            por_chave[chave] = a
    return sorted(por_chave.values(), key=lambda a: (a.distribuidor_id, a.data, a.aviso, a.produto))


def linha_sobrevivencia(situacao, data_primeira, data_corte, t0=T0):
    """(tempo_dias, evento, incluir_analise) para a análise de Kaplan-Meier."""
    if situacao == "corrigido" and data_primeira:
        return (data_primeira - t0).days, 1, "sim"
    if situacao == "sem_correcao_publicada":
        return (data_corte - t0).days, 0, "sim"  # censurado: não corrigiu até a data de corte
    return "", "", "não"


def consolidar(fontes, avisos, pendentes, manual, data_corte, t0=T0):
    """Gera uma linha por distribuidor (ignora as fontes de referência)."""
    linhas, alertas = [], []
    for f in fontes:
        if f["grupo"] == "referencia":
            continue
        dist_id = int(f["id"])
        linha = {c: "" for c in CAMPOS_SAIDA}
        linha.update(id=dist_id, distribuidor=f["distribuidor"], grupo=f["grupo"], data_corte=data_corte)

        if f["forma_coleta"] == "api":
            dos_dist = [a for a in avisos if a.distribuidor_id == dist_id]
            da_cve = [a for a in dos_dist if CVE in a.cves]
            da_cve2 = [a for a in dos_dist if CVE_2 in a.cves]
            linha.update(forma_coleta="api", fonte_url=f["url_api"], pendentes=pendentes.get(dist_id, ""))
            if da_cve:
                primeira = min(a.data for a in da_cve)
                ultima = max(a.data for a in da_cve)
                ids = sorted({a.aviso for a in da_cve})
                linha.update(situacao="corrigido", data_primeira_correcao=primeira, data_ultima_correcao=ultima,
                             precisao_data="exata", n_avisos=len(ids), avisos=";".join(ids))
            else:
                linha.update(situacao="sem_correcao_publicada",
                             observacao="a API respondeu, mas nenhum aviso cita a CVE até a data de corte")
            if da_cve2:
                linha["data_primeira_correcao_109619"] = min(a.data for a in da_cve2)
            if dist_id in manual:
                alertas.append(f"{f['distribuidor']}: tem linha manual, mas a coleta automática prevalece")
        elif dist_id in manual:
            m = manual[dist_id]
            linha.update(
                forma_coleta="manual", situacao=m["situacao"], precisao_data=m["precisao_data"],
                data_primeira_correcao=m["data_primeira_correcao"], data_ultima_correcao=m["data_ultima_correcao"],
                avisos=m["avisos"], n_avisos=len([x for x in m["avisos"].split(";") if x]) or "",
                pendentes=m["pendentes"], fonte_url=m["url_evidencia"], observacao=m["observacao"],
            )
            for campo in ("data_primeira_correcao", "data_ultima_correcao"):
                if linha[campo]:
                    linha[campo] = date.fromisoformat(linha[campo])
        else:
            linha.update(forma_coleta=f["forma_coleta"], situacao="a_verificar",
                         observacao="sem coleta automática e sem linha em rq3_correcoes_manual.csv")

        for campo, campo_dias in (("data_primeira_correcao", "dias_ate_primeira_correcao"),
                                  ("data_ultima_correcao", "dias_ate_ultima_correcao")):
            d = linha[campo]
            if d:
                linha[campo_dias] = (d - t0).days
                if d < t0:
                    alertas.append(f"{f['distribuidor']}: {campo} {d} é anterior ao T0 ({t0})")
                if d > data_corte:
                    alertas.append(f"{f['distribuidor']}: {campo} {d} é posterior à data de corte ({data_corte})")

        primeira = linha["data_primeira_correcao"] or None
        linha["tempo_dias"], linha["evento"], linha["incluir_analise"] = linha_sobrevivencia(
            linha["situacao"], primeira, data_corte, t0)
        if linha["situacao"] not in SITUACOES_NA_ANALISE:
            alertas.append(f"{f['distribuidor']}: situação '{linha['situacao']}' fica fora da análise")
        linhas.append(linha)
    return linhas, alertas


# ----------------------------------------------------------------------------------------------
# Rede e cache
# ----------------------------------------------------------------------------------------------

class Cliente:
    """GET com User-Agent genérico, 1 req/s e cópia de cada resposta em dados/rq3_bruto/."""

    def __init__(self, offline=False, pasta=BRUTO):
        self.offline = offline
        self.pasta = pasta
        self.sessao = requests.Session()
        self.sessao.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        self._ultima = 0.0
        self.requisicoes = 0

    def json(self, url, nome):
        arquivo = self.pasta / (re.sub(r"[^A-Za-z0-9._-]", "_", nome) + ".json")
        if self.offline:
            if not arquivo.exists():
                print(f"   (offline) sem cache para {nome}")
                return None
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            return None if "_http_status" in dados else dados

        espera = PAUSA_S - (time.monotonic() - self._ultima)
        if espera > 0:
            time.sleep(espera)
        resposta = self.sessao.get(url, timeout=TIMEOUT_S)
        self._ultima = time.monotonic()
        self.requisicoes += 1
        self.pasta.mkdir(parents=True, exist_ok=True)
        if resposta.status_code == 404:
            arquivo.write_text(json.dumps({"_http_status": 404, "_url": url}), encoding="utf-8")
            return None
        resposta.raise_for_status()
        dados = resposta.json()
        arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
        return dados


def coletar_api(cliente):
    avisos, pendentes, relacionados = [], {}, set()

    for cve in CVES:
        print(f"Ubuntu, Red Hat e OSV: {cve}")
        url = URL_UBUNTU.format(cve=cve)
        dados = cliente.json(url, f"ubuntu_{cve}")
        if dados:
            avisos += avisos_ubuntu(dados, cve, url)
            if cve == CVE:
                pendentes[ID_UBUNTU] = pendentes_ubuntu(dados)

        url = URL_REDHAT.format(cve=cve)
        dados = cliente.json(url, f"redhat_{cve}")
        if dados:
            avisos += avisos_redhat(dados, cve, url)
            if cve == CVE:
                pendentes[ID_REDHAT] = pendentes_redhat(dados)

        dados = cliente.json(URL_OSV.format(id=cve), f"osv_{cve}")
        if dados:
            relacionados.update(ids_relacionados_osv(dados))

    print(f"OSV: {len(relacionados)} avisos de AlmaLinux / SUSE / openSUSE")
    for aviso_id in sorted(relacionados):
        url = URL_OSV.format(id=aviso_id)
        dados = cliente.json(url, f"osv_{aviso_id}")
        a = aviso_osv(dados, url) if dados else None
        if a:
            avisos.append(a)

    rhsa = sorted({a.aviso for a in avisos if a.distribuidor_id == ID_REDHAT})
    print(f"Rocky: {len(rhsa)} avisos equivalentes aos do Red Hat")
    for r in rhsa:
        rlsa = id_rocky(r)
        url = URL_ROCKY.format(id=rlsa)
        dados = cliente.json(url, f"rocky_{rlsa}")
        a = aviso_rocky(dados, url) if dados else None
        if a:
            avisos.append(a)

    print(f"Fedora: busca por {', '.join(VERSOES_CORRIGIDAS)}")
    for versao in VERSOES_CORRIGIDAS:
        url = URL_BODHI.format(versao=versao)
        dados = cliente.json(url, f"bodhi_php-{versao}")
        if dados:
            avisos += avisos_bodhi(dados, url)

    return unificar(avisos), pendentes


# ----------------------------------------------------------------------------------------------
# Arquivos
# ----------------------------------------------------------------------------------------------

def ler_csv(caminho):
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def salvar_csv(caminho, campos, linhas):
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="não acessa a rede: reprocessa dados/rq3_bruto/")
    ap.add_argument("--data-corte", type=date.fromisoformat, default=datetime.now().date(),
                    help="data de corte da censura (padrão: hoje)")
    args = ap.parse_args()

    fontes = ler_csv(ARQ_FONTES)
    manual = {int(m["id"]): m for m in ler_csv(ARQ_MANUAL)} if ARQ_MANUAL.exists() else {}
    nomes = {int(f["id"]): f["distribuidor"] for f in fontes}

    cliente = Cliente(offline=args.offline)
    avisos, pendentes = coletar_api(cliente)

    salvar_csv(ARQ_AVISOS, CAMPOS_AVISOS, [{
        "distribuidor_id": a.distribuidor_id, "distribuidor": nomes.get(a.distribuidor_id, ""),
        "aviso": a.aviso, "data": a.data, "dias_desde_t0": (a.data - T0).days, "produto": a.produto,
        "cves": ";".join(sorted(a.cves)), "url": a.url,
    } for a in avisos])

    linhas, alertas = consolidar(fontes, avisos, pendentes, manual, args.data_corte)
    salvar_csv(ARQ_SAIDA, CAMPOS_SAIDA, linhas)

    print(f"\n{'distribuidor':<34}{'coleta':<8}{'situação':<24}{'1ª correção':<13}{'dias':<6}{'última':<12}evento")
    for l in linhas:
        print(f"{l['distribuidor'][:33]:<34}{l['forma_coleta']:<8}{l['situacao']:<24}"
              f"{str(l['data_primeira_correcao']):<13}{str(l['dias_ate_primeira_correcao']):<6}"
              f"{str(l['data_ultima_correcao']):<12}{l['evento']}")
    na_analise = [l for l in linhas if l["incluir_analise"] == "sim"]
    print(f"\n{len(avisos)} avisos automáticos | {len(na_analise)} de {len(linhas)} distribuidores na análise "
          f"({sum(1 for l in na_analise if l['evento'] == 1)} corrigiram, "
          f"{sum(1 for l in na_analise if l['evento'] == 0)} censurados) | data de corte {args.data_corte}"
          f" | {cliente.requisicoes} requisições")
    if alertas:
        print("\nAlertas:")
        for a in alertas:
            print(f" - {a}")
    print(f"\nSalvo em {ARQ_AVISOS.name} e {ARQ_SAIDA.name}")


if __name__ == "__main__":
    sys.exit(main())
