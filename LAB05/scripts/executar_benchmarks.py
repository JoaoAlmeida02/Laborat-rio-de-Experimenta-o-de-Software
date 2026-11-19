"""Orquestrador de benchmarks do experimento fatorial 2x2 (LAB05 - Integrante B).

Executa os 4 tratamentos (PHP 8.4.26 vs 8.4.27 × mitigação desligada vs ligada)
em ordem aleatória com semente fixa, reiniciando os contêineres e o banco a cada
repetição, rodando a carga k6 (30 s aquecimento + 60 s medição) e amostrando a
memória RSS do PHP-FPM durante a medição.

Uso típico (a partir da pasta LAB05):
    python scripts/executar_benchmarks.py --piloto
    python scripts/executar_benchmarks.py --k 10 --saida dados/completo/

Smoke test curto (1 tratamento, 1 repetição, carga curta):
    python scripts/executar_benchmarks.py --k 1 --tratamentos T1 --aquecimento 5 --medicao 10 --vus 2 --saida dados/piloto/smoke/

Estrutura preparada para a S02 (modo completo e retomada por execucao_id).
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import json
import logging
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import psutil  # type: ignore
except ImportError:
    psutil = None

# Diretórios padrão relativos à raiz LAB05/
RAIZ_LAB05 = Path(__file__).resolve().parents[1]
DIR_AMBIENTE = RAIZ_LAB05 / "ambiente"
COMPOSE_FILE = DIR_AMBIENTE / "docker-compose.yml"
DIR_K6 = DIR_AMBIENTE / "k6"
SCRIPT_K6 = DIR_K6 / "carga.js"

# Imagens fixadas utilizadas no experimento (registradas em ambiente_maquina.json)
IMAGENS_FIXADAS = {
    "php_vulneravel": "php:8.4.26-fpm",
    "php_corrigido": "php:8.4.27-fpm",
    "nginx": "nginx:1.27.5-alpine",
    "mariadb": "mariadb:11.4.13",
    "wordpress": "wordpress:6.9.4-fpm",
    "k6_docker": "grafana/k6:1.0.0",
}

# Definição dos 4 tratamentos do fatorial 2x2
TRATAMENTOS: dict[str, dict[str, Any]] = {
    "T1": {"php_version": "8.4.26", "mitigacao": 0, "descricao": "PHP 8.4.26 (vulnerável), mitigação desligada"},
    "T2": {"php_version": "8.4.26", "mitigacao": 1, "descricao": "PHP 8.4.26 (vulnerável), mitigação ligada"},
    "T3": {"php_version": "8.4.27", "mitigacao": 0, "descricao": "PHP 8.4.27 (corrigido), mitigação desligada"},
    "T4": {"php_version": "8.4.27", "mitigacao": 1, "descricao": "PHP 8.4.27 (corrigido), mitigação ligada"},
}

COLUNAS_CSV = [
    "execucao_id",
    "ordem",
    "tratamento",
    "php_version",
    "mitigacao",
    "repeticao",
    "endpoint",
    "rps",
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "taxa_erro",
    "mem_php_media_mb",
    "mem_php_pico_mb",
    "timestamp_inicio",
    "timestamp_fim",
]

ENDPOINTS_ORDEM = ["geral", "home", "rest_posts", "sessao_upload"]


@dataclass(frozen=True)
class ExecucaoPlano:
    """Representa uma unidade de execução (tratamento × repetição) já ordenada."""

    execucao_id: str
    ordem: int
    tratamento: str
    php_version: str
    mitigacao: int
    repeticao: int


def configurar_logger(caminho_log: Path) -> logging.Logger:
    """Configura log no terminal e em arquivo de erros/eventos."""
    logger = logging.getLogger("lab05.benchmarks")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formato = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    handler_console = logging.StreamHandler(sys.stdout)
    handler_console.setFormatter(formato)
    logger.addHandler(handler_console)

    caminho_log.parent.mkdir(parents=True, exist_ok=True)
    handler_arquivo = logging.FileHandler(caminho_log, encoding="utf-8")
    handler_arquivo.setFormatter(formato)
    logger.addHandler(handler_arquivo)

    return logger


def executar_comando(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
    checar: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Executa um comando externo retornando stdout/stderr em UTF-8."""
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=checar,
    )


def gerar_plano_execucoes(
    tratamentos: list[str],
    repeticoes: int,
    semente: int,
) -> list[ExecucaoPlano]:
    """Gera e embaralha de forma reprodutível a lista de execuções do experimento."""
    itens: list[tuple[str, int]] = []
    for codigo in tratamentos:
        if codigo not in TRATAMENTOS:
            raise ValueError(f"Tratamento desconhecido: {codigo}. Use T1, T2, T3 ou T4.")
        for rep in range(1, repeticoes + 1):
            itens.append((codigo, rep))

    rng = random.Random(semente)
    rng.shuffle(itens)

    plano: list[ExecucaoPlano] = []
    for ordem, (codigo, rep) in enumerate(itens, start=1):
        meta = TRATAMENTOS[codigo]
        exec_id = f"ord{ordem:02d}_{codigo}_rep{rep:02d}"
        plano.append(
            ExecucaoPlano(
                execucao_id=exec_id,
                ordem=ordem,
                tratamento=codigo,
                php_version=str(meta["php_version"]),
                mitigacao=int(meta["mitigacao"]),
                repeticao=rep,
            )
        )
    return plano


def detectar_modo_k6(modo_solicitado: str) -> str:
    """Define se o k6 será executado localmente ou via contêiner grafana/k6."""
    if modo_solicitado == "local":
        if shutil.which("k6") is None:
            raise RuntimeError("Modo --k6-modo local selecionado, mas o executável 'k6' não foi encontrado no PATH.")
        return "local"
    if modo_solicitado == "docker":
        return "docker"
    # modo == "auto"
    return "local" if shutil.which("k6") is not None else "docker"


def _obter_ram_total_gb() -> float | None:
    """Obtém a RAM total da máquina em GB usando psutil ou fallback nativo."""
    if psutil is not None:
        return round(psutil.virtual_memory().total / (1024**3), 2)

    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        mem = MEMORYSTATUSEX()
        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
            return round(mem.ullTotalPhys / (1024**3), 2)

    if hasattr(os, "sysconf"):
        try:
            paginas = os.sysconf("SC_PHYS_PAGES")
            tam_pagina = os.sysconf("SC_PAGE_SIZE")
            return round((paginas * tam_pagina) / (1024**3), 2)
        except (ValueError, OSError):
            pass
    return None


def _obter_modelo_cpu() -> str:
    """Obtém o nome comercial do processador (com fallback para Windows/Linux)."""
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as chave:
                nome, _ = winreg.QueryValueEx(chave, "ProcessorNameString")
                if str(nome).strip():
                    return str(nome).strip()
        except Exception:
            pass
        try:
            res = executar_comando(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)"],
                timeout=10,
                checar=False,
            )
            nome = res.stdout.strip()
            if nome:
                return nome
        except Exception:
            pass
    proc = platform.processor()
    return proc if proc else platform.machine()


def _versao_comando(cmd: list[str]) -> str:
    """Captura a primeira linha de saída de um comando de versão."""
    try:
        res = executar_comando(cmd, timeout=15, checar=False)
        saida = (res.stdout or res.stderr).strip()
        if not saida:
            return "indisponivel"
        for linha in saida.splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("WARNING:"):
                return linha
        return saida.splitlines()[0].strip()
    except Exception as exc:
        return f"indisponivel ({exc})"


def coletar_ambiente_maquina(caminho_saida: Path, modo_k6: str) -> dict[str, Any]:
    """Coleta informações de hardware, SO e versões das ferramentas e salva em JSON."""
    nucleos_fisicos = psutil.cpu_count(logical=False) if psutil is not None else None
    nucleos_logicos = os.cpu_count()

    if modo_k6 == "local":
        versao_k6 = _versao_comando(["k6", "version"])
    else:
        versao_k6 = f"docker ({IMAGENS_FIXADAS['k6_docker']})"

    dados = {
        "coletado_em_utc": datetime.now(timezone.utc).isoformat(),
        "sistema_operacional": {
            "sistema": platform.system(),
            "release": platform.release(),
            "versao": platform.version(),
            "arquitetura": platform.machine(),
            "plataforma": platform.platform(),
        },
        "cpu": {
            "modelo": _obter_modelo_cpu(),
            "nucleos_fisicos": nucleos_fisicos,
            "nucleos_logicos": nucleos_logicos,
        },
        "ram_total_gb": _obter_ram_total_gb(),
        "ferramentas": {
            "python": platform.python_version(),
            "psutil_instalado": psutil is not None,
            "docker": _versao_comando(["docker", "--version"]),
            "docker_compose": _versao_comando(["docker", "compose", "version"]),
            "k6_modo": modo_k6,
            "k6": versao_k6,
        },
        "imagens_fixadas": IMAGENS_FIXADAS,
    }

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    caminho_saida.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
    return dados


def montar_env_compose(php_version: str, mitigacao: int, porta: int) -> dict[str, str]:
    """Monta o dicionário de variáveis de ambiente para o Docker Compose."""
    env = os.environ.copy()
    env["PHP_VERSION"] = php_version
    env["MITIGACAO"] = str(mitigacao)
    env["NGINX_PORT"] = str(porta)
    return env


def derrubar_ambiente(env: dict[str, str]) -> None:
    """Remove contêineres, rede e volumes (incluindo banco) para estado limpo."""
    executar_comando(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "down", "-v", "--remove-orphans"],
        cwd=DIR_AMBIENTE,
        env=env,
        timeout=180,
        checar=True,
    )


def subir_ambiente(env: dict[str, str]) -> None:
    """Sobe os serviços do tratamento selecionado com build garantido."""
    executar_comando(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d", "--build"],
        cwd=DIR_AMBIENTE,
        env=env,
        timeout=600,
        checar=True,
    )


def _obter_container_id(servico: str, env: dict[str, str]) -> str:
    """Retorna o ID do contêiner de um serviço do Docker Compose."""
    res = executar_comando(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "ps", "-a", "-q", servico],
        cwd=DIR_AMBIENTE,
        env=env,
        timeout=30,
        checar=True,
    )
    cid = res.stdout.strip().splitlines()[0] if res.stdout.strip() else ""
    if not cid:
        raise RuntimeError(f"Contêiner do serviço '{servico}' não encontrado.")
    return cid


def _inspecionar_container(container_id: str) -> dict[str, Any]:
    """Retorna o estado detalhado (State) de um contêiner via docker inspect."""
    res = executar_comando(
        ["docker", "inspect", "--format", "{{json .State}}", container_id],
        timeout=30,
        checar=True,
    )
    return json.loads(res.stdout.strip())


def aguardar_ambiente_pronto(
    execucao: ExecucaoPlano,
    env: dict[str, str],
    porta: int,
    logger: logging.Logger,
    timeout_seg: int = 240,
) -> str:
    """Aguarda healthchecks de mariadb/php/nginx, término do setup e verifica endpoints HTTP.

    Retorna o container_id do serviço php para amostragem de memória.
    """
    inicio = time.monotonic()
    servicos_saude = ["mariadb", "php", "nginx"]

    while True:
        decorrido = time.monotonic() - inicio
        if decorrido > timeout_seg:
            raise TimeoutError(f"Timeout ({timeout_seg}s) aguardando serviços saudáveis para {execucao.execucao_id}.")

        todos_ok = True
        for servico in servicos_saude:
            try:
                cid = _obter_container_id(servico, env)
                estado = _inspecionar_container(cid)
            except Exception:
                todos_ok = False
                break

            saude = (estado.get("Health") or {}).get("Status")
            status = estado.get("Status")
            if status in ("exited", "dead") or saude == "unhealthy":
                raise RuntimeError(f"Serviço '{servico}' falhou durante inicialização (status={status}, health={saude}).")
            if saude != "healthy":
                todos_ok = False
                break

        if todos_ok:
            # Verifica se o setup (WP-CLI) concluiu com sucesso
            try:
                setup_id = _obter_container_id("setup", env)
                estado_setup = _inspecionar_container(setup_id)
                status_setup = estado_setup.get("Status")
                exit_code = estado_setup.get("ExitCode")
                if status_setup == "exited":
                    if exit_code != 0:
                        logs = executar_comando(
                            ["docker", "logs", "--tail", "40", setup_id],
                            timeout=15,
                            checar=False,
                        ).stdout
                        raise RuntimeError(f"Serviço 'setup' saiu com código {exit_code}:\n{logs}")
                    break
            except RuntimeError:
                raise
            except Exception:
                pass

        time.sleep(2)

    # Confirma via endpoint GET /?lab05_upload=1 a versão efetiva do PHP e a diretiva de mitigação
    url_check = f"http://localhost:{porta}/?lab05_upload=1"
    esperado_upload_progress = "0" if execucao.mitigacao == 1 else "1"

    ultima_exc: Exception | None = None
    for _ in range(15):
        try:
            with urllib.request.urlopen(url_check, timeout=10) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    versao_real = str(payload.get("php_version", ""))
                    diretiva_real = str(payload.get("session_upload_progress_enabled", "")).strip().lower()
                    diretiva_norm = "0" if diretiva_real in ("0", "", "off", "false") else "1"

                    if versao_real != execucao.php_version:
                        raise RuntimeError(
                            f"Versão PHP divergente! Esperado={execucao.php_version}, obtido={versao_real}."
                        )
                    if diretiva_norm != esperado_upload_progress:
                        raise RuntimeError(
                            f"Diretiva session.upload_progress.enabled divergente! "
                            f"Esperado={esperado_upload_progress} (mitigacao={execucao.mitigacao}), obtido={diretiva_real}."
                        )
                    logger.info(
                        "Ambiente validado via HTTP: PHP=%s | session.upload_progress.enabled=%s",
                        versao_real,
                        diretiva_norm,
                    )
                    return _obter_container_id("php", env)
        except RuntimeError:
            raise
        except Exception as exc:
            ultima_exc = exc
            time.sleep(2)

    raise RuntimeError(f"Endpoint de verificação {url_check} não respondeu: {ultima_exc}")


def _converter_tamanho_docker_para_mb(texto: str) -> float | None:
    """Converte strings como '142.3MiB / 512MiB' ou '0.25GiB' para MB decimais (MiB)."""
    parte = texto.split("/")[0].strip()
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]+)$", parte)
    if not m:
        return None
    valor = float(m.group(1))
    unidade = m.group(2).lower()
    fatores = {
        "b": 1 / (1024 * 1024),
        "kb": 1 / 1000,
        "kib": 1 / 1024,
        "mb": 1.0,
        "mib": 1.0,
        "gb": 1000.0,
        "gib": 1024.0,
    }
    return valor * fatores.get(unidade, 1.0)


def ler_memoria_php_fpm_mb(container_id: str) -> float | None:
    """Lê a soma do RSS (em MB) dos processos php-fpm via docker top, com fallback para docker stats."""
    # Tentativa 1: soma exata do RSS dos processos php-fpm via docker top
    try:
        res = executar_comando(
            ["docker", "top", container_id, "-o", "rss,comm"],
            timeout=10,
            checar=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            linhas = res.stdout.strip().splitlines()
            soma_kb = 0.0
            encontrou = False
            for linha in linhas[1:]:
                partes = linha.split()
                if len(partes) >= 2 and partes[0].isdigit():
                    comm = partes[1].lower()
                    if "php" in comm:
                        soma_kb += float(partes[0])
                        encontrou = True
            if encontrou:
                return soma_kb / 1024.0
    except Exception:
        pass

    # Tentativa 2 (fallback): docker stats do contêiner php
    try:
        res = executar_comando(
            ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container_id],
            timeout=10,
            checar=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return _converter_tamanho_docker_para_mb(res.stdout.strip())
    except Exception:
        pass

    return None


class MonitorMemoriaPhpFpm:
    """Thread de amostragem periódica da memória do PHP-FPM apenas na fase de medição."""

    def __init__(self, container_id: str, atraso_inicial_seg: float, intervalo_seg: float = 1.5) -> None:
        self.container_id = container_id
        self.atraso_inicial_seg = max(0.0, atraso_inicial_seg)
        self.intervalo_seg = max(0.5, intervalo_seg)
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self.amostras_mb: list[float] = []

    def iniciar(self) -> None:
        self._thread.start()

    def parar_e_resumir(self) -> tuple[float, float, int]:
        """Encerra a amostragem e devolve (media_mb, pico_mb, quantidade_amostras)."""
        self._parar.set()
        self._thread.join(timeout=15)
        if not self.amostras_mb:
            return 0.0, 0.0, 0
        media = sum(self.amostras_mb) / len(self.amostras_mb)
        pico = max(self.amostras_mb)
        return round(media, 3), round(pico, 3), len(self.amostras_mb)

    def _loop(self) -> None:
        # Aguarda o aquecimento terminar antes de começar a registrar amostras
        if self.atraso_inicial_seg > 0 and self._parar.wait(self.atraso_inicial_seg):
            return

        while not self._parar.is_set():
            t0 = time.monotonic()
            leitura = ler_memoria_php_fpm_mb(self.container_id)
            if leitura is not None:
                self.amostras_mb.append(leitura)
            espera = max(0.1, self.intervalo_seg - (time.monotonic() - t0))
            if self._parar.wait(espera):
                break


def executar_k6(
    caminho_resumo_json: Path,
    vus: int,
    aquecimento_seg: int,
    medicao_seg: int,
    porta: int,
    modo_k6: str,
) -> dict[str, Any]:
    """Executa o teste de carga k6 (local ou via Docker) e retorna o JSON de sumário."""
    caminho_resumo_json.parent.mkdir(parents=True, exist_ok=True)
    if caminho_resumo_json.exists():
        caminho_resumo_json.unlink()

    timeout_total = aquecimento_seg + medicao_seg + 180

    if modo_k6 == "local":
        env = os.environ.copy()
        env.update(
            {
                "BASE_URL": f"http://localhost:{porta}",
                "VUS": str(vus),
                "WARMUP_SEC": str(aquecimento_seg),
                "MEDICAO_SEC": str(medicao_seg),
                "SUMMARY_PATH": str(caminho_resumo_json),
            }
        )
        res = executar_comando(
            ["k6", "run", str(SCRIPT_K6)],
            cwd=RAIZ_LAB05,
            env=env,
            timeout=timeout_total,
            checar=False,
        )
    else:
        # Executa k6 via contêiner oficial com versão fixada, mirando o host Windows/WSL2
        nome_arquivo = caminho_resumo_json.name
        dir_brutos = caminho_resumo_json.parent.resolve()
        cmd = [
            "docker",
            "run",
            "--rm",
            "--cpus=2.0",
            "--add-host=host.docker.internal:host-gateway",
            "-v",
            f"{DIR_K6.resolve()}:/scripts:ro",
            "-v",
            f"{dir_brutos}:/saida",
            "-e",
            f"BASE_URL=http://host.docker.internal:{porta}",
            "-e",
            f"VUS={vus}",
            "-e",
            f"WARMUP_SEC={aquecimento_seg}",
            "-e",
            f"MEDICAO_SEC={medicao_seg}",
            "-e",
            f"SUMMARY_PATH=/saida/{nome_arquivo}",
            IMAGENS_FIXADAS["k6_docker"],
            "run",
            "/scripts/carga.js",
        ]
        res = executar_comando(cmd, cwd=RAIZ_LAB05, timeout=timeout_total, checar=False)

    if res.returncode != 0:
        raise RuntimeError(
            f"k6 finalizou com código {res.returncode}.\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )

    if not caminho_resumo_json.exists():
        raise FileNotFoundError(f"Arquivo de sumário do k6 não foi gerado em {caminho_resumo_json}.")

    return json.loads(caminho_resumo_json.read_text(encoding="utf-8"))


def extrair_linhas_csv(
    execucao: ExecucaoPlano,
    resumo_k6: dict[str, Any],
    mem_media_mb: float,
    mem_pico_mb: float,
    timestamp_inicio: str,
    timestamp_fim: str,
) -> list[dict[str, Any]]:
    """Converte o JSON exportado pelo handleSummary do k6 em linhas prontas para o CSV."""
    medicao = resumo_k6.get("medicao") or {}
    bloco_geral = medicao.get("geral") or {}
    blocos_endpoints = medicao.get("endpoints") or {}

    mapa_blocos: dict[str, dict[str, Any]] = {"geral": bloco_geral}
    for ep in ENDPOINTS_ORDEM:
        if ep != "geral":
            mapa_blocos[ep] = blocos_endpoints.get(ep) or {}

    linhas: list[dict[str, Any]] = []
    for ep in ENDPOINTS_ORDEM:
        b = mapa_blocos[ep]
        linhas.append(
            {
                "execucao_id": execucao.execucao_id,
                "ordem": execucao.ordem,
                "tratamento": execucao.tratamento,
                "php_version": execucao.php_version,
                "mitigacao": execucao.mitigacao,
                "repeticao": execucao.repeticao,
                "endpoint": ep,
                "rps": b.get("rps", 0.0),
                "p50_ms": b.get("p50_ms", 0.0),
                "p95_ms": b.get("p95_ms", 0.0),
                "p99_ms": b.get("p99_ms", 0.0),
                "taxa_erro": b.get("taxa_erro", 0.0),
                "mem_php_media_mb": mem_media_mb,
                "mem_php_pico_mb": mem_pico_mb,
                "timestamp_inicio": timestamp_inicio,
                "timestamp_fim": timestamp_fim,
            }
        )
    return linhas


def gravar_linhas_csv(caminho_csv: Path, linhas: list[dict[str, Any]]) -> None:
    """Grava (anexa) linhas no CSV consolidado, escrevendo cabeçalho se o arquivo não existir."""
    caminho_csv.parent.mkdir(parents=True, exist_ok=True)
    arquivo_novo = not caminho_csv.exists() or caminho_csv.stat().st_size == 0
    with caminho_csv.open("a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUNAS_CSV)
        if arquivo_novo:
            escritor.writeheader()
        escritor.writerows(linhas)


def executar_uma_rodada(
    execucao: ExecucaoPlano,
    total_execucoes: int,
    dir_brutos: Path,
    caminho_csv: Path,
    vus: int,
    aquecimento_seg: int,
    medicao_seg: int,
    intervalo_mem_seg: float,
    porta: int,
    modo_k6: str,
    logger: logging.Logger,
) -> bool:
    """Executa o ciclo completo de uma repetição: reinício -> saúde -> k6 + memória -> CSV."""
    prefixo = f"[{execucao.ordem}/{total_execucoes}] {execucao.tratamento} rep {execucao.repeticao}"
    logger.info(
        "%s — iniciando (PHP %s, mitigacao=%d, id=%s)",
        prefixo,
        execucao.php_version,
        execucao.mitigacao,
        execucao.execucao_id,
    )

    env = montar_env_compose(execucao.php_version, execucao.mitigacao, porta)
    ts_inicio = datetime.now(timezone.utc).isoformat()

    try:
        logger.info("%s — derrubando ambiente anterior (down -v)...", prefixo)
        derrubar_ambiente(env)

        logger.info("%s — subindo contêineres (up -d --build)...", prefixo)
        subir_ambiente(env)

        logger.info("%s — aguardando healthchecks e setup do WordPress...", prefixo)
        php_container_id = aguardar_ambiente_pronto(execucao, env, porta, logger)

        caminho_json = dir_brutos / f"{execucao.execucao_id}.json"
        monitor = MonitorMemoriaPhpFpm(
            container_id=php_container_id,
            atraso_inicial_seg=float(aquecimento_seg),
            intervalo_seg=intervalo_mem_seg,
        )

        logger.info(
            "%s — executando k6 (%s): VUs=%d, aquecimento=%ds, medição=%ds...",
            prefixo,
            modo_k6,
            vus,
            aquecimento_seg,
            medicao_seg,
        )
        monitor.iniciar()
        try:
            resumo_k6 = executar_k6(
                caminho_resumo_json=caminho_json,
                vus=vus,
                aquecimento_seg=aquecimento_seg,
                medicao_seg=medicao_seg,
                porta=porta,
                modo_k6=modo_k6,
            )
        finally:
            mem_media_mb, mem_pico_mb, n_amostras = monitor.parar_e_resumir()

        ts_fim = datetime.now(timezone.utc).isoformat()
        linhas = extrair_linhas_csv(
            execucao=execucao,
            resumo_k6=resumo_k6,
            mem_media_mb=mem_media_mb,
            mem_pico_mb=mem_pico_mb,
            timestamp_inicio=ts_inicio,
            timestamp_fim=ts_fim,
        )
        gravar_linhas_csv(caminho_csv, linhas)

        geral = (resumo_k6.get("medicao") or {}).get("geral") or {}
        logger.info(
            "%s — concluído! rps=%.2f | p50=%.1fms | p95=%.1fms | p99=%.1fms | erro=%.4f | mem_php=%.1fMB (pico %.1fMB, %d amostras)",
            prefixo,
            float(geral.get("rps", 0.0)),
            float(geral.get("p50_ms", 0.0)),
            float(geral.get("p95_ms", 0.0)),
            float(geral.get("p99_ms", 0.0)),
            float(geral.get("taxa_erro", 0.0)),
            mem_media_mb,
            mem_pico_mb,
            n_amostras,
        )
        return True
    except Exception as exc:
        logger.exception("%s — FALHA na execução (%s): %s", prefixo, execucao.execucao_id, exc)
        return False


def construir_parser() -> argparse.ArgumentParser:
    """Define os argumentos de linha de comando do orquestrador."""
    parser = argparse.ArgumentParser(
        description="Orquestrador de benchmarks do LAB05 (experimento fatorial 2x2 PHP 8.4.26 vs 8.4.27)."
    )
    parser.add_argument(
        "--piloto",
        action="store_true",
        help="Executa o modo piloto (2 repetições por tratamento = 8 execuções).",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help="Número de repetições por tratamento (útil para S02 ou smoke test). Sobrepõe --piloto se informado.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("dados/piloto"),
        help="Diretório de saída para CSV, brutos_k6/ e ambiente_maquina.json (padrão: dados/piloto/).",
    )
    parser.add_argument(
        "--semente",
        type=int,
        default=42,
        help="Semente fixa para embaralhamento reprodutível da ordem (padrão: 42).",
    )
    parser.add_argument(
        "--tratamentos",
        type=str,
        default="T1,T2,T3,T4",
        help="Lista separada por vírgula dos tratamentos a executar (padrão: T1,T2,T3,T4).",
    )
    parser.add_argument(
        "--vus",
        type=int,
        default=10,
        help="Número de usuários virtuais (VUs) no k6 (padrão: 10).",
    )
    parser.add_argument(
        "--aquecimento",
        type=int,
        default=30,
        help="Duração da fase de aquecimento em segundos (padrão: 30).",
    )
    parser.add_argument(
        "--medicao",
        type=int,
        default=60,
        help="Duração da fase de medição em segundos (padrão: 60).",
    )
    parser.add_argument(
        "--intervalo-mem",
        type=float,
        default=1.5,
        help="Intervalo de amostragem da memória do PHP-FPM em segundos (padrão: 1.5).",
    )
    parser.add_argument(
        "--porta",
        type=int,
        default=8080,
        help="Porta local exposta pelo Nginx (padrão: 8080).",
    )
    parser.add_argument(
        "--k6-modo",
        choices=["auto", "local", "docker"],
        default="auto",
        help="Como executar o k6: auto (usa local se existir, senão Docker), local ou docker (padrão: auto).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas gera o plano embaralhado e grava ambiente_maquina.json, sem subir contêineres.",
    )
    parser.add_argument(
        "--manter-ativo",
        action="store_true",
        help="Mantém os contêineres da última execução de pé ao finalizar o script.",
    )
    return parser


def resolver_dir_saida(caminho: Path) -> Path:
    """Resolve caminhos relativos tomando LAB05/ como base."""
    return caminho if caminho.is_absolute() else (RAIZ_LAB05 / caminho)


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)

    if args.k is not None:
        if args.k < 1:
            parser.error("--k deve ser >= 1.")
        repeticoes = args.k
    elif args.piloto:
        repeticoes = 2
    else:
        parser.error("Informe --piloto (2 repetições/tratamento) ou --k N.")

    tratamentos = [t.strip().upper() for t in args.tratamentos.split(",") if t.strip()]
    dir_saida = resolver_dir_saida(args.saida)
    dir_brutos = dir_saida / "brutos_k6"
    caminho_csv = dir_saida / "piloto.csv"
    caminho_ambiente = dir_saida / "ambiente_maquina.json"
    caminho_log = dir_saida / "execucao.log"

    dir_saida.mkdir(parents=True, exist_ok=True)
    dir_brutos.mkdir(parents=True, exist_ok=True)
    logger = configurar_logger(caminho_log)

    modo_k6 = detectar_modo_k6(args.k6_modo)
    plano = gerar_plano_execucoes(tratamentos, repeticoes, args.semente)

    logger.info("============================================================")
    logger.info("LAB05 — Orquestrador de Benchmarks")
    logger.info("Tratamentos: %s | Repetições (k): %d | Total: %d execuções", ",".join(tratamentos), repeticoes, len(plano))
    logger.info("Semente: %d | VUs: %d | Aquecimento: %ds | Medição: %ds | k6: %s", args.semente, args.vus, args.aquecimento, args.medicao, modo_k6)
    logger.info("Saída: %s", dir_saida)
    logger.info("============================================================")

    ambiente = coletar_ambiente_maquina(caminho_ambiente, modo_k6)
    logger.info(
        "Ambiente registrado em %s (CPU: %s | RAM: %s GB | Docker: %s)",
        caminho_ambiente,
        ambiente["cpu"]["modelo"],
        ambiente["ram_total_gb"],
        ambiente["ferramentas"]["docker"],
    )

    logger.info("Ordem embaralhada das execuções:")
    for item in plano:
        logger.info("  [%d/%d] %s -> %s rep %d (PHP %s, mitigacao=%d)", item.ordem, len(plano), item.execucao_id, item.tratamento, item.repeticao, item.php_version, item.mitigacao)

    if args.dry_run:
        logger.info("Modo --dry-run finalizado sem subir contêineres.")
        return 0

    # Verifica rapidamente se o daemon do Docker está acessível antes de iniciar a fila
    teste_docker = executar_comando(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=15, checar=False)
    if teste_docker.returncode != 0:
        logger.error("Docker Desktop não está respondendo. Inicie o Docker Desktop e tente novamente.\n%s", teste_docker.stderr.strip())
        return 2

    sucessos = 0
    falhas = 0
    for item in plano:
        ok = executar_uma_rodada(
            execucao=item,
            total_execucoes=len(plano),
            dir_brutos=dir_brutos,
            caminho_csv=caminho_csv,
            vus=args.vus,
            aquecimento_seg=args.aquecimento,
            medicao_seg=args.medicao,
            intervalo_mem_seg=args.intervalo_mem,
            porta=args.porta,
            modo_k6=modo_k6,
            logger=logger,
        )
        if ok:
            sucessos += 1
        else:
            falhas += 1

    if not args.manter_ativo and plano:
        try:
            ultimo = plano[-1]
            logger.info("Encerrando contêineres ao final da bateria (down -v)...")
            derrubar_ambiente(montar_env_compose(ultimo.php_version, ultimo.mitigacao, args.porta))
        except Exception as exc:
            logger.warning("Não foi possível derrubar o ambiente ao final: %s", exc)

    logger.info("============================================================")
    logger.info("Bateria finalizada: %d sucesso(s), %d falha(s).", sucessos, falhas)
    logger.info("CSV consolidado : %s", caminho_csv)
    logger.info("Brutos k6       : %s", dir_brutos)
    logger.info("Ambiente máquina: %s", caminho_ambiente)
    logger.info("============================================================")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
