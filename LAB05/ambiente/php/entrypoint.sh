#!/bin/sh
# Entrypoint do contêiner PHP-FPM do LAB05.
# Controla a mitigação (session.upload_progress.enabled) via variável de ambiente MITIGACAO:
#   MITIGACAO=0 -> mitigação desligada -> session.upload_progress.enabled = On  (padrão do PHP)
#   MITIGACAO=1 -> mitigação ligada    -> session.upload_progress.enabled = Off (mitigação recomendada)

set -eu

MITIGACAO="${MITIGACAO:-0}"
ARQUIVO_INI="/usr/local/etc/php/conf.d/99-lab05-mitigacao.ini"

# Garante diretório de sessões gravável pelo usuário www-data
mkdir -p /tmp/php-sessions
chown www-data:www-data /tmp/php-sessions
chmod 1733 /tmp/php-sessions

case "$MITIGACAO" in
  1|true|TRUE|on|ON)
    VALOR_DIRETIVA="Off"
    ;;
  0|false|FALSE|off|OFF)
    VALOR_DIRETIVA="On"
    ;;
  *)
    echo "[LAB05][ERRO] Valor inválido para MITIGACAO='$MITIGACAO'. Use 0 (desligada) ou 1 (ligada)." >&2
    exit 1
    ;;
esac

cat > "$ARQUIVO_INI" <<EOF
; Gerado automaticamente pelo entrypoint do LAB05 (MITIGACAO=${MITIGACAO})
session.upload_progress.enabled = ${VALOR_DIRETIVA}
EOF

echo "============================================================"
echo "[LAB05] PHP_VERSION efetiva : $(php -r 'echo PHP_VERSION;')"
echo "[LAB05] MITIGACAO           : ${MITIGACAO} (esperado: ${VALOR_DIRETIVA})"
echo "[LAB05] Confirmação php -i  :"
php -i | grep -i "session.upload_progress.enabled"
echo "============================================================"

exec "$@"
