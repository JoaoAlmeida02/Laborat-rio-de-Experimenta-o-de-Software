# Imagem base Python slim oficial (versão estável e enxuta)
FROM python:3.12-slim

# Evita criação de arquivos .pyc e força stdout não-bufferizado para logs imediatos
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalação prévia de dependências para otimização de cache de camadas Docker
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte do projeto
COPY . .

# Ponto de entrada padrão: executa o pipeline completo DORA
# Permite passar argumentos adicionais ao final do comando (ex: --dry-run, --etapa selecao)
ENTRYPOINT ["python", "-m", "pipeline"]
CMD []
