"""Execução instrumentada do pipeline de outro grupo (sem rede: comandos Python locais)."""
import csv
import json
import sys

import pandas as pd

from replicacao.executar import main, registrar_execucao, sortear_subamostra


def test_subamostra_reproduzivel(tmp_path):
    caminho = tmp_path / "dataset_deles.csv"
    pd.DataFrame({"repo": [f"o/r{i}" for i in range(100)], "x": range(100)}).to_csv(caminho, index=False)
    a = sortear_subamostra(caminho, n=30)
    b = sortear_subamostra(caminho, n=30)
    assert len(a) == 30 and a["full_name"].is_unique
    assert a.equals(b)                                    # mesma semente, mesma amostra
    assert len(sortear_subamostra(caminho, n=500)) == 100  # n maior que o dataset


def test_execucao_com_sucesso_gera_log_e_ambiente_sem_issue(tmp_path):
    r = registrar_execucao([sys.executable, "-c", "print('pipeline ok')"], tmp_path, destino=tmp_path)
    assert r["codigo"] == 0
    pasta = r["pasta_evidencias"]
    assert "pipeline ok" in (pasta / "log_execucao.txt").read_text(encoding="utf-8")
    ambiente = json.loads((pasta / "ambiente.json").read_text(encoding="utf-8"))
    assert ambiente["python"] and "pip_freeze" in ambiente
    assert not (pasta / "issue.md").exists()


def test_execucao_com_falha_gera_rascunho_de_issue_e_historico(tmp_path):
    comando = [sys.executable, "-c", "import sys; print('coletando...'); sys.exit('KeyError: GITHUB_TOKEN')"]
    r = registrar_execucao(comando, tmp_path, destino=tmp_path)
    assert r["codigo"] != 0
    issue = (r["pasta_evidencias"] / "issue.md").read_text(encoding="utf-8")
    assert "KeyError: GITHUB_TOKEN" in issue and "Comando executado" in issue

    with open(tmp_path / "execucoes.csv", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    assert len(linhas) == 1 and linhas[0]["codigo_saida"] == str(r["codigo"])


def test_comando_inexistente_e_registrado_como_falha(tmp_path):
    r = registrar_execucao(["comando-que-nao-existe-xyz"], tmp_path, destino=tmp_path)
    assert r["codigo"] == 127
    assert (r["pasta_evidencias"] / "issue.md").exists()


def test_cli_subamostra(tmp_path):
    caminho = tmp_path / "d.csv"
    pd.DataFrame({"full_name": [f"o/r{i}" for i in range(40)]}).to_csv(caminho, index=False)
    saida = tmp_path / "sub.csv"
    assert main(["subamostra", "--dataset", str(caminho), "--saida", str(saida)]) == 0
    assert len(pd.read_csv(saida)) == 30
