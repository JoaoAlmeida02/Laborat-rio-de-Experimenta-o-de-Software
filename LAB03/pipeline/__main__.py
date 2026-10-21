import argparse
import csv
from pathlib import Path
import sys

from dotenv import load_dotenv

from pipeline.config_parser import carregar_config
from pipeline.coleta_runs import rodar_coleta_runs_pipeline
from pipeline.consolidar import consolidar_dataset
from pipeline.github_api import GitHubAPI
from pipeline.releases import main as rodar_coleta_releases
from pipeline.selecao import selecionar_repositorios

RAIZ = Path(__file__).resolve().parents[1]

# Carrega .env em LAB03, no repo ou na raiz do workspace
for p in [RAIZ / ".env", RAIZ.parent / ".env", RAIZ.parent.parent / ".env"]:
    if p.exists():
        load_dotenv(p)


def estimar_chamadas_api(cfg: dict, caminho_repos_fixos: Path | None = None) -> dict:
    # Se lista fixa de repositorios for fornecida, pula Etapa 1 e calcula apenas etapas 2 e 3
    if caminho_repos_fixos and caminho_repos_fixos.exists():
        try:
            with open(caminho_repos_fixos, "r", encoding="utf-8") as f:
                linhas = list(csv.DictReader(f))
            limite = len(linhas)
        except Exception:
            limite = cfg.get("limite_repos", 300)
        candidatos_estimados = 0
        total_selecao = 0
        chamadas_busca = 0
        chamadas_workflows = 0
        chamadas_inclusao_releases = 0
        chamadas_inclusao_runs = 0
        chamadas_contrib = 0
    else:
        limite = cfg.get("limite_repos", 300)
        # Projeção de candidatos necessários (~4x a amostra para funil com 5 releases e 50 runs)
        candidatos_estimados = limite * 4

        chamadas_busca = len(cfg.get("faixas_estrelas", [])) * 10
        chamadas_workflows = candidatos_estimados
        chamadas_inclusao_releases = int(candidatos_estimados * 0.75)
        chamadas_inclusao_runs = int(candidatos_estimados * 0.40)
        chamadas_contrib = limite
        total_selecao = (
            chamadas_busca
            + chamadas_workflows
            + chamadas_inclusao_releases
            + chamadas_inclusao_runs
            + chamadas_contrib
        )

    # Releases e commits entre entregas
    chamadas_releases_lista = limite
    media_entregas = 10
    chamadas_compare = limite * (media_entregas - 1)
    total_releases = chamadas_releases_lista + chamadas_compare

    # Runs mensais (12 meses na janela de 1 ano)
    chamadas_runs_meses = limite * 12
    total_runs = chamadas_runs_meses

    total_geral = total_selecao + total_releases + total_runs

    return {
        "limite_repos": limite,
        "candidatos_estimados": candidatos_estimados,
        "is_repos_fixo": bool(caminho_repos_fixos),
        "detalhes": {
            "1_selecao": {
                "busca_faixas": chamadas_busca,
                "verificacao_actions": chamadas_workflows,
                "inclusao_releases": chamadas_inclusao_releases,
                "inclusao_workflow_runs": chamadas_inclusao_runs,
                "contribuidores": chamadas_contrib,
                "subtotal": total_selecao,
            },
            "2_releases": {
                "listar_releases": chamadas_releases_lista,
                "compare_commits": chamadas_compare,
                "subtotal": total_releases,
            },
            "3_runs": {
                "runs_mensais": chamadas_runs_meses,
                "subtotal": total_runs,
            },
        },
        "total_estimado": total_geral,
        "tempo_estimado_horas": round(total_geral / 5000.0, 2),
    }


def imprimir_dry_run(cfg: dict, caminho_repos_fixos: Path | None = None):
    # Exibe relatório de estimativa do --dry-run
    est = estimar_chamadas_api(cfg, caminho_repos_fixos=caminho_repos_fixos)
    print("\n" + "=" * 65)
    print(" [DRY-RUN] ESTIMATIVA DE CHAMADAS À API DO GITHUB ")
    print("=" * 65)
    print(f" Janela temporal: {cfg['inicio']} até {cfg['fim']}")
    if est.get("is_repos_fixo"):
        print(f" Modo replicação: {est['limite_repos']} repositórios fixos informados via --repos")
        print(" Etapa 1 (Seleção e Funil): 0 requisições (pulada)")
    else:
        print(f" Meta de repositórios: {est['limite_repos']}")
        print(f" Candidatos estimados para inspecionar: ~{est['candidatos_estimados']}")
    print("-" * 65)
    print(" Detalhamento por etapa:")
    if not est.get("is_repos_fixo"):
        print("   1. Seleção e Funil:")
        print(f"      - Busca por faixas: {est['detalhes']['1_selecao']['busca_faixas']} requisições")
        print(f"      - Verificação de workflows: ~{est['detalhes']['1_selecao']['verificacao_actions']} requisições")
        print(f"      - Filtro de inclusão (releases): ~{est['detalhes']['1_selecao']['inclusao_releases']} requisições")
        print(f"      - Filtro de inclusão (runs): ~{est['detalhes']['1_selecao']['inclusao_workflow_runs']} requisições")
        print(f"      - Contribuidores (Link rel=last): ~{est['detalhes']['1_selecao']['contribuidores']} requisições")
        print(f"      > Subtotal Etapa 1: ~{est['detalhes']['1_selecao']['subtotal']} requisições")
    else:
        print("   1. Seleção e Funil: Pulada (--repos informado)")
    print("   2. Releases e Lead Time:")
    print(f"      - Listagem de releases: {est['detalhes']['2_releases']['listar_releases']} requisições")
    print(f"      - Comparação de commits (compare): ~{est['detalhes']['2_releases']['compare_commits']} requisições")
    print(f"      > Subtotal Etapa 2: ~{est['detalhes']['2_releases']['subtotal']} requisições")
    print("   3. Workflow Runs e Recuperação:")
    print(f"      - Coleta mensal de runs (12 meses): {est['detalhes']['3_runs']['runs_mensais']} requisições")
    print(f"      > Subtotal Etapa 3: ~{est['detalhes']['3_runs']['subtotal']} requisições")
    print("-" * 65)
    print(f" TOTAL ESTIMADO: ~{est['total_estimado']:,} chamadas à API")
    print(" Cota de Rate Limit: 5.000 requisições/hora por token pessoal")
    print(f" Tempo mínimo estimado (sem cache): ~{est['tempo_estimado_horas']} horas")
    print(" Nota: Com cache (.cache_http/ e checkpoints), requisições já salvas são ignoradas.")
    print("=" * 65 + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Pipeline de Mineracao de Metricas DORA (LAB03)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", default="config.yaml", help="Caminho do arquivo config.yaml (default: config.yaml)")
    parser.add_argument(
        "--etapa",
        choices=["selecao", "releases", "runs", "consolidar", "todas"],
        default="todas",
        help="Etapa a ser executada (default: todas)",
    )
    parser.add_argument(
        "--repos",
        help="Caminho para arquivo CSV com lista de repositorios para replicacao direta (pula a Etapa 1 de busca)",
    )
    parser.add_argument("--limite", type=int, help="Sobrescreve o limite_repos do config.yaml")
    parser.add_argument("--refazer", action="store_true", help="Ignora cache existente e refaz a coleta")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inovação: simula e estima a quantidade de chamadas à API sem executar requisições pesadas",
    )
    args = parser.parse_args(argv)

    caminho_config = RAIZ / args.config if not Path(args.config).is_absolute() else Path(args.config)
    cfg = carregar_config(caminho_config)
    if args.limite:
        cfg["limite_repos"] = args.limite
    if args.refazer:
        cfg["refazer"] = True

    # Se --repos for informado, valida e usa o caminho especificado
    if args.repos:
        caminho_repos_arg = Path(args.repos)
        if not caminho_repos_arg.is_absolute():
            if caminho_repos_arg.exists():
                caminho_repos_csv = caminho_repos_arg.resolve()
            elif (RAIZ / args.repos).exists():
                caminho_repos_csv = (RAIZ / args.repos).resolve()
            else:
                caminho_repos_csv = caminho_repos_arg.resolve()
        else:
            caminho_repos_csv = caminho_repos_arg

        if not caminho_repos_csv.exists():
            sys.exit(f"Erro: Arquivo de repositorios '{args.repos}' nao encontrado.")
    else:
        caminho_repos_csv = RAIZ / cfg["repos_csv"] if not Path(cfg["repos_csv"]).is_absolute() else Path(cfg["repos_csv"])

    print("=" * 65)
    print(" PIPELINE DE MINERACAO DORA - LAB03 ")
    print(f" Janela: {cfg['inicio']} ate {cfg['fim']}")
    if args.repos:
        print(f" Modo replicacao: usando lista fixa de {caminho_repos_csv.name}")
    else:
        print(f" Limite de repositorios: {cfg['limite_repos']}")
        print(f" Criterio de inclusao: >= {cfg['min_releases']} releases e >= {cfg['min_workflow_runs']} runs")
    print("=" * 65)

    if args.dry_run:
        imprimir_dry_run(cfg, caminho_repos_fixos=caminho_repos_csv if args.repos else None)
        return

    pasta_dados = RAIZ / cfg["dados_dir"]
    pasta_dados.mkdir(parents=True, exist_ok=True)

    # ETAPA 1: Seleção com Funil e Critérios de Inclusão
    if args.etapa in ("selecao", "todas"):
        if args.repos:
            print(f"\n>>> ETAPA 1: Ignorada (utilizando lista fixa de repositorios de: {caminho_repos_csv})")
        else:
            api = GitHubAPI()
            print("\n>>> ETAPA 1: Selecao de Repositorios, Funil e Metadados")
            selecionados, funil = selecionar_repositorios(api, cfg)
            print(f"Total selecionado: {len(selecionados)} repositorios.")

    # ETAPA 2: Releases, Commits, Lead Time (a e b) e CFR (b) / Rework Rate (v4)
    if args.etapa in ("releases", "todas"):
        if not caminho_repos_csv.exists():
            sys.exit(f"Erro: Arquivo '{caminho_repos_csv}' nao encontrado. Execute a etapa de selecao primeiro ou informe --repos <arquivo.csv>.")

        print("\n>>> ETAPA 2: Coleta de Releases e Lead Time (a e b, CFR b com heurística v4)")
        argv_releases = [
            "--inicio", cfg["inicio"],
            "--fim", cfg["fim"],
            "--arquivo", str(caminho_repos_csv),
            "--unidade", "release",
            "--saida", str(pasta_dados),
        ]
        if args.refazer:
            argv_releases.append("--refazer")
        rodar_coleta_releases(argv_releases)

    # ETAPA 3: Workflow Runs, CFR (a) e Tempo de Recuperação
    if args.etapa in ("runs", "todas"):
        if not caminho_repos_csv.exists():
            sys.exit(f"Erro: Arquivo '{caminho_repos_csv}' nao encontrado. Execute a etapa de selecao primeiro ou informe --repos <arquivo.csv>.")

        print("\n>>> ETAPA 3: Coleta de Workflow Runs, CFR (a) e Tempo de Recuperacao")
        rodar_coleta_runs_pipeline(
            caminho_repos_csv=caminho_repos_csv,
            inicio=cfg["inicio"],
            fim=cfg["fim"],
            pasta_saida=pasta_dados,
            refazer=args.refazer,
        )

    # ETAPA 4: Consolidação no dataset.csv e geração de MANIFEST.json
    if args.etapa in ("consolidar", "todas"):
        print("\n>>> ETAPA 4: Consolidacao de Metricas em dataset.csv e MANIFEST.json")
        caminho_dataset = pasta_dados / "dataset.csv"
        caminho_manifest = pasta_dados / "MANIFEST.json"
        consolidar_dataset(
            pasta_dados=pasta_dados,
            arquivo_repos=str(caminho_repos_csv),
            arquivo_lead_time="lead_time_release.csv",
            arquivo_metricas_runs="metricas_runs.csv",
            caminho_saida=caminho_dataset,
            caminho_manifest=caminho_manifest,
            inicio_janela=cfg["inicio"],
            fim_janela=cfg["fim"],
        )

    print("\n Pipeline executado com sucesso!")


if __name__ == "__main__":
    main()
