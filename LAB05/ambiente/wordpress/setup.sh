#!/bin/sh
# Provisionamento automático e idempotente do WordPress via WP-CLI (LAB05).
# Executado pelo serviço "setup" no docker-compose.yml.

set -eu

WP_PATH="/var/www/html"
WP_URL="${WP_URL:-http://localhost:8080}"
WP_TITLE="${WP_TITLE:-LAB05 WordPress Benchmark}"
WP_ADMIN_USER="${WP_ADMIN_USER:-admin}"
WP_ADMIN_PASSWORD="${WP_ADMIN_PASSWORD:-admin_lab05}"
WP_ADMIN_EMAIL="${WP_ADMIN_EMAIL:-admin@lab05.local}"
DB_HOST="${WORDPRESS_DB_HOST:-mariadb}"
DB_NAME="${WORDPRESS_DB_NAME:-wordpress}"
DB_USER="${WORDPRESS_DB_USER:-wpuser}"
DB_PASS="${WORDPRESS_DB_PASSWORD:-wppass_lab05}"
TOTAL_POSTS="${LAB05_TOTAL_POSTS:-50}"

echo "[LAB05-SETUP] Aguardando banco de dados em ${DB_HOST}..."
DB_PING_BIN="mariadb-admin"
if ! command -v "${DB_PING_BIN}" >/dev/null 2>&1; then
  DB_PING_BIN="mysqladmin"
fi
TENTATIVAS=0
until "${DB_PING_BIN}" ping -h"${DB_HOST}" -u"${DB_USER}" -p"${DB_PASS}" --silent 2>/dev/null; do
  TENTATIVAS=$((TENTATIVAS + 1))
  if [ "$TENTATIVAS" -ge 60 ]; then
    echo "[LAB05-SETUP][ERRO] MariaDB não respondeu a tempo." >&2
    exit 1
  fi
  sleep 1
done
echo "[LAB05-SETUP] MariaDB disponível."

# Cria wp-config.php de forma idempotente
if [ ! -f "${WP_PATH}/wp-config.php" ]; then
  echo "[LAB05-SETUP] Gerando wp-config.php..."
  wp config create \
    --allow-root \
    --path="${WP_PATH}" \
    --dbname="${DB_NAME}" \
    --dbuser="${DB_USER}" \
    --dbpass="${DB_PASS}" \
    --dbhost="${DB_HOST}" \
    --skip-check \
    --force
fi

# Instala o WordPress apenas se ainda não estiver instalado
if ! wp core is-installed --allow-root --path="${WP_PATH}" 2>/dev/null; then
  echo "[LAB05-SETUP] Instalando WordPress em ${WP_URL}..."
  wp core install \
    --allow-root \
    --path="${WP_PATH}" \
    --url="${WP_URL}" \
    --title="${WP_TITLE}" \
    --admin_user="${WP_ADMIN_USER}" \
    --admin_password="${WP_ADMIN_PASSWORD}" \
    --admin_email="${WP_ADMIN_EMAIL}" \
    --skip-email

  # Configura permalinks amigáveis para habilitar /wp-json/wp/v2/posts
  wp rewrite structure '/%postname%/' --hard --allow-root --path="${WP_PATH}"
  wp rewrite flush --hard --allow-root --path="${WP_PATH}"
else
  echo "[LAB05-SETUP] WordPress já instalado (idempotente)."
fi

# Garante exatamente TOTAL_POSTS posts publicados com conteúdo determinístico
ATUAIS=$(wp post list --post_type=post --post_status=publish --format=count --allow-root --path="${WP_PATH}")
echo "[LAB05-SETUP] Posts publicados atualmente: ${ATUAIS} (alvo: ${TOTAL_POSTS})."

if [ "${ATUAIS}" -lt "${TOTAL_POSTS}" ]; then
  FALTANTES=$((TOTAL_POSTS - ATUAIS))
  echo "[LAB05-SETUP] Criando ${FALTANTES} posts determinísticos para benchmark..."
  IDX=$((ATUAIS + 1))
  while [ "${IDX}" -le "${TOTAL_POSTS}" ]; do
    TITULO=$(printf "Artigo de Benchmark LAB05 #%02d" "${IDX}")
    CONTEUDO="Conteúdo determinístico de teste número ${IDX} para o experimento controlado do LAB05 (PUC Minas). Este texto mantém tamanho estável entre todas as repetições para garantir comparabilidade entre os tratamentos T1, T2, T3 e T4 na página inicial e na API REST do WordPress."
    wp post create \
      --allow-root \
      --path="${WP_PATH}" \
      --post_type=post \
      --post_status=publish \
      --post_title="${TITULO}" \
      --post_content="${CONTEUDO}" \
      --porcelain >/dev/null
    IDX=$((IDX + 1))
  done
  echo "[LAB05-SETUP] Criação de posts concluída."
fi

# Ajusta permissões para o usuário do PHP-FPM
chown -R www-data:www-data "${WP_PATH}/wp-content" "${WP_PATH}/wp-config.php"
touch "${WP_PATH}/.lab05-setup-ok"

FINAL_COUNT=$(wp post list --post_type=post --post_status=publish --format=count --allow-root --path="${WP_PATH}")
echo "[LAB05-SETUP] Pronto! Total de posts publicados: ${FINAL_COUNT}."
