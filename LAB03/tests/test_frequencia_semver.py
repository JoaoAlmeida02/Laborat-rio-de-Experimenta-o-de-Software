from datetime import datetime, timezone

import pytest

from metricas.datas import dentro_janela, janela, para_datetime
from metricas.frequencia import deploy_frequency, semanas
from metricas.semver import parse_versao, somente_patch, tipo_mudanca


@pytest.fixture
def ano_2025():
    return janela("2025-01-01", "2025-12-31")


def test_janela_de_12_meses_tem_cerca_de_52_semanas(ano_2025):
    assert semanas(*ano_2025) == pytest.approx(52.14, abs=0.01)


def test_fim_da_janela_e_inclusivo(ano_2025):
    assert dentro_janela("2025-12-31T23:59:59Z", *ano_2025)
    assert not dentro_janela("2026-01-01T00:00:00Z", *ano_2025)
    assert not dentro_janela("2024-12-31T23:59:59Z", *ano_2025)


def test_deploy_frequency_conta_so_a_janela(ano_2025):
    entregas = [{"data": f"2025-{m:02d}-10T00:00:00Z"} for m in range(1, 13)]
    entregas.append({"data": "2024-06-01T00:00:00Z"})  # anterior: fora da janela
    assert deploy_frequency(entregas, *ano_2025) == pytest.approx(12 / 52.14, abs=1e-3)


def test_para_datetime_aceita_datetime_sem_fuso():
    assert para_datetime(datetime(2025, 1, 1)).tzinfo == timezone.utc


@pytest.mark.parametrize("tag, esperado", [
    ("v1.2.3", (1, 2, 3, None)),
    ("1.2.3-rc1", (1, 2, 3, "rc1")),
    ("release-1.2", (1, 2, 0, None)),
    ("pkg@2.0.1", (2, 0, 1, None)),
    ("nightly", None),
])
def test_parse_versao(tag, esperado):
    assert parse_versao(tag) == esperado


@pytest.mark.parametrize("anterior, nova, esperado", [
    ("v2.3.0", "v2.3.1", "patch"),
    ("v2.3.0", "v2.4.0", "minor"),
    ("v2.3.0", "v3.0.0", "major"),
    ("v2.3.0-rc1", "v2.3.0-rc2", "pre"),
    ("v2.3.0", "2.3.0", "igual"),
    ("v2.3.0", "latest", None),
])
def test_tipo_mudanca(anterior, nova, esperado):
    assert tipo_mudanca(anterior, nova) == esperado


def test_somente_patch():
    assert somente_patch("v2.3.0", "v2.3.1")
    assert not somente_patch("v2.4.0", "v2.5.0")
