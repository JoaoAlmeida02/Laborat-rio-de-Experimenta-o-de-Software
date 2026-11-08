from simulacao import P0, ler_dados_reais, taxa_rejeicao

N_PEQUENOS = (10, 20, 30, 50, 100)


def calcular_erro_tipo1(n_real):
    linhas = []
    for n in (*N_PEQUENOS, n_real):
        erro_z, erro_binomial = taxa_rejeicao(P0, n)
        linhas.append({
            "n": n,
            "pergunta": "Q1" if n == n_real else "Q3",
            "erro_z": erro_z,
            "erro_binomial": erro_binomial,
        })
    return linhas


def main():
    n_real, _, _ = ler_dados_reais()
    print(f"{'n':>5} {'pergunta':>9} {'Teste Z':>9} {'Binomial':>9}")
    for linha in calcular_erro_tipo1(n_real):
        print(f"{linha['n']:>5} {linha['pergunta']:>9} {linha['erro_z']:>9.2%} {linha['erro_binomial']:>9.2%}")


if __name__ == "__main__":
    main()
