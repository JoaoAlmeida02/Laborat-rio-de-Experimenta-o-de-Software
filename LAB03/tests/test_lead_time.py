import pytest

from metricas.lead_time import (
    contar_ignoradas,
    lead_time_commit,
    lead_time_release,
    lead_time_por_commit,
    lead_time_por_release,
    mediana,
)

DIA = 24.0


def commit(data):
    return {"sha": data, "data": f"{data}T00:00:00Z", "mensagem": ""}


@pytest.fixture
def release_v11():
    return {
        "tag": "v1.1",
        "data": "2025-03-15T00:00:00Z",
        "commits": [commit("2025-03-02"), commit("2025-03-10"), commit("2025-03-14")],
    }


def test_variante_a_exemplo_enunciado(release_v11):
    assert lead_time_por_release([release_v11]) == [13 * DIA]


def test_variante_b_exemplo_enunciado(release_v11):
    assert sorted(lead_time_por_commit([release_v11])) == [1 * DIA, 5 * DIA, 13 * DIA]


def test_mediana_por_repositorio(release_v11):
    v12 = {"tag": "v1.2", "data": "2025-03-20T00:00:00Z", "commits": [commit("2025-03-19")]}
    assert lead_time_release([release_v11, v12]) == (13 * DIA + 1 * DIA) / 2
    # variante b: valores 13, 5, 1, 1 dias -> mediana 3 dias
    assert lead_time_commit([release_v11, v12]) == 3 * DIA


def test_commit_antigo_esquecido_explode_a_mas_nao_b():
    entregas = [
        {"tag": "v2", "data": "2025-06-30T00:00:00Z",
         "commits": [commit("2025-01-01")] + [commit("2025-06-29")] * 9},
    ]
    assert lead_time_release(entregas) > 150 * DIA
    assert lead_time_commit(entregas) == 1 * DIA


def test_release_sem_commits_novos_fica_fora():
    entregas = [{"tag": "v1.0.1", "data": "2025-03-15T00:00:00Z", "commits": []}]
    assert lead_time_por_release(entregas) == []
    assert lead_time_release(entregas) is None
    assert contar_ignoradas(entregas)["sem_commits"] == 1


def test_repositorio_com_uma_unica_release():
    entregas = [{"tag": "v1.0", "data": "2025-03-15T00:00:00Z", "commits": None, "motivo": "sem_anterior"}]
    assert lead_time_release(entregas) is None
    assert lead_time_commit(entregas) is None
    assert contar_ignoradas(entregas) == {"sem_anterior": 1, "compare_404": 0, "sem_commits": 0}


def test_compare_404_contado_separadamente(release_v11):
    perdida = {"tag": "v1.0", "data": "2025-03-01T00:00:00Z", "commits": None, "motivo": "compare_404"}
    assert lead_time_por_release([perdida, release_v11]) == [13 * DIA]
    assert contar_ignoradas([perdida, release_v11])["compare_404"] == 1


def test_mediana_vazia():
    assert mediana([]) is None
