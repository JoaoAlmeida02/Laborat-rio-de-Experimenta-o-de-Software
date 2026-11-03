from math import asin, sqrt
from scipy.stats import binomtest, norm


def teste_z(x, n, p0=0.05):
    z = (x / n - p0) / sqrt(p0 * (1 - p0) / n)
    return z, norm.sf(z)


def teste_binomial(x, n, p0=0.05):
    return x, binomtest(int(x), int(n), p0, alternative="greater").pvalue


def h_cohen(p_hat, p0=0.05):
    return 2 * asin(sqrt(p_hat)) - 2 * asin(sqrt(p0))
