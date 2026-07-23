#!/bin/sh
set -eu

. "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/common.sh"

require_command docker
require_command getent
require_command awk
require_command grep
require_var DOMAIN
require_var LETSENCRYPT_EMAIL
require_var PUBLIC_IPV4
require_var CERTBOT_CONF_DIR
require_var CERTBOT_WWW_DIR

case "$DOMAIN" in
  *[!A-Za-z0-9.-]* | '' | .* | *..*) fail "DOMAIN is invalid" ;;
esac
case "$LETSENCRYPT_EMAIL" in
  *@*.*) ;;
  *) fail "LETSENCRYPT_EMAIL is invalid" ;;
esac
case "${CERTBOT_STAGING:-false}" in
  true|false) ;;
  *) fail "CERTBOT_STAGING must be true or false" ;;
esac

require_safe_habitflow_dir "$CERTBOT_CONF_DIR"
require_safe_habitflow_dir "$CERTBOT_WWW_DIR"
mkdir -p "$CERTBOT_CONF_DIR" "$CERTBOT_WWW_DIR"

certificate_path="$CERTBOT_CONF_DIR/live/$DOMAIN/fullchain.pem"
if [ -f "$certificate_path" ]; then
  echo "A certificate already exists for $DOMAIN. No certificate was replaced."
  exit 0
fi

if ! getent ahostsv4 "$DOMAIN" | awk '{print $1}' | grep -Fqx "$PUBLIC_IPV4"; then
  fail "DNS for $DOMAIN does not resolve to PUBLIC_IPV4=$PUBLIC_IPV4"
fi

echo "Starting Nginx in HTTP challenge mode."
compose build web
compose up -d postgres backend web
compose exec -T web nginx -t

set -- certonly --webroot -w /var/www/certbot \
  --email "$LETSENCRYPT_EMAIL" --agree-tos --no-eff-email -d "$DOMAIN"
if [ "${CERTBOT_STAGING:-false}" = true ]; then
  set -- "$@" --staging
fi

echo "Requesting the initial Let's Encrypt certificate for $DOMAIN."
compose run --rm --no-deps certbot "$@"

compose up -d --force-recreate web
compose exec -T web nginx -t
echo "Certificate issued. Nginx now uses the HTTPS configuration."
