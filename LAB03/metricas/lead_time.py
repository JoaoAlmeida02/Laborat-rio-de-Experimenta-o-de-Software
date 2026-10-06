from statistics import median

from metricas.datas import horas, para_datetime


def _comparaveis(entregas):
    return [e for e in entregas if e.get("commits")]


def lead_time_por_release(entregas):
    valores = []
    for e in _comparaveis(entregas):
        data = para_datetime(e["data"])
        mais_antigo = min(para_datetime(c["data"]) for c in e["commits"])
        valores.append(horas(data - mais_antigo))
    return valores


def lead_time_por_commit(entregas):
    valores = []
    for e in _comparaveis(entregas):
        data = para_datetime(e["data"])
        valores.extend(horas(data - para_datetime(c["data"])) for c in e["commits"])
    return valores


def mediana(valores):
    return median(valores) if valores else None


def lead_time_release(entregas):
    return mediana(lead_time_por_release(entregas))


def lead_time_commit(entregas):
    return mediana(lead_time_por_commit(entregas))


def contar_ignoradas(entregas):
    contagem = {"sem_anterior": 0, "compare_404": 0, "sem_commits": 0}
    for e in entregas:
        if e.get("commits") == []:
            contagem["sem_commits"] += 1
        elif e.get("commits") is None:
            motivo = e.get("motivo") or "sem_anterior"
            contagem[motivo] = contagem.get(motivo, 0) + 1
    return contagem
