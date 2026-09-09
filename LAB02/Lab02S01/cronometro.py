"""
Script de cronometragem e coleta de dados de um trial do experimento LAB02.

Uso:
    python cronometro.py --pessoa Ana --kata kata1_validador_cofre --tratamento com_ia

Fluxo:
    1. Copia o template do kata (katas/<kata>/) para uma pasta de trial isolada
       em Lab02S02/trials/<pessoa>_<kata>_<tratamento>/.
    2. Ao pressionar Enter, inicia a cronometragem.
    3. A pessoa implementa solucao.py normalmente (com ou sem IA, conforme o
       tratamento) nessa pasta de trial.
    4. Ao terminar (ou ao ser avisada que os 35 minutos acabaram), pressiona
       Enter novamente para parar o cronometro.
    5. O script roda pytest sobre os testes de aceitacao do kata e registra o
       resultado em dados/resultados.csv.

Trial que atinge o time-box eh registrado como censurado no proprio tempo
limite (nao descartado), conforme pedido no enunciado do laboratorio.
"""

import argparse
import csv
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
KATAS_DIR = BASE_DIR / "katas"
TRIALS_DIR = BASE_DIR.parent / "Lab02S02" / "trials"
RESULTADOS_CSV = BASE_DIR / "dados" / "resultados.csv"

CSV_HEADER = [
    "timestamp",
    "pessoa",
    "kata",
    "tratamento",
    "tempo_segundos",
    "censurado",
    "testes_passando",
    "testes_total",
]

def preparar_pasta_trial(kata: str, pessoa: str, tratamento: str) -> Path:
    origem = KATAS_DIR / kata
    if not origem.is_dir():
        disponiveis = ", ".join(sorted(p.name for p in KATAS_DIR.iterdir() if p.is_dir()))
        sys.exit(f"Kata '{kata}' nao encontrado. Katas disponiveis: {disponiveis}")

    destino = TRIALS_DIR / f"{pessoa}_{kata}_{tratamento}"
    if destino.exists():
        sys.exit(
            f"A pasta de trial '{destino}' ja existe. Remova-a ou escolha "
            "outro nome de pessoa/tratamento antes de rodar de novo."
        )

    destino.mkdir(parents=True)
    for arquivo in origem.glob("*.py"):
        shutil.copy(arquivo, destino / arquivo.name)
    return destino


def avisar_quando_o_tempo_acabar(timeout_segundos: float, parar_evento: threading.Event) -> None:
    if parar_evento.wait(timeout_segundos):
        return
    print("\n*** TEMPO ESGOTADO! Finalize o que puder e pressione ENTER para encerrar o trial. ***\n")


def cronometrar(timeout_minutos: float) -> tuple[float, bool]:
    input("Pressione ENTER para iniciar o cronometro...")
    inicio = time.time()

    parar_evento = threading.Event()
    aviso = threading.Thread(
        target=avisar_quando_o_tempo_acabar,
        args=(timeout_minutos * 60, parar_evento),
        daemon=True,
    )
    aviso.start()

    input("Trial em andamento. Pressione ENTER quando terminar (ou apos o aviso de tempo esgotado)...")
    fim = time.time()
    parar_evento.set()

    tempo_decorrido = fim - inicio
    timeout_segundos = timeout_minutos * 60
    censurado = tempo_decorrido >= timeout_segundos
    tempo_registrado = min(tempo_decorrido, timeout_segundos)
    return tempo_registrado, censurado


def rodar_testes(pasta_trial: Path) -> tuple[int, int]:
    resultado = subprocess.run(
        [sys.executable, "-m", "pytest", str(pasta_trial), "-q", "--no-header"],
        capture_output=True,
        text=True,
    )
    saida = resultado.stdout + resultado.stderr

    passed = failed = errors = 0
    m = re.search(r"(\d+) passed", saida)
    if m:
        passed = int(m.group(1))
    m = re.search(r"(\d+) failed", saida)
    if m:
        failed = int(m.group(1))
    m = re.search(r"(\d+) error", saida)
    if m:
        errors = int(m.group(1))

    total = passed + failed + errors
    print(saida)
    return passed, total


def registrar_resultado(
    pessoa: str,
    kata: str,
    tratamento: str,
    tempo_segundos: float,
    censurado: bool,
    testes_passando: int,
    testes_total: int,
) -> None:
    RESULTADOS_CSV.parent.mkdir(parents=True, exist_ok=True)
    arquivo_novo = not RESULTADOS_CSV.exists()

    with open(RESULTADOS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if arquivo_novo:
            writer.writerow(CSV_HEADER)
        writer.writerow(
            [
                datetime.now().isoformat(timespec="seconds"),
                pessoa,
                kata,
                tratamento,
                f"{tempo_segundos:.1f}",
                censurado,
                testes_passando,
                testes_total,
            ]
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pessoa", required=True, help="Nome do integrante que esta fazendo o trial")
    parser.add_argument("--kata", required=True, help="Nome da pasta do kata (ex.: kata1_validador_cofre)")
    parser.add_argument("--tratamento", required=True, choices=["com_ia", "sem_ia"])
    parser.add_argument(
        "--timeout",
        type=float,
        default=35,
        help="Time-box em minutos (default 35; so pode ser reduzido, nunca aumentado)",
    )
    args = parser.parse_args()

    if args.timeout > 35:
        sys.exit("O time-box nao pode ser maior que 35 minutos (enunciado do laboratorio).")

    pasta_trial = preparar_pasta_trial(args.kata, args.pessoa, args.tratamento)
    print(f"Pasta do trial criada em: {pasta_trial}")
    print(f"Implemente a solucao em: {pasta_trial / 'solucao.py'}")

    tempo_segundos, censurado = cronometrar(args.timeout)
    testes_passando, testes_total = rodar_testes(pasta_trial)

    registrar_resultado(
        pessoa=args.pessoa,
        kata=args.kata,
        tratamento=args.tratamento,
        tempo_segundos=tempo_segundos,
        censurado=censurado,
        testes_passando=testes_passando,
        testes_total=testes_total,
    )

    print(f"Tempo registrado: {tempo_segundos:.1f}s (censurado={censurado})")
    print(f"Testes: {testes_passando}/{testes_total} passando")
    print(f"Resultado salvo em: {RESULTADOS_CSV}")


if __name__ == "__main__":
    main()
