import argparse
from pathlib import Path
import sys

from dotenv import load_dotenv

from pipeline.config_parser import carregar_config
from pipeline.github_api import GitHubAPI
from pipeline.releases import main as rodar_coleta_releases
from pipeline.selecao import selecionar_repositorios

RAIZ = Path(__file__).resolve().parents[1]

# Carrega .env em LAB03, no repo ou na raiz do workspace
for p in [RAIZ / ".env", RAIZ.parent / ".env", RAIZ.parent.parent / ".env"]:
    if p.exists():
        load_dotenv(p)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Pipeline de Mineracao de Metricas DORA (LAB03)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", default="config.yaml", help="Caminho do arquivo config.yaml (default: config.yaml)")
    parser.add_argument(
        "--etapa",
        choices=["selecao", "releases", "todas"],
        default="todas",
        help="Etapa a ser executada (default: todas)",
    )
    parser.add_argument("--limite", type=int, help="Sobrescreve o limite_repos do config.yaml")
    args = parser.parse_args(argv)

    caminho_config = RAIZ / args.config if not Path(args.config).is_absolute() else Path(args.config)
    cfg = carregar_config(caminho_config)
    if args.limite:
        cfg["limite_repos"] = args.limite

    print("=" * 65)
    print(" PIPELINE DE MINERACAO DORA - LAB03 ")
    print(f" Janela: {cfg['inicio']} ate {cfg['fim']}")
    print(f" Limite de repositorios: {cfg['limite_repos']}")
    print("=" * 65)

    if args.etapa in ("selecao", "todas"):
        api = GitHubAPI()
        print("\n>>> ETAPA 1: Selecao de Repositorios, Funil e Metadados")
        selecionados, funil = selecionar_repositorios(api, cfg)
        print(f"Total selecionado: {len(selecionados)} repositorios.")

    if args.etapa in ("releases", "todas"):
        caminho_repos_csv = Path(cfg["repos_csv"])
        if not caminho_repos_csv.exists() and args.etapa == "releases":
            sys.exit(f"Erro: Arquivo '{caminho_repos_csv}' nao encontrado. Execute a etapa de selecao primeiro.")

        print("\n>>> ETAPA 2: Coleta de Releases e Lead Time")
        argv_releases = [
            "--inicio", cfg["inicio"],
            "--fim", cfg["fim"],
            "--arquivo", str(caminho_repos_csv),
            "--unidade", "release",
            "--saida", str(RAIZ / cfg["dados_dir"]),
        ]
        rodar_coleta_releases(argv_releases)

    print("\n Pipeline executado com sucesso!")


if __name__ == "__main__":
    main()
