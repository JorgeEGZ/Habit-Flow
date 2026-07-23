#!/bin/sh
set -eu

. "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/common.sh"

require_command docker
require_var CERTBOT_WWW_DIR
require_safe_habitflow_dir "$CERTBOT_WWW_DIR"

echo "Renewing Let's Encrypt certificates when due."
compose run --rm --no-deps certbot renew --webroot -w /var/www/certbot --quiet
compose exec -T web nginx -s reload
echo "Certificate renewal check completed."
