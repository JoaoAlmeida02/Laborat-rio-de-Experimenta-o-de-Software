#!/usr/bin/env python3
"""
Script de Coleta de Métricas Estáticas de Código (LAB02 - Sprint 01).

Este script analisa o código-fonte de cada trial executado no experimento
(localizado no diretório `dados/`) e extrai métricas estáticas de qualidade,
complexidade e manutenibilidade (RQ3), além de métricas de tamanho e duplicação.

Ferramentas utilizadas:
    - Radon (Python API):
        * radon.raw: LOC (Lines of Code), LLOC (Logical LOC), SLOC (Source LOC),
          comentários e linhas em branco.
        * radon.complexity: Complexidade ciclomática (média, máxima, total e número de funções).
        * radon.metrics: Índice de Manutenibilidade (MI).
    - jscpd (CLI via subprocess):
        * Percentual de duplicação de código (--min-lines 5 --min-tokens 20).

Integração com Sprint 03:
    A coluna `trial_id` (nome da subpasta do trial) é a chave primária que será
    utilizada para realizar o merge/join destas métricas estruturais (RQ3) com
    os dados operacionais gerados pelo `cronometro.py` (tempo_segundos, censurado,
    testes_passando, testes_total - RQ1 e RQ2) na etapa de análise estatística.

Uso:
    python collect_metrics.py [--dados-dir dados] [--output metrics.csv] [--verbose]
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import radon.complexity as radon_cc
import radon.metrics as radon_mi
import radon.raw as radon_raw
import radon.visitors as radon_visitors

# Colunas do CSV de saída
CSV_COLUMNS = [
    "trial_id",
    "kata",
    "participante",
    "tratamento",
    "loc",
    "lloc",
    "sloc",
    "comentarios",
    "linhas_brancas",
    "cc_media",
    "cc_max",
    "cc_total",
    "n_funcoes",
    "indice_manutenibilidade",
    "duplicacao_pct",
]


def carregar_metadata(caminho_trial: Path) -> Dict[str, str]:
    """
    Lê e valida o arquivo metadata.json do trial.
    Aceita 'participante' ou 'pessoa' como identificador do participante.
    """
    metadata_file = caminho_trial / "metadata.json"
    if not metadata_file.exists():
        raise FileNotFoundError(f"Arquivo metadata.json ausente em '{caminho_trial.name}'.")

    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"metadata.json corrompido em '{caminho_trial.name}': {exc}") from exc

    kata = data.get("kata")
    participante = data.get("participante") or data.get("pessoa")
    tratamento = data.get("tratamento")

    erros = []
    if not kata:
        erros.append("campo 'kata' ausente")
    if not participante:
        erros.append("campo 'participante' (ou 'pessoa') ausente")
    if not tratamento or tratamento not in ("com_ia", "sem_ia"):
        erros.append("campo 'tratamento' ausente ou inválido (deve ser 'com_ia' ou 'sem_ia')")

    if erros:
        raise ValueError(f"Metadados inválidos em '{caminho_trial.name}': " + ", ".join(erros))

    return {
        "kata": str(kata),
        "participante": str(participante),
        "tratamento": str(tratamento),
    }


def encontrar_arquivos_solucao(caminho_trial: Path) -> List[Path]:
    """
    Encontra os arquivos de código-fonte Python da solução do trial,
    ignorando arquivos de teste unitário/aceitação (test_*.py, *_test.py).
    """
    arquivos = []
    for file_path in caminho_trial.rglob("*.py"):
        nome = file_path.name.lower()
        if (
            nome.startswith("test_")
            or nome.endswith("_test.py")
            or nome.startswith("test")
            or nome == "conftest.py"
        ):
            continue
        arquivos.append(file_path)

    return sorted(arquivos)


def calcular_metricas_radon(arquivos: List[Path]) -> Dict[str, Any]:
    """
    Calcula as métricas do Radon para os arquivos de código da solução.
    Agrega LOC/LLOC/SLOC/comentários/linhas em branco, complexidade ciclomática e MI.
    """
    total_loc = 0
    total_lloc = 0
    total_sloc = 0
    total_comentarios = 0
    total_linhas_brancas = 0

    todos_blocos_funcoes = []
    valores_mi = []

    for arq in arquivos:
        conteudo = arq.read_text(encoding="utf-8")

        # 1. Análise bruta (LOC, LLOC, SLOC, comments, blank)
        raw = radon_raw.analyze(conteudo)
        total_loc += raw.loc
        total_lloc += raw.lloc
        total_sloc += raw.sloc
        total_comentarios += raw.comments
        total_linhas_brancas += raw.blank

        # 2. Complexidade ciclomática (CC)
        blocos = radon_cc.cc_visit(conteudo)
        # Filtra funções e métodos
        funcoes = [b for b in blocos if isinstance(b, radon_visitors.Function)]
        todos_blocos_funcoes.extend(funcoes)

        # 3. Índice de Manutenibilidade (MI)
        # multi=True considera docstrings de múltiplas linhas na contagem de comentários
        mi = radon_mi.mi_visit(conteudo, multi=True)
        valores_mi.append(mi)

    n_funcoes = len(todos_blocos_funcoes)
    if n_funcoes > 0:
        cc_complexidades = [f.complexity for f in todos_blocos_funcoes]
        cc_total = sum(cc_complexidades)
        cc_max = max(cc_complexidades)
        cc_media = cc_total / n_funcoes
    else:
        cc_total = 0
        cc_max = 0
        cc_media = 0.0

    # Média do Índice de Manutenibilidade entre os arquivos da solução
    indice_manutenibilidade = (sum(valores_mi) / len(valores_mi)) if valores_mi else 0.0

    return {
        "loc": total_loc,
        "lloc": total_lloc,
        "sloc": total_sloc,
        "comentarios": total_comentarios,
        "linhas_brancas": total_linhas_brancas,
        "cc_media": round(cc_media, 2),
        "cc_max": cc_max,
        "cc_total": cc_total,
        "n_funcoes": n_funcoes,
        "indice_manutenibilidade": round(indice_manutenibilidade, 2),
    }


def executar_jscpd(caminho_trial: Path, verbose: bool = False) -> float:
    """
    Executa o jscpd via subprocess sobre a pasta do trial, gerando um relatório
    JSON temporário e extraindo a porcentagem total de duplicação.
    Configurado com --min-lines 5 --min-tokens 20 para sensibilidade a katas pequenos.
    Executa com cwd apontando para o diretório do trial para evitar problemas com
    caracteres especiais ou espaços em caminhos no Windows/Linux.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir).resolve()
        report_file = temp_dir_path / "jscpd-report.json"

        # Tenta invocar jscpd direto ou via npx caso não esteja no PATH global
        comando_base = ["jscpd"] if shutil.which("jscpd") else ["npx", "-y", "jscpd"]
        comando = comando_base + [
            ".",
            "--reporters",
            "json",
            "--output",
            str(temp_dir_path),
            "--min-lines",
            "5",
            "--min-tokens",
            "20",
            "--ignore",
            "**/test_*.py,**/*test*.py,**/__pycache__/**",
            "--silent",
        ]

        is_windows = sys.platform.startswith("win")
        resultado = subprocess.run(
            comando,
            cwd=str(caminho_trial.resolve()),
            shell=is_windows,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )

        if verbose and resultado.stderr:
            print(f"[{caminho_trial.name}] jscpd stderr: {resultado.stderr.strip()}")

        if not report_file.exists():
            if resultado.returncode != 0:
                raise RuntimeError(
                    f"Falha ao executar jscpd (código {resultado.returncode}): {resultado.stderr or resultado.stdout}"
                )
            return 0.0

        try:
            with open(report_file, "r", encoding="utf-8") as f:
                relatorio = json.load(f)
            pct = relatorio.get("statistics", {}).get("total", {}).get("percentage", 0.0)
            return round(float(pct), 2)
        except Exception as exc:
            raise RuntimeError(f"Erro ao processar relatório do jscpd: {exc}") from exc


def processar_trial(caminho_trial: Path, verbose: bool = False) -> Dict[str, Any]:
    """
    Processa um único trial: metadados, métricas Radon e duplicação jscpd.
    """
    trial_id = caminho_trial.name
    if verbose:
        print(f"-> Analisando trial '{trial_id}'...")

    meta = carregar_metadata(caminho_trial)
    arquivos_solucao = encontrar_arquivos_solucao(caminho_trial)

    if not arquivos_solucao:
        raise FileNotFoundError(f"Nenhum arquivo Python de solução (não-teste) encontrado em '{trial_id}'.")

    metricas_radon = calcular_metricas_radon(arquivos_solucao)
    duplicacao_pct = executar_jscpd(caminho_trial, verbose=verbose)

    registro = {
        "trial_id": trial_id,
        "kata": meta["kata"],
        "participante": meta["participante"],
        "tratamento": meta["tratamento"],
        **metricas_radon,
        "duplicacao_pct": duplicacao_pct,
    }

    if verbose:
        print(f"   [OK] CC média: {registro['cc_media']} | MI: {registro['indice_manutenibilidade']} | Duplicação: {registro['duplicacao_pct']}%")

    return registro


def coletar_metricas(
    dados_dir: Path, output_csv: Path, verbose: bool = False
) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
    """
    Varre o diretório de dados, processa todos os trials elegíveis e gera o CSV.
    Retorna a lista de registros de sucesso e a lista de falhas (trial_id, motivo).
    """
    if not dados_dir.exists() or not dados_dir.is_dir():
        sys.exit(f"Erro: O diretório de dados '{dados_dir}' não existe.")

    # Lista subpastas, ignorando 'gabaritos', itens ocultos e arquivos
    subpastas_candidatas = []
    for item in sorted(dados_dir.iterdir()):
        if not item.is_dir():
            continue
        nome = item.name.lower()
        if nome == "gabaritos" or nome.startswith(".") or nome.startswith("__"):
            continue
        subpastas_candidatas.append(item)

    if not subpastas_candidatas:
        print(f"Nenhuma subpasta de trial encontrada em '{dados_dir}'.")
        return [], []

    sucessos: List[Dict[str, Any]] = []
    falhas: List[Tuple[str, str]] = []

    print(f"Iniciando coleta de métricas em {len(subpastas_candidatas)} trial(s)...")

    for trial_path in subpastas_candidatas:
        try:
            registro = processar_trial(trial_path, verbose=verbose)
            sucessos.append(registro)
        except Exception as exc:
            falhas.append((trial_path.name, str(exc)))
            print(f"   [ERRO] Falha no trial '{trial_path.name}': {exc}")

    # Escreve o CSV se houver registros com sucesso
    if sucessos:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(sucessos)
        print(f"\nArquivo CSV gerado com sucesso em: '{output_csv}' ({len(sucessos)} registros)")

    return sucessos, falhas


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dados-dir",
        type=str,
        default="dados",
        help="Caminho para o diretório contendo os trials (default: 'dados')",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="metrics.csv",
        help="Caminho para o arquivo CSV de saída (default: 'metrics.csv')",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Exibe logs detalhados do processamento de cada trial",
    )

    args = parser.parse_args()

    dados_path = Path(args.dados_dir).resolve()
    output_path = Path(args.output).resolve()

    sucessos, falhas = coletar_metricas(dados_path, output_path, verbose=args.verbose)

    print("\n" + "=" * 60)
    print(" RESUMO DA COLETA DE MÉTRICAS ")
    print("=" * 60)
    print(f" Trials analisados com sucesso: {len(sucessos)}")
    print(f" Trials com falhas:             {len(falhas)}")

    if falhas:
        print("\nDetalhamento das falhas:")
        for trial_nome, motivo in falhas:
            print(f" - [{trial_nome}]: {motivo}")

    print("=" * 60)


if __name__ == "__main__":
    main()
