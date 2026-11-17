"""Coleta as evidências dos critérios "em operação" e "alto impacto" do PHP (LAB05S01).

Fontes (todas públicas, sem autenticação, no máximo 1 requisição por segundo):
- php.net, API de releases: ramos suportados, versões e datas de lançamento
  (https://www.php.net/releases/index.php?json&version=X.Y&max=N)
- endoflife.date: datas de fim do suporte ativo e do suporte de segurança de cada ramo
  (https://endoflife.date/api/php.json)
- Docker Hub: total de downloads (pulls) das imagens oficiais `php` e `wordpress`

Os percentuais de uso do W3Techs NÃO são coletados por script (os termos de uso do site
não permitem extração automatizada): eles são registrados à mão em docs/proposta.md.

Saídas:
- dados/evidencias_php.csv     um ramo do PHP por linha (situação, versão vulnerável e corrigida)
- dados/evidencias_docker.csv  downloads das imagens oficiais

Uso (a partir da pasta LAB05):
    python scripts/evidencias_php.py
"""
import csv
import time
from datetime import date, datetime
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "dados"

USER_AGENT = "lab05-experimento-academico"
PAUSA_S = 1.0  # regra de ética do enunciado: no máximo 1 requisição por segundo

DATA_CORRECAO = date(2026, 10, 21)  # releases que corrigiram CVE-2026-109618 e CVE-2026-109619
RAMOS_FIM_DE_VIDA = ["7.4", "8.0", "8.1"]  # ainda muito usados, mas sem correção oficial
IMAGENS_DOCKER = ["php", "wordpress"]

URL_RELEASES = "https://www.php.net/releases/index.php"
URL_ATIVOS = "https://www.php.net/releases/active.php"
URL_EOL = "https://endoflife.date/api/php.json"
URL_DOCKER = "https://hub.docker.com/v2/namespaces/library/repositories/{imagem}"

MESES = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}

CAMPOS_PHP = [
    "ramo", "lancamento_ramo", "fim_suporte_ativo", "fim_suporte_seguranca", "situacao",
    "ultima_versao", "data_ultima_versao", "versao_vulneravel", "data_versao_vulneravel",
    "versao_corrigida", "data_versao_corrigida", "recebeu_correcao_php2shell", "data_coleta",
]
CAMPOS_DOCKER = ["imagem", "pulls", "estrelas", "ultima_atualizacao", "data_coleta"]


def ler_data_php(texto):
    """'21 Oct 2026' -> date(2026, 10, 21). Não depende do idioma do sistema."""
    dia, mes, ano = texto.split()
    return date(int(ano), MESES[mes[:3]], int(dia))


def chave_versao(versao):
    """'8.4.27' -> (8, 4, 27), para ordenar versões corretamente."""
    return tuple(int(p) for p in versao.split("."))


def situacao_do_ramo(fim_ativo, fim_seguranca, hoje):
    if hoje <= fim_ativo:
        return "suporte ativo"
    if hoje <= fim_seguranca:
        return "somente correções de segurança"
    return "fim de vida"


def versoes_da_correcao(releases, data_correcao=DATA_CORRECAO):
    """Recebe {versao: data} de um ramo e devolve (vulnerável, corrigida).

    A corrigida é a versão lançada na data da correção; a vulnerável é a imediatamente anterior.
    Se o ramo não teve release nessa data, devolve (última versão, None).
    """
    ordenadas = sorted(releases, key=chave_versao)
    for i, versao in enumerate(ordenadas):
        if releases[versao] == data_correcao:
            anterior = ordenadas[i - 1] if i > 0 else None
            return anterior, versao
    return (ordenadas[-1] if ordenadas else None), None


class Cliente:
    """GET com User-Agent genérico e pausa mínima entre requisições."""

    def __init__(self, pausa=PAUSA_S):
        self.sessao = requests.Session()
        self.sessao.headers["User-Agent"] = USER_AGENT
        self.pausa = pausa
        self._ultima = 0.0

    def json(self, url, **params):
        espera = self.pausa - (time.monotonic() - self._ultima)
        if espera > 0:
            time.sleep(espera)
        resposta = self.sessao.get(url, params=params, timeout=30)
        self._ultima = time.monotonic()
        resposta.raise_for_status()
        return resposta.json()


def releases_do_ramo(cliente, ramo, maximo=10):
    """{versao: data} das últimas `maximo` versões de um ramo, segundo o php.net."""
    # a API usa parâmetros sem valor (?json&version=...), por isso a URL é montada à mão
    dados = cliente.json(f"{URL_RELEASES}?json&version={ramo}&max={maximo}")
    return {versao: ler_data_php(info["date"]) for versao, info in dados.items()}


def coletar_ramos(cliente, hoje):
    ativos = cliente.json(URL_ATIVOS)
    ramos_suportados = sorted({r for por_maior in ativos.values() for r in por_maior}, key=chave_versao)
    ciclos = {c["cycle"]: c for c in cliente.json(URL_EOL)}

    linhas = []
    for ramo in sorted(set(ramos_suportados + RAMOS_FIM_DE_VIDA), key=chave_versao):
        ciclo = ciclos.get(ramo, {})
        fim_ativo = date.fromisoformat(ciclo["support"]) if ciclo.get("support") else None
        fim_seg = date.fromisoformat(ciclo["eol"]) if ciclo.get("eol") else None
        releases = releases_do_ramo(cliente, ramo)
        ultima = max(releases, key=chave_versao)
        vulneravel, corrigida = versoes_da_correcao(releases)
        linhas.append({
            "ramo": ramo,
            "lancamento_ramo": ciclo.get("releaseDate", ""),
            "fim_suporte_ativo": fim_ativo or "",
            "fim_suporte_seguranca": fim_seg or "",
            "situacao": situacao_do_ramo(fim_ativo, fim_seg, hoje) if fim_ativo and fim_seg else "",
            "ultima_versao": ultima,
            "data_ultima_versao": releases[ultima],
            "versao_vulneravel": vulneravel or "",
            "data_versao_vulneravel": releases.get(vulneravel, "") if vulneravel else "",
            "versao_corrigida": corrigida or "",
            "data_versao_corrigida": releases[corrigida] if corrigida else "",
            "recebeu_correcao_php2shell": "sim" if corrigida else "não",
            "data_coleta": hoje,
        })
    return linhas


def coletar_docker(cliente, hoje):
    linhas = []
    for imagem in IMAGENS_DOCKER:
        info = cliente.json(URL_DOCKER.format(imagem=imagem))
        linhas.append({
            "imagem": imagem,
            "pulls": info.get("pull_count", ""),
            "estrelas": info.get("star_count", ""),
            "ultima_atualizacao": (info.get("last_updated") or "")[:10],
            "data_coleta": hoje,
        })
    return linhas


def salvar_csv(caminho, campos, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)


def main():
    hoje = datetime.now().date()
    cliente = Cliente()

    ramos = coletar_ramos(cliente, hoje)
    salvar_csv(DADOS / "evidencias_php.csv", CAMPOS_PHP, ramos)
    docker = coletar_docker(cliente, hoje)
    salvar_csv(DADOS / "evidencias_docker.csv", CAMPOS_DOCKER, docker)

    print(f"Coleta de {hoje}\n")
    print(f"{'ramo':<6}{'situação':<34}{'vulnerável':<12}{'corrigida':<12}correção PHP2Shell")
    for r in ramos:
        print(f"{r['ramo']:<6}{r['situacao']:<34}{r['versao_vulneravel']:<12}"
              f"{r['versao_corrigida'] or '-':<12}{r['recebeu_correcao_php2shell']}")
    print()
    for d in docker:
        print(f"Docker Hub '{d['imagem']}': {int(d['pulls']):,} pulls".replace(",", "."))
    print(f"\nArquivos salvos em {DADOS}")


if __name__ == "__main__":
    main()
