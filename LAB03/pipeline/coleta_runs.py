"""Coleta mensal de workflow runs da API do GitHub com suporte a subdivisão e checkpoint.

Inovações:
1. Subdivisão automática (mês -> semana -> dia) ao atingir o teto de 1.000 resultados da API.
2. Barra de progresso tqdm com acompanhamento em tempo real da cota restante da API.
3. Retomada atômica e segura via checkpoint tolerante a interrupções (Ctrl+C).
"""

from __future__ import annotations

import argparse
import calendar
from datetime import date, timedelta
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

from tqdm import tqdm

from pipeline.http import ClienteHTTP

logger = logging.getLogger(__name__)


def converter_data(valor: str | date) -> date:
    """Converte string no formato YYYY-MM-DD para objeto date."""
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor))


def gerar_meses(inicio: date, fim: date) -> list[tuple[date, date]]:
    """Gera uma lista de intervalos mensais cobrindo o período informado."""
    meses: list[tuple[date, date]] = []
    atual = inicio
    while atual <= fim:
        _, ultimo_dia = calendar.monthrange(atual.year, atual.month)
        fim_mes = min(date(atual.year, atual.month, ultimo_dia), fim)
        meses.append((atual, fim_mes))
        if fim_mes >= fim:
            break
        # Próximo primeiro dia do mês
        if atual.month == 12:
            atual = date(atual.year + 1, 1, 1)
        else:
            atual = date(atual.year, atual.month + 1, 1)
    return meses


def subdividir_semanas(inicio: date, fim: date) -> list[tuple[date, date]]:
    """Subdivide um intervalo de datas em blocos de até 7 dias."""
    semanas: list[tuple[date, date]] = []
    atual = inicio
    while atual <= fim:
        fim_semana = min(atual + timedelta(days=6), fim)
        semanas.append((atual, fim_semana))
        atual = fim_semana + timedelta(days=1)
    return semanas


def subdividir_dias(inicio: date, fim: date) -> list[tuple[date, date]]:
    """Subdivide um intervalo de datas dia a dia."""
    dias: list[tuple[date, date]] = []
    atual = inicio
    while atual <= fim:
        dias.append((atual, atual))
        atual += timedelta(days=1)
    return dias


def salvar_checkpoint_atomico(caminho: Path, dados: dict[str, Any]) -> None:
    """Grava o arquivo de checkpoint atomicamente para evitar corrupção em Ctrl+C."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temp = caminho.with_suffix(f".tmp.{os.getpid()}")
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(temp, caminho)


def carregar_checkpoint(caminho: Path | None) -> dict[str, Any]:
    """Carrega dados existentes do checkpoint ou retorna estrutura vazia."""
    if caminho and caminho.exists():
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as err:
            logger.warning("Falha ao ler checkpoint %s (%s). Iniciando do zero.", caminho, err)
    return {"periodos_concluidos": [], "runs": {}}


def coletar_periodo(
    cliente: ClienteHTTP,
    owner: str,
    repo: str,
    branch: str,
    inicio: date,
    fim: date,
    nivel: str = "mes",
) -> list[dict[str, Any]]:
    """Coleta workflow runs de um período, subdividindo recursivamente se atingir 1.000 resultados."""
    url = f"/repos/{owner}/{repo}/actions/runs"
    param_created = f"{inicio.isoformat()}..{fim.isoformat()}"
    params = {"branch": branch, "event": "push", "created": param_created, "per_page": 100}

    dados_iniciais = cliente.get(url, params=params)
    total_count = (
        dados_iniciais.get("total_count", 0)
        if isinstance(dados_iniciais, dict)
        else len(dados_iniciais)
    )

    if total_count >= 1000:
        if nivel == "mes":
            logger.warning(
                "Período mensal %s atingiu o teto de 1000 runs (%d). Subdividindo em semanas.",
                param_created,
                total_count,
            )
            runs_semanas: list[dict[str, Any]] = []
            for s_ini, s_fim in subdividir_semanas(inicio, fim):
                runs_semanas.extend(
                    coletar_periodo(cliente, owner, repo, branch, s_ini, s_fim, nivel="semana")
                )
            return runs_semanas

        if nivel == "semana":
            logger.warning(
                "Período semanal %s atingiu o teto de 1000 runs (%d). Subdividindo em dias.",
                param_created,
                total_count,
            )
            runs_dias: list[dict[str, Any]] = []
            for d_ini, d_fim in subdividir_dias(inicio, fim):
                runs_dias.extend(
                    coletar_periodo(cliente, owner, repo, branch, d_ini, d_fim, nivel="dia")
                )
            return runs_dias

        # nivel == "dia"
        logger.warning(
            "Período diário %s atingiu o teto da API (%d runs). Coletando limite disponível.",
            param_created,
            total_count,
        )
        return cliente.get_paginado(url, params=params, chave_lista="workflow_runs")

    # total_count < 1000
    if total_count <= 100:
        if isinstance(dados_iniciais, dict):
            return list(dados_iniciais.get("workflow_runs", []))
        return list(dados_iniciais)

    return cliente.get_paginado(url, params=params, chave_lista="workflow_runs")


def coletar_runs(
    owner: str,
    repo: str,
    branch: str = "main",
    data_inicio: str | date = "2024-01-01",
    data_fim: str | date = "2024-12-31",
    cliente: ClienteHTTP | None = None,
    caminho_checkpoint: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Coleta workflow runs mês a mês com subdivisão automática, barra de progresso e retomada."""
    cliente = cliente or ClienteHTTP()
    d_inicio = converter_data(data_inicio)
    d_fim = converter_data(data_fim)

    if caminho_checkpoint is None:
        caminho_cp = Path(f"data/runs_{owner}_{repo}.json")
    else:
        caminho_cp = Path(caminho_checkpoint)

    checkpoint = carregar_checkpoint(caminho_cp)
    periodos_concluidos: set[str] = set(checkpoint.get("periodos_concluidos", []))
    runs_map: dict[str, dict[str, Any]] = {
        str(r["id"]): r for r in checkpoint.get("runs", {}).values()
    }

    intervalos_meses = gerar_meses(d_inicio, d_fim)

    with tqdm(total=len(intervalos_meses), desc=f"Coletando {owner}/{repo}", unit="mês") as pbar:
        try:
            for mes_ini, mes_fim in intervalos_meses:
                chave_periodo = f"{mes_ini.isoformat()}..{mes_fim.isoformat()}"
                cota = cliente.cota_restante if cliente.cota_restante is not None else "N/A"
                pbar.set_postfix(cota=cota)

                if chave_periodo in periodos_concluidos:
                    pbar.set_description(f"Coletando {owner}/{repo} (cached {chave_periodo})")
                    pbar.update(1)
                    continue

                novos_runs = coletar_periodo(
                    cliente, owner, repo, branch, mes_ini, mes_fim, nivel="mes"
                )

                for run in novos_runs:
                    runs_map[str(run["id"])] = run

                periodos_concluidos.add(chave_periodo)
                checkpoint["owner"] = owner
                checkpoint["repo"] = repo
                checkpoint["branch"] = branch
                checkpoint["periodos_concluidos"] = sorted(list(periodos_concluidos))
                checkpoint["runs"] = runs_map

                salvar_checkpoint_atomico(caminho_cp, checkpoint)

                cota = cliente.cota_restante if cliente.cota_restante is not None else "N/A"
                pbar.set_postfix(cota=cota)
        except KeyboardInterrupt:
            logger.warning("Interrupção detectada (Ctrl+C). Salvando progresso com segurança...")
            checkpoint["periodos_concluidos"] = sorted(list(periodos_concluidos))
            checkpoint["runs"] = runs_map
            salvar_checkpoint_atomico(caminho_cp, checkpoint)
            raise

    return list(runs_map.values())


import csv

from metricas.falhas import cfr_ci
from metricas.recuperacao import tempo_recuperacao


def rodar_coleta_runs_pipeline(
    caminho_repos_csv: Path | str,
    inicio: str,
    fim: str,
    pasta_saida: Path | str = "data",
    refazer: bool = False,
    cliente: ClienteHTTP | None = None,
) -> list[dict[str, Any]]:
    """Coleta workflow runs dos repositórios da amostra final e calcula CFR (a) e Tempo de Recuperação."""
    caminho_csv = Path(caminho_repos_csv)
    saida = Path(pasta_saida)
    pasta_runs = saida / "runs"
    pasta_runs.mkdir(parents=True, exist_ok=True)
    cliente = cliente or ClienteHTTP()

    if not caminho_csv.exists():
        raise FileNotFoundError(f"Arquivo '{caminho_csv}' não encontrado.")

    repos = []
    with open(caminho_csv, "r", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            repos.append(linha)

    print(f"\nColetando runs para {len(repos)} repositórios da amostra...")
    metricas = []
    caminho_metricas_csv = saida / "metricas_runs.csv"

    def _salvar_metricas():
        if not metricas:
            return
        with open(caminho_metricas_csv, "w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=list(metricas[0].keys()))
            escritor.writeheader()
            escritor.writerows(metricas)

    try:
        for idx, item in enumerate(repos, 1):
            raw_nome = item.get("full_name") or item.get("repo") or ""
            if "/" in raw_nome:
                full_name = raw_nome
                owner = item.get("owner") or raw_nome.split("/")[0]
                repo = raw_nome.split("/")[1]
            else:
                owner = item.get("owner") or ""
                repo = item.get("repo") or raw_nome
                full_name = f"{owner}/{repo}" if owner and repo else raw_nome
            default_branch = item.get("default_branch") or "main"
            caminho_cp = pasta_runs / f"{owner}__{repo}.json"

            print(f"[{idx}/{len(repos)}] Processando runs de {full_name}...")

            if caminho_cp.exists() and not refazer:
                try:
                    cp_data = carregar_checkpoint(caminho_cp)
                    runs = list(cp_data.get("runs", {}).values())
                    print(f"  -> {len(runs)} runs carregados do checkpoint (cache)")
                except Exception:
                    runs = coletar_runs(
                        owner=owner,
                        repo=repo,
                        branch=default_branch,
                        data_inicio=inicio,
                        data_fim=fim,
                        cliente=cliente,
                        caminho_checkpoint=caminho_cp,
                    )
            else:
                runs = coletar_runs(
                    owner=owner,
                    repo=repo,
                    branch=default_branch,
                    data_inicio=inicio,
                    data_fim=fim,
                    cliente=cliente,
                    caminho_checkpoint=caminho_cp,
                )

            # Cálculo de CFR (a) e Tempo de Recuperação
            valor_cfr = cfr_ci(runs)
            recup = tempo_recuperacao(runs)
            mediana_s = round(recup.mediana.total_seconds(), 2) if recup.mediana else None
            mediana_h = round(recup.mediana.total_seconds() / 3600.0, 2) if recup.mediana else None

            linha_metrica = {
                "repo": full_name,
                "total_runs": len(runs),
                "cfr_ci": round(valor_cfr, 4) if valor_cfr is not None else None,
                "tempo_recuperacao_s": mediana_s,
                "tempo_recuperacao_h": mediana_h,
                "recuperacao_proporcao_censurados": round(recup.proporcao_censurados, 4),
                "total_episodios": len(recup.episodios),
            }
            metricas.append(linha_metrica)

            if idx % 10 == 0:
                _salvar_metricas()
    finally:
        _salvar_metricas()

    print(f"\nMétricas de runs salvas com sucesso em: {caminho_metricas_csv}")
    return metricas


def main() -> None:
    """Ponto de entrada via CLI para execução e retomada da coleta de runs."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Coleta de workflow runs da API do GitHub.")
    parser.add_argument("--owner", help="Proprietário do repositório (ex: psf)")
    parser.add_argument("--repo", help="Nome do repositório (ex: requests)")
    parser.add_argument("--arquivo", help="Caminho para arquivo CSV com lista de repositórios (ex: data/repos.csv)")
    parser.add_argument("--saida", default="data", help="Diretório de saída (padrão: data)")
    parser.add_argument("--branch", default="main", help="Branch de filtro (padrão: main)")
    parser.add_argument("--inicio", default="2025-01-01", help="Data de início (YYYY-MM-DD)")
    parser.add_argument("--fim", default="2025-12-31", help="Data de término (YYYY-MM-DD)")
    parser.add_argument("--checkpoint", default=None, help="Caminho personalizado para o checkpoint")
    parser.add_argument("--refazer", action="store_true", help="Ignora checkpoints existentes e refaz coleta")

    args = parser.parse_args()

    if args.arquivo:
        rodar_coleta_runs_pipeline(
            caminho_repos_csv=args.arquivo,
            inicio=args.inicio,
            fim=args.fim,
            pasta_saida=args.saida,
            refazer=args.refazer,
        )
        return

    if not args.owner or not args.repo:
        parser.error("Informe --owner e --repo ou use --arquivo com o CSV de repositórios.")

    try:
        runs = coletar_runs(
            owner=args.owner,
            repo=args.repo,
            branch=args.branch,
            data_inicio=args.inicio,
            data_fim=args.fim,
            caminho_checkpoint=args.checkpoint,
        )
        print(f"\nColeta concluída com sucesso! Total de runs coletados: {len(runs)}")
    except KeyboardInterrupt:
        print("\n[Ctrl+C] Execução pausada com sucesso. Execute o mesmo comando para retomar de onde parou.")
        sys.exit(0)


if __name__ == "__main__":
    main()
