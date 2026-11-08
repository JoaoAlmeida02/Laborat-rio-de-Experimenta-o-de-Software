import csv
from pathlib import Path

import numpy as np

from testes import h_cohen, teste_binomial, teste_z

BASE = Path(__file__).resolve().parent.parent
ALFA = 0.05
P0 = 0.05


def criar_rng(semente=42):
    return np.random.default_rng(semente)


def simular_falhas(n, p, reps=10_000, rng=None):
    if rng is None:
        rng = criar_rng()
    return rng.binomial(n, p, size=reps)


def taxa_rejeicao(p, n, reps=10_000, alfa=ALFA, p0=P0, rng=None):
    valores, contagens = np.unique(simular_falhas(n, p, reps, rng), return_counts=True)
    rejeicoes_z = sum(c for v, c in zip(valores, contagens) if teste_z(int(v), n, p0)[1] < alfa)
    rejeicoes_binomial = sum(c for v, c in zip(valores, contagens) if teste_binomial(int(v), n, p0)[1] < alfa)
    return float(rejeicoes_z / reps), float(rejeicoes_binomial / reps)


def ler_dados_reais(caminho=None):
    if caminho is None:
        caminho = BASE / "dados" / "ci_runs.csv"
    with caminho.open("r", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    n = len(linhas)
    x = sum(int(linha["falha"]) for linha in linhas)
    p_hat = x / n
    return n, x, p_hat


def decisao(p_valor, alfa=ALFA):
    return "Rejeita H0" if p_valor < alfa else "Não rejeita H0"


def imprimir_resultado(titulo, x, n, p0=P0, alfa=ALFA):
    z, p_z = teste_z(x, n, p0)
    x_bin, p_bin = teste_binomial(x, n, p0)
    h = h_cohen(x / n, p0)
    print(f"=== {titulo} ===")
    print(f"n = {n}, x = {x}, p_hat = {x / n:.4f} ({x / n:.2%}), h de Cohen = {h:.3f}")
    print(f"Teste Z         -> estatística z = {z:.3f} | p-valor = {p_z:.4f} | Decisão: {decisao(p_z, alfa)}")
    print(f"Binomial exato  -> estatística x = {x_bin} | p-valor = {p_bin:.4f} | Decisão: {decisao(p_bin, alfa)}")
    print()


def main():
    n, x_real, p_hat = ler_dados_reais()
    imprimir_resultado("Validação nos dados reais (pytest-dev/pytest)", x_real, n)

    rng = criar_rng(42)
    x_sim = int(simular_falhas(n, p_hat, reps=1, rng=rng)[0])
    imprimir_resultado(f"Exemplo simulado 1 (calibrado com dados reais: p = {p_hat:.4f}, n = {n})", x_sim, n)

    x_sim_efeito = int(simular_falhas(n, 0.09, reps=1, rng=rng)[0])
    imprimir_resultado(f"Exemplo simulado 2 (com efeito: p = 0.0900, n = {n})", x_sim_efeito, n)


if __name__ == "__main__":
    main()
