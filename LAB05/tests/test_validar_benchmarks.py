"""Testes unitarios para o script de validacao de benchmarks (LAB05)."""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validar_benchmarks import (
    COLUNAS_OBRIGATORIAS,
    validar_ambiente_json,
    validar_benchmarks,
    validar_csv_benchmarks,
)


def _criar_linha_valida(
    exec_id="ord01_T1_rep01",
    ordem=1,
    tratamento="T1",
    php_version="8.4.26",
    mitigacao=0,
    repeticao=1,
    endpoint="geral",
    rps=120.5,
    p50_ms=45.2,
    p95_ms=88.1,
    p99_ms=115.4,
    taxa_erro=0.0,
    mem_media=140.2,
    mem_pico=155.0,
    ts_ini="2026-11-25T12:00:00+00:00",
    ts_fim="2026-11-25T12:01:30+00:00",
):
    return {
        "execucao_id": exec_id,
        "ordem": str(ordem),
        "tratamento": tratamento,
        "php_version": php_version,
        "mitigacao": str(mitigacao),
        "repeticao": str(repeticao),
        "endpoint": endpoint,
        "rps": str(rps),
        "p50_ms": str(p50_ms),
        "p95_ms": str(p95_ms),
        "p99_ms": str(p99_ms),
        "taxa_erro": str(taxa_erro),
        "mem_php_media_mb": str(mem_media),
        "mem_php_pico_mb": str(mem_pico),
        "timestamp_inicio": ts_ini,
        "timestamp_fim": ts_fim,
    }


def _gravar_csv(caminho: Path, linhas: list[dict]):
    with caminho.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS_OBRIGATORIAS)
        escritor.writeheader()
        escritor.writerows(linhas)


def test_validacao_csv_valido(tmp_path):
    caminho = tmp_path / "piloto.csv"
    linhas = []
    for ep in ["geral", "home", "rest_posts", "sessao_upload"]:
        linhas.append(_criar_linha_valida(endpoint=ep))
    _gravar_csv(caminho, linhas)

    res = validar_benchmarks(caminho, checar_brutos=False, checar_ambiente=False)
    assert res.valido is True
    assert res.total_linhas == 4
    assert res.total_execucoes == 1
    assert res.repeticoes_por_tratamento["T1"] == 1
    assert len(res.erros) == 0


def test_coluna_faltante_invalida(tmp_path):
    caminho = tmp_path / "incompleto.csv"
    with caminho.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=["execucao_id", "ordem"])
        escritor.writeheader()
        escritor.writerow({"execucao_id": "ord01_T1_rep01", "ordem": "1"})

    res = validar_benchmarks(caminho, checar_brutos=False, checar_ambiente=False)
    assert res.valido is False
    assert any("Colunas obrigatorias ausentes" in e for e in res.erros)


def test_percentis_invertidos_invalida(tmp_path):
    caminho = tmp_path / "percentil_invalido.csv"
    linhas = [
        _criar_linha_valida(endpoint="geral", p50_ms=100.0, p95_ms=90.0, p99_ms=120.0),
        _criar_linha_valida(endpoint="home"),
        _criar_linha_valida(endpoint="rest_posts"),
        _criar_linha_valida(endpoint="sessao_upload"),
    ]
    _gravar_csv(caminho, linhas)

    res = validar_benchmarks(caminho, checar_brutos=False, checar_ambiente=False)
    assert res.valido is False
    assert any("violacao de ordenacao dos percentis" in e for e in res.erros)


def test_taxa_erro_fora_dos_limites(tmp_path):
    caminho = tmp_path / "erro_invalido.csv"
    linhas = [
        _criar_linha_valida(endpoint="geral", taxa_erro=1.5),
        _criar_linha_valida(endpoint="home"),
        _criar_linha_valida(endpoint="rest_posts"),
        _criar_linha_valida(endpoint="sessao_upload"),
    ]
    _gravar_csv(caminho, linhas)

    res = validar_benchmarks(caminho, checar_brutos=False, checar_ambiente=False)
    assert res.valido is False
    assert any("taxa_erro" in e for e in res.erros)


def test_incompatibilidade_de_tratamento(tmp_path):
    caminho = tmp_path / "tratamento_errado.csv"
    linhas = [
        _criar_linha_valida(endpoint="geral", tratamento="T1", php_version="8.4.27"),
        _criar_linha_valida(endpoint="home", tratamento="T1", php_version="8.4.27"),
        _criar_linha_valida(endpoint="rest_posts", tratamento="T1", php_version="8.4.27"),
        _criar_linha_valida(endpoint="sessao_upload", tratamento="T1", php_version="8.4.27"),
    ]
    _gravar_csv(caminho, linhas)

    res = validar_benchmarks(caminho, checar_brutos=False, checar_ambiente=False)
    assert res.valido is False
    assert any("incompativel com php_version" in e for e in res.erros)


def test_endpoint_faltante_na_execucao(tmp_path):
    caminho = tmp_path / "endpoint_faltando.csv"
    linhas = [
        _criar_linha_valida(endpoint="geral"),
        _criar_linha_valida(endpoint="home"),
        _criar_linha_valida(endpoint="rest_posts"),
    ]
    _gravar_csv(caminho, linhas)

    res = validar_benchmarks(caminho, checar_brutos=False, checar_ambiente=False)
    assert res.valido is False
    assert any("endpoints ausentes" in e for e in res.erros)


def test_diretorio_completo_com_brutos_e_ambiente(tmp_path):
    dir_dados = tmp_path / "dados"
    dir_brutos = dir_dados / "brutos_k6"
    dir_dados.mkdir()
    dir_brutos.mkdir()

    exec_id = "ord01_T1_rep01"
    linhas = []
    for ep in ["geral", "home", "rest_posts", "sessao_upload"]:
        linhas.append(_criar_linha_valida(exec_id=exec_id, endpoint=ep))
    _gravar_csv(dir_dados / "piloto.csv", linhas)

    ambiente_json = dir_dados / "ambiente_maquina.json"
    ambiente_json.write_text(
        json.dumps({
            "sistema_operacional": {"sistema": "Windows"},
            "cpu": {"modelo": "AMD"},
            "ram_total_gb": 16.0,
            "ferramentas": {"docker": "29.8.2"},
        }),
        encoding="utf-8",
    )

    bruto_json = dir_brutos / f"{exec_id}.json"
    bruto_json.write_text(
        json.dumps({
            "medicao": {
                "geral": {"rps": 120.0},
                "endpoints": {"home": {"rps": 40.0}},
            }
        }),
        encoding="utf-8",
    )

    res = validar_benchmarks(dir_dados, checar_brutos=True, checar_ambiente=True)
    assert res.valido is True
    assert res.ambiente_validado is True
    assert res.brutos_validados == 1
    assert len(res.erros) == 0
