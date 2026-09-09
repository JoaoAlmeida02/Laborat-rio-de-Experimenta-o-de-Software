import sys

TIME_BOX_MINUTOS = 35
KATAS = [
    "kata1_validador_cofre",
    "kata2_rota_entregador",
    "kata3_compressor_log",
    "kata4_escalonador_plantao",
]
MATRIZ_TRIALS = {
    "Joao": [
        {"kata": "kata1_validador_cofre", "tratamento": "com_ia"},
        {"kata": "kata2_rota_entregador", "tratamento": "sem_ia"},
        {"kata": "kata3_compressor_log", "tratamento": "com_ia"},
        {"kata": "kata4_escalonador_plantao", "tratamento": "sem_ia"},
    ],
    "Lucas": [
        {"kata": "kata1_validador_cofre", "tratamento": "sem_ia"},
        {"kata": "kata2_rota_entregador", "tratamento": "com_ia"},
        {"kata": "kata3_compressor_log", "tratamento": "sem_ia"},
        {"kata": "kata4_escalonador_plantao", "tratamento": "com_ia"},
    ],
    "Vitor": [
        {"kata": "kata1_validador_cofre", "tratamento": "com_ia"},
        {"kata": "kata2_rota_entregador", "tratamento": "com_ia"},
        {"kata": "kata3_compressor_log", "tratamento": "sem_ia"},
        {"kata": "kata4_escalonador_plantao", "tratamento": "sem_ia"},
    ],
}

def obter_trials(pessoa: str) -> list[dict]:
    return MATRIZ_TRIALS.get(pessoa, [])

def validar_trial(pessoa: str, kata: str, tratamento: str) -> bool:
    trials_pessoa = obter_trials(pessoa)
    for trial in trials_pessoa:
        if trial["kata"] == kata and trial["tratamento"] == tratamento:
            return True
    return False

def listar_plano() -> None:
    print("=" * 60)
    print(" PLANO DE TRIALS DO EXPERIMENTO (MATRIZ CROSSOVER) ")
    print(f" Time-box: {TIME_BOX_MINUTOS} minutos por trial")
    print("=" * 60)
    for pessoa, trials in MATRIZ_TRIALS.items():
        print(f"\nIntegrante: {pessoa}")
        for i, t in enumerate(trials, start=1):
            print(f"  Trial {i}: Kata = {t['kata']} | Tratamento = {t['tratamento']}")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        nome_pessoa = sys.argv[1]
        trials = obter_trials(nome_pessoa)
        if not trials:
            print(f"Pessoa '{nome_pessoa}' nao encontrada na matriz.")
        else:
            print(f"Trials de {nome_pessoa}:")
            for t in trials:
                print(f" - {t['kata']}: {t['tratamento']}")
    else:
        listar_plano()
