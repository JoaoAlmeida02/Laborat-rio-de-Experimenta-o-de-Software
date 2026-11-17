"""Testes offline (sem rede) das funções puras de scripts/evidencias_php.py."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evidencias_php import chave_versao, ler_data_php, situacao_do_ramo, versoes_da_correcao  # noqa: E402


def test_ler_data_php_independe_do_idioma():
    assert ler_data_php("21 Oct 2026") == date(2026, 10, 21)
    assert ler_data_php("3 Nov 2022") == date(2022, 11, 3)


def test_chave_versao_ordena_numericamente():
    assert sorted(["8.4.9", "8.4.27", "8.4.10"], key=chave_versao) == ["8.4.9", "8.4.10", "8.4.27"]


def test_versoes_da_correcao_encontra_vulneravel_e_corrigida():
    releases = {
        "8.4.25": date(2026, 8, 27),
        "8.4.26": date(2026, 9, 24),
        "8.4.27": date(2026, 10, 21),
    }
    assert versoes_da_correcao(releases) == ("8.4.26", "8.4.27")


def test_versoes_da_correcao_com_release_posterior():
    releases = {
        "8.4.26": date(2026, 9, 24),
        "8.4.27": date(2026, 10, 21),
        "8.4.28": date(2026, 11, 20),
    }
    assert versoes_da_correcao(releases) == ("8.4.26", "8.4.27")


def test_ramo_sem_correcao_devolve_ultima_versao():
    releases = {"8.1.33": date(2025, 7, 3), "8.1.34": date(2025, 12, 18)}
    assert versoes_da_correcao(releases) == ("8.1.34", None)


def test_situacao_do_ramo():
    hoje = date(2026, 11, 17)
    assert situacao_do_ramo(date(2026, 12, 31), date(2028, 12, 31), hoje) == "suporte ativo"
    assert situacao_do_ramo(date(2025, 12, 31), date(2027, 12, 31), hoje) == "somente correções de segurança"
    assert situacao_do_ramo(date(2023, 11, 25), date(2025, 12, 31), hoje) == "fim de vida"
