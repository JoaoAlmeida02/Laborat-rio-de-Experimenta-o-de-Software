from metricas.datas import dentro_janela


def semanas(inicio, fim):
    return (fim - inicio).total_seconds() / (7 * 24 * 3600)


def entregas_na_janela(entregas, inicio, fim):
    return [e for e in entregas if dentro_janela(e["data"], inicio, fim)]


def deploy_frequency(entregas, inicio, fim):
    return len(entregas_na_janela(entregas, inicio, fim)) / semanas(inicio, fim)
