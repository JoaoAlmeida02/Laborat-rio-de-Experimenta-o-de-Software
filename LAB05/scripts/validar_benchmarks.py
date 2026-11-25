"""Modulo de validacao de integridade e sanidade dos benchmarks do LAB05."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

COLUNAS_OBRIGATORIAS = [
    "execucao_id",
    "ordem",
    "tratamento",
    "php_version",
    "mitigacao",
    "repeticao",
    "endpoint",
    "rps",
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "taxa_erro",
    "mem_php_media_mb",
    "mem_php_pico_mb",
    "timestamp_inicio",
    "timestamp_fim",
]

MAPA_TRATAMENTOS = {
    "T1": {"php_version": "8.4.26", "mitigacao": 0},
    "T2": {"php_version": "8.4.26", "mitigacao": 1},
    "T3": {"php_version": "8.4.27", "mitigacao": 0},
    "T4": {"php_version": "8.4.27", "mitigacao": 1},
}

ENDPOINTS_ESPERADOS = {"geral", "home", "rest_posts", "sessao_upload"}


@dataclass
class ResultadoValidacao:
    valido: bool = True
    total_linhas: int = 0
    total_execucoes: int = 0
    repeticoes_por_tratamento: dict[str, int] = field(default_factory=dict)
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    ambiente_validado: bool = False
    brutos_validados: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "valido": self.valido,
            "total_linhas": self.total_linhas,
            "total_execucoes": self.total_execucoes,
            "repeticoes_por_tratamento": self.repeticoes_por_tratamento,
            "erros": self.erros,
            "avisos": self.avisos,
            "ambiente_validado": self.ambiente_validado,
            "brutos_validados": self.brutos_validados,
        }


def _parsear_iso(ts_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        return None


def validar_ambiente_json(caminho_json: Path, res: ResultadoValidacao) -> bool:
    if not caminho_json.exists():
        res.avisos.append(f"Arquivo de ambiente '{caminho_json.name}' nao encontrado.")
        return False

    try:
        conteudo = json.loads(caminho_json.read_text(encoding="utf-8"))
    except Exception as exc:
        res.erros.append(f"Falha ao ler JSON de ambiente '{caminho_json}': {exc}")
        res.valido = False
        return False

    campos_obrigatorios = ["sistema_operacional", "cpu", "ram_total_gb", "ferramentas"]
    for c in campos_obrigatorios:
        if c not in conteudo:
            res.erros.append(f"Campo obrigatorio ausente no ambiente_maquina.json: '{c}'")
            res.valido = False

    res.ambiente_validado = res.valido
    return res.ambiente_validado


def validar_arquivos_brutos(
    dir_brutos: Path,
    execucoes_ids: set[str],
    res: ResultadoValidacao,
) -> None:
    if not dir_brutos.exists() or not dir_brutos.is_dir():
        res.avisos.append(f"Diretorio de brutos '{dir_brutos}' nao encontrado.")
        return

    encontrados = 0
    for exec_id in sorted(execucoes_ids):
        arquivo_bruto = dir_brutos / f"{exec_id}.json"
        if not arquivo_bruto.exists():
            res.erros.append(f"Arquivo bruto esperado ausente: {arquivo_bruto.name}")
            res.valido = False
            continue

        try:
            dados = json.loads(arquivo_bruto.read_text(encoding="utf-8"))
            medicao = dados.get("medicao")
            if not isinstance(medicao, dict):
                res.erros.append(f"Campo 'medicao' ausente ou invalido em {arquivo_bruto.name}")
                res.valido = False
            else:
                encontrados += 1
        except Exception as exc:
            res.erros.append(f"JSON invalido em {arquivo_bruto.name}: {exc}")
            res.valido = False

    res.brutos_validados = encontrados


def validar_csv_benchmarks(
    caminho_csv: Path,
    res: ResultadoValidacao,
) -> set[str]:
    execucoes_ids: set[str] = set()

    if not caminho_csv.exists():
        res.erros.append(f"Arquivo CSV nao encontrado: {caminho_csv}")
        res.valido = False
        return execucoes_ids

    linhas: list[dict[str, str]] = []
    try:
        with caminho_csv.open(mode="r", encoding="utf-8", newline="") as f:
            leitor = csv.DictReader(f)
            campos_presentes = leitor.fieldnames or []
            faltantes = [c for c in COLUNAS_OBRIGATORIAS if c not in campos_presentes]
            if faltantes:
                res.erros.append(f"Colunas obrigatorias ausentes no CSV: {', '.join(faltantes)}")
                res.valido = False
                return execucoes_ids

            for linha in leitor:
                linhas.append(linha)
    except Exception as exc:
        res.erros.append(f"Erro ao abrir CSV '{caminho_csv}': {exc}")
        res.valido = False
        return execucoes_ids

    res.total_linhas = len(linhas)
    if res.total_linhas == 0:
        res.erros.append("O arquivo CSV de benchmarks esta vazio.")
        res.valido = False
        return execucoes_ids

    execucoes_por_id: dict[str, list[dict[str, str]]] = {}
    contagem_tratamento_rep: dict[str, set[int]] = {t: set() for t in MAPA_TRATAMENTOS}

    for idx, row in enumerate(linhas, start=2):
        for col in COLUNAS_OBRIGATORIAS:
            val = row.get(col, "")
            if val is None or str(val).strip() == "":
                res.erros.append(f"Linha {idx}: campo obrigatorio '{col}' vazio.")
                res.valido = False

        exec_id = row.get("execucao_id", "").strip()
        if not exec_id:
            res.erros.append(f"Linha {idx}: execucao_id ausente.")
            res.valido = False
            continue

        execucoes_ids.add(exec_id)
        execucoes_por_id.setdefault(exec_id, []).append(row)

        try:
            ordem = int(row.get("ordem", "0"))
            if ordem < 1:
                res.erros.append(f"Linha {idx}: ordem={ordem} deve ser >= 1.")
                res.valido = False
        except ValueError:
            res.erros.append(f"Linha {idx}: ordem nao e inteiro valido.")
            res.valido = False

        tratamento = row.get("tratamento", "").strip()
        if tratamento not in MAPA_TRATAMENTOS:
            res.erros.append(f"Linha {idx}: tratamento '{tratamento}' desconhecido. Esperado T1..T4.")
            res.valido = False
        else:
            php_esperado = MAPA_TRATAMENTOS[tratamento]["php_version"]
            mit_esperada = MAPA_TRATAMENTOS[tratamento]["mitigacao"]
            php_real = row.get("php_version", "").strip()
            try:
                mit_real = int(row.get("mitigacao", "-1"))
            except ValueError:
                mit_real = -1

            if php_real != php_esperado:
                res.erros.append(
                    f"Linha {idx}: tratamento {tratamento} incompativel com php_version={php_real} (esperado {php_esperado})."
                )
                res.valido = False
            if mit_real != mit_esperada:
                res.erros.append(
                    f"Linha {idx}: tratamento {tratamento} incompativel com mitigacao={mit_real} (esperado {mit_esperada})."
                )
                res.valido = False

        try:
            repeticao = int(row.get("repeticao", "0"))
            if repeticao < 1:
                res.erros.append(f"Linha {idx}: repeticao={repeticao} deve ser >= 1.")
                res.valido = False
            elif tratamento in contagem_tratamento_rep:
                contagem_tratamento_rep[tratamento].add(repeticao)
        except ValueError:
            res.erros.append(f"Linha {idx}: repeticao nao e inteiro valido.")
            res.valido = False

        endpoint = row.get("endpoint", "").strip()
        if endpoint not in ENDPOINTS_ESPERADOS:
            res.erros.append(f"Linha {idx}: endpoint '{endpoint}' invalido.")
            res.valido = False

        try:
            rps = float(row.get("rps", "-1"))
            if rps < 0:
                res.erros.append(f"Linha {idx}: rps={rps} nao pode ser negativo.")
                res.valido = False
        except ValueError:
            res.erros.append(f"Linha {idx}: rps nao e float valido.")
            res.valido = False

        try:
            p50 = float(row.get("p50_ms", "-1"))
            p95 = float(row.get("p95_ms", "-1"))
            p99 = float(row.get("p99_ms", "-1"))
            if p50 < 0 or p95 < 0 or p99 < 0:
                res.erros.append(f"Linha {idx}: percentis de latencia nao podem ser negativos.")
                res.valido = False
            elif not (p50 <= p95 <= p99):
                res.erros.append(
                    f"Linha {idx}: violacao de ordenacao dos percentis: p50={p50} <= p95={p95} <= p99={p99} falhou."
                )
                res.valido = False
        except ValueError:
            res.erros.append(f"Linha {idx}: percentis de latencia devem ser valores numericos.")
            res.valido = False

        try:
            taxa_erro = float(row.get("taxa_erro", "-1"))
            if not (0.0 <= taxa_erro <= 1.0) and not math.isnan(taxa_erro):
                res.erros.append(f"Linha {idx}: taxa_erro={taxa_erro} fora do intervalo [0.0, 1.0].")
                res.valido = False
        except ValueError:
            res.erros.append(f"Linha {idx}: taxa_erro nao e float valido.")
            res.valido = False

        try:
            mem_media = float(row.get("mem_php_media_mb", "-1"))
            mem_pico = float(row.get("mem_php_pico_mb", "-1"))
            if mem_media < 0 or mem_pico < 0:
                res.erros.append(f"Linha {idx}: metricas de memoria nao podem ser negativas.")
                res.valido = False
            elif mem_media > (mem_pico + 0.05):
                res.erros.append(
                    f"Linha {idx}: mem_php_media_mb ({mem_media}) maior que mem_php_pico_mb ({mem_pico})."
                )
                res.valido = False
        except ValueError:
            res.erros.append(f"Linha {idx}: valores de memoria devem ser floats.")
            res.valido = False

        ts_ini = _parsear_iso(row.get("timestamp_inicio", ""))
        ts_fim = _parsear_iso(row.get("timestamp_fim", ""))
        if ts_ini is None:
            res.erros.append(f"Linha {idx}: timestamp_inicio invalido.")
            res.valido = False
        if ts_fim is None:
            res.erros.append(f"Linha {idx}: timestamp_fim invalido.")
            res.valido = False
        if ts_ini and ts_fim and ts_fim < ts_ini:
            res.erros.append(f"Linha {idx}: timestamp_fim anterior a timestamp_inicio.")
            res.valido = False

    res.total_execucoes = len(execucoes_por_id)
    for exec_id, rows_exec in execucoes_por_id.items():
        endpoints_vistos = {r.get("endpoint", "") for r in rows_exec}
        if endpoints_vistos != ENDPOINTS_ESPERADOS:
            faltam = ENDPOINTS_ESPERADOS - endpoints_vistos
            res.erros.append(f"Execucao {exec_id}: endpoints ausentes ({faltam}).")
            res.valido = False
        if len(rows_exec) != 4:
            res.erros.append(f"Execucao {exec_id}: esperado exatamente 4 linhas, obtido {len(rows_exec)}.")
            res.valido = False

    for t, reps in contagem_tratamento_rep.items():
        res.repeticoes_por_tratamento[t] = len(reps)
        if len(reps) > 0:
            esperado = set(range(1, len(reps) + 1))
            if reps != esperado:
                res.erros.append(
                    f"Tratamento {t}: repeticoes inconsistentes (presentes: {sorted(reps)}, esperado: {sorted(esperado)})."
                )
                res.valido = False

    return execucoes_ids


def validar_benchmarks(
    alvo: str | Path,
    checar_brutos: bool = True,
    checar_ambiente: bool = True,
) -> ResultadoValidacao:
    caminho = Path(alvo)
    res = ResultadoValidacao()

    if caminho.is_dir():
        candidatos_csv = ["completo.csv", "piloto.csv", "benchmarks.csv"]
        caminho_csv: Path | None = None
        for nome in candidatos_csv:
            p = caminho / nome
            if p.exists():
                caminho_csv = p
                break
        if caminho_csv is None:
            csvs = list(caminho.glob("*.csv"))
            if csvs:
                caminho_csv = csvs[0]
            else:
                res.erros.append(f"Nenhum arquivo CSV encontrado no diretorio '{caminho}'.")
                res.valido = False
                return res

        caminho_ambiente = caminho / "ambiente_maquina.json"
        dir_brutos = caminho / "brutos_k6"
    else:
        caminho_csv = caminho
        caminho_ambiente = caminho.parent / "ambiente_maquina.json"
        dir_brutos = caminho.parent / "brutos_k6"

    execucoes_ids = validar_csv_benchmarks(caminho_csv, res)

    if checar_ambiente and caminho_ambiente.exists():
        validar_ambiente_json(caminho_ambiente, res)

    if checar_brutos and dir_brutos.exists() and execucoes_ids:
        validar_arquivos_brutos(dir_brutos, execucoes_ids, res)

    return res


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Script de validacao da integridade dos benchmarks do experimento (LAB05)."
    )
    parser.add_argument(
        "--dados",
        type=Path,
        default=Path("LAB05/dados/piloto"),
        help="Caminho do diretorio de dados ou do arquivo CSV consolidado.",
    )
    parser.add_argument(
        "--ignorar-brutos",
        action="store_true",
        help="Nao falha se os arquivos brutos k6 nao estiverem presentes.",
    )
    parser.add_argument(
        "--ignorar-ambiente",
        action="store_true",
        help="Nao verifica o arquivo ambiente_maquina.json.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Exibe o resultado da validacao em formato JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)

    resultado = validar_benchmarks(
        alvo=args.dados,
        checar_brutos=not args.ignorar_brutos,
        checar_ambiente=not args.ignorar_ambiente,
    )

    if args.json:
        print(json.dumps(resultado.to_dict(), indent=2, ensure_ascii=False))
    else:
        print("=" * 60)
        print("LAB05 — Relatorio de Validacao dos Benchmarks")
        print("=" * 60)
        print(f"Alvo analisado          : {args.dados}")
        print(f"Status geral            : {'VALIDO' if resultado.valido else 'INVALIDO'}")
        print(f"Total de linhas no CSV  : {resultado.total_linhas}")
        print(f"Total de execucoes      : {resultado.total_execucoes}")
        print(f"Repeticoes / tratamento : {resultado.repeticoes_por_tratamento}")
        print(f"Ambiente validado       : {resultado.ambiente_validado}")
        print(f"Brutos k6 validados     : {resultado.brutos_validados}")

        if resultado.avisos:
            print("\nAvisos:")
            for av in resultado.avisos:
                print(f"  [AVISO] {av}")

        if resultado.erros:
            print("\nErros encontrados:")
            for er in resultado.erros:
                print(f"  [ERRO]  {er}")
        print("=" * 60)

    return 0 if resultado.valido else 1


if __name__ == "__main__":
    raise SystemExit(main())
