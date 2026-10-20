"""Executa o pipeline de outro grupo registrando tudo como evidência para as Issues.

Uso (de dentro de LAB03):
    # 1. sortear a subamostra de 30 repositórios do dataset original do outro grupo
    python -m replicacao.executar subamostra --dataset <caminho/dataset_deles.csv> --n 30

    # 2. executar o comando do README deles, a partir da pasta do projeto deles
    python -m replicacao.executar rodar --pasta <pasta_do_projeto_deles> -- python -m pipeline --config config.yaml

Cada execução grava em replicacao/execucoes/<data_hora>/:
    log_execucao.txt   comando, pasta, duração, código de saída e toda a saída (stdout + stderr)
    ambiente.json      sistema operacional, versão do Python, commit do projeto deles e pip freeze
    issue.md           rascunho de Issue com as evidências, gerado quando o comando falha
e acrescenta uma linha em replicacao/execucoes.csv (histórico de tentativas).
"""
import argparse
import csv
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
PASTA_REPLICACAO = RAIZ / "replicacao"
SEMENTE = 42
LINHAS_ERRO = 40


def sortear_subamostra(caminho_dataset, n=30, semente=SEMENTE, coluna=None):
    """Sorteia n repositórios do dataset do outro grupo com semente fixa (reproduzível)."""
    df = pd.read_csv(caminho_dataset)
    coluna = coluna or next((c for c in ("repo", "full_name", "repository", "nome") if c in df.columns), df.columns[0])
    amostra = df.sample(n=min(n, len(df)), random_state=semente)
    return amostra[[coluna]].rename(columns={coluna: "full_name"}).reset_index(drop=True)


def _rodar(comando, pasta):
    """Roda o comando mostrando a saída ao vivo e devolve (código, saída, segundos)."""
    inicio = time.monotonic()
    linhas = []
    try:
        proc = subprocess.Popen(comando, cwd=pasta, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", bufsize=1)
    except (FileNotFoundError, OSError) as erro:
        return 127, f"Falha ao iniciar o comando: {erro}\n", time.monotonic() - inicio
    for linha in proc.stdout:
        try:
            sys.stdout.write(linha)
            sys.stdout.flush()
        except Exception:
            enc = sys.stdout.encoding or "utf-8"
            sys.stdout.write(linha.encode(enc, errors="replace").decode(enc, errors="replace"))
            sys.stdout.flush()
        linhas.append(linha)
    proc.wait()
    return proc.returncode, "".join(linhas), time.monotonic() - inicio


def _git_commit(pasta):
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=pasta, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def coletar_ambiente(pasta):
    try:
        freeze = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True,
                                         stderr=subprocess.DEVNULL).splitlines()
    except Exception:
        freeze = []
    return {
        "sistema_operacional": platform.platform(),
        "python": sys.version.split()[0],
        "executavel_python": sys.executable,
        "pasta_projeto": str(Path(pasta).resolve()),
        "commit_projeto": _git_commit(pasta),
        "pip_freeze": freeze,
    }


def rascunho_issue(comando, pasta, codigo, saida, duracao, ambiente):
    ultimas = "".join(saida.splitlines(keepends=True)[-LINHAS_ERRO:])
    return "\n".join([
        "## Falha ao executar o pipeline seguindo o README",
        "",
        "**Comando executado:**",
        "```",
        " ".join(comando),
        "```",
        f"**Pasta:** `{pasta}`  ",
        f"**Commit do projeto:** `{ambiente['commit_projeto'] or 'desconhecido'}`  ",
        f"**Código de saída:** {codigo} · **Duração:** {duracao:.1f} s",
        "",
        f"**Mensagem de erro (últimas {LINHAS_ERRO} linhas):**",
        "```",
        ultimas.rstrip(),
        "```",
        "",
        "**Ambiente:**",
        f"- Sistema operacional: {ambiente['sistema_operacional']}",
        f"- Python: {ambiente['python']}",
        "",
        "**Esperado:** o pipeline executa até o fim seguindo apenas as instruções do README.",
        "**Obtido:** a execução terminou com erro (saída acima).",
        "",
        "<!-- Complete com o passo do README em que o problema ocorreu e o que estava faltando. -->",
        "",
    ])


def registrar_execucao(comando, pasta, destino=PASTA_REPLICACAO):
    """Executa o comando e grava log, ambiente, histórico e (se falhar) o rascunho de Issue."""
    pasta = Path(pasta)
    carimbo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pasta_exec = Path(destino) / "execucoes" / carimbo
    pasta_exec.mkdir(parents=True, exist_ok=True)

    print(f"Executando em {pasta}: {' '.join(comando)}\n")
    codigo, saida, duracao = _rodar(comando, pasta)
    ambiente = coletar_ambiente(pasta)

    (pasta_exec / "log_execucao.txt").write_text("\n".join([
        f"data_hora_utc: {carimbo}",
        f"comando: {' '.join(comando)}",
        f"pasta: {pasta.resolve()}",
        f"duracao_s: {duracao:.1f}",
        f"codigo_saida: {codigo}",
        "-" * 70,
        saida,
    ]), encoding="utf-8")
    (pasta_exec / "ambiente.json").write_text(json.dumps(ambiente, ensure_ascii=False, indent=2), encoding="utf-8")
    if codigo != 0:
        (pasta_exec / "issue.md").write_text(
            rascunho_issue(comando, pasta, codigo, saida, duracao, ambiente), encoding="utf-8")

    historico = Path(destino) / "execucoes.csv"
    novo = not historico.exists()
    with open(historico, "a", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        if novo:
            escritor.writerow(["data_hora_utc", "comando", "pasta", "codigo_saida", "duracao_s", "evidencias"])
        escritor.writerow([carimbo, " ".join(comando), str(pasta.resolve()), codigo, f"{duracao:.1f}",
                           pasta_exec.relative_to(destino).as_posix()])

    return {"codigo": codigo, "duracao_s": duracao, "pasta_evidencias": pasta_exec}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="acao", required=True)

    p_sub = sub.add_parser("subamostra", help="sorteia a subamostra de repositórios do dataset do outro grupo")
    p_sub.add_argument("--dataset", required=True)
    p_sub.add_argument("--n", type=int, default=30)
    p_sub.add_argument("--coluna", help="coluna com owner/repo (detectada automaticamente)")
    p_sub.add_argument("--saida", default=str(PASTA_REPLICACAO / "subamostra_30.csv"))

    p_rodar = sub.add_parser("rodar", help="executa o comando do README do outro grupo")
    p_rodar.add_argument("--pasta", required=True, help="pasta do projeto do outro grupo")
    p_rodar.add_argument("comando", nargs=argparse.REMAINDER, help="comando a executar, depois de --")

    args = parser.parse_args(argv)
    if args.acao == "subamostra":
        amostra = sortear_subamostra(args.dataset, args.n, coluna=args.coluna)
        Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
        amostra.to_csv(args.saida, index=False, encoding="utf-8")
        print(f"{len(amostra)} repositórios sorteados (semente {SEMENTE}) em {args.saida}")
        return 0

    comando = [c for c in args.comando if c != "--"]
    if not comando:
        parser.error("informe o comando depois de --")
    r = registrar_execucao(comando, args.pasta)
    status = "OK" if r["codigo"] == 0 else f"FALHOU (código {r['codigo']}); rascunho de Issue em issue.md"
    print(f"\n{status}. Evidências em {r['pasta_evidencias']}")
    return r["codigo"]


if __name__ == "__main__":
    sys.exit(main())
