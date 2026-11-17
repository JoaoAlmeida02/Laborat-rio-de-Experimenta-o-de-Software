"""Testes offline de scripts/poder.py."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from poder import ler_piloto, menor_k, poder_por_k, sigma_log_agrupado, sigma_superior, simular_tost  # noqa: E402


def test_sigma_agrupado_recupera_sigma_verdadeiro():
    rng = np.random.default_rng(1)
    linhas = [{"tratamento": f"T{i}", "rps": float(np.exp(rng.normal(5, 0.05)))} for i in range(1, 5) for _ in range(200)]
    sigma, gl = sigma_log_agrupado(pd.DataFrame(linhas), "rps")
    assert sigma == pytest.approx(0.05, rel=0.1)
    assert gl == 796


def test_sigma_superior_e_maior_que_o_estimado():
    assert sigma_superior(0.05, 4) > 0.05


def test_piloto_com_uma_repeticao_por_tratamento_falha():
    df = pd.DataFrame({"tratamento": ["T1", "T2", "T3", "T4"], "rps": [10.0, 11.0, 12.0, 13.0]})
    with pytest.raises(ValueError):
        sigma_log_agrupado(df, "rps")


def test_poder_aumenta_com_k_e_cai_com_sigma():
    a = poder_por_k(0.05, [3, 20], reps=3000)
    assert a.loc[1, "poder_equiv_efeito0"] > a.loc[0, "poder_equiv_efeito0"]
    b = poder_por_k(0.15, [20], reps=3000)
    assert b.loc[0, "poder_equiv_efeito0"] < a.loc[1, "poder_equiv_efeito0"]


def test_efeito_real_maior_que_a_margem_nao_e_declarado_equivalente():
    poder_eq, poder_dif = simular_tost(30, 0.03, efeito=0.10, reps=3000)
    assert poder_eq < 0.05  # H0 (não equivalência) é verdadeira: taxa de erro tipo I <= alfa
    assert poder_dif > 0.95


def test_erro_tipo1_do_tost_na_borda_da_margem_fica_perto_de_alfa():
    poder_eq, _ = simular_tost(10, 0.05, efeito=0.05, reps=20000)
    assert poder_eq <= 0.06


def test_menor_k_devolve_none_se_ninguem_atinge():
    df = poder_por_k(0.5, [2, 3], reps=1000)
    assert menor_k(df, alvo=0.99) is None


def test_ler_piloto_sem_pasta_devolve_none(tmp_path):
    assert ler_piloto(tmp_path / "nao_existe") is None
