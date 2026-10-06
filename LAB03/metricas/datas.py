
from datetime import date, datetime, timedelta, timezone


def para_datetime(valor):
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def janela(inicio, fim):
    d_inicio = date.fromisoformat(str(inicio))
    d_fim = date.fromisoformat(str(fim)) + timedelta(days=1)
    return (
        datetime(d_inicio.year, d_inicio.month, d_inicio.day, tzinfo=timezone.utc),
        datetime(d_fim.year, d_fim.month, d_fim.day, tzinfo=timezone.utc),
    )


def dentro_janela(valor, inicio, fim):
    return inicio <= para_datetime(valor) < fim


def horas(delta):
    return delta.total_seconds() / 3600
