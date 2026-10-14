"""Heurística de release corretiva, CFR (b) e avaliação contra a amostra-ouro."""
import pandas as pd
import pytest

from metricas.corretiva import (
    HEURISTICAS,
    commits_corretivos,
    eh_corretiva,
    HEURISTICA_PADRAO,
    commits_feature,
    heuristica_v0,
    heuristica_v1,
    heuristica_v2,
    heuristica_v3,
    heuristica_v4,
    mensagens_da_entrega,
)
from metricas.datas import janela
from metricas.falhas import avaliar_entregas, cfr_entrega, rework_rate
from rotulagem.avaliar_heuristica import avaliar, preparar_consenso, salvar


def entrega(tag, data, *mensagens):
    return {"tag": tag, "data": f"{data}T00:00:00Z",
            "commits": [{"sha": str(i), "data": f"{data}T00:00:00Z", "mensagem": m} for i, m in enumerate(mensagens)]}


@pytest.fixture
def ano_2025():
    return janela("2025-01-01", "2025-12-31")


@pytest.fixture
def exemplo_enunciado():
    """v2.3.0 seguida de patch com fix em 2 dias; v2.4.0 seguida de minor após 19 dias."""
    return [
        entrega("v2.3.0", "2025-05-10", "feat: exportar PDF"),
        entrega("v2.3.1", "2025-05-12", "fix: crash ao abrir arquivo"),
        entrega("v2.4.0", "2025-06-01", "feat: modo escuro"),
        entrega("v2.5.0", "2025-06-20", "feat: plugins"),
    ]


@pytest.mark.parametrize("mensagem, esperado", [
    ("fix: crash ao abrir arquivo", 1),
    ("Fixes #123", 1),
    ("bugfix in parser", 1),
    ("HOTFIX urgente", 1),
    ('Revert "feat: x"', 1),
    ("feat: add fixture loader", 0),
    ("chore: prefix names", 0),
    ("", 0),
])
def test_commits_corretivos(mensagem, esperado):
    assert commits_corretivos([mensagem]) == esperado


def test_versoes_da_heuristica():
    assert heuristica_v1("v2.3.0", "v2.3.1", ["docs: readme"])        # só patch basta na v1
    assert heuristica_v1("v2.3.0", "v2.4.0", ["fix: bug"])            # só fix basta na v1
    assert not heuristica_v2("v2.3.0", "v2.3.1", ["docs: readme"])    # v2 exige os dois
    assert heuristica_v2("v2.3.0", "v2.3.1", ["fix: bug"])
    assert heuristica_v3("v2.3.0", "v2.3.1", ["chore: deps"])
    assert not heuristica_v3("v2.3.0", "v2.3.1", ["feat: novo"])      # v3 rejeita patch com feature
    assert not heuristica_v1("nightly", "latest", [])                 # sem SemVer e sem fix
    assert heuristica_v0("v2.3.0", "v2.3.1", ["feat: novo"])        # v0 só olha a versão
    assert heuristica_v4("v2.3.0", "v2.3.1", ["feat: novo", "fix: bug"])  # empate feat x fix: corretiva
    assert not heuristica_v4("v2.3.0", "v2.3.1", ["feat: a", "feat: b", "fix: c"])
    assert not heuristica_v4("v2.3.0", "v2.4.0", ["fix: bug"])
    assert commits_feature(["feat: a", "Feature x", "fix: b"]) == 2
    assert set(HEURISTICAS) == {"v0", "v1", "v2", "v3", "v4"}
    assert HEURISTICA_PADRAO == "v4"
    assert eh_corretiva("1.0.0", "1.0.1", [], versao="v3")


def test_mensagens_da_entrega_sem_commits():
    assert mensagens_da_entrega({"commits": None}) == []


def test_cfr_entrega_exemplo_enunciado(exemplo_enunciado, ano_2025):
    _, fim = ano_2025
    contagem = avaliar_entregas(exemplo_enunciado, fim)
    # v2.3.0 falhou; v2.3.1 e v2.4.0 não (próxima fora do prazo ou não corretiva); v2.5.0 sem próxima
    assert contagem == {"falhas": 1, "avaliadas": 4, "censuradas": 0}
    assert cfr_entrega(exemplo_enunciado, fim) == 0.25


def test_correcao_depois_de_7_dias_nao_e_falha(ano_2025):
    _, fim = ano_2025
    entregas = [entrega("v1.0.0", "2025-03-01"), entrega("v1.0.1", "2025-03-09", "fix: bug")]
    assert avaliar_entregas(entregas, fim)["falhas"] == 0


def test_censura_dos_ultimos_7_dias(ano_2025):
    _, fim = ano_2025
    entregas = [
        entrega("v1.0.0", "2025-12-20"),
        entrega("v1.0.1", "2025-12-26", "fix: bug"),   # últimos 7 dias: censurada
        entrega("v1.0.2", "2025-12-30", "fix: bug"),   # últimos 7 dias: censurada
    ]
    contagem = avaliar_entregas(entregas, fim)
    assert contagem == {"falhas": 1, "avaliadas": 1, "censuradas": 2}
    assert cfr_entrega(entregas, fim) == 1.0


def test_cfr_entrega_sem_avaliaveis(ano_2025):
    _, fim = ano_2025
    assert cfr_entrega([entrega("v1.0.0", "2025-12-30")], fim) is None
    assert cfr_entrega([], fim) is None


def test_rework_rate(exemplo_enunciado):
    # pares: 2.3.0→2.3.1 (corretiva), 2.3.1→2.4.0, 2.4.0→2.5.0
    assert rework_rate(exemplo_enunciado) == pytest.approx(1 / 3)
    assert rework_rate([entrega("v1.0.0", "2025-01-01")]) is None


@pytest.fixture
def consenso_falso():
    return pd.DataFrame([
        {"repo": "o/r", "release_anterior": "v1.0.0", "release_tag": "v1.0.1", "corretiva_consenso": "sim"},
        {"repo": "o/r", "release_anterior": "v1.0.1", "release_tag": "v1.1.0", "corretiva_consenso": "nao"},
        {"repo": "o/r", "release_anterior": "v1.1.0", "release_tag": "v1.1.1", "corretiva_consenso": "nao"},
        {"repo": "o/r", "release_anterior": "v1.1.1", "release_tag": "v1.2.0", "corretiva_consenso": "sim"},
        {"repo": "o/r", "release_anterior": "-", "release_tag": "v1.0.0", "corretiva_consenso": "nao"},
        {"repo": "o/r", "release_anterior": "v1.2.0", "release_tag": "v1.2.1", "corretiva_consenso": "empate"},
    ])


def test_preparar_consenso_descarta_sem_anterior_e_empate(consenso_falso):
    df, descartados = preparar_consenso(consenso_falso)
    assert len(df) == 4 and descartados == 2


def test_avaliar_precisao_recall_f1(consenso_falso, tmp_path):
    df, _ = preparar_consenso(consenso_falso)
    mensagens = {
        "v1.0.1": ["fix: bug"],
        "v1.1.0": ["feat: x"],
        "v1.1.1": ["docs: readme"],
        "v1.2.0": ["feat: y"],
    }
    tabela, erros = avaliar(df, lambda repo, base, head: mensagens[head])
    v1 = tabela.set_index("versao").loc["v1"]
    # v1 marca v1.0.1 (VP) e v1.1.1 (FP); perde v1.2.0 (FN); acerta v1.1.0 (VN)
    assert (v1.vp, v1.fp, v1.fn, v1.vn) == (1, 1, 1, 1)
    assert v1.precisao == 0.5 and v1.recall == 0.5 and v1.f1 == 0.5
    assert set(erros["v1"]["tipo_erro"]) == {"falso_positivo", "falso_negativo"}

    salvar(tabela, erros, tmp_path)
    assert (tmp_path / "heuristicas_f1.csv").exists()
    assert (tmp_path / "erros_v2.csv").exists()
